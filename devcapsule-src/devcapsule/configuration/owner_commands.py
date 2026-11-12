"""The project owner's commands: what the project requires, offers and recommends.

Each operation edits the shared manifest through one writer
(:func:`manifest_document.render_manifest`) and, when the tools change,
regenerates every platform lock the project carries, validating each
candidate pair before anything is written and promoting the files under the
capability transaction journal of :mod:`capability_commands`. The rc4 IDE recommendation command stays; agents are ordinary shared
capabilities. Component acquisition still requires the developer's consent.

The verbs are the ones the CLI UX redesign work order of 2026-10-24 settled:
``require``, ``offer`` and ``drop`` for capabilities and environment variables,
``recommend`` for a capability provider, the IDE, resources and curated host
accesses, each with the owner's reason (``--because``).
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence

from devcapsule.platforms import Platform
from devcapsule.resolution_matrix import MATRICES, ResolutionMatrix

from .authorization import CURATED_HOST_RECOMMENDATIONS, render_authorization_value
from .capabilities import CapabilityPolicy, requirement, resolution_recommendations
from .capability_commands import canonical_tool_name, check_documents, paths, project_locks, promote, regenerate_locks
from .file_formats import ProjectConfigurationError
from .manifest import current_manifest
from .manifest_document import (
    RECOMMENDATION_NAMES,
    EnvironmentPolicy,
    Recommendations,
    capability_reasons,
    capability_table,
    environment_name,
)
from .sources import WrappedSource, WrappedSources, has_control_characters, java_line, source_path
from .storage import discover_project, load_toml, project_platform, require_settled
from .values import normalize_memory_size

__all__ = [
    "declare_source",
    "edit_capabilities",
    "drop_environment",
    "drop_tools",
    "offer_environment",
    "offer_tools",
    "recommend",
    "require_environment",
    "require_tools",
]


def _project(start: Path, *, check_resolutions: bool = True) -> tuple[
    Path, dict[str, Any], dict[Platform, dict[str, Any]], ResolutionMatrix,
]:
    """The project's root, manifest and every lock, validated, and this host's matrix for its vocabulary."""
    root = discover_project(start)
    require_settled(root)
    manifest_path = paths(root)[0]
    manifest, locks = current_manifest(load_toml(manifest_path), manifest_path).document(), project_locks(root)
    for lock in locks.values():
        check_documents(manifest, lock, check_resolutions=check_resolutions)
    return root, manifest, locks, MATRICES[project_platform(root)]


def _policy_edit(
    start: Path, *, change: str, names: Sequence[str], because: str | None,
    preview: bool, allow_unverified: bool, native: bool = False,
) -> str:
    root, manifest, locks, matrix = _project(start)
    policy = CapabilityPolicy.read(manifest)
    reasons = capability_reasons(manifest)
    required, optional = set(policy.required), set(policy.optional)
    minimums = dict(policy.minimums)
    # Preserve a hand-written component alias while editing its declaration.
    declared: dict[str, str] = {}
    for name in (*policy.required, *policy.optional):
        try:
            declared[matrix.canonical_name(name)] = name
        except ProjectConfigurationError:
            continue  # Unknown optional declarations remain opaque.
    def declared_name(name: str) -> str:
        if native and name in required | optional:
            return name
        canonical = canonical_tool_name(matrix, name)
        return name if native else declared.get(canonical, canonical)
    if change == "drop":
        canonical = tuple(declared_name(name) for name in names)
        unknown = sorted(set(canonical) - required - optional)
        if unknown:
            raise ProjectConfigurationError(
                "Not declared by this project: " + ", ".join(unknown) + "; nothing changed."
            )
        for name in canonical:
            required.discard(name)
            optional.discard(name)
            minimums.pop(name, None)
            reasons.pop(name, None)
    else:
        parsed = [requirement(name) for name in names] if native else [(name, None) for name in names]
        if change == "offer" and any(minimum is not None for _, minimum in parsed):
            raise ProjectConfigurationError("A minimum belongs on a required capability, not an optional one.")
        canonical = tuple(dict.fromkeys(declared_name(name) for name, _ in parsed))
        if change == "require":
            for name, minimum in parsed:
                key = declared_name(name)
                if minimum is not None:
                    minimums[key] = minimum
                else:
                    minimums.pop(key, None)
        if any(matrix.is_ide(name) for name in canonical):
            raise ProjectConfigurationError(
                "IDE choices are each developer's; recommend one with 'config recommend ide NAME'."
            )
        target, other = (required, optional) if change == "require" else (optional, required)
        for name in canonical:
            target.add(name)
            other.discard(name)
            if because is not None:
                reasons[name] = because
        if change == "offer":
            for name in canonical:
                minimums.pop(name, None)
    required_order = [requirement(item)[0] for item in manifest["capabilities"].get("required", [])]
    optional_order = list(manifest["capabilities"].get("optional", []))
    def ordered(values: set[str], previous: list[str]) -> tuple[str, ...]:
        return tuple(name for name in dict.fromkeys((*previous, *canonical)) if name in values) if native else tuple(sorted(values))
    candidate = CapabilityPolicy(ordered(required, required_order), ordered(optional, optional_order), tuple(sorted(minimums.items())))
    candidate_manifest = deepcopy(manifest)
    candidate_manifest["capabilities"] = capability_table(candidate, reasons, previous=manifest["capabilities"])
    generated = regenerate_locks(candidate, locks, allow_unverified=allow_unverified,
                                 recommendations=resolution_recommendations(candidate_manifest))
    for lock in generated.values():
        check_documents(candidate_manifest, lock)
    if not preview:
        promote(root, candidate_manifest, generated)
    verb = {"require": "Required", "offer": "Offered", "drop": "Dropped"}[change]
    lines = [
        ("Preview; nothing written." if preview else
         f"{verb} {', '.join(canonical)}; the manifest and {'the lock' if len(generated) == 1 else 'its locks'} are updated."),
        f"Required: {' '.join(candidate.requirements()) or 'none'}",
        f"Offered: {' '.join(candidate.optional) or 'none'}",
    ]
    if not preview:
        lines.extend(_refresh_own_checkout(root, candidate_manifest))
    return "\n".join(lines)


def edit_capabilities(start: Path, change: str, names: Sequence[str], *, because: str | None = None,
                      preview: bool = False, allow_unverified: bool = False) -> str:
    """Edit capability declarations in the owner's input order, retaining aliases and minimums."""
    return _policy_edit(start, change=change, names=names, because=because, preview=preview,
                        allow_unverified=allow_unverified, native=True)


def _refresh_own_checkout(root: Path, manifest: Mapping[str, Any]) -> list[str]:
    """Re-derive the owner's own resolution after a lock change, so ``run`` works at once.

    Only a registered checkout is touched, and only when nothing is pending;
    otherwise the pending decisions are named, as ``config show`` names them.
    """
    from .storage import find_checkout_record
    from .operations import resolve_checkout
    if find_checkout_record(manifest, root) is None:
        return []
    try:
        report = resolve_checkout(root)
    except ProjectConfigurationError as exc:
        first = str(exc).splitlines()[0]
        return [f"Your checkout is not ready to run yet: {first}", "Review with 'devcapsule project config show'."]
    return [report.render()]


def require_tools(start: Path, names: Sequence[str], *, because: str | None = None,
                  preview: bool = False, allow_unverified: bool = False) -> str:
    """Make ``names`` required tools of the project, with an optional reason; regenerate the locks."""
    return _policy_edit(start, change="require", names=names, because=because, preview=preview, allow_unverified=allow_unverified)


def offer_tools(start: Path, names: Sequence[str], *, because: str | None = None,
                preview: bool = False, allow_unverified: bool = False) -> str:
    """Make ``names`` offered (optional) tools of the project; a developer may omit them."""
    return _policy_edit(start, change="offer", names=names, because=because, preview=preview, allow_unverified=allow_unverified)


def drop_tools(start: Path, names: Sequence[str], *, preview: bool = False, allow_unverified: bool = False) -> str:
    """Remove ``names`` from the project's required and offered tools, with their minimum versions."""
    return _policy_edit(start, change="drop", names=names, because=None, preview=preview, allow_unverified=allow_unverified)


def _environment_edit(start: Path, *, change: str, names: Sequence[str], because: str | None, preview: bool) -> str:
    root, manifest, _locks, _matrix = _project(start)
    environment = deepcopy(manifest.get("environment", {}))
    required, optional = environment.get("required", {}), environment.get("optional", {})
    canonical = tuple(environment_name(name, field_name="environment variable") for name in names)
    if change == "drop":
        unknown = sorted(set(canonical) - set(required) - set(optional))
        if unknown:
            raise ProjectConfigurationError("Not declared by this project: " + ", ".join(unknown) + "; nothing changed.")
        for name in canonical:
            required.pop(name, None)
            optional.pop(name, None)
    else:
        target, other = (required, optional) if change == "require" else (optional, required)
        for name in canonical:
            entry = other.pop(name, target.get(name, {}))
            if because is not None:
                entry["reason"] = because
            target[name] = entry
    candidate_manifest = deepcopy(manifest)
    candidate_manifest.pop("environment", None)
    document = {scope: dict(sorted(entries.items())) for scope, entries in
                (("required", required), ("optional", optional)) if entries}
    if document:
        candidate_manifest["environment"] = document
    candidate = EnvironmentPolicy.read(candidate_manifest)
    if not preview:
        promote(root, candidate_manifest)
    verb = {"require": "Required", "offer": "Offered", "drop": "Dropped"}[change]
    lines = [("Preview; nothing written." if preview else f"{verb} environment {', '.join(canonical)}; the manifest is updated.")]
    for scope, entries in (("Required environment", candidate.required), ("Offered environment", candidate.optional)):
        rendered = ", ".join(f"{name} ({reason})" if reason else name for name, reason in entries.items()) or "none"
        lines.append(f"{scope}: {rendered}")
    lines.append("Values belong to each developer; this command stores declarations only.")
    return "\n".join(lines)


def require_environment(start: Path, names: Sequence[str], *, because: str | None = None, preview: bool = False) -> str:
    """Declare environment variables every developer must supply, with the owner's reason."""
    return _environment_edit(start, change="require", names=names, because=because, preview=preview)


def offer_environment(start: Path, names: Sequence[str], *, because: str | None = None, preview: bool = False) -> str:
    """Declare environment variables a developer may supply, with the owner's reason."""
    return _environment_edit(start, change="offer", names=names, because=because, preview=preview)


def drop_environment(start: Path, names: Sequence[str], *, preview: bool = False) -> str:
    """Remove environment declarations from the project."""
    return _environment_edit(start, change="drop", names=names, because=None, preview=preview)


HOST_RECOMMENDATION_NODES = tuple(CURATED_HOST_RECOMMENDATIONS)


def recommend(start: Path, name: str, value: str, *, because: str | None = None, preview: bool = False) -> str:
    """Record, change or remove one project recommendation.

    ``name`` is ``ide``, ``memory`` or ``cpus`` (an ordinary recommendation,
    applied by the launcher as the default and disclosed) or a curated host
    access (``network``, ``docker-daemon``, ``development-sudo``,
    ``host-browser``), which the developer is asked about with the reason.
    ``value`` is the recommended value, or ``none`` to remove the
    recommendation. A host recommendation requires ``because``: the reason is
    what the developer reads when asked.
    """
    root, manifest, locks, matrix = _project(start, check_resolutions=False)
    candidate_manifest = deepcopy(manifest)
    removing = value.strip().lower() == "none"
    generated = None
    if name in RECOMMENDATION_NAMES:
        current = Recommendations.read(manifest)
        reasons = dict(current.reasons)
        fields: dict[str, Any] = {"ide": current.ide, "memory": current.memory, "cpus": current.cpus}
        if removing:
            if fields[name] is None:
                raise ProjectConfigurationError(f"The project recommends no {name}; nothing changed.")
            fields[name] = None
            reasons.pop(name, None)
            rendered = "none"
        else:
            fields[name] = _ordinary_recommendation_value(matrix, name, value)
            if because is not None:
                reasons[name] = because
            rendered = str(fields[name])
        candidate = Recommendations(fields["ide"], fields["memory"], fields["cpus"], reasons)
        candidate_manifest.pop("recommendations", None)
        document = candidate.document()
        if document:
            candidate_manifest["recommendations"] = document
        effect = {
            "ide": "a developer who has not chosen an IDE gets this one, and may choose another",
            "memory": "the capsule's memory limit unless the developer sets another",
            "cpus": "the capsule's CPU count unless the developer sets another",
        }[name]
    elif name in HOST_RECOMMENDATION_NODES:
        path, supported = CURATED_HOST_RECOMMENDATIONS[name]
        host = candidate_manifest.setdefault("host", {})
        if removing:
            if _host_recommendation(host, path) is None:
                raise ProjectConfigurationError(f"The project recommends no {name}; nothing changed.")
            _remove_host_recommendation(host, path)
            rendered = "none"
        else:
            accepted = render_authorization_value(supported)
            if value.strip().lower() not in {accepted, "default"}:
                raise ProjectConfigurationError(
                    f"Recommendation {name!r} accepts exactly {accepted!r} (or 'none' to remove it); got {value!r}."
                )
            if not because:
                raise ProjectConfigurationError(
                    f"A host access recommendation needs the reason the developer will read: "
                    f"--because \"...\" with 'recommend {name} {accepted}'."
                )
            node = host
            for key in path:
                node = node.setdefault(key, {})
            node["value"] = supported
            node["justification"] = because
            rendered = accepted
        if not candidate_manifest["host"]:
            del candidate_manifest["host"]
        effect = "every developer is asked, with your reason; a recommendation grants nothing"
    else:
        if because is not None:
            raise ProjectConfigurationError("A resolution recommendation takes no --because; give the capability requirement a reason instead.")
        resolutions = resolution_recommendations(manifest)
        try:
            capability = name if removing and name in resolutions else matrix.canonical_name(name)
        except ProjectConfigurationError:
            raise ProjectConfigurationError(f"Unknown recommendation {name!r}; name a capability, IDE, resource or host access.") from None
        if removing:
            if capability not in resolutions:
                raise ProjectConfigurationError(f"The project recommends no resolution for {capability}; nothing changed.")
            del resolutions[capability]
            rendered = "none"
        else:
            minimums = {matrix.canonical_name(key): minimum for key, minimum in CapabilityPolicy.read(manifest).minimums}
            matrix.resolve_provider(capability, minimums.get(capability), recommended=value)
            resolutions[capability] = value
            rendered = value
        capabilities = candidate_manifest["capabilities"]
        capabilities.pop("resolution", None)
        if resolutions:
            capabilities["resolution"] = resolutions
        generated = regenerate_locks(CapabilityPolicy.read(candidate_manifest), locks, recommendations=resolutions)
        effect = "the provider default; acquisition still needs the developer's trust or consent"
    _validate(candidate_manifest)
    for lock in (generated if generated is not None else locks).values():
        check_documents(candidate_manifest, lock)
    if not preview:
        promote(root, candidate_manifest, generated)
    head = "Preview; nothing written." if preview else (
        f"Recommendation removed: {name}." if removing else f"Recommended {name} = {rendered}: {effect}."
    )
    if preview:
        from .manifest_document import render_manifest
        head += "\n" + render_manifest(candidate_manifest)
    return head


def _ordinary_recommendation_value(matrix: ResolutionMatrix, name: str, value: str) -> str | int:
    if name == "ide":
        candidate = value.strip()
        surfaces = list(matrix.ide_capabilities())
        by_component = {matrix.resolve_provider(capability): capability for capability in surfaces}
        if candidate in by_component:
            candidate = by_component[candidate]
        if candidate not in surfaces:
            raise ProjectConfigurationError(
                f"Unknown IDE {value!r}; this launcher knows: " + ", ".join(surfaces) + "."
            )
        return candidate
    if name == "memory":
        return normalize_memory_size(value, field_name="recommendation memory")
    if not value.strip().isdecimal() or int(value) < 1:
        raise ProjectConfigurationError(f"Recommendation cpus takes a positive integer; got {value!r}.")
    return int(value)


def _host_recommendation(host: Mapping[str, Any], path: tuple[str, ...]) -> Mapping[str, Any] | None:
    node: Any = host
    for key in path:
        if not isinstance(node, Mapping) or key not in node:
            return None
        node = node[key]
    return node if isinstance(node, Mapping) else None


def _remove_host_recommendation(host: dict[str, Any], path: tuple[str, ...]) -> None:
    parents: list[dict[str, Any]] = [host]
    node: dict[str, Any] = host
    for key in path:
        node = node[key]
        parents.append(node)
    for index in range(len(path) - 1, -1, -1):
        parent = parents[index]
        child = parent[path[index]]
        if index == len(path) - 1 or not child:
            del parent[path[index]]
        else:
            break


def _validate(manifest: dict[str, Any]) -> None:
    from .manifest_schemas import ManifestV2
    ManifestV2.read(manifest, Path("manifest"))
    from .authorization import authorization_declarations
    authorization_declarations(manifest, {})


def declare_source(start: Path, path: str, *, upstream: str | None = None, java: str | None = None,
                   preview: bool = False) -> str:
    """Declare, or redeclare, one wrapped source under ``[sources."<path>"]``; the manifest alone changes.

    ``path`` is the submodule's path in the wrapper. ``upstream`` is the
    upstream's URL when the submodule's origin is the developer's fork, else
    ``None``. ``java`` is the Java line the source builds with, or ``None``
    when the source does not build with Java. A second declaration of the
    same path replaces its known keys and keeps any key this launcher does
    not know. The lock is untouched: a source adds no capability by itself;
    ``require_tools`` does that, and ``project wrap`` calls both.
    """
    root, manifest, locks, _matrix = _project(start, check_resolutions=False)
    path = source_path(path, field_name="source path")
    if upstream is not None and (not isinstance(upstream, str) or not upstream.strip() or has_control_characters(upstream)):
        raise ProjectConfigurationError("The upstream is the upstream repository's URL, on one line; it cannot be blank.")
    if java is not None:
        java = java_line(java, field_name="java line")
    previous = deepcopy(manifest.get("sources", {}))
    declared = WrappedSources.read(manifest)
    entries = [source for source in declared.entries if source.path != path]
    entries.append(WrappedSource(path, upstream, java))
    candidate = WrappedSources(tuple(sorted(entries, key=lambda source: source.path)))
    candidate_manifest = deepcopy(manifest)
    candidate_manifest["sources"] = candidate.document(previous=previous)
    WrappedSources.read(candidate_manifest)
    for lock in locks.values():
        check_documents(candidate_manifest, lock, check_resolutions=False)
    if not preview:
        promote(root, candidate_manifest)
    verb = "Redeclared" if declared.get(path) is not None else "Declared"
    lines = ["Preview; nothing written." if preview else f"{verb} source {path}; the manifest is updated."]
    lines.append(f"  {path}: " + ("learn from it; the origin is the upstream and nothing is pushed" if upstream is None
                                   else f"change it in your fork of {upstream}; pull requests go to the fork")
                 + (f"; builds with Java {java}" if java is not None else ""))
    return "\n".join(lines)
