"""Package and unpack the capsule web console carried inside a DevCapsule PEX.

Under ``D-0017``, ``scripts/build-pex.sh`` bundles the pure-Python
``devcapsule_webconsole`` tree and its static assets into a deterministic stored
zip resource inside ``devcapsule.pex``. During environment materialization, the
launcher extracts that bundle from the delivered ``runtime_pex`` and installs it
read-only at ``/opt/devcapsule/webconsole``, where the base image's
``/opt/devcapsule-webconsole/venv/bin/python`` runs it ahead of the base copy.

Public operations: ``build_webconsole_bundle``, ``extract_webconsole_bundle``,
``main``.
"""

from __future__ import annotations

import argparse
from io import BytesIO
from pathlib import Path, PurePosixPath
import stat
import sys
from typing import Sequence
from zipfile import BadZipFile, ZIP_STORED, ZipFile, ZipInfo

__all__ = [
    "BUNDLE_RESOURCE_NAME",
    "BUNDLE_RESOURCE_SUFFIX",
    "LAUNCHER_WEBCONSOLE_PATH",
    "PACKAGE_NAME",
    "WebconsoleBundleError",
    "build_webconsole_bundle",
    "extract_webconsole_bundle",
    "main",
]

PACKAGE_NAME = "devcapsule_webconsole"
BUNDLE_RESOURCE_NAME = "_webconsole_bundle.zip"
BUNDLE_RESOURCE_SUFFIX = f"/devcapsule/{BUNDLE_RESOURCE_NAME}"
LAUNCHER_WEBCONSOLE_PATH = "/opt/devcapsule/webconsole"

_FIXED_ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
_SKIPPED_SUFFIXES = frozenset({".pyc", ".pyo"})


class WebconsoleBundleError(ValueError):
    """A web console bundle cannot be built or unpacked."""


def build_webconsole_bundle(package_dir: Path, destination: Path) -> Path:
    """Write ``package_dir`` as a deterministic stored zip at ``destination``."""

    if package_dir.is_symlink() or not package_dir.is_dir():
        raise WebconsoleBundleError(f"web console package directory does not exist: {package_dir}")
    if package_dir.name != PACKAGE_NAME:
        raise WebconsoleBundleError(
            f"web console package directory must be named {PACKAGE_NAME!r}; got {package_dir.name!r}"
        )
    init_file = package_dir / "__init__.py"
    if init_file.is_symlink() or not init_file.is_file():
        raise WebconsoleBundleError(f"web console package lacks __init__.py at {init_file}")

    entries = _collect_package_files(package_dir)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(destination, "w") as archive:
        for relative, source in entries:
            info = ZipInfo(filename=f"{PACKAGE_NAME}/{relative}", date_time=_FIXED_ZIP_TIMESTAMP)
            info.compress_type = ZIP_STORED
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(info, source.read_bytes())
    return destination


def _collect_package_files(package_dir: Path) -> list[tuple[str, Path]]:
    collected: list[tuple[str, Path]] = []

    def walk(directory: Path) -> None:
        for child in sorted(directory.iterdir(), key=lambda item: item.name):
            if child.name == "__pycache__":
                continue
            if child.is_symlink():
                raise WebconsoleBundleError(f"web console package must not contain symlinks: {child}")
            if child.is_dir():
                walk(child)
                continue
            if not child.is_file():
                raise WebconsoleBundleError(f"web console package entry is not a regular file: {child}")
            if child.suffix in _SKIPPED_SUFFIXES:
                continue
            collected.append((child.relative_to(package_dir).as_posix(), child))

    walk(package_dir)
    return collected


def extract_webconsole_bundle(runtime_pex: Path, destination: Path) -> Path:
    """Unpack the web console package embedded in ``runtime_pex`` into ``destination``."""

    if destination.exists() or destination.is_symlink():
        raise WebconsoleBundleError(f"extraction destination must not already exist: {destination}")
    try:
        with ZipFile(runtime_pex) as pex_archive:
            candidates = [name for name in pex_archive.namelist() if name.endswith(BUNDLE_RESOURCE_SUFFIX)]
            if len(candidates) != 1:
                raise WebconsoleBundleError(
                    f"PEX must contain exactly one devcapsule/{BUNDLE_RESOURCE_NAME}; found {len(candidates)}"
                )
            bundle_bytes = pex_archive.read(candidates[0])
        with ZipFile(BytesIO(bundle_bytes)) as bundle:
            extracted: set[str] = set()
            destination.mkdir(parents=True)
            destination.chmod(0o755)
            for info in bundle.infolist():
                if info.is_dir():
                    continue
                # The Unix file type travels in the high external attributes; a
                # member that declares one must be a regular file, never a symlink,
                # a directory or a device. A member without one (a zip from a
                # non-Unix tool) is a regular file by the archive format.
                file_type = stat.S_IFMT(info.external_attr >> 16)
                if file_type and file_type != stat.S_IFREG:
                    raise WebconsoleBundleError(
                        f"bundled web console member {info.filename!r} is not a regular file"
                    )
                relative = _validated_member_path(info.filename)
                if relative in extracted:
                    raise WebconsoleBundleError(
                        f"bundled web console contains duplicate member {info.filename!r}"
                    )
                target = destination / relative
                _mkdirs_mode_0755(destination, target.parent)
                target.write_bytes(bundle.read(info))
                target.chmod(0o644)
                extracted.add(relative)
    except WebconsoleBundleError:
        raise
    except (OSError, BadZipFile) as exc:
        raise WebconsoleBundleError(f"cannot read web console bundle from PEX {runtime_pex}: {exc}") from exc

    if f"{PACKAGE_NAME}/__init__.py" not in extracted:
        raise WebconsoleBundleError(f"bundled web console lacks {PACKAGE_NAME}/__init__.py")
    return destination


def _validated_member_path(filename: str) -> str:
    if not filename or filename.startswith("/") or "\\" in filename or "\x00" in filename:
        raise WebconsoleBundleError(f"invalid bundled web console path {filename!r}")
    parts = PurePosixPath(filename).parts
    if not parts or parts[0] != PACKAGE_NAME or len(parts) < 2:
        raise WebconsoleBundleError(
            f"bundled web console member {filename!r} must live beneath {PACKAGE_NAME}/"
        )
    if any(part in {"", ".", ".."} for part in parts):
        raise WebconsoleBundleError(f"invalid bundled web console path {filename!r}")
    normalized = "/".join(parts)
    if normalized != filename:
        raise WebconsoleBundleError(f"non-canonical bundled web console path {filename!r}")
    return normalized


def _mkdirs_mode_0755(root: Path, directory: Path) -> None:
    current = root
    for part in directory.relative_to(root).parts:
        current = current / part
        if not current.exists():
            current.mkdir()
            current.chmod(0o755)


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point invoked by ``scripts/build-pex.sh``."""

    parser = argparse.ArgumentParser(description="Build the deterministic web console bundle for devcapsule.pex.")
    parser.add_argument("--package", type=Path, required=True, help="path to devcapsule_webconsole/")
    parser.add_argument("--output", type=Path, required=True, help="destination _webconsole_bundle.zip")
    arguments = parser.parse_args(argv)
    try:
        build_webconsole_bundle(arguments.package, arguments.output)
    except WebconsoleBundleError as exc:
        print(f"webconsole_bundle: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
