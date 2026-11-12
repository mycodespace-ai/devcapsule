from __future__ import annotations

from tests.launch_preparation import run_until_prepared

import os
import re
import json
from pathlib import Path
import shutil
import tomllib
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from devcapsule import cli
from devcapsule.components.codex import CODEX_CONFIG_SEED
from devcapsule.launch.pycharm import DockerMode
from devcapsule.materialization import ImageDetails, parse_locked_environment
from devcapsule.configuration.file_formats import (
    ProjectConfigurationError,
    canonical_digest,
)
from devcapsule.configuration.authorization import (
    immutable_registry_reference,
)
from devcapsule.configuration.resolution import Resolution
from devcapsule.configuration.storage import (
    registered_checkouts,
)
from devcapsule.project import project_namespace

pytestmark = pytest.mark.legacy


LOCKED_BASE = f"docker.io/example/devcapsule-base@sha256:{'b' * 64}"


def initialize_project(project: Path) -> None:
    """Author the legacy dogfood project fixture directly.

    A hand-authored manifest is the ordinary partially-initialized form the
    v027 init honors, and the image-reference lock is the retired lock stub's
    output shape, kept as a compatibility fixture now that the stub is gone.
    """

    target = project / ".devcapsule"
    target.mkdir(parents=True, exist_ok=True)
    manifest_lines = [
        "devcapsule-schema-version = 1",
        "",
        "[capabilities]",
        'need = ["python", "python-ide"]',
        "",
        "[project]",
        f'name = "{project.name}"',
        f'slug = "{project.name.lower()}"',
        'creator = "mailto:dev@example.test"',
        'mount = "/workspace/project"',
        "",
    ]
    (target / "devcapsule.toml").write_text("\n".join(manifest_lines), encoding="utf-8")
    with (target / "devcapsule.toml").open("rb") as stream:
        manifest = tomllib.load(stream)
    lock_lines = [
        "devcapsule-lock-format-version = 1",
        'resolution-matrix-version = "dogfood-v1"',
        f'manifest-digest = "{canonical_digest(manifest)}"',
        'platform = "linux-amd64"',
        "",
        "[image]",
        'reference = "local/pycharm:dogfood"',
        "",
        "[components]",
        'interactive-surface = "pycharm"',
        "",
    ]
    (target / "devcapsule.linux-amd64.lock").write_text(
        "\n".join(lock_lines), encoding="utf-8"
    )


def write_formation_lock(project: Path, reference: str = LOCKED_BASE) -> Path:
    manifest_path = project / ".devcapsule" / "devcapsule.toml"
    with manifest_path.open("rb") as stream:
        manifest = tomllib.load(stream)
    lock_path = project / ".devcapsule" / "devcapsule.linux-amd64.lock"
    lock_path.write_text(
        "\n".join(
            [
                "devcapsule-lock-format-version = 1",
                'resolution-matrix-version = "formation-v1"',
                f'manifest-digest = "{canonical_digest(manifest)}"',
                'platform = "linux-amd64"',
                "",
                "[base]",
                f'reference = "{reference}"',
                'build-mnemonic = "v026"',
                "",
                "[components]",
                'interactive-surface = "pycharm"',
                "",
                "[components.pycharm]",
                'version = "2026.2.0.1"',
                'variant = "professional"',
                'delivery-policy = "local-materialization"',
                'url = "https://example.test/pycharm.tar.gz"',
                f'sha256 = "{"a" * 64}"',
                "",
                "[materialization]",
                'recipe = "jetbrains-local-materialization"',
                'recipe-version = "1"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    return lock_path


def select_codex_component(project: Path) -> None:
    lock_path = project / ".devcapsule" / "devcapsule.linux-amd64.lock"
    with lock_path.open("a", encoding="utf-8") as stream:
        stream.write(
            """
[components.codex]
version = "0.145.0"
delivery-policy = "local-materialization"
npm-package = "@openai/codex"
url = "https://example.test/codex-0.145.0.tgz"
sha256 = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"

[components.codex.artifacts.linux-amd64]
npm-package = "@openai/codex-linux-x64"
url = "https://example.test/codex-0.145.0-linux-x64.tgz"
sha256 = "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"
"""
        )


def append_manifest_metadata(project: Path, declaration: str) -> None:
    manifest_path = project / ".devcapsule" / "devcapsule.toml"
    with manifest_path.open("a", encoding="utf-8") as stream:
        stream.write(f"\n{declaration.strip()}\n")
    with manifest_path.open("rb") as stream:
        manifest = tomllib.load(stream)
    lock_path = project / ".devcapsule" / "devcapsule.linux-amd64.lock"
    lines = lock_path.read_text(encoding="utf-8").splitlines()
    lines = [
        f'manifest-digest = "{canonical_digest(manifest)}"'
        if line.startswith("manifest-digest = ")
        else line
        for line in lines
    ]
    lock_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_project_resolve_registers_default_checkout_and_list_uses_registry(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    config_home = tmp_path / "config"
    env = {
        "HOME": str(tmp_path / "home"),
        "XDG_CONFIG_HOME": str(config_home),
        "XDG_DATA_HOME": str(tmp_path / "data"),
    }

    with patch.dict(os.environ, env, clear=False):
        initialize_project(project)
        nested = project / "src" / "package"
        nested.mkdir(parents=True)
        monkeypatch.chdir(nested)

        assert run_until_prepared() == 0
        records = registered_checkouts()
        assert len(records) == 1
        assert records[0].checkout_name == "default"
        assert records[0].checkout_path == project.resolve()
        assert records[0].status == "ready"

        capsys.readouterr()
        assert cli.main(["project", "list"]) == 0
        output = capsys.readouterr().out
        assert "PROJECT" in output
        assert "mailto:dev@example.test/project" in output
        assert str(project.resolve()) in output
        assert "ready" in output


def test_named_checkout_registration_selects_distinct_record_and_reports_missing(
    tmp_path: Path,
    capsys,
    monkeypatch,
) -> None:
    # The launcher fixture owns this cwd; do not select the enclosing dogfood
    # capsule's actual project when exercising the global list command.
    monkeypatch.chdir(tmp_path)
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    config_home = tmp_path / "config"
    env = {"HOME": str(tmp_path / "home"), "XDG_CONFIG_HOME": str(config_home)}

    with patch.dict(os.environ, env, clear=False):
        initialize_project(first)
        shutil.copytree(first / ".devcapsule", second / ".devcapsule")
        assert run_until_prepared(first) == 0

        assert (
            cli.main(
                [
                    "project",
                    "--path",
                    str(second),
                    "checkout",
                    "register",
                    "second-checkout",
                ]
            )
            == 0
        )
        assert run_until_prepared(second) == 0

        records = registered_checkouts()
        assert [(record.checkout_name, record.checkout_path) for record in records] == [
            ("default", first.resolve()),
            ("second-checkout", second.resolve()),
        ]

        shutil.rmtree(second)
        capsys.readouterr()
        assert cli.main(["project", "list"]) == 0
        output = capsys.readouterr().out
        assert "default" in output
        assert "second-checkout" in output
        assert "missing" in output


def test_project_list_does_not_scan_unregistered_source_trees(tmp_path: Path, capsys, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    project = tmp_path / "unregistered"
    project.mkdir()
    config_home = tmp_path / "config"
    env = {"HOME": str(tmp_path / "home"), "XDG_CONFIG_HOME": str(config_home)}

    with patch.dict(os.environ, env, clear=False):
        initialize_project(project)
        capsys.readouterr()
        assert cli.main(["project", "list"]) == 0

    assert "No registered DevCapsule project checkouts" in capsys.readouterr().out


def test_project_config_list_writes_nothing_and_lists_from_nothing(
    tmp_path: Path, capsys
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    config_home = tmp_path / "config"
    env = {"HOME": str(tmp_path / "home"), "XDG_CONFIG_HOME": str(config_home)}

    with patch.dict(os.environ, env, clear=False):
        initialize_project(project)
        append_manifest_metadata(
            project,
            """
            [configuration.values."runtime.memory-limit"]
            type = "memory-size"
            runtime-effect = "docker.memory-limit"

            [host.docker.mode.recommended]
            value = "host-socket"
            justification = "Run peer development containers."
            """,
        )
        write_formation_lock(project)
        select_codex_component(project)

        assert cli.main(["project", "--path", str(project), "config", "show"]) == 0
        output = capsys.readouterr().out
        assert "Checkout name: default" in output
        assert "Checkout record:" in output
        # The legacy memory declaration is the memory row; nothing is set yet.
        assert "runtime.memory-limit" not in output
        assert re.search(r"^memory\s+memory\s+no limit\s+none", output, re.M)
        assert re.search(r"^binding\s+home\s+managed directory\s+managed default", output, re.M)
        assert re.search(r"^secret\s+codex/openai-api-key\s+unbound", output, re.M)
        assert re.search(r"^access\s+docker-daemon\s+none\s+secure default; project recommends host-socket", output, re.M)
        assert "the project asks for docker-daemon host-socket; allow or deny" in output
        assert "config authorize base-image default" in output
        # The listing is read-only: no record and no placeholder exist afterwards.
        assert registered_checkouts() == ()
        assert not list(config_home.rglob("*.toml"))


def _listing_document(project: Path, capsys) -> tuple[dict, str]:
    assert cli.main(["project", "--path", str(project), "config", "show", "--json"]) == 0
    captured = capsys.readouterr()
    return json.loads(captured.out), captured.err


def test_project_config_list_json_carries_the_listing(
    tmp_path: Path, capsys
) -> None:
    """``--json`` is the contract the web console reads: schema version 2,
    the identity, and every row of the text table under the same columns."""
    project = tmp_path / "project"
    project.mkdir()
    env = {"HOME": str(tmp_path / "home"), "XDG_CONFIG_HOME": str(tmp_path / "config")}

    with patch.dict(os.environ, env, clear=False):
        initialize_project(project)
        append_manifest_metadata(
            project,
            """
            [configuration.values."runtime.memory-limit"]
            type = "memory-size"
            runtime-effect = "docker.memory-limit"
            """,
        )
        write_formation_lock(project)
        select_codex_component(project)

        document, stderr = _listing_document(project, capsys)
        assert stderr == ""
        assert document["schema-version"] == 2
        assert document["context"] == "host selection (next launch)"
        assert document["project"] == {"creator": "mailto:dev@example.test", "slug": "project"}
        assert document["checkout"]["name"] == "default"
        assert document["checkout"]["launcher-path"] == str(project.resolve())
        rows = {(row["kind"], row["name"]): row for row in document["rows"]}
        assert set(rows[("memory", "memory")]) == {"kind", "name", "effective", "source", "pending", "command"}
        assert rows[("memory", "memory")]["effective"] == "no limit"
        assert rows[("secret", "codex/openai-api-key")]["source"] == "component (optional)"
        assert rows[("access", "base-image")]["pending"]
        assert "base-image" in document["pending"]

        # The JSON names the same rows the text table prints, in the same order.
        assert cli.main(["project", "--path", str(project), "config", "show"]) == 0
        text = capsys.readouterr().out
        table = text[text.index("KIND"):text.index("\nPending decisions:")].splitlines()
        kinds = {row["kind"] for row in document["rows"]}
        printed = [line for line in table[1:] if line.split()[:1] and line.split()[0] in kinds]
        assert [line.split()[:2] for line in printed] == [[row["kind"], row["name"]] for row in document["rows"]]

        assert cli.main(["project", "--path", str(project), "config", "set", "memory", "2GiB"]) == 0
        capsys.readouterr()
        changed, _ = _listing_document(project, capsys)
        memory = {(row["kind"], row["name"]): row for row in changed["rows"]}[("memory", "memory")]
        assert (memory["effective"], memory["source"]) == ("2GiB", "checkout")


@pytest.mark.parametrize("name", ["second-checkout", "devcapsule"])
def test_project_config_list_json_names_a_registered_checkout(tmp_path: Path, capsys, name: str) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    env = {"HOME": str(tmp_path / "home"), "XDG_CONFIG_HOME": str(tmp_path / "config")}

    with patch.dict(os.environ, env, clear=False):
        initialize_project(first)
        shutil.copytree(first / ".devcapsule", second / ".devcapsule")
        assert cli.main(["project", "--path", str(first), "config", "set", "memory", "1GiB"]) == 0
        assert cli.main(["project", "--path", str(second), "checkout", "register", name]) == 0
        capsys.readouterr()
        document, _ = _listing_document(second, capsys)
        assert document["checkout"]["name"] == name
        assert document["checkout"]["launcher-path"] == str(second.resolve())
        assert document["checkout"]["input"].endswith(f"{name}.checkout.toml")
        assert next(record for record in registered_checkouts() if record.checkout_path == second).checkout_name == name
        assert cli.main(["project", "--path", str(second), "config", "show"]) == 0
        assert f"Checkout name: {name}\n" in capsys.readouterr().out

    # An explicit registry environment must also govern name derivation.
    with patch.dict(os.environ, {"XDG_CONFIG_HOME": str(tmp_path / "unrelated-config")}):
        records = registered_checkouts(env)
        assert [(record.checkout_name, record.checkout_path) for record in records] == sorted([
            ("default", first), (name, second),
        ])


def test_checkout_record_name_rejects_a_non_record_path() -> None:
    from devcapsule.configuration.storage import checkout_record_name

    with pytest.raises(ValueError, match="not a DevCapsule checkout record path"):
        checkout_record_name(Path("devcapsule.resolved.toml"))


@pytest.mark.parametrize("command", [("config", "show"), ("versions", "show")])
def test_json_help_names_the_schema_contract(command, capsys) -> None:
    assert cli.main(["project", *command, "--help"]) == 0
    help_text = capsys.readouterr().out
    assert "--json" in help_text
    assert "schema-version1" in "".join(help_text.split())


def test_project_config_list_names_a_registered_second_checkout(
    tmp_path: Path, capsys
) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    config_home = tmp_path / "config"
    env = {"HOME": str(tmp_path / "home"), "XDG_CONFIG_HOME": str(config_home)}

    with patch.dict(os.environ, env, clear=False):
        initialize_project(first)
        shutil.copytree(first / ".devcapsule", second / ".devcapsule")
        assert cli.main(["project", "--path", str(first), "config", "set", "memory", "1GiB"]) == 0
        # The second checkout is listed from nothing while the default record is the first's.
        assert cli.main(["project", "--path", str(second), "config", "show"]) == 0
        assert "Checkout name: (unregistered)" in capsys.readouterr().out
        assert (
            cli.main(
                ["project", "--path", str(second), "checkout", "register", "second-checkout"]
            )
            == 0
        )
        capsys.readouterr()
        assert cli.main(["project", "--path", str(second), "config", "show"]) == 0
        output = capsys.readouterr().out
        assert "Checkout name: second-checkout" in output
        records = {record.checkout_name: record for record in registered_checkouts()}
        assert records["second-checkout"].record_path.name == "second-checkout.checkout.toml"


def test_project_config_list_reports_complete_and_stale_readiness(
    tmp_path: Path, capsys
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    bound_home = tmp_path / "persistent-home"
    bound_home.mkdir()
    config_home = tmp_path / "config"
    env = {"HOME": str(tmp_path / "home"), "XDG_CONFIG_HOME": str(config_home)}

    with patch.dict(os.environ, env, clear=False):
        initialize_project(project)
        append_manifest_metadata(
            project,
            """
            [configuration.values."runtime.memory-limit"]
            type = "memory-size"
            required = true
            runtime-effect = "docker.memory-limit"

            [host.network.mode.recommended]
            value = "host"
            justification = "Reach host-bound development services."
            """,
        )
        write_formation_lock(project)

        assert cli.main(["project", "--path", str(project), "config", "show"]) == 0
        assert "Pending decisions:" in capsys.readouterr().out
        assert (
            cli.main(
                [
                    "project",
                    "--path",
                    str(project),
                    "config",
                    "set",
                    "memory",
                    "8GiB",
                ]
            )
            == 0
        )
        assert (
            cli.main(
                [
                    "project",
                    "--path",
                    str(project),
                    "config",
                    "bind",
                    "home",
                    f"host-directory:{bound_home}",
                ]
            )
            == 0
        )
        for name, value in (("base-image", LOCKED_BASE), ("network", "host")):
            assert (
                cli.main(
                    [
                        "project",
                        "--path",
                        str(project),
                        "config",
                        "authorize",
                        name,
                        value,
                    ]
                )
                == 0
            )
        assert run_until_prepared(project) == 0
        capsys.readouterr()

        assert cli.main(["project", "--path", str(project), "config", "show"]) == 0
        output = capsys.readouterr().out
        assert re.search(r"^memory\s+memory\s+8GiB\s+checkout", output, re.M)
        assert re.search(r"^binding\s+home\s+" + re.escape(str(bound_home)) + r"\s+checkout", output, re.M)
        assert re.search(r"^access\s+base-image\s+\S+\s+checkout", output, re.M)
        assert re.search(r"^access\s+network\s+host\s+checkout", output, re.M)

        record = registered_checkouts()[0].record_path
        checkout_text = record.read_text(encoding="utf-8")
        with record.open("rb") as stream:
            checkout = tomllib.load(stream)
        recommendation_digest = checkout["authorization"]["network"]["recommendation-digest"]
        record.write_text(
            checkout_text.replace(recommendation_digest, "0" * 64),
            encoding="utf-8",
        )

        assert cli.main(["project", "--path", str(project), "config", "show"]) == 0
        output = capsys.readouterr().out
        network_row = next(line for line in output.splitlines() if re.match(r"^access\s+network\s", line))
        assert "kept" in network_row  # the answer stands under the changed recommendation


def test_project_resolve_accepts_formation_lock_without_completed_image(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    config_home = tmp_path / "config"
    env = {"HOME": str(tmp_path / "home"), "XDG_CONFIG_HOME": str(config_home)}

    with patch.dict(os.environ, env, clear=False):
        initialize_project(project)
        write_formation_lock(project)
        assert cli.main(["project", "--path", str(project), "config", "authorize", "base-image", "default"]) == 0

        assert run_until_prepared(project) == 0

        records = registered_checkouts()
        resolved_path = records[0].record_path.with_name("devcapsule.resolved.toml")
        with resolved_path.open("rb") as stream:
            resolved = tomllib.load(stream)
        assert resolved["runtime"]["component"] == "pycharm"
        assert "image" not in resolved["runtime"]


def initialize_codium_project(project: Path) -> Path:
    """Author a frontend project whose formation lock selects codium."""

    target = project / ".devcapsule"
    target.mkdir(parents=True, exist_ok=True)
    manifest_lines = [
        "devcapsule-schema-version = 1",
        "",
        "[capabilities]",
        'need = ["node", "frontend-ide"]',
        "",
        "[project]",
        f'name = "{project.name}"',
        f'slug = "{project.name.lower()}"',
        'creator = "mailto:dev@example.test"',
        'mount = "/workspace/project"',
        "",
    ]
    (target / "devcapsule.toml").write_text("\n".join(manifest_lines), encoding="utf-8")
    with (target / "devcapsule.toml").open("rb") as stream:
        manifest = tomllib.load(stream)
    lock_path = target / "devcapsule.linux-amd64.lock"
    lock_path.write_text(
        "\n".join(
            [
                "devcapsule-lock-format-version = 1",
                'resolution-matrix-version = "formation-v1"',
                f'manifest-digest = "{canonical_digest(manifest)}"',
                'platform = "linux-amd64"',
                "",
                "[base]",
                f'reference = "{LOCKED_BASE}"',
                'build-mnemonic = "v026"',
                "",
                "[components]",
                'interactive-surface = "codium"',
                "",
                "[components.codium]",
                'version = "1.126.04524"',
                'license = "MIT"',
                'delivery-policy = "local-materialization"',
                'url = "https://example.test/codium.tar.gz"',
                f'sha256 = "{"c" * 64}"',
                "",
                "[materialization]",
                'recipe = "vscode-local-materialization"',
                'recipe-version = "2"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    return lock_path


def test_project_run_starts_immediately_after_init(tmp_path: Path, capsys) -> None:
    """Init's postcondition is run-readiness: no 'project run' in between."""

    project = tmp_path / "fresh-project"
    project.mkdir()
    env = {
        "HOME": str(tmp_path / "home"),
        "XDG_CONFIG_HOME": str(tmp_path / "config"),
        "XDG_DATA_HOME": str(tmp_path / "data"),
        "XDG_STATE_HOME": str(tmp_path / "state"),
    }
    with patch.dict(os.environ, env, clear=False):
        assert (
            cli.main(
                [
                    "project",
                    "--path",
                    str(project),
                    "init",
                    "--require",
                    "python",
                    "--ide",
                    "python-ide",
                    "--creator",
                    "https://github.com/example",
                    "--authorize",
                    "base-image",
                    "default",
                ]
            )
            == 0
        )
        capsys.readouterr()
        from devcapsule.configuration.execution import ExecutionConfiguration
        # The shared lock is project-only; the checkout's effective lock carries the IDE.
        effective_lock = ExecutionConfiguration.load(project).project.lock
        realized = SimpleNamespace(
            image=SimpleNamespace(labels={}, reference="devcapsule-local-pycharm:0123456789abcdef0123"),
            created=True,
            locked=parse_locked_environment(effective_lock),
        )

        with (
            patch("devcapsule.commands.project.realize_environment", return_value=realized),
            patch("devcapsule.commands.project.run_pycharm", return_value=0),
        ):
            assert cli.main(["project", "--path", str(project), "run"]) == 0


def test_project_run_records_known_good_configuration_only_on_success(
    tmp_path: Path, capsys
) -> None:
    project = tmp_path / "history-project"
    project.mkdir()
    env = {
        "HOME": str(tmp_path / "home"),
        "XDG_CONFIG_HOME": str(tmp_path / "config"),
        "XDG_DATA_HOME": str(tmp_path / "data"),
        "XDG_STATE_HOME": str(tmp_path / "state"),
    }
    history_root = tmp_path / "state" / "devcapsule" / "config-history"

    with patch.dict(os.environ, env, clear=False):
        lock_path = initialize_codium_project(project)
        assert (
            cli.main(
                ["project", "--path", str(project), "config", "authorize", "base-image", LOCKED_BASE]
            )
            == 0
        )
        assert run_until_prepared(project) == 0
        realized = SimpleNamespace(
            image=SimpleNamespace(labels={}, reference="devcapsule-local-codium:0123456789abcdef0123"),
            created=True,
            locked=parse_locked_environment(tomllib.loads(lock_path.read_text(encoding="utf-8"))),
        )
        capsys.readouterr()

        with (
            patch("devcapsule.commands.project.realize_environment", return_value=realized),
            patch("devcapsule.commands.project.run_pycharm", return_value=3),
        ):
            assert cli.main(["project", "--path", str(project), "run"]) == 3
        # A failed session proves nothing; no generation appears.
        assert not history_root.exists()

        with (
            patch("devcapsule.commands.project.realize_environment", return_value=realized),
            patch("devcapsule.commands.project.run_pycharm", return_value=0),
        ):
            assert cli.main(["project", "--path", str(project), "run"]) == 0
        assert "Recorded known-good configuration:" in capsys.readouterr().out
        generations = sorted(history_root.rglob("snapshot.toml"))
        assert len(generations) == 1
        generation = generations[0].parent
        records = registered_checkouts()
        assert (generation / "devcapsule.checkout.toml").read_bytes() == (
            records[0].record_path.read_bytes()
        )
        assert (generation / "devcapsule.resolved.toml").read_bytes() == (
            records[0].record_path.with_name("devcapsule.resolved.toml").read_bytes()
        )

        with (
            patch("devcapsule.commands.project.realize_environment", return_value=realized),
            patch("devcapsule.commands.project.run_pycharm", return_value=0),
        ):
            assert cli.main(["project", "--path", str(project), "run"]) == 0
        # An unchanged configuration succeeding again records nothing new.
        assert "Recorded known-good configuration:" not in capsys.readouterr().out
        assert sorted(history_root.rglob("snapshot.toml")) == generations


def test_project_run_launches_a_codium_surface_from_its_plan_slots(
    tmp_path: Path, capsys
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    env = {
        "HOME": str(tmp_path / "home"),
        "XDG_CONFIG_HOME": str(tmp_path / "config"),
        "XDG_DATA_HOME": str(tmp_path / "data"),
    }
    canonical = "devcapsule-local-codium:0123456789abcdef0123"

    with patch.dict(os.environ, env, clear=False):
        lock_path = initialize_codium_project(project)
        assert (
            cli.main(
                ["project", "--path", str(project), "config", "authorize", "base-image", LOCKED_BASE]
            )
            == 0
        )
        assert run_until_prepared(project) == 0
        records = registered_checkouts()
        resolved_path = records[0].record_path.with_name("devcapsule.resolved.toml")
        with resolved_path.open("rb") as stream:
            resolved = tomllib.load(stream)
        assert resolved["runtime"]["component"] == "codium"
        capsys.readouterr()

        realized = SimpleNamespace(
            image=SimpleNamespace(labels={}, reference=canonical),
            created=True,
            locked=parse_locked_environment(tomllib.loads(lock_path.read_text(encoding="utf-8"))),
        )
        with (
            patch("devcapsule.commands.project.realize_environment", return_value=realized),
            patch("devcapsule.commands.project.run_pycharm", return_value=0) as launch,
        ):
            assert cli.main(["project", "--path", str(project), "run"]) == 0

        options = launch.call_args.args[0]
        assert options.image == canonical
        assert options.use_image_process is True
        assert options.runtime_plan.component.id == "codium"
        assert options.runtime_plan.component.adapter == "vscode"
        assert options.ide_config is None
        assert options.plugins is None
        mounts = options.interactive_state_mounts
        assert mounts["codium/user-data"][1] == "/ide-user-data"
        assert mounts["codium/extensions"][1] == "/ide-extensions"
        assert mounts["codium/cache"][1] == "/home/devcapsule/.cache"
        assert mounts["codium/user-data"][0] == (
            tmp_path
            / "data"
            / "devcapsule"
            / "projects"
            / "by-path"
            / project_namespace(project.resolve())
            / "components"
            / "codium"
            / "user-data"
        ).resolve()
        assert "Materialized canonical environment" in capsys.readouterr().out


def test_project_run_realizes_formation_and_launches_canonical_image(
    tmp_path: Path, capsys
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    config_home = tmp_path / "config"
    env = {
        "HOME": str(tmp_path / "home"),
        "XDG_CONFIG_HOME": str(config_home),
        "XDG_DATA_HOME": str(tmp_path / "data"),
        "OPENAI_API_KEY": "sk-test-never-persist",
    }
    canonical = "devcapsule-local-pycharm:0123456789abcdef0123"

    with patch.dict(os.environ, env, clear=False):
        initialize_project(project)
        (project / "devcapsule-src").mkdir()
        (project / "devcapsule-src" / "pyproject.toml").write_text(
            '[project]\nname = "devcapsule"\nversion = "0.0.0"\n',
            encoding="utf-8",
        )
        lock_path = write_formation_lock(project)
        select_codex_component(project)
        assert (
            cli.main(
                [
                    "project",
                    "--path",
                    str(project),
                    "config",
                    "authorize",
                    "base-image",
                    LOCKED_BASE,
                ]
            )
            == 0
        )
        assert (
            cli.main(
                [
                    "project",
                    "--path",
                    str(project),
                    "config",
                    "bind",
                    "codex/openai-api-key",
                    "host-environment:OPENAI_API_KEY",
                ]
            )
            == 0
        )
        assert run_until_prepared(project) == 0
        capsys.readouterr()

        realized = SimpleNamespace(
            image=SimpleNamespace(labels={}, reference=canonical),
            created=False,
            locked=parse_locked_environment(tomllib.loads(lock_path.read_text(encoding="utf-8"))),
        )
        with (
            patch("devcapsule.commands.project.realize_environment", return_value=realized) as realize,
            patch("devcapsule.commands.project.run_pycharm", return_value=0) as launch,
        ):
            assert (
                cli.main(
                    [
                        "project",
                        "--path",
                        str(project),
                        "run",
                        "--authorize",
                        "docker-daemon",
                        "host-socket",
                        "--authorize",
                        "host-browser",
                        "true",
                    ]
                )
                == 0
            )

        selected = realize.call_args.args[0]
        assert selected.root == project.resolve()
        assert selected.checkout_path == registered_checkouts()[0].record_path
        assert selected.resolution_path == selected.checkout_path.with_name(
            "devcapsule.resolved.toml"
        )
        assert "sk-test-never-persist" not in selected.checkout_path.read_text(encoding="utf-8")
        assert selected.resolution["secret"]["bindings"]["host-environment"] == {
            "codex/openai-api-key": "OPENAI_API_KEY"
        }
        options = launch.call_args.args[0]
        assert options.image == canonical
        assert options.use_image_process is True
        assert options.runtime_plan.project_path == "/workspace/project"
        assert options.runtime_plan.home == "/home/devcapsule"
        assert options.runtime_plan.slots_by_name()["pycharm/config"] == "/ide-config"
        codex_state, codex_destination = options.additional_state_mounts["codex/home"]
        assert codex_state == (
            tmp_path
            / "data"
            / "devcapsule"
            / "projects"
            / "by-path"
            / project_namespace(project.resolve())
            / "components"
            / "codex"
            / "home"
        ).resolve()
        assert codex_destination == "/home/devcapsule/.codex"
        # The fresh managed slot starts with the component's seeded
        # configuration, written as the invoking user before the launch.
        seeded = codex_state / "config.toml"
        assert seeded.read_text(encoding="utf-8") == CODEX_CONFIG_SEED
        assert oct(seeded.stat().st_mode & 0o777) == "0o600"
        assert options.runtime_plan.component_environment() == {
            "CODEX_HOME": "/home/devcapsule/.codex",
            "JAVA_TOOL_OPTIONS": "-Dide.browser.jcef.sandbox.enable=false",
        }
        assert options.secret_environment == ("OPENAI_API_KEY",)
        assert options.additional_environment == {"DEVCAPSULE_RECURSIVE_E2E": "1"}
        assert options.enable_host_browser is True
        assert "Reused canonical environment" in capsys.readouterr().out

        with (
            patch("devcapsule.commands.project.realize_environment", return_value=realized),
            patch("devcapsule.commands.project.run_pycharm", return_value=0) as downgraded_launch,
        ):
            assert (
                cli.main(
                    [
                        "project",
                        "--path",
                        str(project),
                        "run",
                        "--authorize",
                        "docker-daemon",
                        "host-socket",
                        "--authorize",
                        "development-sudo",
                        "true",
                        "--no-recursive-e2e",
                    ]
                )
                == 0
            )

        downgraded = downgraded_launch.call_args.args[0]
        assert downgraded.docker_mode is DockerMode.none
        assert downgraded.enable_sudo is False
        assert downgraded.network_mode == "bridge"
        assert downgraded.additional_environment == {"DEVCAPSULE_RECURSIVE_E2E": "0"}
        assert downgraded.enable_host_browser is False
        assert "were downgraded" in capsys.readouterr().out


def test_host_browser_authorization_persists_and_drives_run(tmp_path: Path, capsys) -> None:
    project = tmp_path / "project"
    project.mkdir()
    env = {"HOME": str(tmp_path / "home"), "XDG_CONFIG_HOME": str(tmp_path / "config")}

    with patch.dict(os.environ, env, clear=False):
        initialize_project(project)
        # The manifest recommends nothing: host-browser is a home
        # capability the developer may authorize without project advice.
        assert (
            cli.main(
                [
                    "project",
                    "--path",
                    str(project),
                    "config",
                    "authorize",
                    "host-browser",
                    "true",
                ]
            )
            == 0
        )
        assert run_until_prepared(project) == 0
        with patch("devcapsule.commands.project.run_pycharm", return_value=0) as launch:
            assert cli.main(["project", "--path", str(project), "run"]) == 0
    assert launch.call_args.args[0].enable_host_browser is True


def test_run_once_authorization_rejects_unknown_and_persistent_nodes(
    tmp_path: Path, capsys
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    env = {"HOME": str(tmp_path / "home"), "XDG_CONFIG_HOME": str(tmp_path / "config")}

    with patch.dict(os.environ, env, clear=False):
        initialize_project(project)
        assert run_until_prepared(project) == 0
        capsys.readouterr()
        assert (
            cli.main(
                [
                    "project",
                    "--path",
                    str(project),
                    "run",
                    "--authorize",
                    "quantum-tunnel",
                    "open",
                ]
            )
            == 2
        )
    message = capsys.readouterr().err
    assert "cannot be answered for one launch" in message
    assert "docker-daemon" in message
    assert "network" in message  # on every project since 2026-10-22, recommended or not


def test_project_run_does_not_launch_when_environment_realization_fails(
    tmp_path: Path, capsys
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    config_home = tmp_path / "config"
    env = {"HOME": str(tmp_path / "home"), "XDG_CONFIG_HOME": str(config_home)}

    with patch.dict(os.environ, env, clear=False):
        initialize_project(project)
        write_formation_lock(project)
        assert (
            cli.main(
                [
                    "project",
                    "--path",
                    str(project),
                    "config",
                    "authorize",
                    "base-image",
                    LOCKED_BASE,
                ]
            )
            == 0
        )
        assert run_until_prepared(project) == 0
        capsys.readouterr()

        with (
            patch(
                "devcapsule.commands.project.realize_environment",
                side_effect=ProjectConfigurationError("canonical image metadata conflict"),
            ),
            patch("devcapsule.commands.project.run_pycharm") as launch,
        ):
            assert cli.main(["project", "--path", str(project), "run"]) == 2

        launch.assert_not_called()
        assert "canonical image metadata conflict" in capsys.readouterr().err


def test_project_config_set_uses_declared_metadata_and_resolves_runtime_effect(
    tmp_path: Path, capsys
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    config_home = tmp_path / "config"
    env = {"HOME": str(tmp_path / "home"), "XDG_CONFIG_HOME": str(config_home)}

    with patch.dict(os.environ, env, clear=False):
        initialize_project(project)
        append_manifest_metadata(
            project,
            """
            [configuration.values."editor.theme"]
            type = "string"

            [configuration.values."runtime.memory-limit"]
            type = "memory-size"
            runtime-effect = "docker.memory-limit"
            """,
        )

        assert (
            cli.main(
                [
                    "project",
                    "--path",
                    str(project),
                    "config",
                    "set",
                    "editor.theme",
                    "dark",
                ]
            )
            == 0
        )
        assert "Checkout record:" in capsys.readouterr().out
        assert (
            cli.main(
                [
                    "project",
                    "--path",
                    str(project),
                    "config",
                    "set",
                    "memory",
                    "8GiB",
                ]
            )
            == 0
        )
        assert (
            cli.main(
                ["project", "--path", str(project), "config", "set", "undeclared", "value"]
            )
            == 2
        )

        assert "No value named 'undeclared'" in capsys.readouterr().err

        # 'default' is an input artifact that resolves at decision time
        # (owner ruling 2026-09-03); value declarations carry no default
        # field, so there is nothing for it to resolve to — including for a
        # string-typed node where the literal is now reserved.
        # 'default' forgets the checkout's answer (answer 13 of the CLI UX work
        # order): the value recorded above is gone, and a second 'default'
        # finds nothing to forget.
        assert (
            cli.main(
                ["project", "--path", str(project), "config", "set", "editor.theme", "default"]
            )
            == 0
        )
        assert "Forgot editor.theme" in capsys.readouterr().out
        assert (
            cli.main(
                ["project", "--path", str(project), "config", "set", "editor.theme", "default"]
            )
            == 0
        )
        assert "has no recorded answer for this checkout; nothing changed" in capsys.readouterr().out
        assert cli.main(["project", "--path", str(project), "config", "set", "editor.theme", "dark"]) == 0
        assert (
            cli.main(
                [
                    "project",
                    "--path",
                    str(project),
                    "config",
                    "set",
                    "memory",
                    "eight",
                ]
            )
            == 2
        )
        assert "positive memory size" in capsys.readouterr().err
        # The legacy declaration's name is an alias of memory, not a node of its own.
        assert cli.main(["project", "--path", str(project), "config", "set", "runtime.memory-limit", "8GiB"]) == 2
        assert "config set memory SIZE" in capsys.readouterr().err
        assert cli.main(["project", "--path", str(project), "config", "set", "memory", "8GiB"]) == 0

        assert run_until_prepared(project) == 0
        record = registered_checkouts()[0].record_path
        with record.open("rb") as stream:
            checkout = tomllib.load(stream)
        assert checkout["configuration"]["values"] == {
            "editor.theme": "dark",
            "memory": "8GiB",
        }
        with record.with_name("devcapsule.resolved.toml").open("rb") as stream:
            resolved = tomllib.load(stream)
        assert resolved["configuration"]["values"] == checkout["configuration"]["values"]
        assert resolved["runtime"]["memory-limit-bytes"] == 8 * 1024**3


def test_authorize_records_denial_as_a_value(tmp_path: Path, capsys) -> None:
    """The 2026-09-02 denial-grammar bug, closed by the 2026-09-03 'none'
    ruling: denial is a value (bool false, or the string node's deny
    spelling), so a checkout's recorded denial outranks a home-level
    allow; 'none' resolves to the deny value at decision time."""

    project = tmp_path / "project"
    project.mkdir()
    config_home = tmp_path / "config"
    env = {"HOME": str(tmp_path / "home"), "XDG_CONFIG_HOME": str(config_home)}

    with patch.dict(os.environ, env, clear=False):
        initialize_project(project)

        assert (
            cli.main(
                [
                    "project",
                    "--path",
                    str(project),
                    "config",
                    "authorize",
                    "development-sudo",
                    "false",
                ]
            )
            == 0
        )
        records = list(config_home.rglob("devcapsule.checkout.toml"))
        with records[0].open("rb") as stream:
            checkout = tomllib.load(stream)
        assert checkout["authorization"]["development-sudo"]["value"] is False

        # 'none' resolves to the same deny value and stores the resolution.
        assert (
            cli.main(
                [
                    "project",
                    "--path",
                    str(project),
                    "config",
                    "authorize",
                    "docker-daemon",
                    "none",
                ]
            )
            == 0
        )
        with records[0].open("rb") as stream:
            checkout = tomllib.load(stream)
        assert checkout["authorization"]["docker-daemon"]["value"] == "none"

        # The denials survive resolution: the resolver honors them as values.
        assert run_until_prepared(project) == 0
        with records[0].with_name("devcapsule.resolved.toml").open("rb") as stream:
            resolved = tomllib.load(stream)
        assert resolved["authorization"]["development-sudo"] is False
        assert resolved["authorization"]["docker-daemon"] == "none"


def test_set_none_records_an_explicit_omission(tmp_path: Path, capsys) -> None:
    """The 2026-09-03 ruling: 'none' stores a recorded decision and the key
    is absent from the runtime configuration."""

    project = tmp_path / "project"
    project.mkdir()
    config_home = tmp_path / "config"
    env = {"HOME": str(tmp_path / "home"), "XDG_CONFIG_HOME": str(config_home)}

    with patch.dict(os.environ, env, clear=False):
        initialize_project(project)
        append_manifest_metadata(
            project,
            """
            [configuration.values."editor.theme"]
            type = "string"

            [configuration.values."registry.token-name"]
            type = "string"
            required = true
            """,
        )
        assert (
            cli.main(
                ["project", "--path", str(project), "config", "set", "editor.theme", "dark"]
            )
            == 0
        )
        assert (
            cli.main(
                [
                    "project",
                    "--path",
                    str(project),
                    "config",
                    "set",
                    "registry.token-name",
                    "CI_TOKEN",
                ]
            )
            == 0
        )
        assert (
            cli.main(
                ["project", "--path", str(project), "config", "set", "editor.theme", "none"]
            )
            == 0
        )
        assert "explicitly absent" in capsys.readouterr().out

        records = list(config_home.rglob("devcapsule.checkout.toml"))
        with records[0].open("rb") as stream:
            checkout = tomllib.load(stream)
        assert checkout["configuration"]["omitted-values"] == ["editor.theme"]
        assert "editor.theme" not in checkout["configuration"].get("values", {})

        assert run_until_prepared(project) == 0
        with records[0].with_name("devcapsule.resolved.toml").open("rb") as stream:
            resolved = tomllib.load(stream)
        assert "editor.theme" not in resolved.get("configuration", {}).get("values", {})
        assert resolved["configuration"]["omitted-values"] == ["editor.theme"]

        # A mandatory value has no absent state to choose.
        assert (
            cli.main(
                [
                    "project",
                    "--path",
                    str(project),
                    "config",
                    "set",
                    "registry.token-name",
                    "none",
                ]
            )
            == 2
        )
        assert "mandatory" in capsys.readouterr().err

        # A later value answer clears the omission; unset returns to silence.
        assert (
            cli.main(
                ["project", "--path", str(project), "config", "set", "editor.theme", "light"]
            )
            == 0
        )
        with records[0].open("rb") as stream:
            checkout = tomllib.load(stream)
        assert "omitted-values" not in checkout.get("configuration", {})
        assert checkout["configuration"]["values"]["editor.theme"] == "light"
        assert (
            cli.main(["project", "--path", str(project), "config", "set", "editor.theme", "none"])
            == 0
        )
        assert (
            cli.main(["project", "--path", str(project), "config", "set", 'editor.theme', "default"])
            == 0
        )
        with records[0].open("rb") as stream:
            checkout = tomllib.load(stream)
        assert "omitted-values" not in checkout.get("configuration", {})


def test_default_forgets_required_and_optional_value_answers(
    tmp_path: Path, capsys
) -> None:
    """Default forgets an answer while preserving its declaration."""

    project = tmp_path / "project"
    project.mkdir()
    config_home = tmp_path / "config"
    env = {"HOME": str(tmp_path / "home"), "XDG_CONFIG_HOME": str(config_home)}

    with patch.dict(os.environ, env, clear=False):
        initialize_project(project)
        append_manifest_metadata(
            project,
            """
            [configuration.values."editor.theme"]
            type = "string"

            [configuration.values."registry.token-name"]
            type = "string"
            required = true
            """,
        )
        for name, value in (("editor.theme", "dark"), ("registry.token-name", "CI_TOKEN")):
            assert (
                cli.main(
                    ["project", "--path", str(project), "config", "set", name, value]
                )
                == 0
            )
        capsys.readouterr()

        # Forgetting leaves the required declaration intact and makes it pending.
        assert (
            cli.main(
                ["project", "--path", str(project), "config", "set", 'registry.token-name', "default"]
            )
            == 0
        )
        message = capsys.readouterr().err
        assert message == ""
        assert cli.main(["project", "--path", str(project), "config", "check"]) == 3
        assert "registry.token-name" in capsys.readouterr().err

        # An optional node still unsets — the name is removed from the tree.
        assert (
            cli.main(["project", "--path", str(project), "config", "set", 'editor.theme', "default"])
            == 0
        )
        assert "Forgot editor.theme" in capsys.readouterr().out
        records = list(config_home.rglob("devcapsule.checkout.toml"))
        with records[0].open("rb") as stream:
            checkout = tomllib.load(stream)
        assert "editor.theme" not in checkout.get("configuration", {}).get("values", {})


def test_project_config_bind_uses_component_metadata_and_resolves_host_directories(
    tmp_path: Path, capsys
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    config_home = tmp_path / "config"
    env = {"HOME": str(tmp_path / "home"), "XDG_CONFIG_HOME": str(config_home)}
    slots = (
        "home",
        "pycharm/config",
        "pycharm/plugins",
        "pycharm/system",
        "pycharm/log",
        "pycharm/cache",
    )
    directories = {slot: tmp_path / slot.replace("/", "-") for slot in slots}
    for directory in directories.values():
        directory.mkdir()

    with patch.dict(os.environ, env, clear=False):
        initialize_project(project)
        for slot, directory in directories.items():
            assert (
                cli.main(
                    [
                        "project",
                        "--path",
                        str(project),
                        "config",
                        "bind",
                        slot,
                        f"host-directory:{directory}",
                    ]
                )
                == 0
            )
            warning = capsys.readouterr().err
            assert "exposing host directory read-write" in warning
            assert "Concurrency: exclusive" in warning

        assert (
            cli.main(
                [
                    "project",
                    "--path",
                    str(project),
                    "config",
                    "bind",
                    "pycharm/unknown",
                    f"host-directory:{directories["home"]}",
                ]
            )
            == 2
        )
        assert "is not declared" in capsys.readouterr().err
        assert (
            cli.main(
                [
                    "project",
                    "--path",
                    str(project),
                    "config",
                    "bind",
                    "home",
                    f"host-directory:{tmp_path / "missing"}",
                ]
            )
            == 2
        )
        assert "not an existing directory" in capsys.readouterr().err

        assert run_until_prepared(project) == 0
        record = registered_checkouts()[0].record_path
        with record.open("rb") as stream:
            checkout = tomllib.load(stream)
        expected = {slot: str(path.resolve()) for slot, path in directories.items()}
        assert checkout["configuration"]["bindings"]["host-directory"] == expected
        with record.with_name("devcapsule.resolved.toml").open("rb") as stream:
            resolved = tomllib.load(stream)
        assert resolved["state"]["bindings"] == expected


def test_project_config_authorize_uses_exact_recommendations_and_drives_run(
    tmp_path: Path, capsys
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    config_home = tmp_path / "config"
    env = {"HOME": str(tmp_path / "home"), "XDG_CONFIG_HOME": str(config_home)}

    with patch.dict(os.environ, env, clear=False):
        initialize_project(project)
        append_manifest_metadata(
            project,
            """
            [configuration.values."runtime.memory-limit"]
            type = "memory-size"
            runtime-effect = "docker.memory-limit"

            [host.docker.mode.recommended]
            value = "host-socket"
            justification = "Run peer development containers."

            [host.network.mode.recommended]
            value = "host"
            justification = "Reach host-bound development services."

            [host.privilege.development-sudo.recommended]
            value = true
            justification = "Perform reviewed development administration."
            """,
        )

        commands = (
            ("docker-daemon", "host-socket"),
            ("network", "host"),
            ("development-sudo", "true"),
        )
        for name, value in commands:
            assert (
                cli.main(
                    [
                        "project",
                        "--path",
                        str(project),
                        "config",
                        "authorize",
                        name,
                        value,
                    ]
                )
                == 0
            )
            output = capsys.readouterr().out
            assert f"Authorized {name} for this checkout" in output
            assert "Checkout record:" in output

        assert (
            cli.main(
                [
                    "project",
                    "--path",
                    str(project),
                    "config",
                    "set",
                    "memory",
                    "8GiB",
                ]
            )
            == 0
        )

        # 'bridge' is the network node's deny value — recording it is the
        # developer's reduce-privilege decision and needs no reviewed
        # metadata (2026-09-03 ruling closing the denial-grammar bug). A
        # value beyond recommendation-or-deny still refuses.
        assert (
            cli.main(
                [
                    "project",
                    "--path",
                    str(project),
                    "config",
                    "authorize",
                    "network",
                    "bridge",
                ]
            )
            == 0
        )
        assert "Authorized network for this checkout" in capsys.readouterr().out
        assert (
            cli.main(
                [
                    "project",
                    "--path",
                    str(project),
                    "config",
                    "authorize",
                    "network",
                    "vpn0",
                ]
            )
            == 2
        )
        message = capsys.readouterr().err
        assert "deny value 'bridge'" in message
        assert "Project recommendation" not in message
        # Restore the recommended posture for the run assertions below.
        assert (
            cli.main(
                ["project", "--path", str(project), "config", "authorize", "network", "host"]
            )
            == 0
        )
        capsys.readouterr()
        assert (
            cli.main(
                [
                    "project",
                    "--path",
                    str(project),
                    "config",
                    "authorize",
                    "device",
                    "gpu",
                ]
            )
            == 2
        )
        assert "is not declared" in capsys.readouterr().err

        assert run_until_prepared(project) == 0
        record = registered_checkouts()[0].record_path
        with record.open("rb") as stream:
            checkout = tomllib.load(stream)
        assert checkout["authorization"]["docker-daemon"]["value"] == "host-socket"
        assert checkout["authorization"]["network"]["value"] == "host"
        assert checkout["authorization"]["development-sudo"]["value"] is True
        with record.with_name("devcapsule.resolved.toml").open("rb") as stream:
            resolved = tomllib.load(stream)
        assert resolved["authorization"] == {
            "development-sudo": True,
            "docker-daemon": "host-socket",
            "network": "host",
        }

        with patch("devcapsule.commands.project.run_pycharm", return_value=0) as run:
            assert cli.main(["project", "--path", str(project), "run"]) == 0
        options = run.call_args.args[0]
        assert options.docker_mode.value == "host"
        assert options.network_mode == "host"
        assert options.enable_sudo is True
        assert options.memory_limit_bytes == 8 * 1024**3

        manifest_path = project / ".devcapsule" / "devcapsule.toml"
        manifest_path.write_text(
            manifest_path.read_text(encoding="utf-8").replace(
                "Reach host-bound development services.",
                "Changed host-network justification.",
            ),
            encoding="utf-8",
        )
        with manifest_path.open("rb") as stream:
            manifest = tomllib.load(stream)
        lock_path = project / ".devcapsule" / "devcapsule.linux-amd64.lock"
        lock_path.write_text(
            "\n".join(
                f'manifest-digest = "{canonical_digest(manifest)}"'
                if line.startswith("manifest-digest = ")
                else line
                for line in lock_path.read_text(encoding="utf-8").splitlines()
            )
            + "\n",
            encoding="utf-8",
        )
        # The changed justification does not re-ask: the answer is kept (D-0012).
        assert run_until_prepared(project) == 0


def test_project_config_authorize_accepts_inspected_local_base_and_pins_image_id(
    tmp_path: Path, capsys
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    config_home = tmp_path / "config"
    env = {"HOME": str(tmp_path / "home"), "XDG_CONFIG_HOME": str(config_home)}
    local_reference = "devcapsule-local-base:v022"
    local_identity = f"sha256:{'c' * 64}"
    local_base = ImageDetails(
        reference=local_reference,
        identity=local_identity,
        labels={
            "devcapsule.image.managed": "true",
            "devcapsule.metadata.version": "1",
            "devcapsule.image.kind": "base",
        },
        operating_system="linux",
        architecture="amd64",
    )

    with patch.dict(os.environ, env, clear=False):
        initialize_project(project)
        write_formation_lock(project)
        with patch(
            "devcapsule.commands.project.required_local_image",
            return_value=local_base,
        ) as inspect_local:
            assert (
                cli.main(
                    [
                        "project",
                        "--path",
                        str(project),
                        "config",
                        "authorize",
                        "base-image",
                        local_reference,
                    ]
                )
                == 0
            )
        inspect_local.assert_called_once_with(local_reference)
        output = capsys.readouterr().out
        assert f"Authorized base-image for this checkout: {local_reference}" in output
        assert f"Local image ID: {local_identity}" in output
        assert "overrides the published base recommendation" in output

        record = registered_checkouts()[0].record_path
        with record.open("rb") as stream:
            checkout = tomllib.load(stream)
        assert checkout["authorization"]["base-image"] == {
            "reference": local_reference,
            "lock-digest": canonical_digest(
                tomllib.loads(
                    (project / ".devcapsule" / "devcapsule.linux-amd64.lock").read_text(
                        encoding="utf-8"
                    )
                )
            ),
            "image-id": local_identity,
        }

        with patch(
            "devcapsule.configuration.operations.required_local_image",
            return_value=local_base,
        ) as inspect_resolved_local:
            assert run_until_prepared(project) == 0
        inspect_resolved_local.assert_called_once_with(local_reference)
        with record.with_name("devcapsule.resolved.toml").open("rb") as stream:
            resolved = tomllib.load(stream)
        assert resolved["authorization"]["base-image"] == {
            "reference": local_reference,
            "lock-digest": checkout["authorization"]["base-image"]["lock-digest"],
            "image-id": local_identity,
        }

        assert cli.main(["project", "--path", str(project), "config", "show"]) == 0
        base_row = next(
            line for line in capsys.readouterr().out.splitlines() if "base-image" in line
        )
        assert "checkout" in base_row and "devcapsule-local-base:v022" in base_row
        assert local_reference in base_row


def test_project_config_authorize_all_recommended_previews_and_requires_lowercase_y(
    tmp_path: Path, capsys
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    config_home = tmp_path / "config"
    env = {"HOME": str(tmp_path / "home"), "XDG_CONFIG_HOME": str(config_home)}

    with patch.dict(os.environ, env, clear=False):
        initialize_project(project)
        append_manifest_metadata(
            project,
            """
            [host.docker.mode.recommended]
            value = "host-socket"
            justification = "Run peer development containers."

            [host.network.mode.recommended]
            value = "host"
            justification = "Reach host-bound development services."

            [host.privilege.development-sudo.recommended]
            value = true
            justification = "Perform reviewed development administration."
            """,
        )
        write_formation_lock(project)
        assert cli.main(["project", "--path", str(project), "config", "show"]) == 0
        capsys.readouterr()

        with (
            patch("devcapsule.commands.project.sys.stdin") as terminal,
            patch("devcapsule.commands.project._confirmation_key", return_value="y") as readkey,
        ):
            terminal.isatty.return_value = True
            assert (
                cli.main(
                    [
                        "project",
                        "--path",
                        str(project),
                        "config",
                        "authorize",
                        "--all-recommended",
                    ]
                )
                == 0
            )
        readkey.assert_called_once_with()
        output = capsys.readouterr().out
        assert output.index("- base-image:") < output.index("Press y to authorize")
        assert output.index("- docker-daemon: host-socket") < output.index("Press y to authorize")
        assert output.index("- network: host") < output.index("Press y to authorize")
        assert output.index("- development-sudo: true") < output.index("Press y to authorize")
        assert "Justification: Run peer development containers." in output
        assert "Recommendation digest:" in output
        assert "Authorized 4 recommendations for this checkout." in output

        record = registered_checkouts()[0].record_path
        with record.open("rb") as stream:
            checkout = tomllib.load(stream)
        assert set(checkout["authorization"]) == {
            "base-image",
            "development-sudo",
            "docker-daemon",
            "network",
        }
        assert checkout["authorization"]["base-image"]["reference"] == LOCKED_BASE
        assert checkout["authorization"]["docker-daemon"]["value"] == "host-socket"
        assert checkout["authorization"]["network"]["value"] == "host"
        assert checkout["authorization"]["development-sudo"]["value"] is True


@pytest.mark.parametrize("key", ["Y", "n", "\n"])
def test_project_config_authorize_all_recommended_cancels_without_lowercase_y(
    tmp_path: Path, capsys, key: str
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    config_home = tmp_path / "config"
    env = {"HOME": str(tmp_path / "home"), "XDG_CONFIG_HOME": str(config_home)}

    with patch.dict(os.environ, env, clear=False):
        initialize_project(project)
        write_formation_lock(project)
        assert cli.main(["project", "--path", str(project), "config", "set", "memory", "1GiB"]) == 0
        record = registered_checkouts()[0].record_path
        original_input = record.read_bytes()
        capsys.readouterr()
        with (
            patch("devcapsule.commands.project.sys.stdin") as terminal,
            patch("devcapsule.commands.project._confirmation_key", return_value=key),
        ):
            terminal.isatty.return_value = True
            assert (
                cli.main(
                    [
                        "project",
                        "--path",
                        str(project),
                        "config",
                        "authorize",
                        "--all-recommended",
                    ]
                )
                == 1
            )
        assert "Authorization cancelled; no changes written." in capsys.readouterr().out
        assert record.read_bytes() == original_input


def test_project_config_authorize_all_recommended_rejects_noninteractive_input(
    tmp_path: Path, capsys
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    config_home = tmp_path / "config"
    env = {"HOME": str(tmp_path / "home"), "XDG_CONFIG_HOME": str(config_home)}

    with patch.dict(os.environ, env, clear=False):
        initialize_project(project)
        write_formation_lock(project)
        capsys.readouterr()
        with (
            patch("devcapsule.commands.project.sys.stdin") as terminal,
            patch("devcapsule.commands.project._confirmation_key") as readkey,
        ):
            terminal.isatty.return_value = False
            assert (
                cli.main(
                    [
                        "project",
                        "--path",
                        str(project),
                        "config",
                        "authorize",
                        "--all-recommended",
                    ]
                )
                == 2
            )
        readkey.assert_not_called()
        captured = capsys.readouterr()
        assert "The following authorizations will be granted" in captured.out
        assert "requires an interactive terminal" in captured.err
        assert registered_checkouts() == ()


def test_project_authorizes_only_exact_locked_base_and_lock_change_stales_it(
    tmp_path: Path, capsys
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    config_home = tmp_path / "config"
    env = {"HOME": str(tmp_path / "home"), "XDG_CONFIG_HOME": str(config_home)}

    with patch.dict(os.environ, env, clear=False):
        initialize_project(project)
        lock_path = write_formation_lock(project)
        # An unconsented formation is inspectable, but cannot be resolved as ready.
        assert run_until_prepared(project) == 3

        wrong = f"docker.io/example/devcapsule-base@sha256:{'c' * 64}"
        assert (
            cli.main(
                ["project", "--path", str(project), "config", "authorize", "base-image", wrong]
            )
            == 2
        )
        message = capsys.readouterr().err
        assert "Authorization 'base-image' accepts its recommended value" in message
        assert "reviewed metadata" in message

        assert (
            cli.main(
                [
                    "project",
                    "--path",
                    str(project),
                    "config",
                    "authorize",
                    "base-image",
                    LOCKED_BASE,
                ]
            )
            == 0
        )
        authorization_output = capsys.readouterr().out
        assert "Checkout record:" in authorization_output
        record = registered_checkouts()[0].record_path
        with record.open("rb") as stream:
            checkout = tomllib.load(stream)
        assert checkout["authorization"]["base-image"]["reference"] == LOCKED_BASE

        home = tmp_path / "persistent-home"
        home.mkdir()
        assert (
            cli.main(
                [
                    "project",
                    "--path",
                    str(project),
                    "state",
                    "adopt",
                    "home",
                    "--from",
                    str(home),
                ]
            )
            == 0
        )
        with record.open("rb") as stream:
            checkout = tomllib.load(stream)
        assert checkout["authorization"]["base-image"]["reference"] == LOCKED_BASE

        assert run_until_prepared(project) == 0
        resolved_path = record.with_name("devcapsule.resolved.toml")
        with resolved_path.open("rb") as stream:
            resolved = tomllib.load(stream)
        assert resolved["authorization"]["base-image"]["reference"] == LOCKED_BASE

        # Consent binds to the image: a lock edit that leaves the base alone
        # stales the resolution, which resolve refreshes, and asks nothing.
        lock_path.write_text(
            lock_path.read_text(encoding="utf-8").replace("formation-v1", "formation-v2"),
            encoding="utf-8",
        )
        capsys.readouterr()
        assert run_until_prepared(project) == 0
        with resolved_path.open("rb") as stream:
            assert tomllib.load(stream)["authorization"]["base-image"]["reference"] == LOCKED_BASE


@pytest.mark.parametrize(
    "reference",
    [
        "devcapsule-local-base:v020",
        "sha256:" + "a" * 64,
        "docker.io/example/devcapsule-base:latest",
        "localhost:5000/example/devcapsule-base@sha256:" + "a" * 64,
    ],
)
def test_committed_base_reference_rejects_local_or_mutable_names(reference: str) -> None:
    with pytest.raises(ProjectConfigurationError):
        immutable_registry_reference(reference)


def test_manifest_edit_after_lock_never_blocks_commands_and_resolve_reconciles(
    tmp_path: Path, capsys
) -> None:
    """Regression: an ordinary manifest edit must never dead-end the checkout.

    Editing the manifest after the lock exists (the trading-research failure:
    adding ``workflow-type`` as the workflow-init step instructs) used to make
    every project command — including read-only ``config show`` — fail with
    "<lock> is stale; run 'devcapsule project lock'", a remedy that could not
    produce a valid lock. The lock's ``manifest-digest`` is informational
    (R-COMPAT-001): drift is the resolution layer's to report, ``config
    resolve`` is the remedy, and inspection never gates.
    """

    project = tmp_path / "project"
    project.mkdir()
    config_home = tmp_path / "config"
    env = {"HOME": str(tmp_path / "home"), "XDG_CONFIG_HOME": str(config_home)}

    with patch.dict(os.environ, env, clear=False):
        initialize_project(project)
        assert run_until_prepared(project) == 0
        lock_path = project / ".devcapsule" / "devcapsule.linux-amd64.lock"
        lock_before = lock_path.read_text(encoding="utf-8")

        # Edit the manifest WITHOUT re-syncing the lock's manifest-digest --
        # exactly what a user does when adopting the multiple-stream workflow.
        manifest_path = project / ".devcapsule" / "devcapsule.toml"
        manifest_path.write_text(
            'workflow-type = "multiple-streams"\n'
            + manifest_path.read_text(encoding="utf-8"),
            encoding="utf-8",
        )

        # Inspection never gates: list succeeds and reports the resolution
        # as stale instead of refusing to run.
        capsys.readouterr()
        assert cli.main(["project", "--path", str(project), "config", "show"]) == 0
        listing = capsys.readouterr().out
        assert "Nothing is pending." in listing

        # The documented remedy reconciles the ordinary change.
        assert run_until_prepared(project) == 0
        records = registered_checkouts()
        assert [record.status for record in records] == ["ready"]

        # The committed lock is a record: reconciling a manifest edit does not
        # rewrite it, and its stale manifest-digest field is simply not read.
        assert lock_path.read_text(encoding="utf-8") == lock_before

        capsys.readouterr()
        assert cli.main(["project", "--path", str(project), "config", "show"]) == 0
        assert "stale" not in capsys.readouterr().out


def test_component_state_seed_is_written_once_and_never_overwrites(tmp_path: Path) -> None:
    from devcapsule.commands.project import _seed_component_state

    declaration = SimpleNamespace(component_id="codex", slot_name="home")
    slot = tmp_path / "codex-home"
    slot.mkdir()

    _seed_component_state(slot, declaration)
    seeded = slot / "config.toml"
    assert seeded.read_text(encoding="utf-8") == CODEX_CONFIG_SEED
    assert oct(seeded.stat().st_mode & 0o777) == "0o600"

    # A developer's edit — or codex's own appended tables — must survive
    # every later launch untouched.
    seeded.write_text('model = "gpt-6-astra"\n', encoding="utf-8")
    _seed_component_state(slot, declaration)
    assert seeded.read_text(encoding="utf-8") == 'model = "gpt-6-astra"\n'

    # Slots of components without seeds, and slots the component does not
    # seed, are left empty.
    other = tmp_path / "other"
    other.mkdir()
    _seed_component_state(other, SimpleNamespace(component_id="postgresql-client", slot_name="home"))
    _seed_component_state(other, SimpleNamespace(component_id="codex", slot_name="cache"))
    _seed_component_state(other, SimpleNamespace(component_id="unknown", slot_name="home"))
    assert list(other.iterdir()) == []


def test_run_selects_the_display_transport_from_the_image_and_the_host_x11_answer(
    capsys: pytest.CaptureFixture[str],
) -> None:
    from devcapsule.commands.project import _select_display_transport

    contained = {"devcapsule.base.display": "contained"}
    assert _select_display_transport(contained, host_x11_answer=False) == "contained"
    assert "contained desktop" in capsys.readouterr().out
    assert _select_display_transport(contained, host_x11_answer=True) == "host-x11"
    assert "authorized by 'host-x11'" in capsys.readouterr().out
    assert _select_display_transport({}, host_x11_answer=None) == "host-x11"
    assert "predates the contained display" in capsys.readouterr().out
    # Unanswered means the contained desktop (flipped for the release 2026-09-14).
    assert _select_display_transport(contained, host_x11_answer=None) == "contained"
    assert "contained desktop" in capsys.readouterr().out


def test_run_passes_the_selected_transport_and_accepts_host_x11_run_once(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    env = {
        "HOME": str(tmp_path / "home"),
        "XDG_CONFIG_HOME": str(tmp_path / "config"),
        "XDG_DATA_HOME": str(tmp_path / "data"),
    }
    with patch.dict(os.environ, env, clear=False):
        initialize_project(project)
        lock_path = write_formation_lock(project)
        assert cli.main(["project", "--path", str(project), "config", "authorize", "base-image", LOCKED_BASE]) == 0
        assert run_until_prepared(project) == 0
        capsys.readouterr()
        realized = SimpleNamespace(
            image=SimpleNamespace(labels={"devcapsule.base.display": "contained"}, reference="devcapsule-local-pycharm:0123456789abcdef0123"),
            created=False,
            locked=parse_locked_environment(tomllib.loads(lock_path.read_text(encoding="utf-8"))),
        )
        with (
            patch("devcapsule.commands.project.realize_environment", return_value=realized),
            patch("devcapsule.commands.project.run_pycharm", return_value=0) as launch,
        ):
            assert cli.main(["project", "--path", str(project), "run"]) == 0
            assert launch.call_args.args[0].display_transport == "contained"  # unanswered: the safe default
            assert cli.main(["project", "--path", str(project), "run", "--authorize", "host-x11", "false"]) == 0
            assert launch.call_args.args[0].display_transport == "contained"
            assert cli.main(["project", "--path", str(project), "run", "--authorize", "host-x11", "true"]) == 0
            assert launch.call_args.args[0].display_transport == "host-x11"
    err = capsys.readouterr().err
    assert "Run-once authorization: host-x11 = false" in err
    assert "Run-once authorization: host-x11 = true" in err


def test_network_is_a_node_on_every_project(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The bug of 2026-10-05: a project without a network recommendation refused
    the documented run-once command. The node exists on every project with
    bridge as the deny value; a recommendation only attaches a justification."""
    project = tmp_path / "project"
    project.mkdir()
    env = {
        "HOME": str(tmp_path / "home"),
        "XDG_CONFIG_HOME": str(tmp_path / "config"),
        "XDG_DATA_HOME": str(tmp_path / "data"),
    }
    with patch.dict(os.environ, env, clear=False):
        initialize_project(project)
        manifest_text = (project / ".devcapsule" / "devcapsule.toml").read_text(encoding="utf-8")
        assert "[host.network" not in manifest_text  # the precondition: no recommendation
        lock_path = write_formation_lock(project)
        assert cli.main(["project", "--path", str(project), "config", "authorize", "base-image", LOCKED_BASE]) == 0
        assert run_until_prepared(project) == 0
        capsys.readouterr()
        record = registered_checkouts()[0].record_path
        original_input = record.read_bytes()
        resolution = record.with_name("devcapsule.resolved.toml")
        realized = SimpleNamespace(
            image=SimpleNamespace(labels={"devcapsule.base.display": "contained"}, reference="devcapsule-local-pycharm:0123456789abcdef0123"),
            created=False,
            locked=parse_locked_environment(tomllib.loads(lock_path.read_text(encoding="utf-8"))),
        )
        with (
            patch("devcapsule.commands.project.realize_environment", return_value=realized),
            patch("devcapsule.commands.project.run_pycharm", return_value=0) as launch,
        ):
            assert cli.main(["project", "--path", str(project), "run"]) == 0
            assert launch.call_args.args[0].network_mode == "bridge"  # unanswered: the deny value
            assert cli.main(["project", "--path", str(project), "run", "--authorize", "network", "host"]) == 0
            assert launch.call_args.args[0].network_mode == "host"
        err = capsys.readouterr().err
        assert "Run-once authorization: network = host" in err
        assert record.read_bytes() == original_input
        # The derived plan describes this run; the persistent answer stays unchanged.
        assert tomllib.loads(resolution.read_text())["authorization"]["network"] == "host"
        # The persistent form writes the checkout's answer; nothing is recorded by the run-once form.
        assert cli.main(["project", "--path", str(project), "config", "authorize", "network", "host"]) == 0
        output = capsys.readouterr().out
        assert "Authorized network for this checkout" in output
        assert "This removes network namespace isolation." in output
        assert "Deny with 'bridge' (the default)." in output
        record = registered_checkouts()[0].record_path
        with record.open("rb") as stream:
            checkout = tomllib.load(stream)
        assert checkout["authorization"]["network"]["value"] == "host"
        # Only the node's grammar is accepted; the refusal names the deny value.
        assert cli.main(["project", "--path", str(project), "config", "authorize", "network", "vpn0"]) == 2
        assert "deny value 'bridge'" in capsys.readouterr().err
        assert cli.main(["project", "--path", str(project), "config", "show"]) == 0
    rows = {line.split()[1]: line.split() for line in capsys.readouterr().out.splitlines() if line.startswith("access")}
    assert (rows["network"][2], rows["network"][3]) == ("host", "checkout")


def test_unanswered_network_lists_its_source_and_is_not_bulk_authorized(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    env = {"HOME": str(tmp_path / "home"), "XDG_CONFIG_HOME": str(tmp_path / "config")}
    with patch.dict(os.environ, env, clear=False):
        initialize_project(project)
        write_formation_lock(project)
        document, _ = _listing_document(project, capsys)
        network = next(row for row in document["rows"] if row["name"] == "network")
        assert network == {
            "kind": "access", "name": "network", "effective": "bridge",
            "source": "secure default", "pending": "", "command": "",
        }
        with (
            patch("devcapsule.commands.project.sys.stdin") as terminal,
            patch("devcapsule.commands.project._confirmation_key", return_value="y"),
        ):
            terminal.isatty.return_value = True
            assert cli.main([
                "project", "--path", str(project), "config", "authorize", "--all-recommended",
            ]) == 0
        assert "- network:" not in capsys.readouterr().out
        record = registered_checkouts()[0].record_path
        assert set(tomllib.loads(record.read_text())["authorization"]) == {"base-image"}


@pytest.mark.parametrize("value", ["host", "bridge"])
def test_network_answer_stales_when_recommendation_appears_and_disappears(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], value: str,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    env = {"HOME": str(tmp_path / "home"), "XDG_CONFIG_HOME": str(tmp_path / "config")}
    command = ["project", "--path", str(project), "config"]
    with patch.dict(os.environ, env, clear=False):
        initialize_project(project)
        write_formation_lock(project)
        manifest_path = project / ".devcapsule" / "devcapsule.toml"
        original_manifest = manifest_path.read_text()
        assert cli.main([*command, "authorize", "base-image", "default"]) == 0
        assert cli.main([*command, "authorize", "network", value]) == 0
        assert run_until_prepared(project) == 0
        record = registered_checkouts()[0].record_path
        default_digest = tomllib.loads(record.read_text())["authorization"]["network"]["recommendation-digest"]
        recommendation = (
            '\n[host.network.mode.recommended]\nvalue = "host"\n'
            'justification = "Reach host-bound development services."\n'
        )
        for text, source, description in (
            (original_manifest + recommendation, "manifest", "Reach host-bound development services."),
            (original_manifest, "home default", "Share the host network namespace"),
        ):
            manifest_path.write_text(text)
            write_formation_lock(project)
            before = record.read_bytes()
            capsys.readouterr()
            # The recorded answer is kept under the changed recommendation and
            # disclosed; nothing is asked and nothing is written (D-0012, answer 23).
            assert run_until_prepared(project) == 0
            assert record.read_bytes() == before
            capsys.readouterr()
            document, _ = _listing_document(project, capsys)
            network = next(row for row in document["rows"] if row["name"] == "network")
            assert network["effective"] == value and not network["pending"]
            assert "kept" in network["source"]
            assert cli.main([*command, "authorize", "network", value]) == 0
            digest = tomllib.loads(record.read_text())["authorization"]["network"]["recommendation-digest"]
            assert (digest == default_digest) == (source == "home default")
            assert run_until_prepared(project) == 0
            resolved = tomllib.loads(record.with_name("devcapsule.resolved.toml").read_text())
            assert resolved["authorization"]["network"] == value
            assert Resolution(resolved).host_access.network == value


@pytest.mark.parametrize("value", ["host", "bridge"])
def test_forget_network_removes_the_answer_and_resolves_to_bridge(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], value: str,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    env = {"HOME": str(tmp_path / "home"), "XDG_CONFIG_HOME": str(tmp_path / "config")}
    command = ["project", "--path", str(project), "config"]
    with patch.dict(os.environ, env, clear=False):
        initialize_project(project)
        write_formation_lock(project)
        assert cli.main([*command, "authorize", "base-image", "default"]) == 0
        assert cli.main([*command, "authorize", "network", value]) == 0
        assert run_until_prepared(project) == 0
        record = registered_checkouts()[0].record_path
        resolution = record.with_name("devcapsule.resolved.toml")
        original = resolution.read_bytes()
        capsys.readouterr()
        assert cli.main([*command, "forget", "network"]) == 0
        assert "Forgot network for this checkout." in capsys.readouterr().out
        assert "network" not in tomllib.loads(record.read_text())["authorization"]
        assert resolution.read_bytes() == original
        assert run_until_prepared(project) == 0
        resolved = tomllib.loads(resolution.read_text())
        assert "network" not in resolved["authorization"]
        assert Resolution(resolved).host_access.network == "bridge"
        capsys.readouterr()
        document, _ = _listing_document(project, capsys)
        network = next(row for row in document["rows"] if row["name"] == "network")
        assert network["effective"] == "bridge"
        assert network["source"] == "secure default"
        assert cli.main([*command, "forget", "network"]) == 2
        assert "has no recorded answer" in capsys.readouterr().err


def test_config_list_shows_the_recorded_answer_and_names_a_denial(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    env = {"HOME": str(tmp_path / "home"), "XDG_CONFIG_HOME": str(tmp_path / "config")}
    with patch.dict(os.environ, env, clear=False):
        initialize_project(project)
        assert cli.main(["project", "--path", str(project), "config", "authorize", "host-x11", "false"]) == 0
        assert cli.main(["project", "--path", str(project), "config", "authorize", "host-browser", "true"]) == 0
        capsys.readouterr()
        assert cli.main(["project", "--path", str(project), "config", "show"]) == 0
    # Columns: KIND NAME EFFECTIVE SOURCE PENDING; the source may contain
    # spaces, so read the effective value and the source's first word by position.
    rows = {line.split()[1]: line.split() for line in capsys.readouterr().out.splitlines() if line.startswith("access")}
    assert (rows["host-x11"][2], rows["host-x11"][3]) == ("false", "checkout")
    assert (rows["host-browser"][2], rows["host-browser"][3]) == ("true", "checkout")
    assert (rows["development-sudo"][2], " ".join(rows["development-sudo"][3:5])) == ("false", "secure default")


@pytest.mark.parametrize('surface,needs', [('pycharm', ['python', 'python-ide']), ('codium', ['node', 'frontend-ide'])])
@pytest.mark.parametrize('display', ['contained', 'host-x11'])
def test_print_command_uses_real_launch_builder_without_launch_or_success(
    tmp_path, monkeypatch, capfd, surface, needs, display,
):
    import shlex
    import subprocess
    from devcapsule.commands import project as command
    from devcapsule.launch.pycharm import _launcher as launcher
    from devcapsule.configuration.execution import ExecutionConfiguration

    project = tmp_path / 'project'
    project.mkdir()
    monkeypatch.chdir(project)
    for key, leaf in [('HOME', 'home'), ('XDG_CONFIG_HOME', 'config'), ('XDG_DATA_HOME', 'data'),
                      ('XDG_STATE_HOME', 'state'), ('XDG_RUNTIME_DIR', 'runtime')]:
        monkeypatch.setenv(key, str(tmp_path / leaf))
    monkeypatch.setenv('DISPLAY', ':fixture')
    monkeypatch.setenv('PRINT_TEST_SECRET', 'do-not-render-this-value')
    need_arguments = [arg for need in needs for arg in ('--ide' if need.endswith('-ide') else '--offer', need)]
    assert cli.main(['project', 'init', *need_arguments, '--creator', 'https://example.test',
                     '--unverified', '--authorize', 'base-image', 'default']) == 0
    assert cli.main(['project', 'config', 'authorize', 'host-x11', str(display == 'host-x11').lower()]) == 0
    assert run_until_prepared() == 0
    assert cli.main(['project', 'config', 'docker-args', 'set', '--', '--gpus', 'all', '--volume', str(tmp_path / 'data dir') + ':/data:ro']) == 0
    assert cli.main(['project', 'config', 'env', 'set', 'APP_PASSWORD', 'managed-secret-sentinel']) == 0
    assert cli.main(['project', 'config', 'set', 'cpus', '2']) == 0
    assert run_until_prepared() == 0
    selected = ExecutionConfiguration.load(project).project
    assert selected.resolution['runtime']['cpus'] == 2
    locked = parse_locked_environment(selected.lock)
    realized = SimpleNamespace(image=SimpleNamespace(labels={'devcapsule.base.display': 'contained'},
                                 reference='devcapsule-local-' + surface + ':fixture'), created=False, locked=locked)
    before = {p: p.read_bytes() for p in (selected.checkout_path, selected.resolution_path)}
    def forbidden(*args, **kwargs):
        pytest.fail('print mode must not launch, offer updates, watch display, or record successful use')
    monkeypatch.setattr(command, 'offer_upgrades', forbidden)
    monkeypatch.setattr(command, 'record_known_good_configuration', forbidden)
    monkeypatch.setattr(command.version_sets, 'record_success', forbidden)
    def realize(*args, **kwargs):
        print('Python preparation progress')
        os.write(1, b'Child-style preparation progress\n')
        return realized
    monkeypatch.setattr(command, 'realize_environment', realize)
    monkeypatch.setattr(launcher, 'requires_translation', lambda env: False)
    monkeypatch.setattr(launcher, 'write_xauthority', lambda path, env: None)
    monkeypatch.setattr(launcher, 'apply_host_git_identity', lambda mode, name, email: (name, email))
    monkeypatch.setattr(launcher, 'watch_display_ready', forbidden)
    original_run = launcher.run_pycharm
    # Supply a secret name at the actual launcher boundary, without changing
    # selected checkout authorization or the production argument builder.
    def run(options):
        options.secret_environment = ('PRINT_TEST_SECRET',)
        return original_run(options)
    monkeypatch.setattr(command, 'run_pycharm', run)
    captured = {}
    original_build = launcher.build_docker_args
    def build(config, files, env):
        args = original_build(config, files, env)
        captured.update(args=args, image=config.image, files=files)
        return args
    monkeypatch.setattr(launcher, 'build_docker_args', build)
    # A synthetic external-daemon translation proves rendering sees the final
    # host-side bind paths rather than an earlier intermediate plan.
    monkeypatch.setattr(launcher, 'translate_for_external_daemon',
                        lambda args, env: [arg.replace(str(tmp_path), '/daemon/fixture') for arg in args])
    capfd.readouterr()
    with patch.object(launcher.subprocess, 'run', side_effect=forbidden):
        assert cli.main(['project', 'run', '--print-command', '--set', 'cpus', '3']) == 0
    assert captured['args'][captured['args'].index('--cpus') + 1] == '3'
    output = capfd.readouterr()
    assert 'Python preparation progress' in output.err
    assert 'Child-style preparation progress' in output.err
    assert 'preparation progress' not in output.out
    assert 'do-not-render-this-value' not in output.out
    assert 'managed-secret-sentinel' not in output.out + output.err
    assert 'APP_PASSWORD=<redacted>' in output.out
    assert '--gpus' in output.out and '/data:ro' in output.out
    assert 'Required environment variables' in output.out
    assert 'Temporary Runtime plan:' in output.out
    assert ('Temporary Display token:' in output.out) == (display == 'contained')
    expected = ['docker', 'run', *[a.replace(str(tmp_path), '/daemon/fixture') for a in captured['args']], captured['image']]
    from devcapsule.docker_arguments import redact_environment
    assert shlex.split(output.out.replace('\\\n', ''), comments=True) == redact_environment(expected, {'APP_PASSWORD'})
    subprocess.run(['sh', '-n'], input=output.out, text=True, check=True)
    assert all(not path.exists() for path in vars(captured['files']).values() if isinstance(path, Path))
    assert all(p.read_bytes() == content for p, content in before.items())
    assert not (tmp_path / 'state' / 'devcapsule' / 'config-history').exists()


@pytest.mark.parametrize(
    "component,relative_path,defaults,explicit",
    [
        ("claude-code", "settings.json",
         {"permissions": {"defaultMode": "bypassPermissions"},
          "skipDangerousModePermissionPrompt": True},
         {"permissions": {"defaultMode": "plan", "allow": ["Read"]},
          "skipDangerousModePermissionPrompt": False, "model": "custom"}),
        ("antigravity-cli", "antigravity-cli/settings.json",
         {"toolPermission": "always-proceed"},
         {"toolPermission": "ask", "model": "custom"}),
    ],
)
def test_agent_settings_seed_and_upgrade_preserve_explicit_choices(
    tmp_path: Path, component: str, relative_path: str, defaults: dict, explicit: dict,
) -> None:
    from devcapsule.commands.project import _seed_component_state

    declaration = SimpleNamespace(component_id=component, slot_name="home")
    _seed_component_state(tmp_path, declaration)
    target = tmp_path / relative_path
    assert json.loads(target.read_text()) == defaults
    assert target.stat().st_mode & 0o777 == 0o600

    original = json.dumps(explicit)
    target.write_text(original)
    _seed_component_state(tmp_path, declaration)
    assert target.read_text() == original  # No rewrite, even formatting.

    partial: dict = {"model": "custom"}
    if component == "claude-code":
        partial["permissions"] = {"deny": ["WebFetch"]}
    target.write_text(json.dumps(partial))
    _seed_component_state(tmp_path, declaration)
    merged = json.loads(target.read_text())
    assert merged["model"] == "custom"
    if component == "claude-code":
        assert merged["permissions"] == {"defaultMode": "bypassPermissions", "deny": ["WebFetch"]}
    else:
        assert merged["toolPermission"] == "always-proceed"
    before = target.read_bytes(), target.stat().st_mtime_ns
    _seed_component_state(tmp_path, declaration)
    assert (target.read_bytes(), target.stat().st_mtime_ns) == before


@pytest.mark.parametrize("content", ['{broken', '[]', '{"permissions": null}', '{"permissions": "plan"}'])
def test_invalid_agent_settings_are_preserved(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], content: str,
) -> None:
    from devcapsule.commands.project import _seed_component_state

    target = tmp_path / "settings.json"
    target.write_text(content)
    _seed_component_state(tmp_path, SimpleNamespace(component_id="claude-code", slot_name="home"))
    assert target.read_text() == content
    assert "leaving component settings unchanged" in capsys.readouterr().err


@pytest.mark.parametrize("linked_parent", [False, True])
def test_agent_defaults_leave_linked_settings_untouched(tmp_path: Path, linked_parent: bool) -> None:
    from devcapsule.commands.project import _seed_component_state

    external = tmp_path / "external"
    external.mkdir()
    slot = tmp_path / "slot"
    slot.mkdir()
    if linked_parent:
        (slot / "antigravity-cli").symlink_to(external, target_is_directory=True)
    else:
        (slot / "antigravity-cli").mkdir()
        (slot / "antigravity-cli/settings.json").symlink_to(external / "settings.json")
    _seed_component_state(slot, SimpleNamespace(component_id="antigravity-cli", slot_name="home"))
    assert not (external / "settings.json").exists()


def test_adopted_agent_settings_are_not_seeded(tmp_path: Path) -> None:
    from devcapsule.commands.project import _component_state_mounts
    from devcapsule.platforms import Platform
    from devcapsule.resolution_matrix import MATRICES

    lock = tomllib.loads(MATRICES[Platform.LINUX_AMD64].resolve(
        ["frontend-ide", "claude-code-agent", "antigravity-agent"]
    ).render_lock())
    claude = tmp_path / "claude"
    gemini = tmp_path / "gemini"
    claude.mkdir()
    gemini.mkdir()
    configured = {"claude-code/home": str(claude), "antigravity-cli/home": str(gemini)}
    mounts = _component_state_mounts(tmp_path, lock, configured, object(), {"claude-code", "antigravity-cli"})
    assert len(mounts) == 2
    assert list(claude.iterdir()) == list(gemini.iterdir()) == []


def test_every_project_leaf_declares_its_capsule_access() -> None:
    """The project group applies CapsuleAccess per leaf after resolving the
    subcommand; a leaf without its own declaration would be a silent default."""
    from devcapsule.commands.framework import Group
    from devcapsule.commands.project import ProjectCommand
    from devcapsule.runtime_configuration import CapsuleAccess

    def leaves(group, prefix=()):
        for name, entry in group.subcommands().items():
            if isinstance(entry, type) and issubclass(entry, Group):
                yield from leaves(entry, (*prefix, name))
            else:
                yield (*prefix, name), entry

    declared = {path: leaf.__dict__.get("capsule_access") for path, leaf in leaves(ProjectCommand)}
    assert all(isinstance(access, CapsuleAccess) for access in declared.values()), declared
    assert declared[("config", "show")] is CapsuleAccess.INSPECTS
    assert declared[("versions", "show")] is CapsuleAccess.INSPECTS
    assert declared[("info",)] is CapsuleAccess.INSPECTS
    assert declared[("diagnose",)] is CapsuleAccess.INSPECTS
    assert declared[("run",)] is CapsuleAccess.MUTATES
    assert declared[("versions", "select")] is CapsuleAccess.MUTATES
    assert declared[("init",)] is CapsuleAccess.CREATES_HERE
    assert declared[("list",)] is CapsuleAccess.INDEPENDENT
    assert declared[("recursive-e2e", "preflight")] is CapsuleAccess.INDEPENDENT
    # Notifications are capsule state, never the project's records: they are
    # neither refused inside a capsule nor sent to the launcher.
    for leaf in ("list", "post", "read", "dismiss"):
        assert declared[("checkout", "notifications", leaf)] is CapsuleAccess.INDEPENDENT
    assert declared[("checkout", "decisions")] is CapsuleAccess.INDEPENDENT


def test_checkout_notifications_round_trip_from_the_host(tmp_path: Path, capsys, monkeypatch) -> None:
    """From the host the group acts on the checkout's persistent home, where the
    capsule's state lives; the file lands exactly where `project info` says the
    home is backed, and the listing shows it with its unread mark."""
    from devcapsule.configuration.bindings import configuration_binding_declarations, managed_binding_path
    from devcapsule.configuration.storage import lock_for, manifest_for

    project = tmp_path / "project"
    project.mkdir()
    initialize_project(project)
    for key, leaf in [("HOME", "home"), ("XDG_CONFIG_HOME", "config"), ("XDG_DATA_HOME", "data"),
                      ("XDG_STATE_HOME", "state")]:
        monkeypatch.setenv(key, str(tmp_path / leaf))
    for key in ("DEVCAPSULE_CONTAINER_NAME", "DEVCAPSULE_NOTIFICATIONS", "DEVCAPSULE_HOME_DIR",
                "DEVCAPSULE_CONSOLE_DECISIONS"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("USER", "owner")
    _, manifest = manifest_for(project)
    _, lock = lock_for(project, manifest)
    home = managed_binding_path(project, configuration_binding_declarations(lock)["home"])
    state = home / ".local" / "state" / "devcapsule"

    assert cli.main(["project", "--path", str(project), "checkout", "notifications", "post", "--kind", "gate",
                     "--title", "Gate failed on main", "--summary", "Two cases.", "--link", "/records/README.md",
                     "--json"]) == 0
    posted = json.loads(capsys.readouterr().out)
    assert posted["kind"] == "gate" and posted["posted-by"] == "owner" and posted["read-at"] is None
    assert (state / "notifications" / f"{posted['id']}.json").is_file()
    assert json.loads((state / "notifications" / f"{posted['id']}.json").read_text(encoding="utf-8")) == posted

    # A pending decision page of the console is merged into the listing, never copied.
    (state / "decisions").mkdir(parents=True)
    (state / "decisions" / "intake-pass.json").write_text(json.dumps(
        {"format": 1, "id": "intake-pass", "title": "Intake pass", "asked-by": "project-management",
         "asked-at": "2026-10-09T12:00:00+00:00", "items": []}), encoding="utf-8")
    assert cli.main(["project", "--path", str(project), "checkout", "notifications", "list"]) == 0
    listing = capsys.readouterr().out
    assert listing.startswith("2 unread of 2; * marks unread.\n")
    assert f"* {posted['posted-at']}  gate        {posted['id']}  Gate failed on main  /records/README.md" in listing
    assert "* 2026-10-09T12:00:00+00:00  decision    intake-pass  Intake pass  /decisions/intake-pass" in listing

    assert cli.main(["project", "--path", str(project), "checkout", "notifications", "read", posted["id"]]) == 0
    assert capsys.readouterr().out.startswith(f"Read {posted['id']} at ")
    assert cli.main(["project", "--path", str(project), "checkout", "notifications", "list", "--unread", "--json"]) == 0
    unread = json.loads(capsys.readouterr().out)
    assert unread["unread"] == 1 and [entry["id"] for entry in unread["notifications"]] == ["intake-pass"]
    assert unread["directory"] == str(state / "notifications") and unread["decisions"] == str(state / "decisions")

    assert cli.main(["project", "--path", str(project), "checkout", "notifications", "dismiss", "intake-pass"]) == 2
    assert "'intake-pass' is a decision: answer it in the web console" in capsys.readouterr().err
    assert cli.main(["project", "--path", str(project), "checkout", "notifications", "dismiss", posted["id"]]) == 0
    assert capsys.readouterr().out == f"Dismissed {posted['id']}\n"
    assert list((state / "notifications").iterdir()) == []
    assert cli.main(["project", "--path", str(project), "checkout", "notifications", "read", posted["id"]]) == 2
    assert "no notification" in capsys.readouterr().err
    assert cli.main(["project", "--path", str(project), "checkout", "notifications", "post", "--kind", "decision",
                     "--title", "No"]) == 2
    assert "Cannot post the notification: kind 'decision' is reserved" in capsys.readouterr().err

    # The launcher's home override moves the store with the home it mounts.
    monkeypatch.setenv("DEVCAPSULE_HOME_DIR", str(tmp_path / "elsewhere"))
    assert cli.main(["project", "--path", str(project), "checkout", "notifications", "list", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["directory"] == str(
        tmp_path / "elsewhere" / ".local" / "state" / "devcapsule" / "notifications")


def test_checkout_notifications_inside_a_capsule_use_its_own_state(tmp_path: Path, capsys, monkeypatch) -> None:
    """Inside a capsule the environment names the one checkout; `--path`, which
    the web console always passes, does not send the store to a host-side path."""
    monkeypatch.setenv("DEVCAPSULE_CONTAINER_NAME", "capsule-fixture")
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "home" / ".local" / "state"))
    monkeypatch.delenv("DEVCAPSULE_NOTIFICATIONS", raising=False)
    monkeypatch.chdir(tmp_path)
    assert cli.main(["project", "--path", str(tmp_path / "workspace" / "project"), "checkout", "notifications",
                     "post", "--kind", "note", "--title", "Hello", "--posted-by", "agent"]) == 0
    out = capsys.readouterr().out
    directory = tmp_path / "home" / ".local" / "state" / "devcapsule" / "notifications"
    assert out.startswith("Posted ") and out.rstrip().endswith(".json") and str(directory) in out
    assert len(list(directory.iterdir())) == 1
    assert cli.main(["project", "checkout", "notifications", "list", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["notifications"][0]["posted-by"] == "agent"


def test_checkout_notifications_outside_a_project_name_the_problem(tmp_path: Path, capsys, monkeypatch) -> None:
    monkeypatch.delenv("DEVCAPSULE_CONTAINER_NAME", raising=False)
    monkeypatch.delenv("DEVCAPSULE_NOTIFICATIONS", raising=False)
    monkeypatch.chdir(tmp_path)
    assert cli.main(["project", "checkout", "notifications", "list"]) == 2
    assert "Cannot locate this checkout's notifications" in capsys.readouterr().err


@pytest.mark.parametrize("binding", ["managed", "adopted", "explicit"])
def test_notification_host_store_matches_info_and_isolates_checkouts(tmp_path: Path, monkeypatch, binding: str) -> None:
    from devcapsule import notifications
    from devcapsule.configuration.file_formats import render_toml
    from devcapsule.configuration.storage import checkout_record_paths, manifest_for
    from devcapsule.project_information import project_information

    for key in ("HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME"):
        monkeypatch.setenv(key, str(tmp_path / key))
    for key in ("DEVCAPSULE_CONTAINER_NAME", "DEVCAPSULE_NOTIFICATIONS", "DEVCAPSULE_HOME_DIR"):
        monkeypatch.delenv(key, raising=False)
    project = tmp_path / "project"
    project.mkdir()
    initialize_project(project)
    other = tmp_path / "other"
    shutil.copytree(project, other)
    _, manifest = manifest_for(project)
    if binding != "managed":
        record, _ = checkout_record_paths(manifest, project)
        record.parent.mkdir(parents=True)
        document = {"devcapsule-checkout-schema-version": 1, "project": {key: manifest["project"][key] for key in ("creator", "slug")},
                    "checkout": {"path": str(project)}, "state": {"adopted": {"home": str(tmp_path / "adopted")}}}
        if binding == "explicit":
            document["configuration"] = {"bindings": {"host-directory": {"home": str(tmp_path / "explicit")}}}
        record.write_text(render_toml(document), encoding="utf-8")
    nested = project / "src"
    nested.mkdir()
    report = project_information(nested, runtime_fallback=False)
    home = Path(next(row["backing"] for row in report["persistence"] if row["name"] == "home"))
    store = notifications.store_for(nested)
    assert store.directory == home / ".local/state/devcapsule/notifications"
    if binding != "managed":
        assert home == tmp_path / binding
    second = notifications.store_for(other)
    assert store.directory != second.directory
    entry = store.post(kind="note", title="First checkout only", posted_by="agent")
    assert store.read(entry.id) == entry
    assert second.list() == [] and not second.directory.exists()
    override = tmp_path / "override"
    override.mkdir()
    alias = tmp_path / "home-link"
    alias.symlink_to(override, target_is_directory=True)
    monkeypatch.setenv("DEVCAPSULE_HOME_DIR", str(alias))
    assert notifications.store_for(nested).directory == override / ".local/state/devcapsule/notifications"


def test_notification_cli_empty_errors_read_and_no_link_text(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("DEVCAPSULE_NOTIFICATIONS", str(tmp_path / "notifications"))
    monkeypatch.delenv("DEVCAPSULE_CONSOLE_DECISIONS", raising=False)
    monkeypatch.delenv("USER", raising=False)
    command = ["project", "checkout", "notifications"]
    assert cli.main([*command, "list"]) == 0
    assert capsys.readouterr().out == f"No notifications under {tmp_path / 'notifications'}.\n"
    assert cli.main([*command, "post", "--kind", "note", "--title", "Hello", "--json"]) == 0
    entry = json.loads(capsys.readouterr().out)
    assert entry["posted-by"] == "unknown"
    assert cli.main([*command, "read", entry["id"]]) == 0
    capsys.readouterr()
    (tmp_path / "notifications/broken.json").write_text("{", encoding="utf-8")
    assert cli.main([*command, "list"]) == 0
    output = capsys.readouterr().out
    assert output.startswith("0 unread of 2; * marks unread.\n")
    assert f"  {entry['posted-at']}  note        {entry['id']}  Hello\n" in output
    assert "  ! broken: broken.json is not a JSON document" in output
    assert cli.main([*command, "list", "--unread", "--json"]) == 0
    document = json.loads(capsys.readouterr().out)
    assert document["unread"] == 0 and [item["id"] for item in document["notifications"]] == ["broken"]


@pytest.mark.parametrize("operation", ["list", "post", "read", "dismiss"])
def test_notification_cli_reports_filesystem_refusals(tmp_path: Path, monkeypatch, capsys, operation: str) -> None:
    directory = tmp_path / "notifications"
    monkeypatch.setenv("DEVCAPSULE_NOTIFICATIONS", str(directory))
    directory.write_text("not a directory", encoding="utf-8")
    arguments = {"list": [], "post": ["--kind", "note", "--title", "No"], "read": ["missing"], "dismiss": ["missing"]}
    assert cli.main(["project", "checkout", "notifications", operation, *arguments[operation]]) == 2
    error = capsys.readouterr().err
    assert "not a directory" in error.lower() and "Traceback" not in error
    assert directory.read_text() == "not a directory"
