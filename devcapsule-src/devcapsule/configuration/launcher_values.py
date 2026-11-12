"""The launcher-owned values, memory and CPUs: their precedence and their runtime effects.

Answer 6 of the CLI UX redesign work order: the launcher owns the
container's memory limit and CPU count on every project. Neither needs a
declaration. The precedence is the checkout's answer, then the project's
recommendation, then the home default, then nothing. A manifest that
declares a value with the ``docker.memory-limit`` effect, as manifests did
before 0.3.0 rc4, is read here as a recommendation for ``memory`` and that
name as an alias, so recorded answers keep working.
"""

from __future__ import annotations

from typing import Any, Mapping

from .file_formats import ConfigurationScalar, ProjectConfigurationError
from .manifest_document import Recommendations
from .values import (
    LAUNCHER_VALUE_NAMES,
    RuntimeEffects,
    configuration_value_declarations,
    checkout_omitted_values,
    legacy_memory_names,
    memory_size_bytes,
    normalize_launcher_value,
)
from .home import HomeDefaults

__all__ = ["launcher_value_source", "launcher_value_sources", "resolve_launcher_values"]


def launcher_value_sources(
    manifest: Mapping[str, Any], checkout: Mapping[str, Any], home: Mapping[str, Any] | None = None,
) -> dict[str, tuple[str | int | None, str]]:
    """Both launcher values and their sources; invalid answers raise."""
    return {name: launcher_value_source(name, manifest, checkout, home) for name in LAUNCHER_VALUE_NAMES}


def launcher_value_source(
    name: str, manifest: Mapping[str, Any], checkout: Mapping[str, Any], home: Mapping[str, Any] | None = None,
) -> tuple[str | int | None, str]:
    """One resource's value and source, independently of errors in the other.

    Precedence: checkout answer, project recommendation, home default,
    then no limit. Legacy memory declarations retain requiredness and explicit
    omissions; a reset clears the omission and follows defaults again.
    """
    if name not in LAUNCHER_VALUE_NAMES:
        raise ProjectConfigurationError(f"Unknown launcher value {name!r}.")
    configuration = checkout.get("configuration", {})
    if not isinstance(configuration, dict):
        raise ProjectConfigurationError("Checkout configuration must be a table.")
    raw_values = configuration.get("values", {})
    if not isinstance(raw_values, dict):
        raise ProjectConfigurationError("Checkout configuration.values must be a table.")
    recommendations = Recommendations.read(manifest)
    declarations = configuration_value_declarations(manifest)
    defaults = HomeDefaults.read(home or {}).values
    aliases = legacy_memory_names(manifest)
    omitted = set(checkout_omitted_values(checkout))
    related = {name, *(aliases if name == "memory" else ())}
    if related & omitted:
        if related & set(raw_values):
            raise ProjectConfigurationError(f"{name} is both recorded and omitted; set {name} again.")
        if any(declarations.get(alias, {}).get("required", False) for alias in related):
            raise ProjectConfigurationError(f"Required value {name} cannot be omitted; config set {name} VALUE.")
        return (None, "checkout (omitted)")
    recorded: object = raw_values.get(name)
    if recorded is None and name == "memory":
        for alias in aliases:
            if alias in raw_values:
                recorded = raw_values[alias]
                break
    if recorded is not None:
        return (normalize_launcher_value(name, recorded, field_name=f"checkout value {name}"), "checkout")
    recommended: object = recommendations.value(name)
    if recommended is None and name == "memory":
        for alias in aliases:
            if "recommended" in declarations[alias]:
                recommended = declarations[alias]["recommended"]
                break
    if recommended is not None:
        return (normalize_launcher_value(name, recommended, field_name=f"recommended {name}"), "project recommendation")
    if name in defaults:
        return (defaults[name], "home default")
    if name == "memory" and any(declarations[alias].get("required", False) for alias in aliases):
        raise ProjectConfigurationError("Required value memory is missing; config set memory SIZE.")
    return (None, "none")


def resolve_launcher_values(
    manifest: Mapping[str, Any], checkout: Mapping[str, Any], home: Mapping[str, Any] | None = None,
) -> tuple[dict[str, ConfigurationScalar], RuntimeEffects]:
    """The effective launcher values and their effects, ``memory-limit-bytes`` and ``cpus``."""
    values: dict[str, ConfigurationScalar] = {}
    effects: RuntimeEffects = {}
    for name, (value, _source) in launcher_value_sources(manifest, checkout, home).items():
        if value is None:
            continue
        values[name] = value
        if name == "memory":
            effects["memory-limit-bytes"] = memory_size_bytes(str(value))
        else:
            effects["cpus"] = int(value)
    return values, effects
