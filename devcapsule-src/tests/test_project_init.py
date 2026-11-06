"""Focused tests for the v027 ``project init`` postcondition and entry states."""

from __future__ import annotations

from tests.launch_preparation import run_until_prepared

import io
import argparse
import os
from pathlib import Path
import tomllib
from unittest.mock import patch

import pytest
import shutil

from devcapsule import cli
from devcapsule.commands.project import ProjectInitCommand, _init_selection
from devcapsule.elicitation import ElicitationIncomplete
from devcapsule.configuration.operations import (
    InitializeRequest,
    ProvidedAnswer,
    initialize_project,
)
from devcapsule.configuration.file_formats import (
    ProjectConfigurationError,
)
from devcapsule.platforms import Platform
from devcapsule.resolution_matrix import MATRICES, ResolutionMatrix

pytestmark = pytest.mark.legacy


def matrix_without_antigravity_validation() -> ResolutionMatrix:
    """The embedded matrix with the Antigravity CLI's validation removed.

    Tests of behaviour that needs a need with *no* fully validated base —
    here PyCharm plus antigravity — rebuild that state from the real pins
    rather than freezing a copy of them.
    """

    real = MATRICES[Platform.LINUX_AMD64]
    return ResolutionMatrix(
        platform=real._platform,
        matrix_version=real._matrix_version,
        bases=real._bases,
        components=real._components,
        edges=tuple(
            edge for edge in real._verified.values() if edge.component_id != "antigravity-cli"
        ),
        couplings=real._couplings,
        capability_table=real._capability_table,
        materialization=real._materialization,
    )


def sparse_matrix():
    """Patch the matrix project operations consult to the reduced one."""

    return patch(
        "devcapsule.configuration.operations.MATRICES",
        {Platform.LINUX_AMD64: matrix_without_antigravity_validation()},
    )


def isolated_env(tmp_path: Path) -> dict[str, str]:
    return {
        "HOME": str(tmp_path / "home"),
        "XDG_CONFIG_HOME": str(tmp_path / "config"),
        "XDG_DATA_HOME": str(tmp_path / "data"),
    }


def read_toml(path: Path) -> dict:
    with path.open("rb") as stream:
        return tomllib.load(stream)


def matrix_reference_lock() -> dict:
    content = MATRICES[Platform.LINUX_AMD64].resolve(["python-ide"]).render_lock()
    return tomllib.loads(content)


def matrix_base_reference() -> str:
    return str(matrix_reference_lock()["base"]["reference"])




@pytest.mark.parametrize("flags,message", [
    (["--offer", "python=3"], "Unsupported requirement form"),
    (["--require", "python", "--offer", "python"], "both required and optional"),
])
def test_init_refuses_invalid_tool_scope_before_writes(tmp_path: Path, monkeypatch, capsys, flags, message) -> None:
    for key, value in isolated_env(tmp_path).items():
        monkeypatch.setenv(key, value)
    project = tmp_path / "project"
    project.mkdir()
    assert cli.main(["project", "--path", str(project), "init", "--creator", "owner@example.test", *flags]) == 2
    assert message in capsys.readouterr().err
    assert not (project / ".devcapsule").exists()
    assert not list((tmp_path / "config").rglob("*.toml"))


def test_init_bad_mount_is_refused_before_writes(tmp_path: Path, monkeypatch) -> None:
    for key, value in isolated_env(tmp_path).items():
        monkeypatch.setenv(key, value)
    project = tmp_path / "project"
    project.mkdir()
    assert cli.main([*full_init_command(project), "--project-mount", "relative/path"]) == 2
    assert not (project / ".devcapsule").exists()
    assert not list((tmp_path / "config").rglob("*.toml"))


def test_explicit_no_ide_keeps_its_normalization(tmp_path: Path, monkeypatch) -> None:
    for key, value in isolated_env(tmp_path).items():
        monkeypatch.setenv(key, value)
    project = tmp_path / "project"
    project.mkdir()
    assert cli.main(["project", "--path", str(project), "init", "--creator", "owner@example.test",
                     "--ide", " NONE ", "--require", "none"]) == 0
    assert read_toml(project / ".devcapsule/devcapsule.toml")["capabilities"] == {"required": []}
    records = list((tmp_path / "config").rglob("devcapsule.checkout.toml"))
    assert len(records) == 1
    assert "capabilities" not in read_toml(records[0])
    assert not records[0].with_name("devcapsule.resolved.toml").exists()


def test_init_refuses_a_pending_capability_transaction_before_writes(tmp_path: Path, monkeypatch) -> None:
    for key, value in isolated_env(tmp_path).items():
        monkeypatch.setenv(key, value)
    project = tmp_path / "project"
    journal = project / ".devcapsule/.capability-transaction.toml"
    journal.parent.mkdir(parents=True)
    journal.write_text("# unfinished edit\n")
    with pytest.raises(ProjectConfigurationError, match="Interrupted configuration edit"):
        initialize_project(InitializeRequest(directory=project, creator="owner@example.test", interactive=False))
    assert list(journal.parent.iterdir()) == [journal]
    assert journal.read_text() == "# unfinished edit\n"
    assert not list((tmp_path / "config").rglob("*.toml"))


def test_legacy_manifest_ide_prevents_a_second_ide_question(tmp_path: Path, monkeypatch) -> None:
    for key, value in isolated_env(tmp_path).items():
        monkeypatch.setenv(key, value)
    project = tmp_path / "project"
    manifest_path = project / ".devcapsule/devcapsule.toml"
    manifest_path.parent.mkdir(parents=True)
    original = '''# Keep this note.
devcapsule-schema-version = 1
[project]
name = "Project"
slug = "project"
creator = "mailto:owner@example.test"
mount = "/workspace/project"
[capabilities]
need = ["python", "python-ide"]
'''
    manifest_path.write_text(original)
    prompts = io.StringIO()
    report = initialize_project(
        InitializeRequest(directory=project, interactive=True,
                          answers=(ProvidedAnswer("authorize", "base-image", "default"),)),
        input_stream=io.StringIO(""), output_stream=prompts,
    )
    assert prompts.getvalue() == ""
    assert report.resolve is not None
    assert read_toml(report.resolve.resolution_path)["runtime"]["component"] == "pycharm"
    assert manifest_path.read_text() == original


def test_batch_failure_keeps_an_existing_manifest_and_lock(tmp_path: Path, monkeypatch) -> None:
    for key, value in isolated_env(tmp_path).items():
        monkeypatch.setenv(key, value)
    project = tmp_path / "project"
    project.mkdir()
    assert cli.main(["project", "--path", str(project), "init", "--creator", "owner@example.test"]) == 0
    before = {path: path.read_bytes() for path in tmp_path.rglob("*.toml")}
    lock = project / ".devcapsule/devcapsule.linux-amd64.lock"
    lock_before = lock.read_bytes()
    with pytest.raises(ElicitationIncomplete, match="base-image"):
        initialize_project(InitializeRequest(
            directory=project, ide="pycharm", regenerate=True, interactive=False,
            answers=(ProvidedAnswer("authorize", "network", "host", justification="dev servers"),),
        ))
    assert {path: path.read_bytes() for path in tmp_path.rglob("*.toml")} == before
    assert lock.read_bytes() == lock_before


@pytest.mark.parametrize("ide", ["python-ide", "pycharm"])
def test_noninteractive_init_reaches_the_full_postcondition(tmp_path: Path, capsys, ide: str) -> None:
    project = tmp_path / "fresh-project"
    project.mkdir()
    with patch.dict(os.environ, isolated_env(tmp_path), clear=False):
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
                    ide,
                    "--creator",
                    "https://github.com/example",
                    "--authorize",
                    "base-image",
                    "default",
                ]
            )
            == 0
        )
        output = capsys.readouterr().out

        manifest = read_toml(project / ".devcapsule" / "devcapsule.toml")
        assert manifest["project"] == {
            "name": "fresh-project",
            "slug": "fresh-project",
            "creator": "https://github.com/example",
            "mount": "/workspace/fresh-project",
        }
        assert manifest["capabilities"]["required"] == ["python"]
        assert manifest["devcapsule-schema-version"] == 2
        assert "host" not in manifest

        lock = read_toml(project / ".devcapsule" / "devcapsule.linux-amd64.lock")
        assert lock["resolution-matrix-version"] == (
            matrix_reference_lock()["resolution-matrix-version"]
        )
        assert lock["base"]["reference"] == matrix_base_reference()

        config_root = tmp_path / "config" / "devcapsule" / "projects"
        records = list(config_root.rglob("devcapsule.checkout.toml"))
        assert len(records) == 1
        checkout = read_toml(records[0])
        assert checkout["authorization"]["base-image"]["reference"] == matrix_base_reference()
        assert "network" not in checkout["authorization"]
        resolution = read_toml(records[0].with_name("devcapsule.resolved.toml"))
        assert resolution["devcapsule-resolved-schema-version"] == 1
        assert resolution["runtime"]["component"] == "pycharm"

        assert "Created" in output
        assert "Project initialized" in output


def full_init_command(project: Path) -> list[str]:
    return [
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


def test_repeated_init_applies_carried_answers_to_the_standing_checkout(
    tmp_path: Path, capsys
) -> None:
    project = tmp_path / "fresh-project"
    project.mkdir()
    with patch.dict(os.environ, isolated_env(tmp_path), clear=False):
        assert cli.main(full_init_command(project)) == 0
        capsys.readouterr()

        # Re-pasting the identical full command must not silently drop its
        # --authorize answers: they are applied and the resolution refreshed.
        assert cli.main(full_init_command(project)) == 0
        output = capsys.readouterr().out
        assert "Kept" in output
        assert "Answered for this checkout: base-image." in output
        assert "Project initialized; 'devcapsule project run' starts it." in output


def test_repeated_init_without_answers_still_refuses(tmp_path: Path, capsys) -> None:
    project = tmp_path / "fresh-project"
    project.mkdir()
    with patch.dict(os.environ, isolated_env(tmp_path), clear=False):
        assert cli.main(full_init_command(project)) == 0
        capsys.readouterr()

        assert cli.main(full_init_command(project)[:-3]) == 2
        assert "already fully initialized" in capsys.readouterr().err


def test_require_tool_grows_the_project_and_keeps_the_leading_comment(
    tmp_path: Path, capsys
) -> None:
    project = tmp_path / "fresh-project"
    project.mkdir()
    manifest_path = project / ".devcapsule" / "devcapsule.toml"
    with patch.dict(os.environ, isolated_env(tmp_path), clear=False):
        assert cli.main(full_init_command(project)) == 0
        manifest_path.write_text(
            "# authored note at the head\n" + manifest_path.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        capsys.readouterr()

        assert cli.main(["project", "--path", str(project), "config", "require", "postgresql-client"]) == 0
        output = capsys.readouterr().out
        assert "Required postgresql-client; the manifest and the lock are updated." in output
        assert "Required: python postgresql-client" in output
        # The owner's own checkout is re-derived so 'project run' works at once.
        assert "Resolved " in output

        manifest_text = manifest_path.read_text(encoding="utf-8")
        assert manifest_text.startswith("# authored note at the head\n")
        assert 'required = ["python", "postgresql-client"]' in manifest_text
        lock = read_toml(project / ".devcapsule" / "devcapsule.linux-amd64.lock")
        assert lock["components"]["postgresql-client"]["delivery-policy"] == "base-image"
        assert "interactive-surface" not in lock["components"]

        # Requiring it again converges: the same declaration, nothing new.
        assert cli.main(["project", "--path", str(project), "config", "require", "postgresql-client"]) == 0
        assert 'required = ["python", "postgresql-client"]' in manifest_path.read_text(encoding="utf-8")


def test_require_tool_refuses_personal_and_unknown_names_without_touching_the_manifest(
    tmp_path: Path, capsys
) -> None:
    project = tmp_path / "fresh-project"
    project.mkdir()
    manifest_path = project / ".devcapsule" / "devcapsule.toml"
    with patch.dict(os.environ, isolated_env(tmp_path), clear=False):
        assert cli.main(full_init_command(project)) == 0
        before = manifest_path.read_text(encoding="utf-8")
        capsys.readouterr()

        assert cli.main(["project", "--path", str(project), "config", "require", "frontend-ide"]) == 2
        assert "each developer's" in capsys.readouterr().err
        assert manifest_path.read_text(encoding="utf-8") == before

        assert cli.main(["project", "--path", str(project), "config", "require", "quantum-debugger"]) == 2
        assert "Unknown tool 'quantum-debugger'" in capsys.readouterr().err
        assert manifest_path.read_text(encoding="utf-8") == before


def test_init_repairs_a_deleted_checkout_config_tree(tmp_path: Path, capsys) -> None:
    project = tmp_path / "fresh-project"
    project.mkdir()
    with patch.dict(os.environ, isolated_env(tmp_path), clear=False):
        assert cli.main(full_init_command(project)) == 0
        capsys.readouterr()
        config_root = tmp_path / "config" / "devcapsule" / "projects"
        record = next(config_root.rglob("devcapsule.checkout.toml"))
        shutil.rmtree(record.parent)

        # The owner's recovery flow: wipe the checkout's config directory and
        # re-run the identical init; repair restores record, authorization,
        # and a fresh resolution.
        assert cli.main(full_init_command(project)) == 0
        output = capsys.readouterr().out
        assert "Answered for this checkout: base-image." in output
        restored = next(config_root.rglob("devcapsule.checkout.toml"))
        assert read_toml(restored)["authorization"]["base-image"]["reference"] == (
            matrix_base_reference()
        )
        resolution = read_toml(restored.with_name("devcapsule.resolved.toml"))
        assert resolution["devcapsule-resolved-schema-version"] == 1


def test_missing_base_authorization_batch_fails_with_the_exact_remedy(
    tmp_path: Path, capsys
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    with patch.dict(os.environ, isolated_env(tmp_path), clear=False):
        assert (
            cli.main(
                [
                    "project",
                    "--path",
                    str(project),
                    "init",
                    "--ide",
                    "python-ide",
                    "--creator",
                    "dev@example.test",
                ]
            )
            == 2
        )
    message = capsys.readouterr().err
    assert f"--authorize base-image {matrix_base_reference()}" in message
    # The silent no-recommendation decision: unflagged intent questions do not
    # appear in the failure and record no recommendation.
    assert "docker-daemon" not in message
    assert not (project / ".devcapsule").exists()
    assert not list((tmp_path / "config").rglob("*.toml"))


def test_missing_creator_fails_before_writing_any_artifact(tmp_path: Path, capsys) -> None:
    project = tmp_path / "project"
    project.mkdir()
    with patch.dict(os.environ, isolated_env(tmp_path), clear=False):
        assert (
            cli.main(["project", "--path", str(project), "init", "--ide", "python-ide"])
            == 2
        )
    assert "--creator CREATOR" in capsys.readouterr().err
    assert not (project / ".devcapsule").exists()


def test_email_creator_is_normalized_to_mailto(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    with patch.dict(os.environ, isolated_env(tmp_path), clear=False):
        assert (
            cli.main(
                [
                    "project",
                    "--path",
                    str(project),
                    "init",
                    "--ide",
                    "python-ide",
                    "--creator",
                    "dev@example.test",
                    "--authorize",
                    "base-image",
                    "default",
                ]
            )
            == 0
        )
    manifest = read_toml(project / ".devcapsule" / "devcapsule.toml")
    assert manifest["project"]["creator"] == "mailto:dev@example.test"


def test_recommendation_answer_authors_manifest_and_owner_authorization(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    with patch.dict(os.environ, isolated_env(tmp_path), clear=False):
        assert (
            cli.main(
                [
                    "project",
                    "--path",
                    str(project),
                    "init",
                    "--ide",
                    "python-ide",
                    "--creator",
                    "https://github.com/example",
                    "--authorize",
                    "docker-daemon",
                    "host-socket",
                    "Required to run peer capsules in the test suite.",
                    "--authorize",
                    "base-image",
                    "default",
                ]
            )
            == 0
        )
        manifest = read_toml(project / ".devcapsule" / "devcapsule.toml")
        recommended = manifest["host"]["docker"]["mode"]["recommended"]
        assert recommended["value"] == "host-socket"
        assert recommended["justification"] == "Required to run peer capsules in the test suite."

        config_root = tmp_path / "config" / "devcapsule" / "projects"
        record = read_toml(next(config_root.rglob("devcapsule.checkout.toml")))
        assert record["authorization"]["docker-daemon"]["value"] == "host-socket"
        resolution = read_toml(
            next(config_root.rglob("devcapsule.resolved.toml"))
        )
        assert resolution["authorization"]["docker-daemon"] == "host-socket"


def test_recommendation_without_justification_batch_fails(tmp_path: Path, capsys) -> None:
    project = tmp_path / "project"
    project.mkdir()
    with patch.dict(os.environ, isolated_env(tmp_path), clear=False):
        assert (
            cli.main(
                [
                    "project",
                    "--path",
                    str(project),
                    "init",
                    "--ide",
                    "python-ide",
                    "--creator",
                    "https://github.com/example",
                    "--authorize",
                    "docker-daemon",
                    "host-socket",
                ]
            )
            == 2
        )
    message = capsys.readouterr().err
    assert "docker-daemon (justification)" in message


def test_repair_completes_a_hand_authored_manifest(tmp_path: Path, capsys) -> None:
    project = tmp_path / "project"
    (project / ".devcapsule").mkdir(parents=True)
    (project / ".devcapsule" / "devcapsule.toml").write_text(
        "\n".join(
            [
                "devcapsule-schema-version = 1",
                "",
                "[capabilities]",
                'need = ["python", "python-ide"]',
                "",
                "[project]",
                'name = "Hand Authored"',
                'slug = "hand-authored"',
                'creator = "https://github.com/example"',
                'mount = "/workspace/hand-authored"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    original = (project / ".devcapsule" / "devcapsule.toml").read_bytes()
    with patch.dict(os.environ, isolated_env(tmp_path), clear=False):
        assert (
            cli.main(
                [
                    "project",
                    "--path",
                    str(project),
                    "init",
                    "--authorize",
                    "base-image",
                    "default",
                ]
            )
            == 0
        )
    output = capsys.readouterr().out
    assert "Honored existing" in output
    # The authored manifest is byte-identical: repair completed the missing
    # derived artifacts without rewriting authored content.
    assert (project / ".devcapsule" / "devcapsule.toml").read_bytes() == original
    assert (project / ".devcapsule" / "devcapsule.linux-amd64.lock").is_file()


def test_fully_initialized_project_fails_loudly_naming_regenerate(
    tmp_path: Path, capsys
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    arguments = [
        "project",
        "--path",
        str(project),
        "init",
        "--ide", "python-ide",
        "--creator",
        "https://github.com/example",
        "--authorize",
        "base-image",
        "default",
    ]
    with patch.dict(os.environ, isolated_env(tmp_path), clear=False):
        assert cli.main(arguments) == 0
        capsys.readouterr()
        # A repeat carrying answers applies them (see the repeated-init
        # tests); the refusal is for a repeat with nothing to apply.
        assert cli.main(arguments[:-3]) == 2
        assert "--regenerate" in capsys.readouterr().err
        assert cli.main([*arguments, "--regenerate"]) == 0


def test_init_denial_changes_checkout_without_rewriting_recommendation(tmp_path: Path, capsys) -> None:
    project = tmp_path / "project"
    project.mkdir()
    with patch.dict(os.environ, isolated_env(tmp_path), clear=False):
        assert (
            cli.main(
                [
                    "project",
                    "--path",
                    str(project),
                    "init",
                    "--ide",
                    "python-ide",
                    "--creator",
                    "https://github.com/example",
                    "--authorize",
                    "network",
                    "host",
                    "Reach host-bound services.",
                    "--authorize",
                    "base-image",
                    "default",
                ]
            )
            == 0
        )
        manifest_path = project / ".devcapsule/devcapsule.toml"
        manifest_before = manifest_path.read_bytes()
        capsys.readouterr()
        assert (
            cli.main(
                [
                    "project",
                    "--path",
                    str(project),
                    "init",
                    "--regenerate",
                    "--authorize",
                    "network",
                    "none",
                ]
            )
            == 0
        )
        assert manifest_path.read_bytes() == manifest_before
        record = next((tmp_path / "config").rglob("devcapsule.checkout.toml"))
        assert read_toml(record)["authorization"]["network"]["value"] == "bridge"


def test_interactive_init_prompts_in_the_settled_order(tmp_path: Path) -> None:
    project = tmp_path / "interactive-project"
    project.mkdir()
    prompts = io.StringIO()
    # creator; require; ide; default agent (no); four recommendations (Enter = none);
    # base (Enter = yes).
    answers = io.StringIO(
        "https://github.com/example\npython\npython-ide\nno\n\n\n\n\n\n"
    )
    with patch.dict(os.environ, isolated_env(tmp_path), clear=False):
        report = initialize_project(
            InitializeRequest(directory=project, interactive=True),
            input_stream=answers,
            output_stream=prompts,
        )
    transcript = prompts.getvalue()
    assert "Project creator" in transcript
    assert "Capabilities the project requires" in transcript
    assert "Your IDE for this checkout" in transcript
    assert "default agent component (antigravity-agent)" in transcript
    assert "[none]" in transcript
    assert "[default]" in transcript
    assert transcript.count("Recommend ") == 4
    assert "Recommend network = host" in transcript
    assert "Recommend host-x11" not in transcript
    manifest = read_toml(project / ".devcapsule" / "devcapsule.toml")
    assert "host" not in manifest
    assert report.answered == ("base-image",)
    assert report.carried == ()
    assert report.recommended == ()
    assert report.required == ("python",)
    assert report.ide == "python-ide"


def local_base_details(reference: str, identity: str):
    from devcapsule.materialization import ImageDetails

    return ImageDetails(
        reference=reference,
        identity=identity,
        labels={
            "devcapsule.image.managed": "true",
            "devcapsule.metadata.version": "1",
            "devcapsule.image.kind": "base",
            "devcapsule.base.recipe-version": "5",
        },
        operating_system="linux",
        architecture="amd64",
    )




def test_init_local_base_selection_needs_interactive_confirmation(
    tmp_path: Path, capsys
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    selection = "mycodespaceai/devcapsule-base:v0.2.9-test"
    with patch.dict(os.environ, isolated_env(tmp_path), clear=False):
        with patch(
            "devcapsule.configuration.operations.required_local_image",
            return_value=local_base_details(selection, f"sha256:{'d' * 64}"),
        ):
            assert (
                cli.main(
                    [
                        "project",
                        "--path",
                        str(project),
                        "init",
                        "--ide", "python-ide",
                        "--creator",
                        "https://github.com/example",
                        "--authorize",
                        "base-image",
                        selection,
                    ]
                )
                == 2
            )
    message = capsys.readouterr().err
    assert "base-image (confirmation)" in message
    assert "config authorize base-image" in message


def test_init_base_selection_solicits_informed_consent_interactively(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    selection = "mycodespaceai/devcapsule-base:v0.2.9-test"
    identity = f"sha256:{'d' * 64}"
    prompts = io.StringIO()
    # creator; require (none); ide; default agent (no); four recommendations (Enter = none);
    # consent (Enter = yes).
    answers = io.StringIO("https://github.com/example\n\npython-ide\nno\n\n\n\n\n\n")
    with patch.dict(os.environ, isolated_env(tmp_path), clear=False):
        with patch(
            "devcapsule.configuration.operations.required_local_image",
            return_value=local_base_details(selection, identity),
        ):
            initialize_project(
                InitializeRequest(
                    directory=project,
                    interactive=True,
                    answers=(
                        ProvidedAnswer(family="authorize", name="base-image", value=selection),
                    ),
                ),
                input_stream=answers,
                output_stream=prompts,
            )
    transcript = prompts.getvalue()
    assert f"Image ID: {identity}" in transcript
    assert "devcapsule.base.recipe-version = 5" in transcript
    assert "overrides the recommendation for this checkout only" in transcript
    records = list((tmp_path / "config").rglob("devcapsule.checkout.toml"))
    authorization = read_toml(records[0])["authorization"]["base-image"]
    assert authorization == {
        "reference": selection,
        "lock-digest": authorization["lock-digest"],
        "image-id": identity,
    }


def test_init_base_selection_consent_can_be_declined(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    selection = "mycodespaceai/devcapsule-base:v0.2.9-test"
    answers = io.StringIO("https://github.com/example\n\npython-ide\nno\n\n\n\n\nno\n")
    with patch.dict(os.environ, isolated_env(tmp_path), clear=False):
        with patch(
            "devcapsule.configuration.operations.required_local_image",
            return_value=local_base_details(selection, f"sha256:{'d' * 64}"),
        ):
            with pytest.raises(ProjectConfigurationError, match="declined"):
                initialize_project(
                    InitializeRequest(
                        directory=project,
                        interactive=True,
                        answers=(
                            ProvidedAnswer(
                                family="authorize", name="base-image", value=selection
                            ),
                        ),
                    ),
                    input_stream=answers,
                    output_stream=io.StringIO(),
                )


def test_init_base_answer_that_is_neither_answer_nor_reference_is_explained(
    tmp_path: Path, capsys
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    with patch.dict(os.environ, isolated_env(tmp_path), clear=False):
        assert (
            cli.main(
                [
                    "project",
                    "--path",
                    str(project),
                    "init",
                    "--ide",
                    "python-ide",
                    "--creator",
                    "https://github.com/example",
                    "--authorize",
                    "base-image",
                    "maybe",
                ]
            )
            == 2
        )
    message = capsys.readouterr().err
    assert "resolution matrix selected" in message
    assert "locally built or pulled image" in message
    assert "neither a value nor an image reference" in message


def test_yes_is_not_an_authorization_value(tmp_path: Path, capsys) -> None:
    """Owner ruling 2026-09-03: authorizations are KV pairs; a digest is a
    value, a tag points at one, 'default' accepts the recommendation —
    'yes' is none of those."""

    project = tmp_path / "project"
    project.mkdir()
    with patch.dict(os.environ, isolated_env(tmp_path), clear=False):
        assert (
            cli.main(
                [
                    "project",
                    "--path",
                    str(project),
                    "init",
                    "--ide",
                    "python-ide",
                    "--creator",
                    "https://github.com/example",
                    "--authorize",
                    "base-image",
                    "yes",
                ]
            )
            == 2
        )
    message = capsys.readouterr().err
    assert "takes a value" in message
    assert "'default'" in message


def test_config_authorize_accepts_the_default_keyword(tmp_path: Path, capsys) -> None:
    project = tmp_path / "project"
    project.mkdir()
    with patch.dict(os.environ, isolated_env(tmp_path), clear=False):
        assert cli.main(full_init_command(project)) == 0
        capsys.readouterr()
        assert (
            cli.main(
                [
                    "project",
                    "--path",
                    str(project),
                    "config",
                    "authorize",
                    "base-image",
                    "default",
                ]
            )
            == 0
        )
        records = list((tmp_path / "config").rglob("devcapsule.checkout.toml"))
        authorization = read_toml(records[0])["authorization"]["base-image"]
        assert authorization["reference"] == matrix_base_reference()
        assert "image-id" not in authorization


def test_init_base_answer_none_is_refused_as_mandatory(tmp_path: Path, capsys) -> None:
    project = tmp_path / "project"
    project.mkdir()
    with patch.dict(os.environ, isolated_env(tmp_path), clear=False):
        assert (
            cli.main(
                [
                    "project",
                    "--path",
                    str(project),
                    "init",
                    "--ide",
                    "python-ide",
                    "--creator",
                    "https://github.com/example",
                    "--authorize",
                    "base-image",
                    "none",
                ]
            )
            == 2
        )
    assert "no deny state" in capsys.readouterr().err


def test_init_unverified_resolves_past_the_matrix_with_a_gentle_warning(
    tmp_path: Path, capsys
) -> None:
    """Owner ruling 2026-09-03: the matrix may be stale or wrong; --unverified
    lets a sophisticated user through, warning gently and recording the
    unverified combinations in the committed lock."""

    project = tmp_path / "project"
    project.mkdir()
    need = [
        "project",
        "--path",
        str(project),
        "init",
        "--ide", "python-ide",
        "--require",
        "antigravity-agent",
        "--creator",
        "https://github.com/example",
        "--authorize",
        "base-image",
        "default",
        "--authorize",
        "antigravity-download",
        "true",
    ]
    with patch.dict(os.environ, isolated_env(tmp_path), clear=False), sparse_matrix():
        # With antigravity's validation removed no fully validated base
        # exists, and the strict form discloses the gap and the experiment.
        assert cli.main(need) == 2
        refusal = capsys.readouterr().err
        assert "Not yet validated: antigravity-cli 1.4.12 on base v0.3.0-local-linux-x86_64." in refusal
        assert "Run it as an experiment with --unverified" in refusal

        assert cli.main([*need, "--unverified"]) == 0
        warning = capsys.readouterr().err
        assert "Running as an experiment. Not yet validated: antigravity-cli 1.4.12 on base v0.3.0-local-linux-x86_64." in warning

    # The required capability records its unvalidated combination in the shared lock.
    lock = read_toml(project / ".devcapsule" / "devcapsule.linux-amd64.lock")
    assert "antigravity-cli" in lock["unverified-combinations"]


def test_init_refuses_a_published_non_recommended_digest(tmp_path: Path, capsys) -> None:
    project = tmp_path / "project"
    project.mkdir()
    foreign = f"docker.io/other/devcapsule-base@sha256:{'e' * 64}"
    with patch.dict(os.environ, isolated_env(tmp_path), clear=False):
        assert (
            cli.main(
                [
                    "project",
                    "--path",
                    str(project),
                    "init",
                    "--ide",
                    "python-ide",
                    "--creator",
                    "https://github.com/example",
                    "--authorize",
                    "base-image",
                    foreign,
                ]
            )
            == 2
        )
    assert "project-reviewed metadata" in capsys.readouterr().err


def test_interactive_decline_of_the_base_is_a_clean_failure(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    answers = io.StringIO("https://github.com/example\n\npython-ide\nno\n\n\n\n\nno\n")
    with patch.dict(os.environ, isolated_env(tmp_path), clear=False):
        with pytest.raises(ProjectConfigurationError, match="declined"):
            initialize_project(
                InitializeRequest(directory=project, interactive=True),
                input_stream=answers,
                output_stream=io.StringIO(),
            )


def test_claude_capability_requires_the_acquisition_answer(tmp_path: Path, capsys) -> None:
    project = tmp_path / "project"
    project.mkdir()
    base_arguments = [
        "project",
        "--path",
        str(project),
        "init",
        "--ide",
        "python-ide",
        "--offer",
        "claude-code-agent",
        "--creator",
        "https://github.com/example",
        "--authorize",
        "base-image",
        "default",
    ]
    with patch.dict(os.environ, isolated_env(tmp_path), clear=False):
        assert cli.main(base_arguments) == 2
        assert "--authorize claude-code-download true" in capsys.readouterr().err
        assert (
            cli.main([*base_arguments, "--authorize", "claude-code-download", "true"]) == 0
        )
        config_root = tmp_path / "config" / "devcapsule" / "projects"
        record = read_toml(next(config_root.rglob("devcapsule.checkout.toml")))
        assert record["authorization"]["claude-code-download"]["value"] is True


def test_antigravity_capability_requires_the_acquisition_answer(
    tmp_path: Path, capsys
) -> None:
    """The generalized gate asks for every locked vendor acquisition."""

    project = tmp_path / "project"
    project.mkdir()
    base_arguments = [
        "project",
        "--path",
        str(project),
        "init",
        "--require",
        "node",
        "--ide",
        "frontend-ide",
        "--offer",
        "antigravity-agent",
        "--creator",
        "https://github.com/example",
        "--authorize",
        "base-image",
        "default",
    ]
    with patch.dict(os.environ, isolated_env(tmp_path), clear=False):
        assert cli.main(base_arguments) == 2
        assert "--authorize antigravity-download true" in capsys.readouterr().err
        assert (
            cli.main([*base_arguments, "--authorize", "antigravity-download", "true"]) == 0
        )
        config_root = tmp_path / "config" / "devcapsule" / "projects"
        record = read_toml(next(config_root.rglob("devcapsule.checkout.toml")))
        assert record["authorization"]["antigravity-download"]["value"] is True
        from devcapsule.configuration.storage import lock_for
        lock = lock_for(project, read_toml(project / ".devcapsule" / "devcapsule.toml"))[1]
        assert lock["components"]["antigravity-cli"]["version"] == "1.4.12"


def test_noninteractive_need_without_an_agent_stays_explicit(tmp_path: Path) -> None:
    """A noninteractive requirement list is authored content; the default agent
    joins only through its own flag or the interactive question."""

    project = tmp_path / "project"
    project.mkdir()
    with patch.dict(os.environ, isolated_env(tmp_path), clear=False):
        assert (
            cli.main(
                [
                    "project",
                    "--path",
                    str(project),
                    "init",
                    "--require",
                    "node",
                    "--ide",
                    "frontend-ide",
                    "--creator",
                    "https://github.com/example",
                    "--authorize",
                    "base-image",
                    "default",
                ]
            )
            == 0
        )
    manifest = read_toml(project / ".devcapsule" / "devcapsule.toml")
    assert manifest["capabilities"]["required"] == ["node"]
    record = read_toml(next((tmp_path / "config").rglob("devcapsule.checkout.toml")))
    assert record["capabilities"]["selected"] == ["frontend-ide"]


def test_interactive_init_offers_the_default_agent(tmp_path: Path) -> None:
    """Enter at the default-agent question selects antigravity and its gate."""

    project = tmp_path / "interactive-project"
    project.mkdir()
    prompts = io.StringIO()
    # creator; require; ide; default agent (Enter = yes); four recommendations
    # (Enter = none); base (Enter = yes); antigravity acquisition (Enter = yes).
    answers = io.StringIO(
        "https://github.com/example\nnode\nfrontend-ide\n\n\n\n\n\n\n\n"
    )
    with patch.dict(os.environ, isolated_env(tmp_path), clear=False):
        report = initialize_project(
            InitializeRequest(directory=project, interactive=True),
            input_stream=answers,
            output_stream=prompts,
        )
    assert "default agent component (antigravity-agent)" in prompts.getvalue()
    assert report.required == ("node",)
    assert (report.ide, report.agents) == ("frontend-ide", ("antigravity-agent",))
    assert "antigravity-download" in report.answered
    manifest = read_toml(project / ".devcapsule" / "devcapsule.toml")
    assert manifest["capabilities"]["required"] == ["node"]


def test_interactive_default_agent_decline_keeps_the_need(tmp_path: Path) -> None:
    project = tmp_path / "interactive-project"
    project.mkdir()
    prompts = io.StringIO()
    # creator; need; default agent (no); four recommendations; base (Enter =
    # yes) — and no acquisition question follows.
    answers = io.StringIO("https://github.com/example\nnode\nfrontend-ide\nno\n\n\n\n\n\n")
    with patch.dict(os.environ, isolated_env(tmp_path), clear=False):
        report = initialize_project(
            InitializeRequest(directory=project, interactive=True),
            input_stream=answers,
            output_stream=prompts,
        )
    assert report.required == ("node",)
    assert report.agents == ()
    assert "antigravity-download" not in report.answered
    assert "antigravity" not in str(read_toml(project / ".devcapsule" / "devcapsule.toml"))


def test_default_agent_is_not_offered_where_it_cannot_resolve(tmp_path: Path) -> None:
    """Where the default agent has no validated combination with the surface,
    the question must not appear, and the init must not fail on the
    default's account."""

    project = tmp_path / "interactive-project"
    project.mkdir()
    prompts = io.StringIO()
    answers = io.StringIO("https://github.com/example\npython\npython-ide\n\n\n\n\n\n")
    with patch.dict(os.environ, isolated_env(tmp_path), clear=False), sparse_matrix():
        report = initialize_project(
            InitializeRequest(directory=project, interactive=True),
            input_stream=answers,
            output_stream=prompts,
        )
    assert "default agent" not in prompts.getvalue()
    assert report.required == ("python",)


def test_unknown_authorize_answer_is_reported_not_ignored(tmp_path: Path, capsys) -> None:
    project = tmp_path / "project"
    project.mkdir()
    with patch.dict(os.environ, isolated_env(tmp_path), clear=False):
        assert (
            cli.main(
                [
                    "project",
                    "--path",
                    str(project),
                    "init",
                    "--ide",
                    "python-ide",
                    "--creator",
                    "https://github.com/example",
                    "--authorize",
                    "base-image",
                    "default",
                    "--authorize",
                    "quantum-tunnel",
                    "open",
                ]
            )
            == 2
        )
    assert "not declared" in capsys.readouterr().err


def test_set_and_bind_extras_are_applied_through_the_registry(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    bound_home = tmp_path / "bound-home"
    bound_home.mkdir()
    manifest_extra = ProvidedAnswer("bind", "home", f"host-directory:{bound_home}")
    with patch.dict(os.environ, isolated_env(tmp_path), clear=False):
        initialize_project(
            InitializeRequest(
                directory=project,
                ide="python-ide",
                creator="https://github.com/example",
                answers=(
                    ProvidedAnswer("authorize", "base-image", "default"),
                    manifest_extra,
                ),
                interactive=False,
            )
        )
        config_root = tmp_path / "config" / "devcapsule" / "projects"
        record = read_toml(next(config_root.rglob("devcapsule.checkout.toml")))
        assert record["configuration"]["bindings"]["host-directory"]["home"] == str(
            bound_home
        )


def test_operation_batch_failure_is_an_elicitation_incomplete(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    with patch.dict(os.environ, isolated_env(tmp_path), clear=False):
        with pytest.raises(ElicitationIncomplete):
            initialize_project(
                InitializeRequest(
                    directory=project, ide="python-ide", interactive=False
                )
            )


def test_local_selection_offers_and_accepts_the_experiment_lever(tmp_path: Path, capsys) -> None:
    """The refusal's remedy must be reachable from the command that printed
    it (owner ruling 2026-09-06): the selection command takes --unverified too."""

    project = tmp_path / "fresh-project"
    project.mkdir()
    select = ["project", "--path", str(project), "config", "add", "antigravity-agent"]
    with patch.dict(os.environ, isolated_env(tmp_path), clear=False), sparse_matrix(), patch(
        "devcapsule.configuration.capability_commands.MATRICES",
        {Platform.LINUX_AMD64: matrix_without_antigravity_validation()},
    ):
        assert cli.main(full_init_command(project)) == 0
        capsys.readouterr()

        assert cli.main(select) == 2
        refusal = capsys.readouterr().err
        assert "Not yet validated: antigravity-cli 1.4.12 on base v0.3.0-local-linux-x86_64." in refusal
        assert "--unverified" in refusal
        manifest = read_toml(project / ".devcapsule" / "devcapsule.toml")
        assert manifest["capabilities"]["required"] == ["python"]

        assert cli.main([*select, "--unverified"]) == 0
        record = read_toml(next((tmp_path / "config").rglob("devcapsule.checkout.toml")))
        assert record["capabilities"]["selected"] == ["antigravity-agent", "python-ide"]
        assert "antigravity-cli" in record["capabilities"]["lock"]


def test_init_report_shows_recommendation_values_and_how_each_node_was_settled(
    tmp_path: Path, capsys
) -> None:
    project = tmp_path / "fresh-project"
    project.mkdir()
    with patch.dict(os.environ, isolated_env(tmp_path), clear=False):
        assert (
            cli.main(
                [
                    *full_init_command(project),
                    "--authorize",
                    "docker-daemon",
                    "host-socket",
                    "Peer capsules run the suite.",
                ]
            )
            == 0
        )
        output = capsys.readouterr().out
    # The value, not the justification, follows the equals sign.
    assert (
        "Recommended docker-daemon = host-socket for every checkout "
        "(Peer capsules run the suite.)." in output
    )
    assert "Answered for this checkout: base-image." in output
    assert "Project recommendations applied to this checkout: docker-daemon." in output
    assert "Standing from the existing checkout record" not in output


def test_undeclared_authorize_name_fails_before_any_prompt_or_write(tmp_path: Path) -> None:
    """Bug of 2026-09-26: the owner's first init answered every prompt, then lost them all.

    ``--authorize docker host`` names no node (``docker-daemon`` does). The
    name check used to run last, after the recommendation and consent
    prompts and after the manifest and lock were written; the checkout
    record holding every answer was never written. The check now precedes
    the first question: nothing is asked, nothing is on disk, and the
    message names the likely spelling.
    """
    project = tmp_path / "chessclub-website"
    project.mkdir()
    prompts = io.StringIO()
    unread = io.StringIO("")
    with patch.dict(os.environ, isolated_env(tmp_path), clear=False):
        with pytest.raises(ProjectConfigurationError) as failure:
            initialize_project(
                InitializeRequest(
                    directory=project,
                    require=("python",), ide="python-ide", agents=("antigravity-agent",),
                    creator="https://github.com/example",
                    answers=(
                        ProvidedAnswer("authorize", "base-image", "default"),
                        ProvidedAnswer("authorize", "network", "host"),
                        ProvidedAnswer("authorize", "docker", "host"),
                    ),
                    interactive=True,
                ),
                input_stream=unread,
                output_stream=prompts,
            )
    message = str(failure.value)
    assert "Configuration node 'docker' is not declared" in message
    assert "Did you mean 'docker-daemon'?" in message
    assert prompts.getvalue() == ""
    assert unread.tell() == 0
    assert not (project / ".devcapsule").exists()
    assert not list((tmp_path / "config").rglob("devcapsule.checkout.toml"))


def test_wrong_family_answer_fails_before_any_prompt_or_write(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    prompts = io.StringIO()
    with patch.dict(os.environ, isolated_env(tmp_path), clear=False):
        with pytest.raises(ProjectConfigurationError, match="answered with --authorize, not --set"):
            initialize_project(
                InitializeRequest(
                    directory=project,
                    require=("python",), ide="python-ide", agents=("antigravity-agent",),
                    creator="https://github.com/example",
                    answers=(ProvidedAnswer("set", "docker-daemon", "host-socket"),),
                    interactive=True,
                ),
                input_stream=io.StringIO(""),
                output_stream=prompts,
            )
    assert prompts.getvalue() == ""
    assert not (project / ".devcapsule").exists()


def test_curated_host_authorization_is_admitted_before_the_recommendation_exists(
    tmp_path: Path,
) -> None:
    """The curated network recommendation takes precedence over its home
    default, and the same invocation records consent to that recommendation."""
    project = tmp_path / "project"
    project.mkdir()
    with patch.dict(os.environ, isolated_env(tmp_path), clear=False):
        assert (
            cli.main(
                [
                    "project", "--path", str(project), "init",
                    "--ide", "python-ide", "--creator", "https://github.com/example",
                    "--authorize", "network", "host", "Host-bound development services.",
                    "--authorize", "base-image", "default",
                ]
            )
            == 0
        )
        manifest = read_toml(project / ".devcapsule" / "devcapsule.toml")
        assert manifest["host"]["network"]["mode"]["recommended"]["value"] == "host"
        record = read_toml(next((tmp_path / "config").rglob("devcapsule.checkout.toml")))
        assert record["authorization"]["network"]["value"] == "host"


@pytest.mark.parametrize("requirement", ["java>=21", "playwright>=1.21"])
def test_init_and_owner_command_share_requirement_grammar(tmp_path, monkeypatch, requirement):
    for key, value in isolated_env(tmp_path).items():
        monkeypatch.setenv(key, value)
    direct, edited = tmp_path / "direct", tmp_path / "edited"
    direct.mkdir()
    edited.mkdir()
    for root, flags in [(direct, ["--require", requirement]), (edited, [])]:
        assert cli.main(["project", "--path", str(root), "init", "--creator", "mailto:owner@example.test", *flags]) == 0
    assert cli.main(["project", "--path", str(edited), "config", "require", requirement]) == 0
    direct_manifest = read_toml(direct / ".devcapsule/devcapsule.toml")
    edited_manifest = read_toml(edited / ".devcapsule/devcapsule.toml")
    assert direct_manifest["capabilities"] == edited_manifest["capabilities"]
    assert direct_manifest["capabilities"]["required"] == [requirement]
    assert cli.main(["project", "--path", str(direct), "init"]) == 0
    assert read_toml(direct / ".devcapsule/devcapsule.toml")["capabilities"] == direct_manifest["capabilities"]


@pytest.mark.parametrize("flags", [
    ["--require", "python>=3.14"], ["--require", "java<25"],
    ["--require", "java>=21,<25"], ["--require", "java>=21,"],
    ["--require", "java python"], ["--offer", "java>=21"],
    ["--with", "no-such-capability"], ["--with", "frontend-ide"],
])
def test_init_refuses_invalid_capability_arguments_without_writes(tmp_path, monkeypatch, flags):
    for key, value in isolated_env(tmp_path).items():
        monkeypatch.setenv(key, value)
    root = tmp_path / "project"
    root.mkdir()
    assert cli.main(["project", "--path", str(root), "init", "--creator", "mailto:owner@example.test", *flags]) == 2
    assert not (root / ".devcapsule").exists()
    assert not list((tmp_path / "config").rglob("*.toml"))


@pytest.mark.parametrize("ide", [None, "java-ide"])
def test_init_with_repeats_and_keeps_additions_private(tmp_path, monkeypatch, ide):
    from devcapsule.configuration.capabilities import LocalCapabilities
    from devcapsule.configuration.storage import checkout_record_paths
    for key, value in isolated_env(tmp_path).items():
        monkeypatch.setenv(key, value)
    root = tmp_path / "project"
    root.mkdir()
    assert cli.main(["project", "--path", str(root), "init", "--creator", "mailto:owner@example.test",
                     "--require", "java>=21", "--with", "codex-agent", "--with", "browser-automation",
                     *(["--ide", ide, "--authorize", "base-image", "default"] if ide else [])]) == 0
    manifest = read_toml(root / ".devcapsule/devcapsule.toml")
    assert manifest["capabilities"] == {"required": ["java>=21"]}
    record, _ = checkout_record_paths(manifest, root)
    assert set(LocalCapabilities.read(read_toml(record)).selected) == ({"codex-agent", "browser-automation"} | ({ide} if ide else set()))
    lock = read_toml(root / f".devcapsule/devcapsule.{Platform.current()}.lock")
    assert "codex" not in lock["components"] and "playwright" not in lock["components"]
