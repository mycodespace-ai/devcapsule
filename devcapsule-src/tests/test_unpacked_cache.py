"""Cache recovery and concurrent reuse, with small files and no Docker."""

from concurrent.futures import ThreadPoolExecutor
import fcntl
import json
from pathlib import Path
import shutil
from threading import Event, current_thread

import pytest

from devcapsule.materialization import UNPACKED_MARKER, unpacked_tree

pytestmark = pytest.mark.legacy


DIGEST = "a" * 64


def unpack_fixture(destination: Path) -> Path:
    root = destination / "tool"
    root.mkdir(parents=True)
    (root / "binary").write_bytes(b"verified fixture")
    return root


def test_concurrent_unpack_preserves_the_first_callers_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pause one extractor until a second caller reaches the same cache key.

    Observe real flock attempts without replacing locking. The old code has
    no lock and reaches the second extractor instead, deleting the first
    caller's in-progress directory because both callers have the same PID.
    Events establish the ordering; no scheduling sleeps are used.
    """
    first_extracting = Event()
    second_at_cache = Event()
    calls: list[Path] = []
    real_flock = fcntl.flock

    def observe_lock(fd: int, operation: int) -> None:
        if current_thread().name == "second" and operation == fcntl.LOCK_EX:
            second_at_cache.set()
        real_flock(fd, operation)

    monkeypatch.setattr(fcntl, "flock", observe_lock)

    def extract(destination: Path) -> Path:
        calls.append(destination)
        root = unpack_fixture(destination)
        if current_thread().name == "first":
            (root / "first-owner").write_text("must survive")
            first_extracting.set()
            assert second_at_cache.wait(5), "second caller never reached the cache"
            assert (root / "first-owner").read_text() == "must survive"
        else:
            second_at_cache.set()
        return root

    def run(name: str) -> Path:
        current_thread().name = name
        return unpacked_tree(tmp_path, DIGEST, extract)

    with ThreadPoolExecutor(max_workers=2) as workers:
        first = workers.submit(run, "first")
        assert first_extracting.wait(5), "first caller never started extracting"
        second = workers.submit(run, "second")
        first_root, second_root = first.result(timeout=10), second.result(timeout=10)
    assert first_root == second_root
    assert (first_root / "first-owner").read_text() == "must survive"
    assert len(calls) == 1


@pytest.mark.parametrize("damage", [
    "absolute-root", "escaping-symlink", "missing-root", "wrong-digest", "wrong-schema",
    "parent-root", "invalid-json", "non-object", "non-string-root",
])
def test_invalid_completion_record_is_rebuilt(tmp_path: Path, damage: str) -> None:
    home = tmp_path / "unpacked" / DIGEST
    root = unpacked_tree(tmp_path, DIGEST, unpack_fixture)
    marker = home / UNPACKED_MARKER
    record = json.loads(marker.read_text())
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "binary").write_bytes(b"unrelated content")
    if damage == "absolute-root":
        record["root"] = str(outside)
    elif damage == "escaping-symlink":
        shutil.rmtree(root)
        root.symlink_to(outside, target_is_directory=True)
    elif damage == "missing-root":
        shutil.rmtree(root)
    elif damage == "wrong-digest":
        record["sha256"] = "b" * 64
    elif damage == "wrong-schema":
        record["schema_version"] = 99
    elif damage == "parent-root":
        record["root"] = "../../outside"
    elif damage == "non-string-root":
        record["root"] = 42
    marker.write_text("{" if damage == "invalid-json" else
                      "[]" if damage == "non-object" else json.dumps(record))
    calls: list[Path] = []

    def extract(destination: Path) -> Path:
        calls.append(destination)
        return unpack_fixture(destination)

    rebuilt = unpacked_tree(tmp_path, DIGEST, extract)
    assert len(calls) == 1
    assert rebuilt.is_relative_to(home) and not rebuilt.is_symlink()
    assert (rebuilt / "binary").read_bytes() == b"verified fixture"
    assert (outside / "binary").read_bytes() == b"unrelated content"


def test_failed_unpack_cleans_partial_and_can_retry(tmp_path: Path) -> None:
    def fail(destination: Path) -> Path:
        unpack_fixture(destination)
        raise OSError("interrupted extraction")

    with pytest.raises(OSError, match="interrupted extraction"):
        unpacked_tree(tmp_path, DIGEST, fail)
    assert not list((tmp_path / "unpacked").iterdir())
    root = unpacked_tree(tmp_path, DIGEST, unpack_fixture)
    assert (root / "binary").read_bytes() == b"verified fixture"


def test_changed_digest_gets_a_different_tree(tmp_path: Path) -> None:
    original = unpacked_tree(tmp_path, DIGEST, unpack_fixture)
    replacement = unpacked_tree(tmp_path, "b" * 64, unpack_fixture)
    assert original != replacement
    assert (original / "binary").read_bytes() == (replacement / "binary").read_bytes()


def test_abandoned_staging_tree_is_recovered(tmp_path: Path) -> None:
    partial = tmp_path / "unpacked" / f"{DIGEST}.partial"
    partial.mkdir(parents=True)
    (partial / "abandoned").write_text("previous process died here")
    root = unpacked_tree(tmp_path, DIGEST, unpack_fixture)
    assert (root / "binary").read_bytes() == b"verified fixture"
    assert not partial.exists()
    assert not (root.parent / "abandoned").exists()


@pytest.mark.parametrize("entry", ["file", "symlink"])
def test_replaced_cache_entry_is_recovered_without_touching_target(tmp_path: Path, entry: str) -> None:
    home = tmp_path / "unpacked" / DIGEST
    home.parent.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "keep").write_text("unrelated")
    if entry == "file":
        home.write_text("incomplete")
    else:
        home.symlink_to(outside, target_is_directory=True)
    root = unpacked_tree(tmp_path, DIGEST, unpack_fixture)
    assert not home.is_symlink()
    assert (root / "binary").read_bytes() == b"verified fixture"
    assert (outside / "keep").read_text() == "unrelated"


def test_extractor_must_return_an_existing_contained_directory(tmp_path: Path) -> None:
    from devcapsule.compat import CliError

    def invalid(destination: Path) -> Path:
        destination.mkdir()
        return destination / "missing"

    with pytest.raises(CliError, match="directory inside its destination"):
        unpacked_tree(tmp_path, DIGEST, invalid)
    assert not list((tmp_path / "unpacked").iterdir())


def test_rename_failure_is_reported_and_staging_is_cleaned(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_rename(source: Path, target: Path) -> None:
        raise OSError("publication failed")

    monkeypatch.setattr(Path, "rename", fail_rename)
    with pytest.raises(OSError, match="publication failed"):
        unpacked_tree(tmp_path, DIGEST, unpack_fixture)
    assert not list((tmp_path / "unpacked").iterdir())
