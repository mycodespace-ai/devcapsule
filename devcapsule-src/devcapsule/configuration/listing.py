"""The truthful listing: every choice of a checkout with its effective value, its source and what is pending.

Principle 6 of the CLI UX redesign work order of 2026-10-24: a listing shows
the value the next launch uses, where it comes from, and whether a decision
is pending; a missing answer is a row, not a refusal, and the listing never
writes anything.  ``config show`` prints it, ``config check`` exits 3 on its
pending rows, the web console renders it.

Every row is one of these kinds:

- ``ide``, ``agent``, ``tool``: the capabilities of the checkout, from the
  project's requirements and offers and the checkout's selection;
- ``memory``, ``cpus``: the launcher-owned values, from the checkout, the
  project's recommendation or the home's defaults;
- ``access``: host access and the base and vendor consents, from the
  authorization review;
- ``env``: the environment the project asks for and the checkout saved;
- ``source``: a wrapped source's declared toolchain and fork or learning intent;
- ``value``, ``binding``, ``secret``: the project's declared values and the
  selected components' state slots and secret inputs.

The sources are plain words: ``checkout``, ``project (required)``,
``project (offered)``, ``project recommendation``, ``home default``,
``secure default``, ``none``.  A pending row carries the one command that
settles it.

This module is pure: the adapters load the documents and pass them in,
with the launcher catalog's view of which capability is an IDE or an agent
and which component supplies it.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shlex
from typing import Any, Mapping

from .authorization import (
    authorization_declarations,
    authorization_deny_value,
    render_authorization_value,
    review_authorizations,
)
from .bindings import component_secret_inputs, configuration_binding_declarations
from .capabilities import CapabilityPolicy, LocalCapabilities, RequirementDeparture, capability_notes
from .file_formats import ProjectConfigurationError, render_toml_scalar, table
from .launcher_values import launcher_value_source
from .manifest_document import EnvironmentPolicy, Recommendations
from .sources import WrappedSources
from .trust import HomeTrust, channels_for
from .values import (
    LAUNCHER_VALUE_NAMES,
    configuration_value_declarations,
    legacy_memory_names,
    normalize_configuration_value,
)

__all__ = ["Decision", "LISTING_SCHEMA_VERSION", "Listing", "ListingRow", "assess_checkout"]

LISTING_SCHEMA_VERSION = 2

HOST_ACCESS_NODES = ("network", "docker-daemon", "development-sudo", "host-browser", "host-x11")


@dataclass(frozen=True)
class Decision:
    """One decision only the developer can take, as ``run`` asks it and ``check`` reports it.

    ``kind`` is ``ide`` (choose among ``choices``, capability names with the
    component each selects), ``env`` (supply a value for ``name``, with the
    project's ``reason``), ``access`` (allow or deny the host access ``name``
    at ``value``, with the project's reason and ``deny`` as the deny value),
    ``renew`` (a recorded host answer that is invalid, to allow or deny
    again), ``trust`` (accept the channel ``name`` of a vendor product or of
    DevCapsule's base images once for this home, D-0011), ``consent``
    (accept a base or download that no channel covers, per checkout),
    ``value`` (a declared value the project requires) or ``secret`` (a
    component's required secret input, bound to ``variable``).
    ``run`` records the answer where the config family would; ``check``
    prints ``command``.
    """

    kind: str
    name: str
    description: str
    command: str
    choices: tuple[tuple[str, str], ...] = ()
    reason: str = ""
    value: str = ""
    deny: str = ""
    variable: str = ""


@dataclass(frozen=True)
class ListingRow:
    kind: str
    name: str
    effective: str
    source: str
    pending: str = ""
    command: str = ""
    decision: Decision | None = None
    provider: str = ""
    provider_source: str = ""

    def document(self) -> dict[str, str]:
        return {"kind": self.kind, "name": self.name, "effective": self.effective, "source": self.source,
                "pending": self.pending, "command": self.command,
                **({"provider": self.provider, "provider-source": self.provider_source} if self.provider else {})}


@dataclass(frozen=True)
class Listing:
    rows: tuple[ListingRow, ...]
    notes: tuple[str, ...] = ()
    # The launch's named departures from the project's contract, when the
    # listing is a launch's; a checkout's listing has none.
    departures: tuple[RequirementDeparture, ...] = ()

    @property
    def pending(self) -> tuple[ListingRow, ...]:
        return tuple(row for row in self.rows if row.pending)

    @property
    def decisions(self) -> tuple[Decision, ...]:
        """The pending rows' decisions, in the order ``run`` asks them: what to choose, then what to allow."""
        return tuple(row.decision for row in self.rows if row.pending and row.decision is not None)

    def render(self) -> str:
        headers = ("KIND", "NAME", "EFFECTIVE", "SOURCE", "PROVIDER", "PENDING")
        values = [(row.kind, row.name, row.effective, row.source,
                   f"{row.provider} ({row.provider_source})" if row.provider else "", row.pending) for row in self.rows]
        widths = [max(len(headers[index]), *(len(row[index]) for row in values)) if values else len(headers[index])
                  for index in range(len(headers))]
        lines = ["  ".join(header.ljust(widths[index]) for index, header in enumerate(headers)).rstrip()]
        lines.extend("  ".join(value.ljust(widths[index]) for index, value in enumerate(row)).rstrip() for row in values)
        lines.extend(self.notes)
        return "\n".join(lines)

    def render_pending(self) -> str:
        """The pending decisions, one per line, each with the command that settles it."""
        if not self.pending:
            return "Nothing is pending."
        lines = ["Pending decisions:"]
        lines.extend(f"  {row.kind} {row.name}: {row.pending}" + (f"\n      {row.command}" if row.command else "")
                     for row in self.pending)
        return "\n".join(lines)

    def document(self) -> dict[str, Any]:
        return {"schema-version": LISTING_SCHEMA_VERSION, "rows": [row.document() for row in self.rows],
                "pending": [row.name for row in self.pending], "notes": list(self.notes),
                **({"departures": [item.document() for item in self.departures]} if self.departures else {})}

    @classmethod
    def from_document(cls, document: Mapping[str, Any]) -> Listing:
        """A listing read back from its ``document``, to render where it was not computed: inside a capsule."""
        rows = document.get("rows")
        if document.get("schema-version") != LISTING_SCHEMA_VERSION or not isinstance(rows, list):
            raise ProjectConfigurationError(f"Not a schema-{LISTING_SCHEMA_VERSION} listing document.")
        fields = ("kind", "name", "effective", "source", "pending", "command")
        result = []
        for row in rows:
            if not isinstance(row, dict) or any(not isinstance(row.get(field, ""), str) for field in (*fields, "provider", "provider-source")):
                raise ProjectConfigurationError("A listing row has eight text columns.")
            kind, name, effective, source, pending, command = (str(row.get(field, "")) for field in fields)
            result.append(ListingRow(kind, name, effective, source, pending, command,
                                     provider=str(row.get("provider", "")), provider_source=str(row.get("provider-source", ""))))
        notes = document.get("notes", [])
        return cls(tuple(result), tuple(str(note) for note in notes) if isinstance(notes, list) else ())


def _command(project: Path | None, *arguments: str) -> str:
    context = ["--path", str(project)] if project is not None else []
    return shlex.join(["devcapsule", "project", *context, "config", *arguments])


def _component_version(lock: Mapping[str, Any], component: str) -> str:
    metadata = table(lock, "components").get(component)
    version = metadata.get("version") if isinstance(metadata, dict) else None
    return f"{component} {version}" if isinstance(version, str) and version else component


def assess_checkout(
    manifest: Mapping[str, Any],
    shared_lock: Mapping[str, Any],
    composed_lock: Mapping[str, Any],
    checkout: Mapping[str, Any],
    *,
    home: Mapping[str, Any] | None = None,
    saved_environment: Mapping[str, str | None] | None = None,
    surfaces: Mapping[str, str],
    project: Path | None = None,
    registered: bool = True,
    home_path: Path | None = None,
    base_display: str | None = None,
    access_lock: Mapping[str, Any] | None = None,
    capability_versions: Mapping[str, str | None] | None = None,
    capability_providers: Mapping[str, tuple[str, str]] | None = None,
    departures: tuple[RequirementDeparture, ...] = (),
) -> Listing:
    """The listing of one checkout, from its documents, writing nothing.

    ``composed_lock`` is the shared lock with the checkout's pins laid over
    it (``capability_selection.compose_lock``); ``surfaces`` maps IDE
    capability names to the component each selects, as
    the launcher's catalog knows them. ``saved_environment`` maps a saved
    variable name to its value, or ``None`` when it is bound to the host's
    variable; values are never shown. ``registered`` says whether the
    checkout has a record yet; an unregistered checkout is listed from an
    empty record. ``base_display`` is the catalog's display contract for
    the selected base, or None when the host must inspect it at launch.
    ``departures`` are a launch's named departures from the project's
    contract: the IDE row and a note say which requirement the launch set
    aside, so the launch's listing never claims the project was satisfied.
    """
    rows: list[ListingRow] = []
    notes: list[str] = list(capability_notes(manifest))
    policy = CapabilityPolicy.read(manifest)
    local = LocalCapabilities.read(checkout)
    recommendations = Recommendations.read(manifest)
    surfaces = {name: (capability_providers or {}).get(name, (component, ""))[0] for name, component in surfaces.items()}
    rows.extend(_capability_rows(policy.departing(departures), local, recommendations, shared_lock, composed_lock,
                                 surfaces, project, capability_versions or {}))
    for departure in departures:
        from dataclasses import replace as _replace
        rows = [_replace(row, source=f"this launch (--force); the project requires {departure.capability}")
                if row.kind == "ide" and row.name == departure.replacement else row for row in rows]
        notes.append(f"Departure: the project's required IDE {departure.capability} is set aside by --force for this "
                     f"launch; {departure.replacement} runs. The requirement and the saved IDE are unchanged.")
    from dataclasses import replace
    rows = [replace(row, provider=capability_providers[row.name][0], provider_source=capability_providers[row.name][1])
            if capability_providers and row.name in capability_providers else row for row in rows]
    rows.extend(_launcher_value_rows(manifest, checkout, home, project))
    rows.extend(_access_rows(manifest, composed_lock if access_lock is None else access_lock,
                             checkout, project, base_display, home, home_path))
    rows.extend(_environment_rows(manifest, saved_environment or {}, project))
    rows.extend(_source_rows(manifest))
    has_surface = bool(table(composed_lock, "components").get("interactive-surface"))
    if has_surface:
        rows.extend(_binding_rows(composed_lock, checkout, project))
        rows.extend(_secret_rows(composed_lock, checkout, project))
    else:
        notes.append("State directories and component secrets are listed once an IDE is chosen.")
    rows.extend(_value_rows(manifest, checkout, project))
    if not registered:
        notes.append("This checkout has no record yet; the first 'devcapsule project run' registers it.")
    return Listing(tuple(rows), tuple(notes), tuple(departures))


def _capability_rows(
    policy: CapabilityPolicy, local: LocalCapabilities, recommendations: Recommendations,
    shared_lock: Mapping[str, Any], composed_lock: Mapping[str, Any],
    surfaces: Mapping[str, str], project: Path | None,
    capability_versions: Mapping[str, str | None],
) -> list[ListingRow]:
    rows: list[ListingRow] = []
    selected_ide = next((name for name in local.selected if name in surfaces), None)
    legacy_ide = next((name for name in policy.required if name in surfaces), None)
    surface_component = table(composed_lock, "components").get("interactive-surface")
    choices = ", ".join(sorted(surfaces))
    if selected_ide is not None:
        rows.append(ListingRow("ide", selected_ide, _component_version(composed_lock, surfaces[selected_ide]), "checkout"))
    elif legacy_ide is not None and isinstance(surface_component, str):
        rows.append(ListingRow("ide", legacy_ide, _component_version(shared_lock, surface_component), "project (required)"))
    elif recommendations.ide is not None and recommendations.ide in surfaces:
        reason = recommendations.reasons.get("ide", "")
        rows.append(ListingRow("ide", recommendations.ide, surfaces[recommendations.ide],
                               "project recommendation" + (f": {reason}" if reason else "") + "; recorded at the first run",
                               "", _command(project, "ide", recommendations.ide)))
    else:
        options = tuple((name, _component_version(composed_lock, surfaces[name])) for name in sorted(surfaces))
        rows.append(ListingRow("ide", "(none)", "-", "none", f"choose one: {choices}", _command(project, "ide", "IDE"),
                               Decision("ide", "ide", "Your IDE for this checkout", _command(project, "ide", "IDE"), options)))
    providers = table(composed_lock, "capability-providers")
    personal = set(surfaces) | set(policy.required) | set(policy.optional)
    for scope, names in (("project (required)", policy.required), ("project (offered)", policy.optional)):
        for name in names:
            if name in surfaces:
                continue
            components = providers.get(name)
            if isinstance(components, list) and components:
                effective = ", ".join(_component_version(composed_lock, str(component)) for component in components)
            else:
                effective = "supplied by the base"
            if name in local.without:
                rows.append(ListingRow("capability", name, "omitted", "checkout (omitted)"))
            else:
                rows.append(ListingRow("capability", name, effective, scope))
    for name in sorted(set(local.selected) - personal):
        components = providers.get(name)
        effective = ", ".join(_component_version(composed_lock, str(c)) for c in components) if isinstance(components, list) and components else name
        rows.append(ListingRow("capability", name, effective, "checkout"))
    if policy.minimums:
        from dataclasses import replace
        minimums = dict(policy.minimums)
        for index, row in enumerate(rows):
            if row.name in minimums and row.source == "project (required)":
                version = capability_versions.get(row.name)
                effective = row.effective
                if effective == "supplied by the base":
                    effective += f", {version or 'version unknown'}"
                rows[index] = replace(row, source=f"project (required, >={minimums[row.name]})",
                                      effective=effective)
    return rows


def _launcher_value_rows(
    manifest: Mapping[str, Any], checkout: Mapping[str, Any], home: Mapping[str, Any] | None, project: Path | None,
) -> list[ListingRow]:
    rows: list[ListingRow] = []
    for name in LAUNCHER_VALUE_NAMES:
        try:
            value, source = launcher_value_source(name, manifest, checkout, home)
        except ProjectConfigurationError as exc:
            rows.append(ListingRow(name, name, "unresolved", "invalid or missing value", str(exc),
                                   _command(project, "set", name, "SIZE" if name == "memory" else "N")))
            continue
        effective = "no limit" if value is None else str(value)
        rows.append(ListingRow(name, name, effective, source))
    return rows


def _access_rows(
    manifest: Mapping[str, Any], lock: Mapping[str, Any], checkout: Mapping[str, Any], project: Path | None,
    base_display: str | None, home: Mapping[str, Any] | None = None,
    home_path: Path | None = None,
) -> list[ListingRow]:
    try:
        trust = HomeTrust.read(home or {})
        reviews = {item.name: item for item in review_authorizations(manifest, lock, checkout, trust)}
        declarations = authorization_declarations(manifest, lock)
    except ProjectConfigurationError as exc:
        return [ListingRow("access", "*", "invalid", str(exc), "repair the checkout record", "")]
    channels = {channel.authorization: channel for channel in channels_for(lock).values()}
    rows: list[ListingRow] = []
    for name in (*HOST_ACCESS_NODES, *sorted(set(declarations) - set(HOST_ACCESS_NODES))):
        declaration = declarations.get(name)
        review = reviews.get(name)
        if declaration is None or review is None:
            continue
        pending = ""
        command = ""
        if name in HOST_ACCESS_NODES:
            deny = authorization_deny_value(declaration)
            rendered_deny = render_authorization_value(deny) if deny is not None else "false"
            recommended = render_authorization_value(declaration.recommended_value)
            legacy = table(checkout, "host").get(name)
            decision: Decision | None = None
            if review.status in {"available", "missing-recommended"} and legacy is not None:
                try:
                    from .review import HostAccess
                    HostAccess().overlay({name: legacy})
                except ProjectConfigurationError as exc:
                    pending = str(exc)
                    command = _command(project, "forget", name)
                    effective, source = "invalid", "checkout (legacy)"
                else:
                    effective, source = render_authorization_value(legacy), "checkout (legacy)"
            elif review.value is not None and review.status not in {"stale", "invalid"}:
                effective = render_authorization_value(review.value)
                source = "checkout"
                if review.superseded:
                    # D-0012, answer 23: the answer stands; the change is disclosed, never asked.
                    source += f" (kept; {review.superseded})"
                    if declaration.project_recommended:
                        source += f": {declaration.description}"
            else:
                effective = rendered_deny
                source = "secure default"
                if name == "host-x11":
                    if base_display == "contained":
                        effective = "contained desktop"
                    elif base_display == "host-x11-only":
                        effective, source = "host X11 (needs your consent)", "no contained desktop on this base"
                    else:
                        effective, source = "determined at launch", "base display support unknown"
            if name == "host-x11" and base_display == "host-x11-only":
                if effective == "false":
                    pending = "this base has no contained desktop; select a newer base or authorize host X11"
                    command = _command(project, "authorize", "host-x11", "true")
                    effective = "unavailable"
                elif review.recorded == "unanswered":
                    pending = "this base has no contained desktop; host X11 shows the IDE only with your consent"
                    command = _command(project, "authorize", "host-x11", "true")
                    decision = Decision("consent", "host-x11", declaration.description, command, value="true")
            if declaration.project_recommended and not review.superseded:
                source += f"; project recommends {recommended}: {declaration.description}"
                if review.recorded == "unanswered" and legacy is None:
                    pending = f"the project asks for {name} {recommended}; allow or deny"
                    command = _command(project, "authorize", name, recommended) + "  |  " + _command(project, "deny", name)
                    decision = Decision("access", name, f"{name} {recommended}", command, reason=declaration.description,
                                        value=recommended, deny=rendered_deny)
            if review.status == "stale":
                pending = "the recommendation changed since your answer; renew or change it"
                command = _command(project, "authorize", name, recommended) + "  |  " + _command(project, "deny", name)
                decision = Decision("renew", name, f"the recommendation changed since your answer: {name} {recommended}", command, reason=declaration.description,
                                    value=recommended, deny=rendered_deny)
            elif review.status == "invalid":
                pending = str(review.problem or "invalid answer")
                command = _command(project, "forget", name)
                decision = Decision("renew", name, f"{name} {recommended}", command, reason=str(review.problem or ""),
                                    value=recommended, deny=rendered_deny)
            rows.append(ListingRow("access", name, effective, source, pending, command, decision))
            continue
        effective = review.recorded if review.recorded != "unanswered" else "-"
        source = "checkout" if review.recorded != "unanswered" else "lock (recommended)"
        decision = None
        channel = channels.get(name)
        if review.trusted_channel is not None:
            effective = str(review.value) if name == "base-image" else "trusted"
            source = f"home trust ({review.trusted_channel})"
        elif review.problem is not None and channel is not None and review.recorded == "unanswered":
            # D-0011: one acceptance per channel per home, instead of a
            # per-checkout consent.
            pending = f"trust {channel.vendor}'s channel once for this home"
            command = f"devcapsule home trust accept {channel.id}"
            decision = Decision("trust", channel.id, channel.statement(home_path), command, reason=channel.note, value=name)
        elif review.problem is not None:
            pending = review.problem
            value = "default" if name == "base-image" else "true"
            command = _command(project, "authorize", name, value)
            decision = Decision("consent", name, declaration.description, command, value=value)
        if review.value is not None and name == "base-image" and review.trusted_channel is None:
            effective = str(review.value)
        rows.append(ListingRow("access", name, effective, source, pending, command, decision))
    for name in sorted(set(reviews) - set(declarations)):
        review = reviews[name]
        rows.append(ListingRow("access", name, "unused", "checkout", str(review.problem or "unsupported answer"),
                               _command(project, "forget", name)))
    return rows


def _source_rows(manifest: Mapping[str, Any]) -> list[ListingRow]:
    """One row per wrapped source: its Java line, and whether it is the upstream to learn from or a fork to change."""
    rows: list[ListingRow] = []
    for source in WrappedSources.read(manifest).entries:
        effective = f"java {source.java}" if source.java is not None else "no toolchain declared"
        origin = f"project: fork of {source.upstream}" if source.upstream else "project: upstream, read-only"
        rows.append(ListingRow("source", source.path, effective, origin))
    return rows


def _environment_rows(
    manifest: Mapping[str, Any], saved: Mapping[str, str | None], project: Path | None,
) -> list[ListingRow]:
    rows: list[ListingRow] = []
    environment = EnvironmentPolicy.read(manifest)
    for scope, entries in (("project (required)", environment.required), ("project (offered)", environment.optional)):
        for name, reason in entries.items():
            source = scope + (f": {reason}" if reason else "")
            if name in saved:
                effective = "set" if saved[name] is not None else "from the host's variable"
                rows.append(ListingRow("env", name, effective, "checkout; " + source))
            elif scope.endswith("(required)"):
                command = _command(project, "env", "set", name, "VALUE")
                rows.append(ListingRow("env", name, "unset", source, "the project needs a value from you", command,
                                       Decision("env", name, f"{name}: {reason}" if reason else name, command, reason=reason)))
            else:
                rows.append(ListingRow("env", name, "unset", source))
    for name in sorted(set(saved) - set(environment.names())):
        effective = "set" if saved[name] is not None else "from the host's variable"
        rows.append(ListingRow("env", name, effective, "checkout"))
    for index, row in enumerate(rows):
        if row.name in saved and saved[row.name] is None and row.name not in os.environ:
            rows[index] = ListingRow("env", row.name, "unset", row.source,
                                     "the bound host variable is missing in this shell",
                                     _command(project, "env", "set", row.name, "VALUE"),
                                     Decision("env", row.name, "The bound host variable is missing in this shell",
                                              _command(project, "env", "set", row.name, "VALUE")))
    return rows


def _binding_rows(lock: Mapping[str, Any], checkout: Mapping[str, Any], project: Path | None) -> list[ListingRow]:
    try:
        declarations = configuration_binding_declarations(lock)
    except ProjectConfigurationError as exc:
        return [ListingRow("binding", "*", "invalid", str(exc))]
    bindings = table(checkout, "configuration", "bindings", "host-directory")
    adopted = table(checkout, "state", "adopted")
    rows: list[ListingRow] = []
    for name in sorted(declarations):
        bound = bindings.get(name, adopted.get(name))
        if isinstance(bound, str):
            path = Path(bound).expanduser()
            if path.is_dir():
                rows.append(ListingRow("binding", name, str(path), "checkout"))
            else:
                rows.append(ListingRow("binding", name, str(path), "checkout", "the directory does not exist",
                                       _command(project, "bind", name, "host-directory:PATH")))
        else:
            rows.append(ListingRow("binding", name, "managed directory", "managed default"))
    return rows


def _secret_rows(lock: Mapping[str, Any], checkout: Mapping[str, Any], project: Path | None) -> list[ListingRow]:
    try:
        declarations = component_secret_inputs(lock)
    except ProjectConfigurationError as exc:
        return [ListingRow("secret", "*", "invalid", str(exc))]
    bound = table(checkout, "configuration", "bindings", "host-environment")
    rows: list[ListingRow] = []
    for name, declaration in sorted(declarations.items()):
        variable = declaration.environment_variable
        if name in bound:
            available = variable in os.environ
            rows.append(ListingRow("secret", name, f"from {variable}", "checkout" if available else "checkout (variable unset in this shell)"))
        elif declaration.required:
            command = _command(project, "bind", name, f"host-environment:{variable}")
            rows.append(ListingRow("secret", name, "unbound", "component (required)", "bind the host variable", command,
                                   Decision("secret", name, declaration.description, command, variable=variable)))
        else:
            rows.append(ListingRow("secret", name, "unbound; sign in inside the capsule", "component (optional)"))
    return rows


def _value_rows(manifest: Mapping[str, Any], checkout: Mapping[str, Any], project: Path | None) -> list[ListingRow]:
    declarations = configuration_value_declarations(manifest)
    aliases = set(legacy_memory_names(manifest))
    configuration = table(checkout, "configuration")
    raw_values = table(configuration, "values")
    omitted = configuration.get("omitted-values", []) if isinstance(configuration.get("omitted-values", []), list) else []
    rows: list[ListingRow] = []
    for name, declaration in sorted(declarations.items()):
        if name in aliases:
            continue
        if name in raw_values:
            try:
                value = normalize_configuration_value(manifest, name, raw_values[name])
            except ProjectConfigurationError as exc:
                rows.append(ListingRow("value", name, repr(raw_values[name]), "checkout", str(exc), _command(project, "set", name, "VALUE")))
            else:
                rows.append(ListingRow("value", name, render_toml_scalar(value), "checkout"))
        elif name in omitted:
            rows.append(ListingRow("value", name, "omitted", "checkout"))
        elif "recommended" in declaration:
            rows.append(ListingRow("value", name, render_toml_scalar(normalize_configuration_value(manifest, name, "default")),
                                   "project recommendation"))
        elif declaration.get("required", False):
            command = _command(project, "set", name, "VALUE")
            rows.append(ListingRow("value", name, "unset", "project (required)", "the project needs a value from you", command,
                                   Decision("value", name, str(declaration.get("description") or name), command)))
        else:
            rows.append(ListingRow("value", name, "unset", "project (optional)"))
    for name in sorted(set(raw_values) - set(declarations) - set(LAUNCHER_VALUE_NAMES) - aliases):
        rows.append(ListingRow("value", name, repr(raw_values[name]), "checkout", "not declared by this project",
                               _command(project, "set", name, "default")))
    return rows
