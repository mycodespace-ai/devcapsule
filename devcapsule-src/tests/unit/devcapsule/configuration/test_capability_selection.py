"""Unit tests of ``devcapsule/configuration/capability_selection.py``: personal pins across capsule platforms.

The pins are built from the matrices' own tables; no file is read.
"""
from __future__ import annotations

from typing import Any

import pytest

from devcapsule.configuration.capability_selection import pins_for_platform
from devcapsule.configuration.file_formats import ProjectConfigurationError
from devcapsule.platforms import Platform
from devcapsule.resolution_matrix import MATRICES, ResolutionMatrix

AMD64 = MATRICES[Platform.LINUX_AMD64]
ARM64 = MATRICES[Platform.LINUX_ARM64]


def personal_pins(label: str, matrix: ResolutionMatrix) -> dict[str, Any]:
    """A checkout's pins of VSCodium as ``matrix`` embeds it, labelled ``label``."""
    return {"platform": label, "components": {"codium": dict(matrix.component_pins()["codium"]),
                                              "interactive-surface": "codium"}}


def test_pins_written_for_another_platform_take_this_platforms_artifacts() -> None:
    """A checkout's amd64 pins, on a project that runs as arm64, deliver arm64's table for the same
    version, relabelled; the input is unchanged."""
    amd64 = personal_pins("linux-amd64", AMD64)
    on_arm64 = pins_for_platform(amd64, ARM64)
    assert on_arm64 == personal_pins("linux-arm64", ARM64)
    assert amd64 == personal_pins("linux-amd64", AMD64)


def test_another_platforms_table_takes_this_platforms_artifacts_whatever_its_label() -> None:
    """A table that is another platform's embedded pin is that platform's, even under this platform's label."""
    mislabelled = personal_pins("linux-arm64", AMD64)
    assert pins_for_platform(mislabelled, ARM64)["components"]["codium"] == dict(ARM64.component_pins()["codium"])


def test_a_table_no_matrix_embeds_is_kept_as_written() -> None:
    """Pins written for the platform they run on, matching no embedded table, are a record, returned as they stand."""
    recorded = personal_pins("linux-amd64", AMD64)
    recorded["components"]["codium"]["note"] = "kept"
    assert pins_for_platform(recorded, AMD64) == recorded


def test_a_personal_version_the_other_platform_lacks_asks_for_a_new_choice() -> None:
    """A component version pinned for another platform, which this platform does not pin, is refused
    with the command that chooses again."""
    channel = {"platform": "linux-amd64", "components": {"codex": {"version": "9.9.9", "url": "https://example.test/x64.tgz"}}}
    with pytest.raises(ProjectConfigurationError, match="codex 9.9.9 is pinned for linux-amd64.*linux-arm64 has no pin.*config use"):
        pins_for_platform(channel, ARM64)
