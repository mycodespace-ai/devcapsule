"""Unit tests of ``devcapsule/environment_realization.py``: obtaining the base and materializing a checkout's environment.

Docker, the materializer and the runtime choice are fakes.
"""
from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from devcapsule.environment_realization import ensure_local_image, realize_environment
from devcapsule.platforms import Platform
from devcapsule.runtime_command import RuntimeCommand
from tests.test_environment_realization import (
    BASE_REFERENCE,
    CANONICAL_IMAGE,
    base_image,
    completed_image,
    resolved_project,
)


@pytest.mark.parametrize("already_local", [True, False])
def test_ensure_local_image_pulls_only_when_missing(already_local: bool) -> None:
    """The base is pulled only when the local store lacks it, with no platform for a native daemon."""
    details = base_image()
    with (
        patch(
            "devcapsule.environment_realization.docker.image.exists",
            return_value=already_local,
        ),
        patch("devcapsule.environment_realization.docker.image.pull") as pull,
        patch(
            "devcapsule.environment_realization.required_local_image",
            return_value=details,
        ) as require,
    ):
        assert ensure_local_image(BASE_REFERENCE, Platform.LINUX_AMD64) == details

    if already_local:
        pull.assert_not_called()
    else:
        pull.assert_called_once_with(BASE_REFERENCE, platform=None)
    require.assert_called_once_with(BASE_REFERENCE)


@pytest.mark.parametrize("daemon,expected", [("arm64", "linux/amd64"), ("amd64", None)])
def test_a_daemon_of_another_architecture_pulls_the_lock_platform(daemon: str, expected: str | None) -> None:
    """A daemon of another architecture than the lock's platform is told the lock's platform when pulling."""
    # Docker Desktop on Apple Silicon is an arm64 daemon; a linux-amd64 lock's
    # base must not resolve to its arm64 variant.
    with (
        patch("devcapsule.environment_realization.daemon_architecture", return_value=daemon),
        patch("devcapsule.environment_realization.docker.image.exists", return_value=False),
        patch("devcapsule.environment_realization.docker.image.pull") as pull,
        patch("devcapsule.environment_realization.required_local_image", return_value=base_image()),
    ):
        ensure_local_image(BASE_REFERENCE, Platform.LINUX_AMD64)
    pull.assert_called_once_with(BASE_REFERENCE, platform=expected)


@pytest.mark.parametrize("command", [None, "devcapsule", "devcapsule0"])
def test_realizer_uses_resolved_shipped_command_choice(tmp_path, monkeypatch, command):
    """Realization delivers the runtime command the resolution chose, the standard one by default."""
    selected = resolved_project(tmp_path)
    if command is not None:
        selected.resolution["runtime"]["devcapsule-command"] = command
    materialize = Mock(return_value=(CANONICAL_IMAGE, True))
    monkeypatch.setattr("devcapsule.environment_realization.ensure_materialized_surface", materialize)
    monkeypatch.setattr("devcapsule.environment_realization.runtime_artifact", lambda _platform: tmp_path / "runtime.pex")
    realize_environment(selected, root=tmp_path / "cache", obtain_image=lambda _ref: base_image(),
                        require_image=lambda _ref: completed_image(), build=Mock(), inspect_image=Mock())
    assert materialize.call_args.kwargs["runtime_command"] is RuntimeCommand(command or "devcapsule")
