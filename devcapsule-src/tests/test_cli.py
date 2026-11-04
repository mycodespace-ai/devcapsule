from __future__ import annotations

from tests.launch_preparation import run_until_prepared

import os
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import zipfile

import pytest

from devcapsule import cli, compat
from devcapsule.launch.pycharm._launcher import AttachedResult
from devcapsule.launch.pycharm._image_build import PycharmImageBuildOptions
from devcapsule.environment_realization import RealizedEnvironment
from devcapsule.images.metadata import LocalImageRecord
from devcapsule.platforms import Platform
from devcapsule.materialization import ImageDetails, parse_locked_environment
from devcapsule.configuration.file_formats import (
    canonical_digest,
)

pytestmark = pytest.mark.legacy


def test_top_level_help_returns_success(capsys) -> None:
    result = cli.main(["--help"])

    assert result == 0
    output = capsys.readouterr().out
    assert "pycharm" in output
    # Retired 2026-08-31: the neutral codium interactive-surface component
    # replaced both agent-welded launch trees.
    assert "vscode_with_claude" not in output
    assert "codium_with_claude" not in output
    assert "runtime" in output
    assert "version" in output
    assert "images" in output
    assert "project" in output
    assert "recursive-e2e" not in output

    assert cli.main(["project", "--help"]) == 0
    assert "recursive-e2e" in capsys.readouterr().out


def test_runtime_command_forwards_arguments_to_container_entrypoint() -> None:
    with patch("devcapsule.commands.runtime.runtime_main", return_value=17) as runtime_main:
        result = cli.main(["runtime", "plan.json", "--future-option", "value"])

    assert result == 17
    runtime_main.assert_called_once_with(["plan.json", "--future-option", "value"])


@pytest.mark.parametrize("options", [
    [], ["--help"], ["--no-docker"],
    ["--image", "legacy:unused", "--docker-in-docker"],
    ["--project-config", "--shared-config"],
])
def test_pycharm_run_is_retired_without_launch_or_state_changes(
    tmp_path: Path, monkeypatch, capsys, options: list[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "state"))
    with (
        patch("devcapsule.launch.pycharm._launcher.run_pycharm") as launch,
        patch("devcapsule.launch.pycharm._launcher.subprocess.run") as process,
    ):
        assert cli.main(["pycharm", "run", *options]) == 2
    launch.assert_not_called()
    process.assert_not_called()
    assert list(tmp_path.iterdir()) == []
    output = capsys.readouterr()
    assert output.out == ""
    assert "was retired" in output.err
    assert "devcapsule project --path DIRECTORY run" in output.err
    assert "devcapsule project --path DIRECTORY init" in output.err


def test_pycharm_help_lists_only_retained_image_utilities(capsys) -> None:
    assert cli.main(["pycharm", "--help"]) == 0
    output = capsys.readouterr().out
    assert "build" in output
    assert "check-runtime" in output
    assert not any(line.split()[:1] == ["run"] for line in output.splitlines())


def test_project_run_image_is_retired(tmp_path, capsys) -> None:
    assert cli.main(["project", "--path", str(tmp_path), "--help"]) == 0
    assert "run-image" not in capsys.readouterr().out
    assert cli.main(["project", "--path", str(tmp_path), "run-image", "unused"]) != 0


def test_build_pycharm_uses_python_buildx_builder(tmp_path: Path) -> None:
    source = tmp_path / "pycharm"
    (source / "bin").mkdir(parents=True)
    (source / "bin" / "pycharm.sh").write_text("#!/usr/bin/env bash\n", encoding="utf-8")

    with patch("devcapsule.commands._pycharm.build_pycharm_image") as build_image:
        build_image.return_value = 0
        result = cli.main(
            [
                "pycharm",
                "build",
                "--pycharm",
                str(source),
                "--image",
                "custom:latest",
                "--base-image",
                "ubuntu:24.04",
                "--extra-apt-package",
                "rsync",
            ]
        )

    assert result == 0
    options = build_image.call_args.args[0]
    assert options == PycharmImageBuildOptions(
        pycharm=source.resolve(),
        image="custom:latest",
        base_image="ubuntu:24.04",
        network="default",
        extra_apt_packages=("rsync",),
    )


def test_build_pycharm_accepts_host_network(tmp_path: Path) -> None:
    source = tmp_path / "pycharm"
    (source / "bin").mkdir(parents=True)
    (source / "bin" / "pycharm.sh").write_text("#!/usr/bin/env bash\n", encoding="utf-8")

    with patch("devcapsule.commands._pycharm.build_pycharm_image") as build_image:
        build_image.return_value = 0
        result = cli.main(["pycharm", "build", "--pycharm", str(source), "--network", "host"])

    assert result == 0
    assert build_image.call_args.args[0].network == "host"


def test_runtime_check_pycharm_delegates_to_current_script() -> None:
    with patch.object(compat.subprocess, "run") as run:
        run.return_value.returncode = 0

        result = cli.main(["pycharm", "check-runtime"])

    assert result == 0
    command = run.call_args.args[0]
    assert command[0].endswith("docker4pycharm/check-runtime-deps.sh")
    assert command[1:] == []


def test_bootstrap_project_installs_packaged_workflow(tmp_path: Path) -> None:
    result = cli.main(["bootstrap", "project", "--project", str(tmp_path)])

    assert result == 0
    assert (tmp_path / "WORKFLOW.md").is_file()
    assert (tmp_path / "CURRENT-STATUS.md").is_file()


def test_bootstrap_without_subcommand_uses_current_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    assert cli.main(["bootstrap"]) == 0

    assert (tmp_path / "WORKFLOW.md").is_file()
    assert (tmp_path / "CURRENT-STATUS.md").is_file()


def test_repo_root_can_be_overridden(tmp_path: Path) -> None:
    with patch.dict(os.environ, {"DOCKER4IDES_REPO_ROOT": str(tmp_path)}):
        assert compat.repo_root() == tmp_path.resolve()


def test_top_level_commands_are_discovered() -> None:
    commands = cli.command_names()

    assert "bootstrap" in commands
    assert "pycharm" in commands
    assert "vscode_with_claude" not in commands
    assert "codium_with_claude" not in commands
    assert "project" in commands
    assert "images" in commands
    assert "version" in commands
    assert "init" not in commands
    assert "lock" not in commands
    assert "config" not in commands
    assert "state" not in commands
    assert "run" not in commands
    assert "run-image" not in commands
    assert "build-base" not in commands
    assert "bootstrap-project" not in commands
    assert "build" not in commands
    assert "check" not in commands


def test_capability_first_dogfood_init_resolve_and_run(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    config_home = tmp_path / "config"
    state_roots = {slot: tmp_path / slot.replace("/", "-") for slot in (
        "home", "pycharm/config", "pycharm/plugins", "pycharm/system", "pycharm/log", "pycharm/cache"
    )}
    for path in state_roots.values():
        path.mkdir()

    env = {
        "DISPLAY": ":1",
        "HOME": str(tmp_path / "host-home"),
        "XDG_CONFIG_HOME": str(config_home),
        "XDG_DATA_HOME": str(tmp_path / "data"),
        "PYCHARM_GIT_IDENTITY_FROM_HOST": "0",
    }
    target = project / ".devcapsule"
    target.mkdir()
    (target / "devcapsule.toml").write_text(
        "\n".join(
            [
                "devcapsule-schema-version = 1",
                "",
                "[capabilities]",
                'need = ["python", "python-ide"]',
                "",
                "[project]",
                'name = "project"',
                'slug = "project"',
                'creator = "mailto:dev@example.test"',
                'mount = "/workspace/existing"',
                "",
                '[configuration.values."runtime.memory-limit"]',
                'type = "memory-size"',
                'runtime-effect = "docker.memory-limit"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    import tomllib

    with (target / "devcapsule.toml").open("rb") as stream:
        manifest_value = tomllib.load(stream)
    (target / "devcapsule.linux-amd64.lock").write_text(
        "\n".join(
            [
                "devcapsule-lock-format-version = 1",
                'resolution-matrix-version = "dogfood-v1"',
                f'manifest-digest = "{canonical_digest(manifest_value)}"',
                'platform = "linux-amd64"',
                "",
                "[image]",
                'reference = "local/pycharm:dogfood"',
                "",
                "[components]",
                'interactive-surface = "pycharm"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    with patch.dict(os.environ, env, clear=False):
        for slot, path in state_roots.items():
            assert cli.main([
                "project", "--path", str(project), "config", "bind", slot,
                f"host-directory:{path}",
            ]) == 0
        assert cli.main([
            "project", "--path", str(project), "config", "set", "memory", "8GiB"
        ]) == 0
        assert run_until_prepared(project) == 0

        with (
            patch("devcapsule.launch.pycharm._launcher.shutil.which", return_value=None),
            patch("devcapsule.launch.pycharm._launcher.run_attached") as run,
        ):
            run.return_value = AttachedResult(0, interrupted=False, stopped=True)
            assert cli.main(
                [
                    "project", "--path", str(project), "run",
                    "--set", "memory", "4GiB",
                    "--", "--cap-add", "SYS_PTRACE",
                ]
            ) == 0

    command = run.call_args.args[0]
    assert "local/pycharm:dogfood" in command
    assert command[command.index("--network") + 1] == "bridge"
    # The run-once --set answer overrides the resolved 8GiB for this launch.
    assert command[command.index("--memory") + 1] == str(4 * 1024**3)
    # The tail after '--' is handed verbatim to docker run, in the options
    # region before the image.
    assert command[command.index("--cap-add") + 1] == "SYS_PTRACE"
    assert command.index("--cap-add") < command.index("local/pycharm:dogfood")
    assert f"type=bind,src={state_roots['home'].resolve()},dst=/home/devcapsule" in command
    assert f"type=bind,src={state_roots['pycharm/system'].resolve()},dst=/ide-project-state/system" in command


def test_noun_first_pycharm_command_order_is_not_supported() -> None:
    assert cli.main(["run", "pycharm"]) == 2
    assert cli.main(["build", "pycharm"]) == 2
    assert cli.main(["check", "runtime", "pycharm"]) == 2


def test_images_list_prints_managed_local_inventory(capsys) -> None:
    record = LocalImageRecord(
        kind="base",
        canonical_name="devcapsule-base:debug-v019",
        aliases=("devcapsule-base:test",),
        image_id="1234567890ab",
        component="-",
        recipe="1",
        created="2026-08-01",
        size="1.0 GiB",
    )
    with patch("devcapsule.commands.images.list_local_images", return_value=(record,)) as list_images:
        result = cli.main(["images", "list", "--include-legacy"])

    assert result == 0
    list_images.assert_called_once_with(include_legacy=True)
    output = capsys.readouterr().out
    assert "CANONICAL" in output
    assert "devcapsule-base:debug-v019" in output
    assert "devcapsule-base:test" in output
    assert "1234567890ab" in output


def test_images_build_base_maps_cli_options(tmp_path: Path, capsys) -> None:
    pex = tmp_path / "devcapsule.pex"
    pex.write_bytes(b"pex")
    inspected = SimpleNamespace(
        id="sha256:abc123",
        config=SimpleNamespace(
            labels={
                "devcapsule.base.recipe-version": "1",
                "devcapsule.pex.build-mnemonic": "v026",
                "devcapsule.pex.sha256": "a" * 64,
                "devcapsule.source.revision": "revision-1",
            }
        ),
    )

    with (
        patch("devcapsule.commands.images.build_base_image") as build,
        patch("devcapsule.commands.images.inspect_local_image", return_value=inspected),
    ):
        result = cli.main(
            [
                "images",
                "build",
                "--type",
                "base",
                "--tag",
                "devcapsule-base:debug-v019",
                "--from",
                "local-root:test",
                "--pex",
                str(pex),
                "--source-revision",
                "revision-1",
                "--network",
                "host",
            ]
        )

    assert result == 0
    options = build.call_args.args[0]
    assert options.pex == pex.resolve()
    assert options.image == "devcapsule-base:debug-v019"
    assert options.root_image == "local-root:test"
    assert options.source_revision == "revision-1"
    assert options.allow_local_source is False
    assert options.recipe == "ubuntu-24.04"
    assert build.call_args.kwargs == {"network": "host", "platform": Platform.LINUX_AMD64}
    output = capsys.readouterr().out
    assert "Image ID: sha256:abc123" in output
    assert "Runtime: supplied by the launcher" in output
    assert "Source verification: public GitHub commit reachable" in output


def test_images_build_base_selects_wip_nvidia_cuda_recipe(tmp_path: Path, capsys) -> None:
    pex = tmp_path / "devcapsule.pex"
    pex.write_bytes(b"pex")
    inspected = SimpleNamespace(
        id="sha256:cuda123",
        config=SimpleNamespace(
            labels={
                "devcapsule.base.recipe": "nvidia-cuda-devel",
                "devcapsule.base.recipe-version": "1",
                "devcapsule.base.recipe-status": "wip",
            }
        ),
    )

    with (
        patch("devcapsule.commands.images.build_base_image") as build,
        patch("devcapsule.commands.images.inspect_local_image", return_value=inspected),
    ):
        result = cli.main(
            [
                "images",
                "build",
                "--type",
                "base",
                "--recipe",
                "nvidia-cuda-devel",
                "--tag",
                "devcapsule-base:cuda",
                "--pex",
                str(pex),
                "--source-revision",
                "a" * 40,
            ]
        )

    assert result == 0
    options = build.call_args.args[0]
    assert options.recipe == "nvidia-cuda-devel"
    assert options.root_image is None
    captured = capsys.readouterr()
    assert "nvidia/cuda:12.8.1-devel-ubuntu24.04" in captured.out
    assert "nvidia-cuda-devel@1 (WIP)" in captured.out
    assert "requires specialized NVIDIA GPU E2E validation" in captured.err


def test_images_build_base_requires_pex_from_source(tmp_path: Path, capsys) -> None:
    with patch("devcapsule.commands.images.sys.argv", [str(tmp_path / "devcapsule")]):
        result = cli.main(
            [
                "images",
                "build",
                "--type",
                "base",
                "--tag",
                "test:latest",
                "--source-revision",
                "a" * 40,
            ]
        )

    assert result == 2
    assert "Expected source revision" in capsys.readouterr().err


def test_images_build_base_defaults_to_running_pex(tmp_path: Path, capsys) -> None:
    pex = tmp_path / "devcapsule.pex"
    with zipfile.ZipFile(pex, "w") as archive:
        archive.writestr("PEX-INFO", "{}")
    inspected = SimpleNamespace(id="sha256:abc", config=SimpleNamespace(labels={}))

    with (
        patch("devcapsule.commands.images.sys.argv", [str(pex)]),
        patch("devcapsule.commands.images.build_base_image") as build,
        patch("devcapsule.commands.images.inspect_local_image", return_value=inspected),
    ):
        assert (
            cli.main(
                ["images", "build", "--type", "base", "--tag", "test:latest", "--allow-local-source"]
            )
            == 0
        )

    assert build.call_args.args[0].pex is None
    assert build.call_args.args[0].recipe == "ubuntu-24.04"
    assert build.call_args.args[0].allow_local_source is True
    assert "Source verification: bypassed for explicit local source" in capsys.readouterr().out


def test_images_build_base_requires_public_revision_by_default(tmp_path: Path, capsys) -> None:
    pex = tmp_path / "devcapsule.pex"
    pex.write_bytes(b"pex")

    result = cli.main(
        ["images", "build", "--type", "base", "--tag", "test:latest", "--pex", str(pex)]
    )

    assert result == 2
    assert "--source-revision is required" in capsys.readouterr().err


def test_images_build_environment_uses_fresh_project_lock_and_verified_base(tmp_path: Path, capsys) -> None:
    base_reference = f"docker.io/example/devcapsule-base@sha256:{'b' * 64}"
    lock = {
        "platform": "linux-amd64",
        "base": {"reference": base_reference, "identity": "sha256:base"},
        "components": {
            "interactive-surface": "pycharm",
            "pycharm": {
                "version": "2026.2.0.1",
                "variant": "professional",
                "delivery-policy": "local-materialization",
                "url": "https://example.test/pycharm.tar.gz",
                "sha256": "a" * 64,
            },
        },
        "materialization": {"recipe": "jetbrains-local-materialization", "recipe-version": "1"},
    }
    checkout = {
        "authorization": {
            "base-image": {
                "reference": base_reference,
                "lock-digest": canonical_digest(lock),
            }
        }
    }
    project = SimpleNamespace(
        lock=lock,
        checkout=checkout,
        resolution={"runtime": {"component": "pycharm"}},
    )
    base = ImageDetails(
        base_reference,
        "sha256:base",
        {
            "devcapsule.image.managed": "true",
            "devcapsule.metadata.version": "1",
            "devcapsule.image.kind": "base",
        },
        "linux",
        "amd64",
    )
    completed = ImageDetails(
        "devcapsule-local-pycharm:0123456789abcdef0123",
        "sha256:environment",
        {"devcapsule.materialization.identity": "f" * 64},
        "linux",
        "amd64",
    )
    realized = RealizedEnvironment(
        image=completed,
        base=base,
        base_reference=base_reference,
        locked=parse_locked_environment(lock),
        cache=tmp_path / "cache" / "devcapsule",
        created=True,
        explicit_base_override=False,
    )

    with (
        patch("devcapsule.commands.images.fresh_resolved_project", return_value=project) as fresh,
        patch("devcapsule.commands.images.realize_environment", return_value=realized) as realize,
        patch("devcapsule.commands.images._add_alias") as add_alias,
    ):
        result = cli.main(
            [
                "images",
                "build",
                "--type",
                "environment",
                "--project",
                str(tmp_path / "project"),
                "--alias",
                "devcapsule-local-pycharm:debug-v019",
            ]
        )

    assert result == 0
    fresh.assert_called_once_with(tmp_path / "project")
    realize.assert_called_once_with(project, base_override=None, report=print)
    add_alias.assert_called_once_with(completed, "devcapsule-local-pycharm:debug-v019")
    output = capsys.readouterr().out
    assert "Built DevCapsule environment image" in output
    assert "No container was launched" in output


def test_images_build_environment_requires_immutable_locked_base(capsys) -> None:
    lock = {
        "platform": "linux-amd64",
        "base": {"reference": "devcapsule-base:debug-v019"},
        "components": {
            "interactive-surface": "pycharm",
            "pycharm": {
                "version": "2026.2.0.1",
                "variant": "professional",
                "delivery-policy": "local-materialization",
                "url": "https://example.test/pycharm.tar.gz",
                "sha256": "a" * 64,
            },
        },
        "materialization": {"recipe": "jetbrains-local-materialization", "recipe-version": "1"},
    }
    project = SimpleNamespace(
        root=Path("/example/project"),
        manifest={},
        lock=lock,
        checkout={},
        resolution={"runtime": {"component": "pycharm"}},
    )
    with patch("devcapsule.commands.images.fresh_resolved_project", return_value=project):
        result = cli.main(["images", "build", "--type", "environment"])

    assert result == 2
    assert "committed locks must end with one immutable" in capsys.readouterr().err


def test_images_build_environment_requires_checkout_base_authorization(capsys) -> None:
    base_reference = f"docker.io/example/devcapsule-base@sha256:{'b' * 64}"
    lock = {
        "platform": "linux-amd64",
        "base": {"reference": base_reference},
        "components": {
            "interactive-surface": "pycharm",
            "pycharm": {
                "version": "2026.2.0.1",
                "variant": "professional",
                "delivery-policy": "local-materialization",
                "url": "https://example.test/pycharm.tar.gz",
                "sha256": "a" * 64,
            },
        },
        "materialization": {"recipe": "jetbrains-local-materialization", "recipe-version": "1"},
    }
    project = SimpleNamespace(
        root=Path("/example/project"),
        manifest={},
        lock=lock,
        checkout={},
        resolution={"runtime": {"component": "pycharm"}},
    )
    with (
        patch("devcapsule.commands.images.fresh_resolved_project", return_value=project),
        patch("devcapsule.environment_realization.ensure_local_image") as obtain,
    ):
        result = cli.main(["images", "build", "--type", "environment"])

    assert result == 2
    assert "config authorize base-image" in capsys.readouterr().err
    obtain.assert_not_called()


def test_images_build_environment_allows_explicit_local_base_override(tmp_path: Path, capsys) -> None:
    locked_reference = f"docker.io/example/devcapsule-base@sha256:{'b' * 64}"
    lock = {
        "platform": "linux-amd64",
        "base": {"reference": locked_reference},
        "components": {
            "interactive-surface": "pycharm",
            "pycharm": {
                "version": "2026.2.0.1",
                "variant": "professional",
                "delivery-policy": "local-materialization",
                "url": "https://example.test/pycharm.tar.gz",
                "sha256": "a" * 64,
            },
        },
        "materialization": {"recipe": "jetbrains-local-materialization", "recipe-version": "1"},
    }
    project = SimpleNamespace(
        root=Path("/example/project"),
        manifest={},
        lock=lock,
        checkout={},
        resolution={"runtime": {"component": "pycharm"}},
    )
    base = ImageDetails(
        "local/devcapsule-base:test",
        "sha256:local-base",
        {
            "devcapsule.image.managed": "true",
            "devcapsule.metadata.version": "1",
            "devcapsule.image.kind": "base",
        },
        "linux",
        "amd64",
    )
    completed = ImageDetails(
        "devcapsule-local-pycharm:0123456789abcdef0123",
        "sha256:environment",
        {"devcapsule.materialization.identity": "f" * 64},
        "linux",
        "amd64",
    )
    realized = RealizedEnvironment(
        image=completed,
        base=base,
        base_reference="local/devcapsule-base:test",
        locked=parse_locked_environment(lock),
        cache=tmp_path / "home" / ".cache" / "devcapsule",
        created=False,
        explicit_base_override=True,
    )
    with (
        patch("devcapsule.commands.images.fresh_resolved_project", return_value=project),
        patch("devcapsule.commands.images.realize_environment", return_value=realized) as realize,
    ):
        result = cli.main(
            [
                "images",
                "build",
                "--type",
                "environment",
                "--base",
                "local/devcapsule-base:test",
            ]
        )

    assert result == 0
    realize.assert_called_once_with(project, base_override="local/devcapsule-base:test", report=print)
    assert "Base selection: explicit developer override" in capsys.readouterr().err


def test_bootstrap_project_alias_is_not_supported() -> None:
    assert cli.main(["bootstrap-project", "--project", "/tmp/example"]) == 2


def test_vscode_with_claude_is_retired() -> None:
    # Retired 2026-08-31 by the product owner: it was a registered stub that
    # never gained an image or launcher; the codium component supersedes it.
    assert cli.main(["vscode_with_claude", "--help"]) == 2


def test_build_pex_script_is_available() -> None:
    script = Path(__file__).resolve().parents[1] / "scripts" / "build-pex.sh"

    assert script.exists()
    assert os.access(script, os.X_OK)

    completed = subprocess.run(
        [str(script), "--help"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    assert completed.returncode == 0
    assert "dist/devcapsule.pex" in completed.stdout
    assert "needs neither host Python nor a first-run download" in completed.stdout
    assert "--allow-unpublished-revision" in completed.stdout
    assert "--allow-local-source" in completed.stdout
    assert "--release-mnemonic" in completed.stdout
