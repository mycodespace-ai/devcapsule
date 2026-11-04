from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from devcapsule.compat import CliError
from devcapsule.materialization import ArtifactSpec, formation_descriptor, formation_identity
from devcapsule.build_info import BuildInfo
from devcapsule.platforms import HostOs, Platform
from devcapsule.runtime_artifact import executable_platform, runtime_artifact
from devcapsule.runtime_command import RuntimeCommand
from tests.test_base_image import pex_fixture
from tests.test_platforms import on_host

pytestmark = pytest.mark.legacy


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
    launcher = pex_fixture(tmp_path / "launcher.pex")
    monkeypatch.setenv("SCIE", str(launcher))
    monkeypatch.setenv("DEVCAPSULE_RUNTIME_PEX", str(tmp_path / "different.pex"))
    assert runtime_artifact(AMD64) == launcher


def test_source_launcher_requires_explicit_built_runtime(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("SCIE", raising=False)
    monkeypatch.delenv("PEX", raising=False)
    monkeypatch.setenv("DEVCAPSULE_RUNTIME_PEX", str(tmp_path / "missing.pex"))
    with pytest.raises(CliError, match="DEVCAPSULE_RUNTIME_PEX"):
        runtime_artifact(AMD64)
    launcher = pex_fixture(tmp_path / "runtime.pex")
    monkeypatch.setenv("DEVCAPSULE_RUNTIME_PEX", str(launcher))
    assert runtime_artifact(AMD64) == launcher


def test_executable_platform_reads_native_headers(tmp_path: Path) -> None:
    assert executable_platform(pex_with_native_header(tmp_path / "mac", MACH_O_ARM64)) is HostOs.DARWIN
    assert executable_platform(pex_with_native_header(tmp_path / "amd64", ELF_AMD64)) is AMD64
    assert executable_platform(pex_with_native_header(tmp_path / "arm64", ELF_ARM64)) is ARM64
    assert executable_platform(pex_with_native_header(tmp_path / "riscv", ELF_RISCV)) is HostOs.LINUX
    assert executable_platform(pex_fixture(tmp_path / "plain.pex")) is None
    assert executable_platform(tmp_path / "absent") is None


@pytest.mark.own_host_patches
def test_macos_launcher_delivers_the_named_linux_runtime(tmp_path: Path, monkeypatch) -> None:
    on_host(monkeypatch, "Darwin", "arm64")
    monkeypatch.setenv("SCIE", str(pex_with_native_header(tmp_path / "devcapsule-macos", MACH_O_ARM64)))
    linux = pex_with_native_header(tmp_path / "devcapsule-linux", ELF_AMD64)
    monkeypatch.setenv("DEVCAPSULE_RUNTIME_PEX", str(linux))
    assert runtime_artifact(AMD64) == linux


@pytest.mark.own_host_patches
def test_macos_launcher_without_a_linux_runtime_says_what_to_set(tmp_path: Path, monkeypatch) -> None:
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


def test_runtime_update_changes_formation_identity_without_changing_components() -> None:
    artifact = ArtifactSpec("1", "https://example.test/ide", "a" * 64)
    before = formation_descriptor(platform="linux-amd64", base_identity="sha256:base", artifact=artifact,
                                  runtime_sha256=hashlib.sha256(b"old").hexdigest())
    after = formation_descriptor(platform="linux-amd64", base_identity="sha256:base", artifact=artifact,
                                 runtime_sha256=hashlib.sha256(b"new").hexdigest())
    assert before["components"] == after["components"]
    assert formation_identity(before) != formation_identity(after)


def test_public_command_contract_invalidates_images_with_identical_runtime_bytes() -> None:
    descriptor = formation_descriptor(
        platform="linux-amd64", base_identity="sha256:base",
        artifact=ArtifactSpec("1", "https://example.test/ide", "a" * 64),
        runtime_sha256=hashlib.sha256(b"same launcher").hexdigest(),
    )
    current = formation_identity(descriptor)
    # Images produced before the repair carried these exact fields, except
    # that they did not promise to install the public CLI command.
    assert descriptor["runtime"].pop("public-command") == "/usr/local/bin/devcapsule"
    assert formation_identity(descriptor) != current


def test_development_alias_changes_image_identity_without_changing_runtime():
    args = dict(platform="linux-amd64", base_identity="sha256:base",
                artifact=ArtifactSpec("1", "https://example.test/ide", "a" * 64),
                runtime_sha256=hashlib.sha256(b"same launcher").hexdigest())
    ordinary = formation_descriptor(**args)
    development = formation_descriptor(**args, runtime_command=RuntimeCommand.DEVELOPMENT)
    assert ordinary["runtime"]["pex-sha256"] == development["runtime"]["pex-sha256"]
    assert ordinary["runtime"]["entrypoint"] == development["runtime"]["entrypoint"]
    assert formation_identity(ordinary) != formation_identity(development)


@pytest.mark.parametrize("existing", ["shipped-link", "development-link", "development-script"])
def test_development_mode_removes_only_its_own_inherited_link(tmp_path, monkeypatch, existing):
    import subprocess
    from devcapsule import materialization
    command = tmp_path / "devcapsule"
    source = tmp_path / "development-cli"
    source.write_text("development command")
    if existing == "shipped-link":
        command.symlink_to("/opt/devcapsule/bin/devcapsule.pex")
    elif existing == "development-link":
        command.symlink_to(source)
    else:
        command.write_text("development command")
    monkeypatch.setattr(materialization, "RUNTIME_COMMAND_PATH", str(command))
    pex = pex_fixture(tmp_path / "runtime.pex")
    spec = materialization.surface_materialization_spec(
        base_reference="base:test", base_identity="sha256:base", image="test:cli",
        surface_root=tmp_path, component_template=tmp_path / "template.json",
        artifact=ArtifactSpec("1", "https://example.test/ide", "a" * 64),
        platform="linux-amd64", runtime_pex=pex, runtime_command=RuntimeCommand.DEVELOPMENT,
    )
    # Execute the generated cleanup operation on temporary paths, before its
    # installation operation; never mutate the test host's /usr/local/bin.
    cleanup = next(step for step in spec.build_plan().exec_steps
                   if step.args[:2] == ("sh", "-c") and str(command) in step.args[2])
    subprocess.run(cleanup.args, check=True)
    if existing == "shipped-link":
        assert not command.is_symlink()
    else:
        assert command.read_text() == "development command"
        assert command.is_symlink() == (existing == "development-link")
