"""Unit tests of ``tests/conftest.py``: the shared fixtures and the marker sets they key on."""
from __future__ import annotations

import tomllib
from pathlib import Path

from tests.conftest import DOCKER_MARKERS

_PYPROJECT = Path(__file__).resolve().parents[3] / "pyproject.toml"

NON_DOCKER_MARKERS = frozenset({"integration", "flaky", "legacy", "own_host_patches"})
"""The registered markers that never need Docker: process-boundary tests, visibility runs, legacy files,
and unit tests that set up their host themselves."""


def test_every_registered_marker_is_a_docker_marker_unless_it_is_a_known_non_docker_one() -> None:
    """Precondition: ``pyproject.toml`` registers the suite's markers. Action: read
    the registered names. Postcondition: ``DOCKER_MARKERS`` is exactly the registered
    set minus the four non-Docker markers, so a Docker suite cannot be registered
    without the isolation fixture learning that it keeps the developer's homes."""
    registered = {entry.split(":", 1)[0] for entry in tomllib.loads(_PYPROJECT.read_text())["tool"]["pytest"]["ini_options"]["markers"]}
    assert set(DOCKER_MARKERS) == registered - NON_DOCKER_MARKERS
