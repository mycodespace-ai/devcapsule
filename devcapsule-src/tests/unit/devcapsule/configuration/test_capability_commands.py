"""Unit tests of ``devcapsule/configuration/capability_commands.py``: the offline check of a project's shared documents.

``check_documents`` is the work of ``project config check``. It takes a
project's manifest and one platform lock, as documents, and refuses the pair
that this launcher cannot launch. A launcher must go on accepting the
projects that earlier launchers wrote. So these tests give it such projects,
kept under ``tests/resources/compat`` as their writers left them, and then
the same documents with one thing changed in memory.

No test reads this repository's own ``.devcapsule`` directory. What a
developer's launcher has written there is not an input of a test.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import tomllib
from typing import Any

import pytest

from devcapsule.compat import CliError
from devcapsule.configuration.capability_commands import check_documents
from devcapsule.configuration.file_formats import ProjectConfigurationError

CAPTURES = Path(__file__).resolve().parents[3] / "resources" / "compat"
"""Projects written by earlier launchers. ``README.md`` there says which launcher wrote each, and when."""

THIS_REPOSITORY = "repository-2026-10-25"
"""DevCapsule's own project as committed on that day: a schema-1 manifest and a lock that pins PyCharm and three agents."""


def captured(name: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """The manifest and the ``linux-amd64`` lock of the captured project ``name``, as documents."""
    directory = CAPTURES / name / "project" / ".devcapsule"
    return (tomllib.loads((directory / "devcapsule.toml").read_text(encoding="utf-8")),
            tomllib.loads((directory / "devcapsule.linux-amd64.lock").read_text(encoding="utf-8")))


@pytest.mark.parametrize("name", ["v026.2", "v0.2.11", THIS_REPOSITORY])
def test_a_project_an_earlier_launcher_wrote_passes_the_check(name: str) -> None:
    """The manifest and the lock that an earlier launcher wrote pass this launcher's check with no warning, and
    the check leaves both documents as it was given them."""
    manifest, lock = captured(name)
    before = deepcopy((manifest, lock))

    assert check_documents(manifest, lock) == ()

    assert (manifest, lock) == before


def test_a_locked_component_that_nothing_needs_and_this_launcher_does_not_know_is_passed_over() -> None:
    """A lock may carry a component of a newer launcher. When no capability of the project needs it, the check
    passes with no warning although this launcher cannot install that component."""
    manifest, lock = captured(THIS_REPOSITORY)
    lock["components"]["fortran-compiler"] = {"version": "1"}

    assert check_documents(manifest, lock) == ()


def test_a_needed_capability_that_this_launcher_does_not_know_is_refused_by_name() -> None:
    """A manifest that needs a capability this launcher has never had is refused. The refusal names the
    capability and says that this launcher does not support it."""
    manifest, lock = captured(THIS_REPOSITORY)
    manifest["capabilities"]["need"].append("fortran")

    with pytest.raises(ProjectConfigurationError, match="Required capability 'fortran' is unavailable: this launcher does not support it"):
        check_documents(manifest, lock)


def test_a_runtime_effect_that_this_launcher_does_not_know_is_refused_as_a_newer_launchers() -> None:
    """A configuration value whose ``runtime-effect`` this launcher does not know is refused. The refusal names
    the value and the effect, and says that the project may require a newer DevCapsule."""
    manifest, lock = captured(THIS_REPOSITORY)
    manifest["configuration"]["values"]["runtime.memory-limit"]["runtime-effect"] = "docker.cpu-limit"

    with pytest.raises(ProjectConfigurationError) as refused:
        check_documents(manifest, lock)

    message = str(refused.value)
    assert "configuration.values.runtime.memory-limit.runtime-effect 'docker.cpu-limit' is not supported" in message
    assert "The project may require a newer DevCapsule." in message


def test_a_locked_component_that_the_launch_installs_is_read_and_a_missing_version_refused() -> None:
    """The check reads every locked component that the launch would install: a lock whose Codex component has
    an empty version is refused, and the refusal names ``components.codex.version``."""
    manifest, lock = captured(THIS_REPOSITORY)
    lock["components"]["codex"]["version"] = ""

    with pytest.raises(CliError, match="components\\.codex\\.version must be a non-empty string"):
        check_documents(manifest, lock)
