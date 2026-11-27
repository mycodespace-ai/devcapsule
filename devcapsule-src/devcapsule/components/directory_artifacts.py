"""extract_tar_directory unpacks bounded toolchains with internal regular-file aliases."""
import os
from pathlib import Path, PurePosixPath
import shutil
import tarfile

from devcapsule.compat import CliError


def extract_tar_directory(archive: Path, destination: Path) -> Path:
    try:
        with tarfile.open(archive, "r:gz") as package:
            members = []
            regular_files: set[PurePosixPath] = set()
            links: list[tuple[PurePosixPath, PurePosixPath]] = []
            size = 0
            for member in package:
                path = PurePosixPath(member.name)
                if (path.is_absolute() or ".." in path.parts or "\\" in member.name
                        or not (member.isfile() or member.isdir() or member.issym())):
                    raise CliError(f"Unsafe component tar entry: {member.name!r}")
                if member.issym():
                    link = PurePosixPath(member.linkname)
                    if not member.linkname or link.is_absolute() or "\\" in member.linkname:
                        raise CliError(f"Unsafe component tar entry: {member.name!r}")
                    referent = PurePosixPath(os.path.normpath(path.parent / link))
                    links.append((path, referent))
                elif member.isfile():
                    regular_files.add(path)
                size += member.size
                members.append(member)
                if len(members) > 100_000 or size > 4 * 1024**3:
                    raise CliError("Component tar exceeds extraction limits.")
            if not members:
                raise CliError("Component tar is empty.")
            for path, referent in links:
                if referent not in regular_files:
                    raise CliError(f"Unsafe component tar entry: {str(path)!r} does not link to an archive file")

            destination.mkdir(parents=True)
            for member in members:
                target = destination / member.name
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    if member.issym():
                        continue
                    source = package.extractfile(member)
                    assert source is not None
                    with source, target.open("wb") as output:
                        shutil.copyfileobj(source, output)
                    target.chmod(0o755 if member.mode & 0o111 else 0o644)
            # All directories and files now exist. No archive write can follow a link.
            for path, referent in links:
                (destination / path).symlink_to(os.path.relpath(referent, path.parent))
    except (OSError, tarfile.TarError) as exc:
        raise CliError(f"Cannot extract verified component tar: {exc}") from exc
    return destination
