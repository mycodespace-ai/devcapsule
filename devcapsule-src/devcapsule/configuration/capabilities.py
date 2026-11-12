"""Capability policy values. Parsing does not depend on the installed catalog.

The project owns required/optional intent and minimum versions. The developer owns
extra selections and omissions. Unknown optional names remain ordinary data;
only a consumer decides which of them it can supply.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from .file_formats import ProjectConfigurationError, table


def names(value: object, label: str) -> tuple[str, ...]:
    """Return sorted, unique names from a decoded TOML array.

    Raise ProjectConfigurationError, using ``label`` to identify the field,
    unless every item is a nonempty, trimmed string without NUL characters.
    Names need not be known to this launcher's component catalog.
    """
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item or item.strip() != item or "\x00" in item
        for item in value
    ):
        raise ProjectConfigurationError(f"{label} must be an array of non-empty capability names.")
    return tuple(sorted(set(value)))


def provider_choices(value: Mapping[str, Any], label: str) -> dict[str, str]:
    """Read a capability-to-component table without consulting the catalog."""
    if any(not isinstance(key, str) or not key or key.strip() != key or "\x00" in key
           or not isinstance(item, str) or not item or item.strip() != item or "\x00" in item
           for key, item in value.items()):
        raise ProjectConfigurationError(f"{label} must map capability names to component names.")
    return dict(value)


def resolution_recommendations(manifest: Mapping[str, Any]) -> dict[str, str]:
    return provider_choices(table(manifest, "capabilities", "resolution"), "capabilities.resolution")


def version_parts(value: str) -> tuple[int, ...]:
    """Dotted integers, with an optional v prefix and numeric build suffix.

    Missing trailing segments compare as zero. Prereleases and nonnumeric
    segments are unsupported; no ecosystem-specific ordering is inferred.
    """
    import re
    if not isinstance(value, str) or re.fullmatch(r"v?[0-9]+(?:\.[0-9]+)*(?:\+[0-9]+(?:\.[0-9]+)*)?", value) is None:
        raise ProjectConfigurationError(
            f"Unsupported version form {value!r}; use dotted integers, optionally prefixed by v "
            "or followed by +build integers. Prereleases and non-numeric segments are unsupported."
        )
    parts = tuple(int(part) for part in value.removeprefix("v").split("+", 1)[0].split("."))
    while len(parts) > 1 and parts[-1] == 0:
        parts = parts[:-1]
    return parts


def meets_minimum(version: str | None, minimum: str) -> bool:
    return version is not None and version_parts(version) >= version_parts(minimum)


def requirement(value: str) -> tuple[str, str | None]:
    """Parse one requirement; the only relation is >= and spaces are not syntax."""
    name, relation, minimum = value.partition(">=")
    if not name or any(character in name for character in "<>=!~ \t\r\n"):
        raise ProjectConfigurationError(f"Unsupported requirement form {value!r}; use NAME or NAME>=VERSION.")
    if relation:
        version_parts(minimum)
    return name, minimum if relation else None


# One compatibility reader owns the obsolete field. Writers use its filter
# without learning the retired vocabulary again.
RETIRED_CAPABILITY_FIELD = "sdk-major"


def current_capability_fields(value: Mapping[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if key != RETIRED_CAPABILITY_FIELD}


def capability_notes(manifest: Mapping[str, Any]) -> tuple[str, ...]:
    if RETIRED_CAPABILITY_FIELD in table(manifest, "capabilities"):
        return ("The SDK major constraint was removed by the capabilities and components change; "
                "its old table is ignored and the next owner write drops it.",)
    return ()


@dataclass(frozen=True)
class CapabilityPolicy:
    """Shared capability names and optional minimums, independent of the catalog.

    Required names must be supplied; optional names may be omitted. Minimums
    are sorted (name, version) pairs from NAME>=VERSION requirements, never
    a separate manifest table.
    Direct construction requires normalized, unique names and minimums.
    """
    required: tuple[str, ...]
    optional: tuple[str, ...] = ()
    minimums: tuple[tuple[str, str], ...] = ()

    @classmethod
    def read(cls, manifest: Mapping[str, Any]) -> CapabilityPolicy:
        """Read ``[capabilities]`` in the schema-2 form.

        A schema-1 ``need`` list is not read here: ``manifest_schemas`` reads
        it as :class:`ManifestV1` and ``upgrade`` turns it into this form.
        """
        value = table(manifest, "capabilities")
        if "need" in value:
            raise ProjectConfigurationError(
                "capabilities.need is the schema-1 form; read the manifest through manifest_schemas.read_manifest and upgrade."
            )
        required: dict[str, str | None] = {}
        for item in names(value.get("required"), "capabilities.required"):
            name, minimum = requirement(item)
            if name in required and required[name] != minimum:
                raise ProjectConfigurationError(f"Conflicting requirements for {name!r}; declare one minimum.")
            required[name] = minimum
        optional = names(value.get("optional", []), "capabilities.optional")
        for item in optional:
            if requirement(item)[1] is not None:
                raise ProjectConfigurationError("A minimum belongs on a required capability, not an optional one.")
        overlap = set(required) & set(optional)
        if overlap:
            raise ProjectConfigurationError(f"Capabilities cannot be both required and optional: {', '.join(sorted(overlap))}.")
        return cls(tuple(sorted(required)), optional,
                   tuple(sorted((name, minimum) for name, minimum in required.items() if minimum is not None)))

    def requirements(self) -> tuple[str, ...]:
        minimums = dict(self.minimums)
        return tuple(f"{name}>={minimums[name]}" if name in minimums else name for name in self.required)

    def departing(self, departures: tuple[RequirementDeparture, ...]) -> CapabilityPolicy:
        """The policy one launch derives from: the departed requirements set aside, nothing else changed.

        The project's declaration is untouched; this is the launch's view of
        it. A departure names a required capability; one that names nothing
        the policy requires changes nothing.
        """
        departed = {departure.capability for departure in departures}
        if not departed & set(self.required):
            return self
        return CapabilityPolicy(tuple(name for name in self.required if name not in departed), self.optional,
                                tuple(item for item in self.minimums if item[0] not in departed))

    def document(self) -> dict[str, Any]:
        return {"required": list(self.requirements()), "optional": list(self.optional)}


IDE_REQUIREMENT = "ide-requirement"


@dataclass(frozen=True)
class RequirementDeparture:
    """One named departure from the project's contract, accepted by the developer for one launch.

    ``policy`` identifies the check set aside; the first and only one is
    :data:`IDE_REQUIREMENT`, the project's required IDE replaced by another
    IDE (``project run --ide IDE --force``). ``capability`` is the required
    capability set aside and ``replacement`` the capability the launch runs
    instead. A departure is not satisfaction: the launch's records say which
    requirement it set aside. It is never saved; the next launch derives
    from the project's declaration again.
    """
    policy: str
    capability: str
    replacement: str

    def document(self) -> dict[str, str]:
        return {"policy": self.policy, "required": self.capability, "launched": self.replacement}


@dataclass(frozen=True)
class LocalCapabilities:
    """One developer's additions and omissions for a project checkout.

    ``selected`` contains capability names chosen locally, such as
    ``("codex-agent", "python-ide")``. Once selected, these must be supplied
    for this checkout to launch. ``without`` contains project optional names
    to skip, such as ``("browser-automation",)``; it cannot waive a required
    capability or a dependency needed by another selected capability.

    ``providers`` stores explicit component choices by capability. Missing
    entries follow the project resolution or the catalog; the table selects
    no capability and grants no acquisition permission.

    Both tuples are sorted and unique, with no name in both. Use
    ``read(checkout)`` then ``validate(policy)`` for external data; direct
    construction assumes these invariants. Version pins remain in the
    checkout document's embedded lock, outside this value.
    """
    selected: tuple[str, ...] = ()
    without: tuple[str, ...] = ()
    providers: dict[str, str] = field(default_factory=dict)

    @classmethod
    def read(cls, checkout: Mapping[str, Any]) -> LocalCapabilities:
        """Read selections from a full decoded checkout without changing it.

        A missing capabilities table means no additions or omissions.
        Raise ProjectConfigurationError for invalid fields or overlapping
        choices. An embedded lock must be a string; parsing its contents and
        checking catalog support belong to lock selection, not this method.
        """
        value = table(checkout, "capabilities")
        if set(value) - {"selected", "without", "lock", "providers"}:
            raise ProjectConfigurationError("Unsupported local capability fields; left intact.")
        selected = names(value.get("selected", []), "local capabilities.selected")
        without = names(value.get("without", []), "local capabilities.without")
        if set(selected) & set(without):
            raise ProjectConfigurationError("A local capability cannot be both selected and omitted.")
        if "lock" in value and not isinstance(value["lock"], str):
            raise ProjectConfigurationError("Local capabilities.lock must contain a TOML lock.")
        return cls(selected, without, provider_choices(table(value, "providers"), "local capabilities.providers"))

    def validate(self, policy: CapabilityPolicy) -> None:
        """Raise ProjectConfigurationError if an omission is not project-optional.

        Call after ``read`` to check choices against a particular project.
        This does not check provider availability or change either value.
        """
        invalid = set(self.without) - set(policy.optional)
        if invalid:
            raise ProjectConfigurationError("Only project optional capabilities may be omitted locally: " + ", ".join(sorted(invalid)) + ".")
