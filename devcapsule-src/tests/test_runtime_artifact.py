from __future__ import annotations

import hashlib

import pytest

from devcapsule.materialization import ArtifactSpec, formation_descriptor, formation_identity
from devcapsule.runtime_command import RuntimeCommand
from tests.test_base_image import pex_fixture

pytestmark = pytest.mark.legacy


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
