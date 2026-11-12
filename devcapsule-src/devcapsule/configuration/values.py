"""Ordinary value declarations, domains, omissions and runtime effects."""

from __future__ import annotations
import re
from typing import Any, Mapping

from devcapsule.build_info import BuildInfoError, current_build_info
from devcapsule.runtime_command import RuntimeCommand

from .file_formats import ConfigurationScalar, ProjectConfigurationError


CONFIGURATION_VALUE_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:[.-][a-z0-9]+)*$")


MEMORY_SIZE_PATTERN = re.compile(r"^([1-9][0-9]*)(B|KiB|MiB|GiB|TiB)$")

# What a user types for a memory size: the canonical form above, or Docker's
# spellings (``6g``, ``6G``, ``512m``, ``6GB``), which the owner and every
# ``docker run`` user know. Stored values are always canonical.
MEMORY_SIZE_INPUT_PATTERN = re.compile(r"^([1-9][0-9]*)\s*([KkMmGgTt])?(?:[Ii]?[Bb])?$")


CONFIGURATION_VALUE_TYPES = {"string", "integer", "boolean", "memory-size"}


RUNTIME_EFFECT_TYPES = {"docker.memory-limit": "memory-size", "devcapsule.command-name": "string"}

# The shipped-command value is recognized by its name, not only by its
# ``runtime-effect`` attribute. Released clients validate the attribute by
# exact membership in their own vocabulary, so a manifest that spells an
# effect they predate is unreadable to them; v0.2.12 rejects this
# repository's manifest that way (bug 2026-09-24, released launchers reject
# the repository manifest). A declaration that omits the attribute is an
# ordinary string value to those clients and carries the effect here.
SHIPPED_COMMAND_VALUE_NAME = "runtime.devcapsule-command"
SHIPPED_COMMAND_EFFECT = "devcapsule.command-name"

RuntimeEffects = dict[str, int | str]

# The values the launcher owns on every project (CLI UX redesign work order,
# answer 6): the container's memory limit and CPU count. They need no
# declaration; a project may recommend them, a home has defaults for
# them, a checkout may set them. ``memory`` carries the ``docker.memory-limit``
# effect that a manifest's declared value used to carry under its own name;
# such a declaration is read as the recommendation for ``memory`` and its
# name as an alias, so recorded answers keep working.
LAUNCHER_VALUE_NAMES = ("memory", "cpus")
LAUNCHER_VALUE_DESCRIPTIONS = {
    "memory": "Hard memory limit of the capsule's container, such as 6GiB or 6g.",
    "cpus": "Number of CPUs the capsule's container may use.",
}
MEMORY_LIMIT_EFFECT = "docker.memory-limit"


def configuration_value_declarations(
    manifest: Mapping[str, Any], *, source: str = "project declaration"
) -> dict[str, Mapping[str, Any]]:
    """Return and validate ordinary configuration-value metadata."""

    configuration = manifest.get("configuration")
    if configuration is None:
        return {}
    if not isinstance(configuration, dict):
        raise ProjectConfigurationError(f"{source} configuration must be a table.")
    values = configuration.get("values", {})
    if not isinstance(values, dict):
        raise ProjectConfigurationError(f"{source} configuration.values must be a table.")

    declarations: dict[str, Mapping[str, Any]] = {}
    for name, declaration in values.items():
        field = f"{source} configuration.values.{name}"
        if not isinstance(name, str) or CONFIGURATION_VALUE_NAME_PATTERN.fullmatch(name) is None:
            raise ProjectConfigurationError(
                f"{source} configuration value names must be lowercase dotted or hyphenated identifiers; "
                f"found {name!r}."
            )
        if not isinstance(declaration, dict):
            raise ProjectConfigurationError(f"{field} must be a table.")
        value_type = declaration.get("type")
        if not isinstance(value_type, str) or value_type not in CONFIGURATION_VALUE_TYPES:
            choices = ", ".join(sorted(CONFIGURATION_VALUE_TYPES))
            raise ProjectConfigurationError(f"{field}.type must be one of: {choices}.")
        required = declaration.get("required", False)
        if not isinstance(required, bool):
            raise ProjectConfigurationError(f"{field}.required must be a boolean when present.")
        description = declaration.get("description")
        if description is not None and not isinstance(description, str):
            raise ProjectConfigurationError(f"{field}.description must be a string when present.")
        effect = declaration.get("runtime-effect")
        if name == SHIPPED_COMMAND_VALUE_NAME:
            if effect is None:
                declaration = {**declaration, "runtime-effect": SHIPPED_COMMAND_EFFECT}
                effect = SHIPPED_COMMAND_EFFECT
            elif effect != SHIPPED_COMMAND_EFFECT:
                raise ProjectConfigurationError(
                    f"{field} is reserved for runtime effect {SHIPPED_COMMAND_EFFECT!r}; "
                    f"found runtime-effect {effect!r}."
                )
        if effect is not None:
            expected_type = RUNTIME_EFFECT_TYPES.get(effect) if isinstance(effect, str) else None
            if expected_type is None:
                choices = ", ".join(sorted(RUNTIME_EFFECT_TYPES))
                raise ProjectConfigurationError(
                    f"{field}.runtime-effect {effect!r} is not supported by DevCapsule "
                    f"{_running_version()}; supported: {choices}. The project may require "
                    "a newer DevCapsule."
                )
            if value_type != expected_type:
                raise ProjectConfigurationError(
                    f"{field}.runtime-effect {effect!r} requires type {expected_type!r}."
                )
        if "recommended" in declaration:
            _normalize_declared_value(declaration, name, declaration["recommended"])
        declarations[name] = declaration
    return declarations


def _running_version() -> str:
    """The version to name in a diagnostic about this executable's limits.

    Build information is derived rather than authored for source-form runs
    and is validated for built ones; a malformed record is someone else's
    error to raise, so a diagnostic about a manifest never fails on it.
    """
    try:
        return current_build_info().version
    except BuildInfoError:
        return "(unknown version)"


def normalize_configuration_value(
    manifest: Mapping[str, Any], name: str, value: object
) -> ConfigurationScalar:
    declarations = configuration_value_declarations(manifest)
    declaration = declarations.get(name)
    if declaration is None:
        available = ", ".join(sorted(declarations)) or "none"
        raise ProjectConfigurationError(
            f"Configuration value {name!r} is not declared by this project; declared values: {available}."
        )
    if isinstance(value, str) and value.strip().lower() == "default":
        if "recommended" not in declaration:
            raise ProjectConfigurationError(
                f"Configuration value {name!r} declares no default for 'default' to "
                "resolve to; set an explicit value, or use 'unset' to leave the value absent."
            )
        value = declaration["recommended"]
    return _normalize_declared_value(declaration, name, value)


def _normalize_declared_value(
    declaration: Mapping[str, Any], name: str, value: object,
) -> ConfigurationScalar:
    """Validate literal answers and recommendations against the same domain."""
    if isinstance(value, str) and value.strip().lower() == "default":
        raise ProjectConfigurationError(f"Configuration value {name!r} recommendation must be a literal value.")
    if isinstance(value, str) and value.strip().lower() == "none":
        # Reserved alongside 'default' (owner ruling 2026-09-03): the
        # explicit-absence answer is recorded by the carriers as an omission,
        # never stored as a literal — a "none" reaching normalization is a
        # carrier that failed to intercept it.
        raise ProjectConfigurationError(
            f"Configuration value {name!r} cannot hold the reserved literal 'none'; "
            "the 'none' answer records an explicit omission."
        )
    value_type = str(declaration["type"])
    field = f"configuration value {name!r}"
    if value_type == "string":
        if not isinstance(value, str) or not value or "\x00" in value:
            raise ProjectConfigurationError(f"{field} must be a non-empty string.")
        if declaration.get("runtime-effect") == "devcapsule.command-name":
            try:
                return RuntimeCommand(value)
            except ValueError as exc:
                raise ProjectConfigurationError(f"{field}: {exc}") from exc
        return value
    if value_type == "integer":
        if isinstance(value, bool):
            raise ProjectConfigurationError(f"{field} must be an integer.")
        if isinstance(value, int):
            return value
        if isinstance(value, str) and re.fullmatch(r"-?[0-9]+", value):
            return int(value)
        raise ProjectConfigurationError(f"{field} must be an integer.")
    if value_type == "boolean":
        if isinstance(value, bool):
            return value
        if isinstance(value, str) and value.lower() in {"true", "false"}:
            return value.lower() == "true"
        raise ProjectConfigurationError(f"{field} must be true or false.")
    return normalize_memory_size(value, field_name=field)


def checkout_omitted_values(checkout: Mapping[str, Any]) -> tuple[str, ...]:
    """The names a checkout explicitly keeps absent from the runtime config."""

    configuration = checkout.get("configuration", {})
    if not isinstance(configuration, dict):
        raise ProjectConfigurationError("Checkout configuration must be a table.")
    omitted = configuration.get("omitted-values", [])
    if not isinstance(omitted, list) or not all(isinstance(name, str) for name in omitted):
        raise ProjectConfigurationError(
            "Checkout configuration omitted-values must be an array of node names."
        )
    return tuple(sorted(set(omitted)))


def resolve_configuration_values(
    manifest: Mapping[str, Any], checkout: Mapping[str, Any]
) -> tuple[dict[str, ConfigurationScalar], RuntimeEffects]:
    """Validate the checkout's declared values and derive their runtime effects.

    The launcher-owned ``memory`` and ``cpus`` are not declared values; they
    are resolved by :mod:`launcher_values` and merged by the review. A
    declared value carrying the memory-limit effect is an alias of ``memory``
    and is left to that module too.
    """

    declarations = configuration_value_declarations(manifest)
    configuration = checkout.get("configuration", {})
    if not isinstance(configuration, dict):
        raise ProjectConfigurationError("Checkout configuration must be a table.")
    raw_values = configuration.get("values", {})
    if not isinstance(raw_values, dict):
        raise ProjectConfigurationError("Checkout configuration.values must be a table.")

    omitted = checkout_omitted_values(checkout)
    problems: list[str] = []
    normalized: dict[str, ConfigurationScalar] = {}
    effects: RuntimeEffects = {}
    aliases = set(legacy_memory_names(manifest))
    for name in sorted((set(raw_values) | set(omitted) | set(declarations)) - set(LAUNCHER_VALUE_NAMES) - aliases):
        try:
            declaration = declarations.get(name)
            if declaration is None:
                raise ProjectConfigurationError(f"Checkout answers undeclared configuration value {name!r}.")
            if name in omitted:
                if declaration.get("required", False):
                    raise ProjectConfigurationError(f"Configuration value {name!r} is mandatory and cannot be omitted.")
                if name in raw_values:
                    raise ProjectConfigurationError(f"Configuration value {name!r} is both recorded and omitted.")
            elif name in raw_values:
                normalized[name] = normalize_configuration_value(manifest, name, raw_values[name])
            elif "recommended" in declaration:
                # This is an ordinary value, not a host/acquisition authorization.
                # Explicit answers and omissions always take precedence.
                normalized[name] = _normalize_declared_value(declaration, name, declaration["recommended"])
            elif declaration.get("required", False):
                raise ProjectConfigurationError(
                    f"Required configuration value {name!r} is missing: project config set {name} VALUE."
                )
        except ProjectConfigurationError as exc:
            problems.append(str(exc))
    if problems:
        raise ProjectConfigurationError("\n".join(problems))
    for name, value in normalized.items():
        if declarations[name].get("runtime-effect") == "devcapsule.command-name":
            effects["devcapsule-command"] = str(value)
    return normalized, effects


def normalize_launcher_value(name: str, value: object, *, field_name: str | None = None) -> str | int:
    """Canonicalize a memory limit or a CPU count as typed; refuse anything else, naming the field."""
    field = field_name or name
    if name == "memory":
        return normalize_memory_size(value, field_name=field)
    if name == "cpus":
        if isinstance(value, bool) or (isinstance(value, int) and value < 1) or (
            isinstance(value, str) and not value.strip().isdecimal()
        ) or not isinstance(value, (int, str)):
            raise ProjectConfigurationError(f"{field} must be a positive integer number of CPUs; found {value!r}.")
        count = int(value)
        if count < 1:
            raise ProjectConfigurationError(f"{field} must be a positive integer number of CPUs; found {value!r}.")
        return count
    raise ProjectConfigurationError(f"The launcher owns no value named {name!r}; it owns " + ", ".join(LAUNCHER_VALUE_NAMES) + ".")


def legacy_memory_names(manifest: Mapping[str, Any]) -> tuple[str, ...]:
    """The names a manifest declares with the memory-limit effect: aliases of ``memory``."""
    return tuple(sorted(
        name for name, declaration in configuration_value_declarations(manifest).items()
        if declaration.get("runtime-effect") == MEMORY_LIMIT_EFFECT and name not in LAUNCHER_VALUE_NAMES
    ))


def normalize_memory_size(value: object, *, field_name: str = "memory size") -> str:
    """Canonicalize a typed memory size to the stored ``<n><unit>`` form.

    Accepts the canonical ``6GiB`` and Docker's ``6g``/``6G``/``6GB``/``512m``;
    a unit letter alone means the binary unit (``g`` is GiB, as Docker reads
    it). Raise ProjectConfigurationError for anything else, naming the field.
    """
    if not isinstance(value, str):
        raise ProjectConfigurationError(f"{field_name} must be a memory size such as 6GiB or 6g.")
    candidate = value.strip()
    if MEMORY_SIZE_PATTERN.fullmatch(candidate):
        return candidate
    match = MEMORY_SIZE_INPUT_PATTERN.fullmatch(candidate)
    if match is None:
        raise ProjectConfigurationError(
            f"{field_name} must be a positive memory size such as 6GiB, 6g or 512m; found {value!r}."
        )
    quantity, unit = match.group(1), (match.group(2) or "").upper()
    suffix = {"": "B", "K": "KiB", "M": "MiB", "G": "GiB", "T": "TiB"}[unit]
    return f"{quantity}{suffix}"


def memory_size_bytes(value: str) -> int:
    match = MEMORY_SIZE_PATTERN.fullmatch(value)
    if match is None:
        raise ProjectConfigurationError(f"Invalid memory size: {value!r}.")
    quantity = int(match.group(1))
    multiplier = {
        "B": 1,
        "KiB": 1024,
        "MiB": 1024**2,
        "GiB": 1024**3,
        "TiB": 1024**4,
    }[match.group(2)]
    return quantity * multiplier
