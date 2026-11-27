"""Contracts for extracting a verified toolchain into a fresh directory."""

import io
from pathlib import Path
import tarfile

import pytest

from devcapsule.compat import CliError
from devcapsule.components.directory_artifacts import extract_tar_directory


def write_archive(archive: Path, link_target: str) -> None:
    with tarfile.open(archive, "w:gz") as package:
        link = tarfile.TarInfo("sdk/locale/alias.dll")
        link.type = tarfile.SYMTYPE
        link.linkname = link_target
        package.addfile(link)
        data = b"shared resource"
        regular = tarfile.TarInfo("sdk/shared/resource.dll")
        regular.size = len(data)
        package.addfile(regular, io.BytesIO(data))


def test_relative_link_to_later_archive_file_survives_relocation(tmp_path: Path) -> None:
    """A relative alias resolves to the same SDK file after the extracted tree moves."""
    archive = tmp_path / "sdk.tar.gz"
    write_archive(archive, "../shared/resource.dll")
    output = extract_tar_directory(archive, tmp_path / "staging").rename(tmp_path / "sdk")
    alias = output / "sdk/locale/alias.dll"
    assert alias.is_symlink()
    assert alias.readlink() == Path("../shared/resource.dll")
    assert alias.read_bytes() == b"shared resource"


@pytest.mark.parametrize("target", ["/outside", "../../../outside", "missing", "alias.dll", "../shared"])
def test_link_must_name_a_regular_file_inside_the_archive(tmp_path: Path, target: str) -> None:
    """Reject external, missing, cyclic and directory targets before creating the output tree."""
    archive = tmp_path / "sdk.tar.gz"
    write_archive(archive, target)
    with pytest.raises(CliError, match="Unsafe"):
        extract_tar_directory(archive, tmp_path / "staging")
    assert not (tmp_path / "staging").exists()
