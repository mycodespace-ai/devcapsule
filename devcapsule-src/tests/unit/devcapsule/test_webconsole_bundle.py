"""Unit tests of ``devcapsule/webconsole_bundle.py``: deterministic bundling and confined extraction."""

from __future__ import annotations

import os
from pathlib import Path
import stat
import warnings
from zipfile import ZIP_STORED, ZipFile, ZipInfo

import pytest

from devcapsule.webconsole_bundle import (
    BUNDLE_RESOURCE_NAME,
    PACKAGE_NAME,
    WebconsoleBundleError,
    build_webconsole_bundle,
    extract_webconsole_bundle,
    main,
)


def _sample_webconsole_package(root: Path) -> Path:
    package = root / PACKAGE_NAME
    (package / "static" / "vendor").mkdir(parents=True)
    (package / "__pycache__").mkdir()
    (package / "__init__.py").write_text('__version__ = "0.1.0"\n', encoding="utf-8")
    (package / "app.py").write_text("ROUTES = ('/files', '/filetree', '/api/project/tree')\n", encoding="utf-8")
    (package / "static" / "files.html").write_text("<!doctype html><title>Files</title>\n", encoding="utf-8")
    (package / "static" / "vendor" / "viz.js").write_text("window.Viz = {};\n", encoding="utf-8")
    (package / "__pycache__" / "app.cpython-312.pyc").write_bytes(b"bytecode")
    (package / "stale.pyc").write_bytes(b"bytecode")
    return package


def _regular_file(name: str) -> ZipInfo:
    info = ZipInfo(name)
    info.external_attr = (stat.S_IFREG | 0o644) << 16
    return info


def _pex_with_bundle(pex_path: Path, bundle_bytes: bytes, *, count: int = 1) -> Path:
    with ZipFile(pex_path, "w") as archive:
        for index in range(count):
            prefix = f".deps/devcapsule-{index}.whl" if count > 1 else ".deps/devcapsule-0.3.1-py3-none-any.whl"
            archive.writestr(f"{prefix}/devcapsule/{BUNDLE_RESOURCE_NAME}", bundle_bytes)
    return pex_path


def test_build_webconsole_bundle_is_deterministic_and_skips_bytecode(tmp_path: Path) -> None:
    """Building a web console bundle twice across differing mtimes produces identical stored zip bytes without bytecode."""
    first_pkg = _sample_webconsole_package(tmp_path / "a")
    second_pkg = _sample_webconsole_package(tmp_path / "b")
    os.utime(first_pkg / "app.py", (1_700_000_000, 1_700_000_000))
    os.utime(second_pkg / "app.py", (1_800_000_000, 1_800_000_000))

    first_zip = build_webconsole_bundle(first_pkg, tmp_path / "out-a" / BUNDLE_RESOURCE_NAME)
    second_zip = build_webconsole_bundle(second_pkg, tmp_path / "out-b" / BUNDLE_RESOURCE_NAME)

    assert first_zip.read_bytes() == second_zip.read_bytes()
    with ZipFile(first_zip) as archive:
        assert archive.namelist() == [
            f"{PACKAGE_NAME}/__init__.py",
            f"{PACKAGE_NAME}/app.py",
            f"{PACKAGE_NAME}/static/files.html",
            f"{PACKAGE_NAME}/static/vendor/viz.js",
        ]
        assert all(info.compress_type == ZIP_STORED for info in archive.infolist())


@pytest.mark.parametrize(
    "defect", ["missing-dir", "wrong-name", "missing-init", "symlink", "symlinked-root", "fifo"]
)
def test_build_webconsole_bundle_refuses_invalid_package_tree(tmp_path: Path, defect: str) -> None:
    """Building a bundle refuses a missing package, a misnamed root, a missing __init__.py, a symlink inside or at the root, or a non-regular file."""
    if defect == "missing-dir":
        package = tmp_path / PACKAGE_NAME
    elif defect == "wrong-name":
        package = tmp_path / "wrong_name"
        package.mkdir()
        (package / "__init__.py").write_text("", encoding="utf-8")
    elif defect == "missing-init":
        package = tmp_path / PACKAGE_NAME
        package.mkdir()
    elif defect == "symlink":
        package = _sample_webconsole_package(tmp_path)
        (package / "escape.py").symlink_to(tmp_path)
    elif defect == "symlinked-root":
        real = _sample_webconsole_package(tmp_path / "real")
        package = tmp_path / PACKAGE_NAME
        package.symlink_to(real, target_is_directory=True)
    else:
        package = _sample_webconsole_package(tmp_path)
        os.mkfifo(package / "static" / "pipe.css")

    with pytest.raises(WebconsoleBundleError):
        build_webconsole_bundle(package, tmp_path / BUNDLE_RESOURCE_NAME)


def test_extract_webconsole_bundle_unpacks_regular_read_only_package_tree(tmp_path: Path) -> None:
    """Extracting a PEX's web console bundle recreates the package hierarchy with 0755 directories and 0644 files."""
    package = _sample_webconsole_package(tmp_path / "src")
    bundle = build_webconsole_bundle(package, tmp_path / BUNDLE_RESOURCE_NAME)
    pex = _pex_with_bundle(tmp_path / "devcapsule.pex", bundle.read_bytes())

    extracted = extract_webconsole_bundle(pex, tmp_path / "staged")

    assert (extracted / PACKAGE_NAME / "__init__.py").read_text(encoding="utf-8") == '__version__ = "0.1.0"\n'
    assert (extracted / PACKAGE_NAME / "static" / "files.html").read_text(encoding="utf-8") == (
        "<!doctype html><title>Files</title>\n"
    )
    assert (extracted / PACKAGE_NAME / "static" / "vendor" / "viz.js").is_file()
    assert (extracted / PACKAGE_NAME / "static").stat().st_mode & 0o777 == 0o755
    assert (extracted / PACKAGE_NAME / "app.py").stat().st_mode & 0o777 == 0o644


@pytest.mark.parametrize(
    "member_name,unix_mode,refusal",
    [
        ("../escape.py", stat.S_IFREG | 0o644, "must live beneath"),
        (f"{PACKAGE_NAME}/../../escape.py", stat.S_IFREG | 0o644, "invalid bundled web console path"),
        (f"/{PACKAGE_NAME}/__init__.py", stat.S_IFREG | 0o644, "invalid bundled web console path"),
        (f"{PACKAGE_NAME}\\__init__.py", stat.S_IFREG | 0o644, "invalid bundled web console path"),
        ("other_pkg/__init__.py", stat.S_IFREG | 0o644, "must live beneath"),
        (PACKAGE_NAME, stat.S_IFREG | 0o644, "must live beneath"),
        (f"{PACKAGE_NAME}//double.py", stat.S_IFREG | 0o644, "non-canonical"),
        (f"{PACKAGE_NAME}/./dot.py", stat.S_IFREG | 0o644, "non-canonical"),
        (f"{PACKAGE_NAME}/link.py", stat.S_IFLNK | 0o777, "is not a regular file"),
        (f"{PACKAGE_NAME}/static", stat.S_IFDIR | 0o755, "is not a regular file"),
        (f"{PACKAGE_NAME}/pipe.css", stat.S_IFIFO | 0o644, "is not a regular file"),
    ],
)
def test_extract_webconsole_bundle_refuses_unsafe_archive_entries(
    tmp_path: Path, member_name: str, unix_mode: int, refusal: str
) -> None:
    """Extracting a bundle refuses traversal, absolute and backslash paths, foreign roots, the bare package name, non-canonical paths, and members that are not regular files, each by name."""
    bundle_path = tmp_path / BUNDLE_RESOURCE_NAME
    with ZipFile(bundle_path, "w") as bundle:
        bundle.writestr(_regular_file(f"{PACKAGE_NAME}/__init__.py"), b"")
        bad_info = ZipInfo(member_name)
        bad_info.external_attr = unix_mode << 16
        bundle.writestr(bad_info, b"bad")
    pex = _pex_with_bundle(tmp_path / "devcapsule.pex", bundle_path.read_bytes())

    with pytest.raises(WebconsoleBundleError, match=refusal):
        extract_webconsole_bundle(pex, tmp_path / "staged")


@pytest.mark.parametrize("permission_bits", [0, 0o600])
def test_extract_webconsole_bundle_accepts_members_without_a_unix_file_type(tmp_path: Path, permission_bits: int) -> None:
    """A member whose external attributes carry no Unix file type, as non-Unix zip tools and ``writestr`` produce, extracts as a regular file."""
    bundle_path = tmp_path / BUNDLE_RESOURCE_NAME
    with ZipFile(bundle_path, "w") as bundle:
        info = ZipInfo(f"{PACKAGE_NAME}/__init__.py")
        info.external_attr = permission_bits << 16
        bundle.writestr(info, b"typeless = True\n")
    pex = _pex_with_bundle(tmp_path / "devcapsule.pex", bundle_path.read_bytes())

    extracted = extract_webconsole_bundle(pex, tmp_path / "staged")

    assert (extracted / PACKAGE_NAME / "__init__.py").read_bytes() == b"typeless = True\n"


def test_extract_webconsole_bundle_skips_directory_entries(tmp_path: Path) -> None:
    """An explicit directory entry in the bundle creates nothing by itself and does not stop the files beneath it."""
    bundle_path = tmp_path / BUNDLE_RESOURCE_NAME
    with ZipFile(bundle_path, "w") as bundle:
        directory = ZipInfo(f"{PACKAGE_NAME}/static/")
        directory.external_attr = ((stat.S_IFDIR | 0o755) << 16) | 0x10
        bundle.writestr(directory, b"")
        bundle.writestr(_regular_file(f"{PACKAGE_NAME}/__init__.py"), b"")
        bundle.writestr(_regular_file(f"{PACKAGE_NAME}/static/files.html"), b"<title>Files</title>")
    pex = _pex_with_bundle(tmp_path / "devcapsule.pex", bundle_path.read_bytes())

    extracted = extract_webconsole_bundle(pex, tmp_path / "staged")

    assert (extracted / PACKAGE_NAME / "static" / "files.html").read_bytes() == b"<title>Files</title>"
    assert (extracted / PACKAGE_NAME / "static").stat().st_mode & 0o777 == 0o755


@pytest.mark.parametrize(
    "problem,refusal",
    [
        ("existing-dest", "must not already exist"),
        ("absent-bundle", "exactly one"),
        ("two-bundles", "exactly one"),
        ("corrupt-pex", "cannot read web console bundle"),
        ("corrupt-bundle", "cannot read web console bundle"),
        ("missing-init", "lacks devcapsule_webconsole/__init__.py"),
        ("duplicate", "duplicate member"),
        ("file-then-directory", "cannot read web console bundle"),
        ("directory-then-file", "cannot read web console bundle"),
    ],
)
def test_extract_webconsole_bundle_refuses_malformed_or_ambiguous_archives(
    tmp_path: Path, problem: str, refusal: str
) -> None:
    """Extracting a bundle refuses an existing destination, a missing, duplicate or corrupt bundle, a missing __init__.py, a duplicate member, and a member that is both a file and a directory, each by name."""
    destination = tmp_path / "staged"
    if problem == "existing-dest":
        destination.mkdir()
        pex = tmp_path / "devcapsule.pex"
    elif problem == "absent-bundle":
        pex = _pex_with_bundle(tmp_path / "devcapsule.pex", b"", count=0)
    elif problem == "two-bundles":
        pex = _pex_with_bundle(tmp_path / "devcapsule.pex", b"not-used", count=2)
    elif problem == "corrupt-pex":
        pex = tmp_path / "devcapsule.pex"
        pex.write_bytes(b"not a zip archive")
    elif problem == "corrupt-bundle":
        pex = _pex_with_bundle(tmp_path / "devcapsule.pex", b"not a zip archive")
    elif problem == "missing-init":
        bundle_path = tmp_path / BUNDLE_RESOURCE_NAME
        with ZipFile(bundle_path, "w") as bundle:
            bundle.writestr(_regular_file(f"{PACKAGE_NAME}/app.py"), b"x = 1\n")
        pex = _pex_with_bundle(tmp_path / "devcapsule.pex", bundle_path.read_bytes())
    elif problem == "duplicate":
        bundle_path = tmp_path / BUNDLE_RESOURCE_NAME
        with warnings.catch_warnings(), ZipFile(bundle_path, "w") as bundle:
            warnings.simplefilter("ignore", UserWarning)
            bundle.writestr(_regular_file(f"{PACKAGE_NAME}/__init__.py"), b"")
            bundle.writestr(_regular_file(f"{PACKAGE_NAME}/__init__.py"), b"duplicate")
        pex = _pex_with_bundle(tmp_path / "devcapsule.pex", bundle_path.read_bytes())
    else:
        bundle_path = tmp_path / BUNDLE_RESOURCE_NAME
        members = [f"{PACKAGE_NAME}/static", f"{PACKAGE_NAME}/static/files.html"]
        if problem == "directory-then-file":
            members.reverse()
        with ZipFile(bundle_path, "w") as bundle:
            bundle.writestr(_regular_file(f"{PACKAGE_NAME}/__init__.py"), b"")
            for member in members:
                bundle.writestr(_regular_file(member), b"content")
        pex = _pex_with_bundle(tmp_path / "devcapsule.pex", bundle_path.read_bytes())

    with pytest.raises(WebconsoleBundleError, match=refusal):
        extract_webconsole_bundle(pex, destination)


def test_main_builds_the_bundle_and_exits_zero(tmp_path: Path) -> None:
    """The CLI entry point writes the bundle zip at ``--output`` and returns 0 on a valid package."""
    package = _sample_webconsole_package(tmp_path / "valid")
    output = tmp_path / "out.zip"

    assert main(["--package", str(package), "--output", str(output)]) == 0
    with ZipFile(output) as archive:
        assert f"{PACKAGE_NAME}/__init__.py" in archive.namelist()


def test_main_reports_an_invalid_package_on_stderr_and_exits_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The CLI entry point returns 1 and names the defect on stderr when the package is invalid."""
    output = tmp_path / "fail.zip"

    assert main(["--package", str(tmp_path / "missing"), "--output", str(output)]) == 1
    assert "webconsole_bundle: web console package directory does not exist" in capsys.readouterr().err
    assert not output.exists()
