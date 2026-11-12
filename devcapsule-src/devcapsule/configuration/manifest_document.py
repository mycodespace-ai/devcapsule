"""The project manifest as a document: its schema versions, the owner's vocabulary, and the one writer.

The manifest, ``.devcapsule/devcapsule.toml``, is read in code review by
every collaborator, so it is written in the form an owner would write by
hand (the CLI UX redesign work order of 2026-10-24, decision 11): bare keys
wherever TOML allows them, tables in a fixed owner-friendly order, a leading
comment block kept across rewrites, nothing derived in it.  Schema version 2
(decision 19) adds the vocabulary of decision 9: the environment a project
requires or offers, each name with the owner's reason, and the project's
recommendations for the IDE, the memory limit and the CPU count, which the
launcher applies as defaults and discloses, never asks (decision 24).

Readers stay tolerant (R-CONFIG-001): a schema-1 manifest is read as it is,
by :class:`manifest_schemas.ManifestV1`, upgraded in memory and never
rewritten by a command that does not edit it.  An owner's edit and
``project init --regenerate`` write the file, and both write schema 2.

This module is pure: it validates and renders mappings.  Validation against
the launcher's catalog (is ``frontend-ide`` an IDE?) belongs to the adapters
that know the catalog; file IO belongs to storage and the command adapters.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time
import re
from typing import Any, Mapping

from .file_formats import MANIFEST_SCHEMA_VERSIONS, ProjectConfigurationError, quote_toml, table
from .values import normalize_memory_size
from .capabilities import current_capability_fields

__all__ = [
    "CURRENT_MANIFEST_SCHEMA_VERSION",
    "EnvironmentPolicy",
    "MANIFEST_SCHEMA_VERSIONS",
    "RECOMMENDATION_NAMES",
    "Recommendations",
    "capability_reasons",
    "capability_table",
    "environment_name",
    "manifest_preamble",
    "render_manifest",
]


CURRENT_MANIFEST_SCHEMA_VERSION = 2

# Tables in the order an owner reads them: who the project is, what it needs,
# what it wraps, what it asks of the developer, what it recommends, the host
# access it asks for with its reasons, the declared values, the workflow
# choice.  Tables this writer does not know precede workflow in sorted order,
# so a newer owner's field is never dropped by an older launcher's edit.
MANIFEST_TABLE_ORDER = ("project", "capabilities", "sources", "environment", "recommendations", "host", "configuration", "workflow")

# An environment variable name as POSIX shells and Docker accept it.
ENVIRONMENT_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

# A key TOML lets us write without quotes.
BARE_KEY_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")

# The ordinary recommendations a project may make.  ``ide`` names a surface
# capability; ``memory`` is a memory size; ``cpus`` a positive integer.  Host
# access recommendations live under ``[host]`` with a justification each and
# are declared by ``authorization.CURATED_HOST_RECOMMENDATIONS``.
RECOMMENDATION_NAMES = ("ide", "memory", "cpus")


def environment_name(name: object, *, field_name: str) -> str:
    """Validate one environment variable name as declared or asked for."""
    if not isinstance(name, str) or ENVIRONMENT_NAME_PATTERN.fullmatch(name) is None:
        raise ProjectConfigurationError(
            f"{field_name}: environment variable names are ASCII identifiers such as POSTGRES_HOST; found {name!r}."
        )
    return name


def _reason(value: object, *, field_name: str) -> str:
    if value is None:
        return ""
    if not isinstance(value, str) or "\x00" in value:
        raise ProjectConfigurationError(f"{field_name}.reason must be a string.")
    return value


@dataclass(frozen=True)
class EnvironmentPolicy:
    """The environment variables a project asks each developer to supply.

    ``required`` names block a launch until the developer has supplied a value
    or bound a host variable; ``optional`` names are offered and listed, never
    demanded.  Each maps the variable name to the owner's reason, the empty
    string when none was given.  The values are never in the manifest: they
    are the developer's, private, kept with the checkout's saved Docker
    arguments.  No name may be both required and optional.
    """

    required: dict[str, str] = field(default_factory=dict)
    optional: dict[str, str] = field(default_factory=dict)

    @classmethod
    def read(cls, manifest: Mapping[str, Any]) -> EnvironmentPolicy:
        """Read ``[environment.required.NAME]`` and ``[environment.optional.NAME]``.

        Each entry is a table whose only known key is ``reason``.  Unknown keys
        inside an entry are tolerated and ignored, so a newer owner's field does
        not make the manifest unreadable.
        """
        environment = table(manifest, "environment")
        unknown = set(environment) - {"required", "optional"}
        if unknown:
            raise ProjectConfigurationError(
                "environment declares " + ", ".join(sorted(unknown)) + "; only 'required' and 'optional' are known."
            )
        result: dict[str, dict[str, str]] = {}
        for scope in ("required", "optional"):
            entries = table(environment, scope)
            result[scope] = {}
            for name, entry in entries.items():
                field_name = f"environment.{scope}.{name}"
                environment_name(name, field_name=field_name)
                if not isinstance(entry, dict):
                    raise ProjectConfigurationError(f"{field_name} must be a table with an optional 'reason'.")
                result[scope][name] = _reason(entry.get("reason"), field_name=field_name)
        overlap = set(result["required"]) & set(result["optional"])
        if overlap:
            raise ProjectConfigurationError(
                "Environment variables cannot be both required and optional: " + ", ".join(sorted(overlap)) + "."
            )
        return cls(dict(sorted(result["required"].items())), dict(sorted(result["optional"].items())))

    def names(self) -> tuple[str, ...]:
        return tuple(sorted({*self.required, *self.optional}))

    def document(self) -> dict[str, Any]:
        """The ``[environment]`` table, with only non-empty scopes present."""
        result: dict[str, Any] = {}
        for scope, entries in (("required", self.required), ("optional", self.optional)):
            if entries:
                result[scope] = {name: ({"reason": reason} if reason else {}) for name, reason in entries.items()}
        return result


@dataclass(frozen=True)
class Recommendations:
    """The project's ordinary recommendations: applied as defaults, disclosed, never asked.

    ``ide`` is a surface capability name such as ``frontend-ide``; whether the
    launcher knows it is checked by the adapter with the catalog.  ``memory``
    is a canonical memory size (``6GiB``).  ``cpus`` is a positive integer.
    ``reasons`` carries the owner's reason per recommendation name.
    """

    ide: str | None = None
    memory: str | None = None
    cpus: int | None = None
    reasons: dict[str, str] = field(default_factory=dict)

    @classmethod
    def read(cls, manifest: Mapping[str, Any]) -> Recommendations:
        recommendations = table(manifest, "recommendations")
        unknown = set(recommendations) - {*RECOMMENDATION_NAMES, "reasons"}
        if unknown:
            raise ProjectConfigurationError(
                "recommendations declares " + ", ".join(sorted(unknown))
                + "; known recommendations: " + ", ".join(RECOMMENDATION_NAMES)
                + ". Host access is recommended under [host] with a justification."
            )
        ide = recommendations.get("ide")
        if ide is not None and (not isinstance(ide, str) or not ide.strip() or "\x00" in ide):
            raise ProjectConfigurationError("recommendations.ide must name an IDE capability such as frontend-ide.")
        memory = recommendations.get("memory")
        if memory is not None:
            if not isinstance(memory, str):
                raise ProjectConfigurationError("recommendations.memory must be a memory size such as 6GiB.")
            memory = normalize_memory_size(memory, field_name="recommendations.memory")
        cpus = recommendations.get("cpus")
        if cpus is not None and (type(cpus) is not int or cpus < 1):
            raise ProjectConfigurationError("recommendations.cpus must be a positive integer.")
        reasons_table = table(recommendations, "reasons")
        reasons: dict[str, str] = {}
        for name, reason in reasons_table.items():
            if name not in RECOMMENDATION_NAMES:
                raise ProjectConfigurationError(f"recommendations.reasons.{name}: no such recommendation.")
            reasons[name] = _reason(reason, field_name=f"recommendations.reasons.{name}")
        return cls(ide, memory, cpus, dict(sorted(reasons.items())))

    def value(self, name: str) -> str | int | None:
        if name not in RECOMMENDATION_NAMES:
            raise ProjectConfigurationError(f"No such recommendation {name!r}; known: {', '.join(RECOMMENDATION_NAMES)}.")
        return getattr(self, name)

    def document(self) -> dict[str, Any]:
        """The ``[recommendations]`` table, with only present recommendations."""
        result: dict[str, Any] = {}
        for name in RECOMMENDATION_NAMES:
            value = getattr(self, name)
            if value is not None:
                result[name] = value
        reasons = {name: reason for name, reason in self.reasons.items() if reason and name in result}
        if reasons:
            result["reasons"] = reasons
        return result


def capability_reasons(manifest: Mapping[str, Any]) -> dict[str, str]:
    """The owner's reasons per required or offered capability, ``[capabilities.reasons]``."""
    reasons = table(manifest, "capabilities", "reasons")
    result: dict[str, str] = {}
    for name, reason in reasons.items():
        if not isinstance(name, str) or not name:
            raise ProjectConfigurationError("capabilities.reasons keys must be capability names.")
        result[name] = _reason(reason, field_name=f"capabilities.reasons.{name}")
    return dict(sorted(result.items()))


def manifest_preamble(text: str) -> str:
    """The leading comment block of a manifest's text, kept across rewrites.

    Everything before the first line that is neither blank nor a comment, with
    trailing blank lines trimmed to one.  An owner's note at the head of the
    file survives every command-driven edit; comments elsewhere do not, which
    the writer's contract states.
    """
    kept: list[str] = []
    for line in text.split("\n"):
        line = line.removesuffix("\r")
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            break
        kept.append(line)
    while kept and not kept[-1].strip():
        kept.pop()
    return "\n".join(kept) + "\n" if kept else ""


def _key(name: object) -> str:
    text = str(name)
    return text if BARE_KEY_PATTERN.fullmatch(text) else quote_toml(text)


def _scalar(value: Any) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, str):
        return quote_toml(value)
    if isinstance(value, list):
        return "[" + ", ".join(_scalar(item) for item in value) + "]"
    if isinstance(value, dict):
        return "{ " + ", ".join(f"{_key(k)} = {_scalar(v)}" for k, v in value.items()) + " }"
    raise ProjectConfigurationError(f"Unsupported manifest value type {type(value).__name__}.")


def render_manifest(document: Mapping[str, Any], *, preamble: str = "") -> str:
    """Render a manifest mapping as the text an owner would have written.

    The schema version and other root values come first. Tables follow
    :data:`MANIFEST_TABLE_ORDER`, with extension tables before workflow.
    Within a table, scalar keys keep the
    mapping's order, so a writer that builds the table in reading order is
    honored; subtables follow their parent.  Whatever the mapping holds is
    rendered; the builders of each table leave out what says nothing, so an
    absent ``optional`` reads as "none" to every reader and no line is noise
    (deficiency 19 of the work order).  ``preamble`` is the leading comment
    block to keep; comments elsewhere are not preserved.
    """
    document = dict(document)
    if "capabilities" in document:
        document["capabilities"] = current_capability_fields(document["capabilities"])
    lines: list[str] = [preamble.rstrip("\n")] if preamble.strip() else []
    if lines:
        lines.append("")
    version = document.get("devcapsule-schema-version", CURRENT_MANIFEST_SCHEMA_VERSION)
    lines.append(f"devcapsule-schema-version = {_scalar(version)}")
    for name, value in document.items():
        if name != "devcapsule-schema-version" and not isinstance(value, dict):
            lines.append(f"{_key(name)} = {_scalar(value)}")
    ordered = [name for name in MANIFEST_TABLE_ORDER if name != "workflow" and isinstance(document.get(name), dict)]
    ordered.extend(sorted(name for name, value in document.items() if name not in MANIFEST_TABLE_ORDER and isinstance(value, dict)))
    if isinstance(document.get("workflow"), dict):
        ordered.append("workflow")

    def emit(value: Mapping[str, Any], path: tuple[str, ...]) -> None:
        scalars = [(key, item) for key, item in value.items() if not isinstance(item, dict)]
        subtables = [(key, item) for key, item in value.items() if isinstance(item, dict)]
        if scalars or not subtables:
            lines.extend(["", "[" + ".".join(_key(part) for part in path) + "]"])
            lines.extend(f"{_key(key)} = {_scalar(item)}" for key, item in scalars)
        for key, item in subtables:
            emit(item, (*path, str(key)))

    for name in ordered:
        value = document[name]
        if name == "workflow":
            lines.extend(["", "# The project's workflow choice."])
        emit(value, (name,))
    return "\n".join(lines) + "\n"


def capability_table(
    policy: Any, reasons: Mapping[str, str] | None = None, *, previous: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """The ``[capabilities]`` table in the ``required`` form, saying only what is so.

    ``policy`` is a ``CapabilityPolicy``; ``reasons`` maps a capability name to
    the owner's reason. Empty optional lists are left out,
    so a project that offers nothing has no ``optional = []`` line.
    Unknown fields in ``previous`` survive an edit by an older launcher.
    """
    result: dict[str, Any] = {"required": list(policy.requirements())}
    if policy.optional:
        result["optional"] = list(policy.optional)
    kept = {name: reason for name, reason in sorted((reasons or {}).items())
            if reason and name in {*policy.required, *policy.optional}}
    if kept:
        result["reasons"] = kept
    result.update({key: value for key, value in current_capability_fields(previous or {}).items()
                   if key not in {"need", "required", "optional", "reasons"}})
    return result
