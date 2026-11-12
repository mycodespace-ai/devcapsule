"""Declared directory and secret-source bindings and their validation."""

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
from devcapsule.components.catalog import ComponentCatalogError, selected_component_definitions, selected_runtime_templates

from .file_formats import ProjectConfigurationError
from devcapsule.project import project_namespace
from devcapsule.platforms import XdgHomes


@dataclass(frozen=True)
class ConfigurationBindingDeclaration:
    name: str
    container_path: str
    sensitivity: str
    concurrent: bool
    description: str
    kind: str
    component_id: str | None = None
    slot_name: str | None = None


@dataclass(frozen=True)
class SecretInputMetadata:
    name: str
    environment_variable: str
    required: bool
    description: str
    exposure: str


def managed_binding_path(root: Path, declaration: ConfigurationBindingDeclaration,
                         env: Mapping[str, str] | None = None) -> Path:
    """Default storage location, without creating directories or reading secrets."""
    homes = XdgHomes.from_environment(env)
    roots = {"durable": homes.data, "state": homes.state, "cache": homes.cache}
    namespace = roots[declaration.kind] / "projects" / "by-path" / project_namespace(root)
    if declaration.name == "home":
        return namespace / "home"
    return namespace / "components" / str(declaration.component_id) / str(declaration.slot_name)


def configuration_binding_declarations(
    lock: Mapping[str, Any], *, source: str = "platform lock"
) -> dict[str, ConfigurationBindingDeclaration]:
    """Return logical host-directory targets from the locked component metadata."""

    components = lock.get("components")
    if not isinstance(components, dict):
        raise ProjectConfigurationError(f"{source} components must be a table.")
    try:
        interactive, ancillary = selected_runtime_templates(lock)
    except ComponentCatalogError as exc:
        raise ProjectConfigurationError(str(exc)) from exc
    declarations = {
        "home": ConfigurationBindingDeclaration(
            name="home",
            container_path="/home/devcapsule",
            sensitivity="credentials",
            concurrent=False,
            description="Persistent container home, including developer and tool state.",
            kind="durable",
        )
    }
    for template in (interactive, *ancillary):
        declarations.update(
            {
            template.logical_slot_name(slot.name): ConfigurationBindingDeclaration(
                name=template.logical_slot_name(slot.name),
                container_path=slot.container_path,
                sensitivity=slot.sensitivity,
                concurrent=slot.concurrent,
                description=slot.deletion_effect,
                kind=slot.kind,
                component_id=template.component.id,
                slot_name=slot.name,
            )
            for slot in template.persistence.state_slots
            }
        )
    return declarations


def component_secret_inputs(
    lock: Mapping[str, Any], *, source: str = "platform lock"
) -> dict[str, SecretInputMetadata]:
    """Return optional/required secret inputs declared by selected components."""

    try:
        interactive, ancillary = selected_component_definitions(lock)
    except ComponentCatalogError as exc:
        raise ProjectConfigurationError(f"{source}: {exc}") from exc
    result: dict[str, SecretInputMetadata] = {}
    for component in (interactive, *ancillary):
        for declaration in component.secret_inputs():
            logical_name = f"{component.id}/{declaration.name}"
            result[logical_name] = SecretInputMetadata(
                name=logical_name,
                environment_variable=declaration.environment_variable,
                required=declaration.required,
                description=declaration.description,
                exposure=declaration.exposure,
            )
    return result


def resolve_secret_bindings(
    lock: Mapping[str, Any], checkout: Mapping[str, Any]
) -> dict[str, str]:
    """Resolve secret source names without reading or serializing secret values."""

    declarations = component_secret_inputs(lock)
    configuration = checkout.get("configuration", {})
    if not isinstance(configuration, dict):
        raise ProjectConfigurationError("Checkout configuration must be a table.")
    bindings = configuration.get("bindings", {})
    if not isinstance(bindings, dict):
        raise ProjectConfigurationError("Checkout configuration.bindings must be a table.")
    raw = bindings.get("host-environment", {})
    if not isinstance(raw, dict):
        raise ProjectConfigurationError(
            "Checkout configuration.bindings.host-environment must be a table."
        )
    resolved: dict[str, str] = {}
    problems: list[str] = []
    for name in sorted(set(raw) | set(declarations)):
        declaration = declarations.get(name)
        if declaration is None:
            problems.append(f"Secret input {name!r} is not declared by the selected components.")
        elif name not in raw:
            if declaration.required:
                problems.append(f"Required secret binding {name!r} is missing: project config bind "
                                f"{name} host-environment:{declaration.environment_variable}.")
        elif raw[name] != declaration.environment_variable:
            problems.append(f"Secret input {name!r} must bind its declared host environment variable "
                            f"{declaration.environment_variable!r}.")
        else:
            resolved[name] = raw[name]
    if problems:
        raise ProjectConfigurationError("\n".join(problems))
    return resolved


def resolve_configuration_bindings(
    lock: Mapping[str, Any], checkout: Mapping[str, Any]
) -> dict[str, str]:
    declarations = configuration_binding_declarations(lock)
    configuration = checkout.get("configuration", {})
    if not isinstance(configuration, dict):
        raise ProjectConfigurationError("Checkout configuration must be a table.")
    bindings = configuration.get("bindings", {})
    if not isinstance(bindings, dict):
        raise ProjectConfigurationError("Checkout configuration.bindings must be a table.")
    host_directories = bindings.get("host-directory", {})
    if not isinstance(host_directories, dict):
        raise ProjectConfigurationError(
            "Checkout configuration.bindings.host-directory must be a table."
        )

    resolved: dict[str, str] = {}
    problems: list[str] = []
    for name, raw_source in host_directories.items():
        if not isinstance(name, str) or name not in declarations:
            problems.append(f"Configuration binding {name!r} is not declared by the selected component; "
                            f"declared bindings: {', '.join(sorted(declarations))}.")
        elif not isinstance(raw_source, str) or not raw_source or "\x00" in raw_source:
            problems.append(f"Host-directory binding {name!r} must contain a filesystem path string.")
        else:
            source = Path(raw_source).expanduser().resolve()
            if not source.is_dir():
                problems.append(f"Host-directory binding {name!r} is not an existing directory: {source}")
            else:
                resolved[name] = str(source)
    if problems:
        raise ProjectConfigurationError("\n".join(problems))
    return resolved
