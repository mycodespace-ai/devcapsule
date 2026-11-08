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


@pytest.mark.parametrize("defect", ["missing-dir", "wrong-name", "missing-init", "symlink"])
def test_build_webconsole_bundle_refuses_invalid_package_tree(tmp_path: Path, defect: str) -> None:
    """Building a web console bundle refuses a missing package, a misnamed root, a missing __init__.py, or a symlink."""
    if defect == "missing-dir":
        package = tmp_path / PACKAGE_NAME
    elif defect == "wrong-name":
        package = tmp_path / "wrong_name"
        package.mkdir()
        (package / "__init__.py").write_text("", encoding="utf-8")
    elif defect == "missing-init":
        package = tmp_path / PACKAGE_NAME
        package.mkdir()
    else:
        package = _sample_webconsole_package(tmp_path)
        (package / "escape.py").symlink_to(tmp_path)

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
    "member_name,unix_mode",
    [
        ("../escape.py", stat.S_IFREG | 0o644),
        (f"{PACKAGE_NAME}/../../escape.py", stat.S_IFREG | 0o644),
        (f"/{PACKAGE_NAME}/__init__.py", stat.S_IFREG | 0o644),
        (f"{PACKAGE_NAME}\\__init__.py", stat.S_IFREG | 0o644),
        ("other_pkg/__init__.py", stat.S_IFREG | 0o644),
        (f"{PACKAGE_NAME}/link.py", stat.S_IFLNK | 0o777),
    ],
)
def test_extract_webconsole_bundle_refuses_unsafe_archive_entries(
    tmp_path: Path, member_name: str, unix_mode: int
) -> None:
    """Extracting a web console bundle refuses path traversal, foreign roots, backslashes, and symbolic links."""
    bundle_path = tmp_path / BUNDLE_RESOURCE_NAME
    with ZipFile(bundle_path, "w") as bundle:
        init_info = ZipInfo(f"{PACKAGE_NAME}/__init__.py")
        init_info.external_attr = (stat.S_IFREG | 0o644) << 16
        bundle.writestr(init_info, b"")
        bad_info = ZipInfo(member_name)
        bad_info.external_attr = unix_mode << 16
        bundle.writestr(bad_info, b"bad")
    pex = _pex_with_bundle(tmp_path / "devcapsule.pex", bundle_path.read_bytes())

    with pytest.raises(WebconsoleBundleError):
        extract_webconsole_bundle(pex, tmp_path / "staged")


@pytest.mark.parametrize("problem", ["existing-dest", "absent-bundle", "two-bundles", "corrupt-pex", "missing-init", "duplicate"])
def test_extract_webconsole_bundle_refuses_malformed_or_ambiguous_archives(tmp_path: Path, problem: str) -> None:
    """Extracting a web console bundle refuses an existing destination, missing or duplicate bundles, or missing __init__.py."""
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
    elif problem == "missing-init":
        bundle_path = tmp_path / BUNDLE_RESOURCE_NAME
        with ZipFile(bundle_path, "w") as bundle:
            bundle.writestr(f"{PACKAGE_NAME}/app.py", b"x = 1\n")
        pex = _pex_with_bundle(tmp_path / "devcapsule.pex", bundle_path.read_bytes())
    else:
        bundle_path = tmp_path / BUNDLE_RESOURCE_NAME
        with warnings.catch_warnings(), ZipFile(bundle_path, "w") as bundle:
            warnings.simplefilter("ignore", UserWarning)
            bundle.writestr(f"{PACKAGE_NAME}/__init__.py", b"")
            bundle.writestr(f"{PACKAGE_NAME}/__init__.py", b"duplicate")
        pex = _pex_with_bundle(tmp_path / "devcapsule.pex", bundle_path.read_bytes())

    with pytest.raises(WebconsoleBundleError):
        extract_webconsole_bundle(pex, destination)


def test_main_builds_bundle_and_reports_errors_on_stderr(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """The CLI entry point writes the bundle zip on valid inputs and exits 1 with an error message on invalid inputs."""
    package = _sample_webconsole_package(tmp_path / "valid")
    output = tmp_path / "out.zip"

    assert main(["--package", str(package), "--output", str(output)]) == 0
    assert output.is_file()
    assert main(["--package", str(tmp_path / "missing"), "--output", str(tmp_path / "fail.zip")]) == 1
    assert "webconsole_bundle:" in capsys.readouterr().err
