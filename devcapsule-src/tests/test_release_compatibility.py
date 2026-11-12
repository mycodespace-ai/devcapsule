"""R-COMPAT-001: a newer client requires no user action for older artifacts.

The fixtures under ``tests/resources/compat`` were produced by earlier
released clients and are versioned inputs — see their README. These tests run
the current client against them and require ordinary commands to succeed with
no user action, which is exactly the property a release must not break.
"""

from __future__ import annotations

from tests.launch_preparation import run_until_prepared

import os
from pathlib import Path
import shutil
import tomllib
from unittest.mock import patch

from devcapsule import cli
from devcapsule.configuration.file_formats import (
    canonical_digest,
)
import pytest

pytestmark = pytest.mark.legacy


FIXTURES = Path(__file__).parent / "resources" / "compat"
# The released client's own path encoding for the fixture project identity;
# stored literally so a change in record placement or encoding fails here.
V0262_RECORD_DIRECTORY = "mailto%3Acompat-fixture%40example.test/project"


def materialize_v0262(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    """Place the stored v026.2 artifacts as a real checkout on this machine.

    Only the two documented machine-specific values are substituted; all
    stored project-side content and digests are used verbatim.
    """

    project = tmp_path / "project"
    shutil.copytree(FIXTURES / "v026.2" / "project", project)
    config_home = tmp_path / "config"
    record_directory = config_home / "devcapsule" / "projects" / V0262_RECORD_DIRECTORY
    record_directory.mkdir(parents=True)

    checkout_text = (FIXTURES / "v026.2" / "checkout" / "devcapsule.checkout.toml").read_text(
        encoding="utf-8"
    ).replace("@CHECKOUT_PATH@", str(project))
    (record_directory / "devcapsule.checkout.toml").write_text(checkout_text, encoding="utf-8")

    checkout_input_digest = canonical_digest(tomllib.loads(checkout_text))
    resolved_text = (FIXTURES / "v026.2" / "checkout" / "devcapsule.resolved.toml").read_text(
        encoding="utf-8"
    ).replace("@CHECKOUT_INPUT_DIGEST@", checkout_input_digest)
    (record_directory / "devcapsule.resolved.toml").write_text(resolved_text, encoding="utf-8")

    env = {"HOME": str(tmp_path / "home"), "XDG_CONFIG_HOME": str(config_home)}
    return project, env


def test_v0262_checkout_resumes_with_no_user_action(tmp_path: Path, capsys, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    project, env = materialize_v0262(tmp_path)
    with patch.dict(os.environ, env, clear=False):
        assert cli.main(["project", "--path", str(project), "config", "show"]) == 0
        output = capsys.readouterr().out
        assert "Nothing is pending." in output

        assert cli.main(["project", "list"]) == 0
        assert "ready" in capsys.readouterr().out

        # Re-resolving is ordinary work and must not prompt or demand anything.
        assert run_until_prepared(project) == 0


def test_v0262_manifest_edit_never_blocks_inspection(tmp_path: Path, capsys) -> None:
    project, env = materialize_v0262(tmp_path)
    manifest = project / ".devcapsule" / "devcapsule.toml"
    manifest.write_text(
        manifest.read_text(encoding="utf-8") + '\nworkflow-type = "single-stream"\n',
        encoding="utf-8",
    )
    with patch.dict(os.environ, env, clear=False):
        assert cli.main(["project", "--path", str(project), "config", "show"]) == 0
        assert "Nothing is pending." in capsys.readouterr().out
        assert run_until_prepared(project) == 0
        assert cli.main(["project", "--path", str(project), "config", "show"]) == 0
        assert "Nothing is pending." in capsys.readouterr().out


def test_v026_formation_artifacts_are_inspectable_despite_manifest_digest(
    tmp_path: Path, capsys
) -> None:
    # The v026-era adopter shape carries the retired whole-manifest digest that
    # once gated every command; inspection must work, before and after drift.
    project = tmp_path / "project"
    shutil.copytree(FIXTURES / "v026-formation" / "project", project)
    env = {"HOME": str(tmp_path / "home"), "XDG_CONFIG_HOME": str(tmp_path / "config")}
    with patch.dict(os.environ, env, clear=False):
        assert cli.main(["project", "--path", str(project), "config", "show"]) == 0
        listing = capsys.readouterr().out
        assert "base-image" in listing
        assert "project lock" not in listing

        manifest = project / ".devcapsule" / "devcapsule.toml"
        manifest.write_text(
            manifest.read_text(encoding="utf-8") + "\n[compat-test-extra]\nnote = 1\n",
            encoding="utf-8",
        )
        assert cli.main(["project", "--path", str(project), "config", "show"]) == 0
