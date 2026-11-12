"""Trusted component catalog selection for the current V1 lock format."""

from __future__ import annotations

from typing import Any, Mapping

from devcapsule.components import ComponentDefinition
from devcapsule.components.antigravity_cli import DEFINITION as ANTIGRAVITY_CLI
from devcapsule.components.claude_code import DEFINITION as CLAUDE_CODE
from devcapsule.components.codex import DEFINITION as CODEX
from devcapsule.components.codium import DEFINITION as CODIUM
from devcapsule.components.dotnet_sdk import DEFINITION as DOTNET_SDK
from devcapsule.components.rider import DEFINITION as RIDER
from devcapsule.components.intellij import DEFINITION as INTELLIJ
from devcapsule.components.eclipse import DEFINITION as ECLIPSE
from devcapsule.components.playwright import DEFINITION as PLAYWRIGHT
from devcapsule.components.postgresql_client import DEFINITION as POSTGRESQL_CLIENT
from devcapsule.components.pycharm import DEFINITION as PYCHARM
from devcapsule.components.vscode import DEFINITION as VSCODE
from devcapsule.container_runtime.contract import ComponentRuntimeTemplate


class ComponentCatalogError(ValueError):
    """The lock selects unsupported or malformed component metadata."""


# Components a lock may name as its one interactive-surface. Every other
# catalog component is ancillary; a definition never appears in both roles.
INTERACTIVE_SURFACES: dict[str, ComponentDefinition] = {
    ECLIPSE.id: ECLIPSE,
    PYCHARM.id: PYCHARM,
    CODIUM.id: CODIUM,
    VSCODE.id: VSCODE,
    INTELLIJ.id: INTELLIJ,
    RIDER.id: RIDER,
}

COMPONENTS: dict[str, ComponentDefinition] = {
    ECLIPSE.id: ECLIPSE,
    PYCHARM.id: PYCHARM,
    CODIUM.id: CODIUM,
    VSCODE.id: VSCODE,
    INTELLIJ.id: INTELLIJ,
    RIDER.id: RIDER,
    CODEX.id: CODEX,
    CLAUDE_CODE.id: CLAUDE_CODE,
    ANTIGRAVITY_CLI.id: ANTIGRAVITY_CLI,
    POSTGRESQL_CLIENT.id: POSTGRESQL_CLIENT,
    PLAYWRIGHT.id: PLAYWRIGHT,
    DOTNET_SDK.id: DOTNET_SDK,
}


def selected_component_definitions(
    lock: Mapping[str, Any],
) -> tuple[ComponentDefinition, tuple[ComponentDefinition, ...]]:
    components = lock.get("components")
    if not isinstance(components, dict):
        raise ComponentCatalogError("platform lock components must be a table")
    interactive_id = components.get("interactive-surface")
    interactive = (
        INTERACTIVE_SURFACES.get(interactive_id) if isinstance(interactive_id, str) else None
    )
    if interactive is None:
        raise ComponentCatalogError(
            f"no V1 runtime template is available for interactive component {interactive_id!r}"
        )
    ancillary: list[ComponentDefinition] = []
    for component_id, metadata in components.items():
        if component_id in {"interactive-surface", interactive_id}:
            continue
        if component_id in INTERACTIVE_SURFACES:
            raise ComponentCatalogError(
                f"component {component_id!r} is an interactive surface and cannot "
                f"accompany the selected surface {interactive_id!r}"
            )
        definition = COMPONENTS.get(component_id)
        if definition is None:
            raise ComponentCatalogError(
                f"no V1 runtime template is available for component {component_id!r}"
            )
        if not isinstance(metadata, dict):
            raise ComponentCatalogError(f"components.{component_id} must be a table")
        ancillary.append(definition)
    for definition in (interactive, *ancillary):
        for required in definition.required_components():
            if required not in components:
                raise ComponentCatalogError(f"component {definition.id!r} requires {required!r} in the lock")
    return interactive, tuple(ancillary)


def selected_runtime_templates(
    lock: Mapping[str, Any],
) -> tuple[ComponentRuntimeTemplate, tuple[ComponentRuntimeTemplate, ...]]:
    interactive, ancillary = selected_component_definitions(lock)
    return interactive.runtime_template(), tuple(
        component.runtime_template() for component in ancillary
    )
