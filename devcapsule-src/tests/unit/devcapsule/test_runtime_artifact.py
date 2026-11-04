"""Unit tests of ``devcapsule/runtime_artifact.py``: which DevCapsule executable a launch delivers into a capsule.

The executables are PEX fixtures under ``tmp_path``, some behind a native header; the running
launcher is the fixtures' build, and a test of another host names it.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from devcapsule.build_info import BuildInfo
from devcapsule.compat import CliError
from devcapsule.platforms import HostOs, Platform
from devcapsule.runtime_artifact import executable_platform, runtime_artifact
from tests.test_base_image import pex_fixture
from tests.unit.devcapsule.test_platforms import on_host


AMD64 = Platform.LINUX_AMD64

ARM64 = Platform.LINUX_ARM64

MACH_O_ARM64 = b"\xcf\xfa\xed\xfe" + bytes(16)

ELF_AMD64 = b"\x7fELF\x02\x01\x01" + bytes(11) + (0x3E).to_bytes(2, "little")

ELF_ARM64 = b"\x7fELF\x02\x01\x01" + bytes(11) + (0xB7).to_bytes(2, "little")

ELF_RISCV = b"\x7fELF\x02\x01\x01" + bytes(11) + (0xF3).to_bytes(2, "little")


def pex_with_native_header(path: Path, header: bytes, *, revision: str = "a" * 40) -> Path:
    """A PEX fixture whose first bytes are a native executable's header.

    A scie is a native launcher with the PEX appended; the build information
    is read from the archive, so the header and the archive coexist.
    """

    pex = pex_fixture(path, revision=revision)
    pex.write_bytes(header + pex.read_bytes())
    return pex


@pytest.fixture(autouse=True)
def launcher_of_the_fixtures_build(monkeypatch: pytest.MonkeyPatch) -> None:
    """The running launcher is the build the fixtures record: 0.1.0 at revision a…a."""

    monkeypatch.setattr("devcapsule.runtime_artifact.current_build_info", lambda: BuildInfo(
        schema_version=2, version="0.1.0", source_repository="https://github.com/example/devcapsule",
        source_revision="a" * 40, source_url="unknown"))


def test_packaged_launcher_supplies_itself_despite_source_override(tmp_path: Path, monkeypatch) -> None:
    """A packaged launcher that runs in the capsule delivers itself, whatever DEVCAPSULE_RUNTIME_PEX names."""
    launcher = pex_fixture(tmp_path / "launcher.pex")
    monkeypatch.setenv("SCIE", str(launcher))
    monkeypatch.setenv("DEVCAPSULE_RUNTIME_PEX", str(tmp_path / "different.pex"))
    assert runtime_artifact(AMD64) == launcher


def test_source_launcher_requires_explicit_built_runtime(tmp_path: Path, monkeypatch) -> None:
    """A launcher run from source delivers the runtime DEVCAPSULE_RUNTIME_PEX names, and refuses one that does not exist."""
    monkeypatch.delenv("SCIE", raising=False)
    monkeypatch.delenv("PEX", raising=False)
    monkeypatch.setenv("DEVCAPSULE_RUNTIME_PEX", str(tmp_path / "missing.pex"))
    with pytest.raises(CliError, match="DEVCAPSULE_RUNTIME_PEX"):
        runtime_artifact(AMD64)
    launcher = pex_fixture(tmp_path / "runtime.pex")
    monkeypatch.setenv("DEVCAPSULE_RUNTIME_PEX", str(launcher))
    assert runtime_artifact(AMD64) == launcher


def test_executable_platform_reads_native_headers(tmp_path: Path) -> None:
    """An executable's platform is read from its native header: macOS, a capsule platform, another Linux, or none for a plain PEX."""
    assert executable_platform(pex_with_native_header(tmp_path / "mac", MACH_O_ARM64)) is HostOs.DARWIN
    assert executable_platform(pex_with_native_header(tmp_path / "amd64", ELF_AMD64)) is AMD64
    assert executable_platform(pex_with_native_header(tmp_path / "arm64", ELF_ARM64)) is ARM64
    assert executable_platform(pex_with_native_header(tmp_path / "riscv", ELF_RISCV)) is HostOs.LINUX
    assert executable_platform(pex_fixture(tmp_path / "plain.pex")) is None
    assert executable_platform(tmp_path / "absent") is None


@pytest.mark.own_host_patches
def test_macos_launcher_delivers_the_named_linux_runtime(tmp_path: Path, monkeypatch) -> None:
    """A macOS launcher delivers the Linux runtime DEVCAPSULE_RUNTIME_PEX names."""
    on_host(monkeypatch, "Darwin", "arm64")
    monkeypatch.setenv("SCIE", str(pex_with_native_header(tmp_path / "devcapsule-macos", MACH_O_ARM64)))
    linux = pex_with_native_header(tmp_path / "devcapsule-linux", ELF_AMD64)
    monkeypatch.setenv("DEVCAPSULE_RUNTIME_PEX", str(linux))
    assert runtime_artifact(AMD64) == linux


@pytest.mark.own_host_patches
def test_macos_launcher_without_a_linux_runtime_says_what_to_set(tmp_path: Path, monkeypatch) -> None:
    """A macOS launcher without a runtime of the capsule's platform says what it is and what to set."""
    on_host(monkeypatch, "Darwin", "arm64")
    monkeypatch.setenv("SCIE", str(pex_with_native_header(tmp_path / "devcapsule-macos", MACH_O_ARM64)))
    monkeypatch.delenv("DEVCAPSULE_RUNTIME_PEX", raising=False)
    with pytest.raises(CliError, match="a macOS executable and cannot run inside linux-amd64 capsules.*DEVCAPSULE_RUNTIME_PEX"):
        runtime_artifact(AMD64)
    monkeypatch.setenv("DEVCAPSULE_RUNTIME_PEX", str(pex_with_native_header(tmp_path / "wrong-arch", ELF_ARM64)))
    with pytest.raises(CliError, match="a linux-arm64 executable"):
        runtime_artifact(AMD64)


@pytest.mark.own_host_patches
def test_a_plain_pex_launcher_on_a_mac_is_not_delivered(tmp_path: Path, monkeypatch) -> None:
    """A plain PEX launcher on a Mac is not delivered, since its native wheels are the Mac's; a named runtime is."""
    # A PEX bundles native wheels for the machine it was built on.
    on_host(monkeypatch, "Darwin", "arm64")
    monkeypatch.delenv("SCIE", raising=False)
    monkeypatch.setenv("PEX", str(pex_fixture(tmp_path / "launcher.pex")))
    linux = pex_with_native_header(tmp_path / "devcapsule-linux", ELF_AMD64)
    monkeypatch.setenv("DEVCAPSULE_RUNTIME_PEX", str(linux))
    assert runtime_artifact(AMD64) == linux
    monkeypatch.delenv("DEVCAPSULE_RUNTIME_PEX")
    with pytest.raises(CliError, match="a plain PEX built for another machine"):
        runtime_artifact(AMD64)


@pytest.mark.own_host_patches
def test_a_runtime_of_another_build_is_refused(tmp_path: Path, monkeypatch) -> None:
    """A delivered runtime of another revision than the launcher's is refused."""
    # D-0009: the runtime runs the plan this launcher writes. A runtime left
    # from an earlier build, after the launcher was updated, is refused.
    on_host(monkeypatch, "Darwin", "arm64")
    monkeypatch.setenv("SCIE", str(pex_with_native_header(tmp_path / "devcapsule-macos", MACH_O_ARM64)))
    stale = pex_with_native_header(tmp_path / "devcapsule-linux", ELF_AMD64, revision="b" * 40)
    monkeypatch.setenv("DEVCAPSULE_RUNTIME_PEX", str(stale))
    with pytest.raises(CliError, match="is DevCapsule 0.1.0 from b+, but this launcher is 0.1.0 from a+"):
        runtime_artifact(AMD64)


@pytest.mark.own_host_patches
def test_a_runtime_directory_serves_each_capsule_platform(tmp_path: Path, monkeypatch) -> None:
    """A runtime directory delivers the executable of each launch's platform, and names the one it lacks."""
    # Apple Silicon runs both platforms; one setting names both runtimes, and
    # each launch delivers the one for its lock's platform.
    on_host(monkeypatch, "Darwin", "arm64")
    monkeypatch.setenv("SCIE", str(pex_with_native_header(tmp_path / "devcapsule-macos", MACH_O_ARM64)))
    runtimes = tmp_path / "runtimes"
    runtimes.mkdir()
    amd64 = pex_with_native_header(runtimes / "devcapsule-linux-amd64", ELF_AMD64)
    arm64 = pex_with_native_header(runtimes / "devcapsule-linux-arm64", ELF_ARM64)
    monkeypatch.setenv("DEVCAPSULE_RUNTIME_PEX", str(runtimes))
    assert runtime_artifact(ARM64) == arm64
    assert runtime_artifact(AMD64) == amd64
    amd64.unlink()
    with pytest.raises(CliError, match="holds no devcapsule-linux-amd64"):
        runtime_artifact(AMD64)
