"""The Files page, the directory tree listing, and the hardened raw file route."""

from __future__ import annotations

import errno
import os
from pathlib import Path

import pytest

from devcapsule_webconsole.security import PathRefused, list_project_directory, open_project_file


def test_list_project_directory_lists_root_including_dotfiles_git_and_links(project: Path) -> None:
    """Listing the project root includes dotfiles, .git, directories, files and symbolic links without following links."""
    (project / ".git").mkdir()
    (project / ".env").write_text("KEY=1\n", encoding="utf-8")

    listing = list_project_directory(project)

    assert listing["path"] == ""
    by_name = {entry["name"]: entry for entry in listing["entries"]}
    assert [entry["name"] for entry in listing["entries"]] == [
        ".devcapsule",
        ".git",
        "docs",
        ".env",
        "escape.md",
        "image.bin",
    ]
    assert by_name[".git"]["kind"] == "directory"
    assert by_name[".git"]["size"] is None
    assert by_name[".env"] == {
        "name": ".env",
        "kind": "file",
        "size": 6,
        "modified": by_name[".env"]["modified"],
    }
    assert by_name["escape.md"]["kind"] == "link"
    assert by_name["escape.md"]["size"] is None


def test_list_project_directory_lists_nested_directory_with_sort_and_kinds(project: Path) -> None:
    """A nested directory listing sorts directories before other entries by case-folded name and classifies directories, files, links and FIFOs."""
    nested = project / "docs" / "nested"
    nested.mkdir()
    (nested / "Zeta").mkdir()
    (nested / "alpha").mkdir()
    beta = nested / "Beta.txt"
    beta.write_bytes(b"hello")
    os.utime(beta, (1794132672, 1794132672))
    (nested / "apple.txt").write_bytes(b"ab")
    (nested / "arrow").symlink_to("Beta.txt")
    (nested / "broken").symlink_to("does-not-exist")
    os.mkfifo(nested / "pipe")

    listing = list_project_directory(project, "docs/nested")

    assert listing["path"] == "docs/nested"
    assert [(entry["name"], entry["kind"], entry["size"]) for entry in listing["entries"]] == [
        ("alpha", "directory", None),
        ("Zeta", "directory", None),
        ("apple.txt", "file", 2),
        ("arrow", "link", None),
        ("Beta.txt", "file", 5),
        ("broken", "link", None),
        ("pipe", "other", None),
    ]
    by_name = {entry["name"]: entry for entry in listing["entries"]}
    assert by_name["Beta.txt"]["modified"] == "2026-11-08T10:11:12Z"


def test_list_project_directory_skips_an_entry_removed_during_scan(
    project: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An entry unlinked between readdir and lstat is skipped without failing the directory listing."""
    vanished = project / "docs" / "transient.tmp"
    vanished.write_text("ephemeral", encoding="utf-8")
    real_scandir = os.scandir

    class VanishingScan:
        def __init__(self, target_fd: int) -> None:
            self._inner = real_scandir(target_fd)

        def __enter__(self) -> list[object]:
            entries = list(self._inner.__enter__())
            vanished.unlink()
            return entries

        def __exit__(self, *exc: object) -> bool | None:
            return self._inner.__exit__(*exc)

    monkeypatch.setattr(os, "scandir", VanishingScan)

    listing = list_project_directory(project, "docs")

    assert [entry["name"] for entry in listing["entries"]] == ["guide.md"]


@pytest.mark.parametrize(
    "requested",
    ["../outside", "docs/../../outside", "/etc", "escape-dir", "docs/\x00sub"],
)
def test_list_project_directory_refuses_paths_that_escape_the_project(project: Path, requested: str) -> None:
    """Paths with parent traversal, absolute roots, NUL bytes or symbolic links leaving the project raise PathRefused."""
    outside_dir = project.parent / "outside-dir"
    outside_dir.mkdir(exist_ok=True)
    (project / "escape-dir").symlink_to(outside_dir, target_is_directory=True)

    with pytest.raises(PathRefused):
        list_project_directory(project, requested)


@pytest.mark.parametrize(
    ("requested", "expected_error"),
    [
        ("docs/missing", FileNotFoundError),
        ("docs/guide.md", NotADirectoryError),
        ("docs/guide.md/child", FileNotFoundError),
    ],
)
def test_list_project_directory_rejects_missing_or_file_paths(
    project: Path, requested: str, expected_error: type[OSError],
) -> None:
    """Listing a missing path raises FileNotFoundError and listing a regular file raises NotADirectoryError."""
    with pytest.raises(expected_error):
        list_project_directory(project, requested)


@pytest.mark.parametrize("swap_parent", [False, True])
def test_list_project_directory_refuses_a_directory_swapped_for_a_link_after_confinement(
    project: Path, monkeypatch: pytest.MonkeyPatch, swap_parent: bool,
) -> None:
    """Replacing a confined directory with an escaping symbolic link before descriptor open raises PathRefused."""
    outside = project.parent / "outside-tree"
    outside.mkdir()
    (outside / "secret.txt").write_text("outside secret", encoding="utf-8")
    target = project / "docs" / "sub"
    target.mkdir()
    resolve = Path.resolve
    swapped = False

    def resolve_then_swap(path: Path, *args: object, **kwargs: object) -> Path:
        nonlocal swapped
        resolved = resolve(path, *args, **kwargs)  # type: ignore[arg-type]
        if path == target and not swapped:
            swapped = True
            victim = target.parent if swap_parent else target
            victim.rename(project / "displaced")
            victim.symlink_to(outside, target_is_directory=True)
        return resolved

    monkeypatch.setattr(Path, "resolve", resolve_then_swap)

    with pytest.raises(PathRefused):
        list_project_directory(project, "docs/sub")
    assert swapped


def test_open_project_file_streams_bytes_and_closes_its_descriptor(project: Path) -> None:
    """open_project_file yields a seekable binary stream with the file's byte length and closes the descriptor on exit."""
    payload = b"0123456789abcdef" * 4
    (project / "docs" / "sample.bin").write_bytes(payload)

    with open_project_file(project, "docs/sample.bin") as (stream, size):
        descriptor = stream.fileno()
        assert size == len(payload)
        stream.seek(10)
        chunk = stream.read(12)

    assert chunk == payload[10:22]
    with pytest.raises(OSError) as closed:
        os.fstat(descriptor)
    assert closed.value.errno == errno.EBADF
