"""Unit tests of ``devcapsule/resolution_matrix.py``: the linux-arm64 matrix beside the linux-amd64 one.

The matrices are the launcher's embedded data; each test asks one of them one question.
"""
from __future__ import annotations

import pytest

from devcapsule.components.linux_arm64_pins import COMPONENT_LOCK_TABLES
from devcapsule.platforms import Platform
from devcapsule.resolution_matrix import MATRICES

AMD64 = MATRICES[Platform.LINUX_AMD64]
ARM64 = MATRICES[Platform.LINUX_ARM64]


def test_the_arm64_matrix_serves_each_arm64_pin_at_its_version() -> None:
    """The arm64 matrix's pin for each component version is that version's arm64 table."""
    assert all(ARM64.component_pin(component, version) == table
               for (component, version), table in COMPONENT_LOCK_TABLES.items())


def test_the_arm64_base_is_its_own_recipe_11_pin() -> None:
    """The arm64 matrix pins one recipe-11 base of DevCapsule's repository, not an amd64 one."""
    (base,) = ARM64.base_images()
    assert base.contract.recipe == 11
    assert base.reference.startswith("docker.io/mycodespaceai/devcapsule-base@sha256:")
    assert base.reference not in {image.reference for image in AMD64.base_images()}


@pytest.mark.parametrize("ide", ["frontend-ide", "vscode-ide", "eclipse-ide", "python-ide", "java-ide"])
def test_each_ide_smoked_natively_on_arm64_resolves_verified(ide: str) -> None:
    """An IDE with a native arm64 smoke resolves on the arm64 matrix without an unverified combination."""
    assert ARM64.resolve([ide]).unverified == ()
