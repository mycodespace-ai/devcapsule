"""Checkout-local component upgrades and recovery through ordinary realization.

Only the atomic checkout selection is authority. Preview files, distribution
checks, prepared images and successful-use records are evidence/resources.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
import difflib
import hashlib
import json
from pathlib import Path
import shutil
import time
import tomllib
from typing import Any, Callable, Mapping, Sequence

from devcapsule.compat import CliError
from devcapsule.components.catalog import COMPONENTS, selected_component_definitions
from devcapsule.configuration.authorization import AuthorizationReview, authorization_declarations, authorized_base_selection, normalize_authorization_value
from devcapsule.configuration.file_formats import canonical_digest, render_toml, selected_version_lock
from devcapsule.configuration.model import Configuration
from devcapsule.configuration.capabilities import CapabilityPolicy, LocalCapabilities
from devcapsule.configuration.capability_selection import matrix_for, usable_lock
from devcapsule.configuration.trust import HomeTrust
from devcapsule.configuration.storage import (
    load_settings,
    ResolvedProject, activate_configuration, atomic_write, checkout_record_paths,
    load_checkout, load_toml, manifest_for, recommendation_lock_for, selection_for,
)
from devcapsule.environment_realization import RealizedEnvironment, realize_environment
from devcapsule.materialization import ArtifactSpec, acquire_artifact, cache_root, parse_locked_environment, sha256_file
from devcapsule.platforms import Platform, XdgHomes
from devcapsule import runtime_configuration
from devcapsule.build_info import current_build_info
from devcapsule.component_status import CompatibilityLookup


def home_trust() -> HomeTrust:
    """The home's trust record (D-0011), which answers the base for every checkout here."""
    return HomeTrust.read(load_settings())


@dataclass
class Workspace:
    root: Path
    manifest: dict[str, Any]
    lock_path: Path
    lock: dict[str, Any]
    input_path: Path
    output_path: Path
    checkout: dict[str, Any]
    composition: dict[str, Any]
    """The persistent selection ``lock`` is projected from; version sets are authored from it."""

    @classmethod
    def load(cls, start: Path) -> Workspace:
        root, manifest = manifest_for(start)
        lock_path, composition, lock = selection_for(root, manifest)
        input_path, output_path = checkout_record_paths(manifest, root)
        checkout = load_checkout(input_path, manifest, root)
        return cls(root, manifest, lock_path, lock, input_path, output_path, checkout, composition)

    @property
    def state(self) -> Path:
        return state_directory(self.root)

    @property
    def identity(self) -> str:
        return effective_set_id(self.lock, self.checkout)

    def recommendation(self) -> dict[str, Any]:
        return recommendation_lock_for(self.root, self.manifest)[1]


def state_directory(root: Path) -> Path:
    identity = hashlib.sha256(str(root.resolve()).encode()).hexdigest()
    return XdgHomes.from_environment().state / "version-sets" / identity


def set_id(lock: Mapping[str, Any], local_base_identity: str | None = None) -> str:
    # Exclude explanatory/history fields; include every executable and recipe input.
    inputs = {key: lock[key] for key in ("platform", "base", "components", "materialization") if key in lock}
    if local_base_identity is not None:
        inputs["local-base-identity"] = local_base_identity
    return canonical_digest(inputs)


def effective_set_id(lock: Mapping[str, Any], checkout: Mapping[str, Any]) -> str:
    base = checkout.get("authorization", {}).get("base-image", {})
    return set_id(lock, base.get("image-id") if isinstance(base, dict) else None)


def _specs(lock: Mapping[str, Any]) -> tuple[ArtifactSpec, ...]:
    locked = parse_locked_environment(lock)
    return (locked.artifact, *(ArtifactSpec(a.version, a.url, a.sha256, a.component_id) for a in locked.ancillary_artifacts))


def _retain(lock: Mapping[str, Any], state: Path, *, acquire: bool) -> None:
    """Retain exact downloads outside reclaimable cache; never delete a predecessor."""
    for spec in _specs(lock):
        retained = state / "artifacts" / "sha256" / spec.sha256
        if retained.is_file() and sha256_file(retained) == spec.sha256:
            continue
        cached = cache_root() / "artifacts" / "sha256" / spec.sha256
        if not cached.is_file() or sha256_file(cached) != spec.sha256:
            if not acquire:
                continue  # A retained canonical environment is also a recovery resource.
            cached = acquire_artifact(spec, cache_root()).path
        retained.parent.mkdir(parents=True, exist_ok=True)
        temporary = retained.with_suffix(".incoming")
        shutil.copyfile(cached, temporary)
        temporary.replace(retained)


def _restore_artifacts(lock: Mapping[str, Any], state: Path) -> list[str]:
    missing = []
    for spec in _specs(lock):
        cached = cache_root() / "artifacts" / "sha256" / spec.sha256
        retained = state / "artifacts" / "sha256" / spec.sha256
        if cached.is_file() and sha256_file(cached) == spec.sha256:
            continue
        if retained.is_file() and sha256_file(retained) == spec.sha256:
            cached.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(retained, cached)
        else:
            missing.append(spec.url)
    return missing


def _validation(lock: Mapping[str, Any], checkout: Mapping[str, Any]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    local_base = checkout.get("authorization", {}).get("base-image", {}).get("image-id")
    if local_base:
        missing = tuple(f"{name} {metadata.get('version')} on local base {local_base}"
                        for name, metadata in lock["components"].items() if isinstance(metadata, dict))
        return (), missing
    return matrix_for(lock).validation_evidence(lock)


INSPECTION_SCHEMA_VERSION = 1
"""Schema version of the ``versions show --json`` document.

The document is a stable contract: the capsule web console reads it. Adding
a key keeps the version; renaming, removing or retyping one bumps it.
"""


def _describe_set(identity: str, origin: str, lock: Mapping[str, Any], base: Any) -> dict[str, Any]:
    """One version set as the facts ``versions show`` prints about it."""
    return {
        "identity": identity, "origin": origin, "platform": lock.get("platform"), "base": base,
        "components": {name: metadata.get("version", "base supplied")
                       for name, metadata in lock["components"].items() if isinstance(metadata, dict)},
    }


def _render_set(described: Mapping[str, Any]) -> list[str]:
    lines = [f"Platform: {described['platform']}", f"Base: {described['base']}"]
    if described.get("local-base-override"):
        lines.append(f"Effective local base override: {described['local-base-override']} (project base above is a recommendation).")
    lines.extend(f"{name}: {version}" for name, version in described["components"].items())
    return lines


def inspection(start: Path) -> dict[str, Any]:
    """The facts behind ``versions show``, as one JSON-ready document.

    Outside a capsule the document describes the launcher's selection for the
    next launch. Inside a capsule it describes the running session from the
    launch context and, when readable, the selection for the next launch. Both
    carry ``schema-version`` and ``context`` so a reader can tell them apart.
    """
    runtime_context = runtime_configuration.for_project(start)
    if runtime_context is not None:
        return _runtime_inspection(runtime_context)
    workspace = Workspace.load(start)
    local = selected_version_lock(workspace.checkout) is not None
    base_answer = workspace.checkout.get("authorization", {}).get("base-image", {})
    override = base_answer.get("image-id") if isinstance(base_answer, dict) else None
    selected = _describe_set(workspace.identity, "local selection" if local else "project recommendation",
                             workspace.lock, workspace.lock.get("base", workspace.lock.get("image")))
    selected["local-base-override"] = override or None
    recommendation: dict[str, Any] | None = None
    if local:
        try:
            digest = canonical_digest(workspace.recommendation())
            diverged = digest != workspace.checkout["version-set"]["recommendation-digest"]
            recommendation = {"status": "changed" if diverged else "unchanged", "detail": None}
        except CliError as exc:
            recommendation = {"status": "unavailable", "detail": str(exc)}
    evidence, missing = _validation(workspace.lock, workspace.checkout)
    known = _known(workspace)
    return {
        "schema-version": INSPECTION_SCHEMA_VERSION, "context": "host selection (next launch)",
        "selected": selected, "project-recommendation": recommendation,
        "validation": {"evidence": list(evidence), "not-yet-validated": list(missing)},
        "local-use": {"zero-exit-launch-recorded": any(identity == workspace.identity for identity, _, _ in known)},
    }


def _runtime_inspection(context: runtime_configuration.RuntimeConfiguration) -> dict[str, Any]:
    running = context.document["running"]
    def base_of(lock: Mapping[str, Any], base: Mapping[str, Any]) -> Any:
        return base.get("image-id") or base.get("reference") or lock.get("base", lock.get("image"))
    document: dict[str, Any] = {
        "schema-version": INSPECTION_SCHEMA_VERSION, "context": "running capsule",
        "running": _describe_set(running["identity"], running["origin"], running["lock"],
                                 base_of(running["lock"], running["base"])),
        "next-launch": None, "selection-changed": None,
        "launcher-command": context.launcher_command(["versions", "show"]),
    }
    try:
        _, lock, checkout = context.current()
        identity = effective_set_id(lock, checkout)
        following = _describe_set(
            identity, "local selection" if selected_version_lock(checkout) else "project recommendation",
            lock, base_of(lock, checkout.get("authorization", {}).get("base-image", {})))
    except CliError as exc:
        # An unreadable next selection must not hide the immutable running set.
        document["next-launch-unavailable"] = str(exc)
        return document
    document["next-launch"] = following
    document["selection-changed"] = identity != running["identity"]
    return document


def inspection_json(start: Path) -> str:
    return json.dumps(inspection(start), indent=2, sort_keys=True)


def inspect(start: Path) -> str:
    """Render ``versions show`` from the same facts ``inspection`` reports."""
    document = inspection(start)
    if document["context"] == "running capsule":
        return _render_runtime_inspection(document)
    selected = document["selected"]
    lines = [f"Version set {selected['identity']}", f"Origin: {selected['origin']}"]
    lines.extend(_render_set(selected))
    recommendation = document["project-recommendation"]
    if recommendation is not None:
        if recommendation["status"] == "unavailable":
            lines.append(f"Project recommendation unavailable: {recommendation['detail']}; local selection remains intact.")
        else:
            lines.append("Project recommendation: " + (
                "changed since selection; local set remains intact. Inspect 'versions follow-project' or export a proposal."
                if recommendation["status"] == "changed" else "unchanged since selection"))
    lines.extend("DevCapsule validation: " + item for item in document["validation"]["evidence"])
    lines.extend("Not yet validated: " + item for item in document["validation"]["not-yet-validated"])
    lines.append("Local use: " + ("zero-exit launch recorded (not comprehensive validation)"
                                  if document["local-use"]["zero-exit-launch-recorded"] else "no successful launch recorded"))
    lines.append("Check distributions explicitly: devcapsule project versions check")
    return "\n".join(lines)


def _render_runtime_inspection(document: Mapping[str, Any]) -> str:
    running = document["running"]
    lines = ["Runtime context: configuration is mounted read-only.",
             f"Running session — version set {running['identity']}", f"Origin at launch: {running['origin']}",
             *_render_set(running)]
    following = document["next-launch"]
    if following is None:
        lines.extend(["", f"Next-launch selection unavailable: {document['next-launch-unavailable']}"])
    else:
        lines.extend(["", f"Selected for next launch — version set {following['identity']}",
                      f"Origin: {following['origin']}", *_render_set(following),
                      "Selection has changed; this running session remains on its launch-time version set."
                      if document["selection-changed"] else "Same software selection as this session."])
    lines.append("\nSuccessful-use history and launch readiness are owned by the launcher; this session is not yet certified successful.")
    lines.append("Inspect or change the selection outside this capsule: " + document["launcher-command"])
    return "\n".join(lines)


def check(start: Path) -> str:
    workspace = Workspace.load(start)
    path = workspace.state / "check.toml"
    previous = load_toml(path) if path.exists() else {}
    lines: list[str] = []
    candidates: list[str] = []
    notices: list[dict[str, Any]] = []
    successes: list[dict[str, Any]] = []
    compatibility = CompatibilityLookup(workspace.state / "compatibility-v1.json", current_build_info().version)
    interactive, ancillary = selected_component_definitions(workspace.lock)
    for definition in (interactive, *ancillary):
        channel = definition.discovery_channel()
        if channel is None:
            lines.append(f"{definition.id}: updates not checked — {definition.channel_omission_reason() or 'contributor must declare a channel or omission reason'}")
            continue
        version = str(workspace.lock["components"][definition.id]["version"])
        try:
            report = channel.check(version, str(workspace.lock["platform"]))
        except Exception as exc:
            # A shipped adapter can break on a new vendor schema. Contain that
            # optional discovery failure; interrupts still propagate normally.
            lines.append(f"{definition.id}: check unavailable — {exc}")
            lines.append(compatibility.explain(definition.id, definition.discovery_adapter_id(), str(workspace.lock["platform"])))
            prior = next((item for item in previous.get("successful-checks", [])
                          if item["component"] == definition.id and item["current"] == version
                          and item["platform"] == workspace.lock["platform"]), None)
            if prior:
                successes.append(prior)
                checked = datetime.fromtimestamp(prior["checked-at"], timezone.utc).isoformat()
                lines.append(f"  Last successful check: {checked} (historical, not current). {prior['report']}")
            # Failed refresh is not evidence that a previously reported issue
            # disappeared. Applicability and its original age remain explicit.
            notices.extend(item for item in previous.get("notices", [])
                           if item["component"] == definition.id and item["current"] == version
                           and item["platform"] == workspace.lock["platform"])
            continue
        lines.append(f"{definition.id} {version}: {report.current.status} {report.current.detail}; source: {report.source}")
        available = [item.version for item in report.candidates
                     if item.status == "available" and not item.notices and item.version != version]
        installable = definition.distribution_channel() is not None
        successes.append({"component": definition.id, "current": version, "platform": workspace.lock["platform"],
                          "checked-at": time.time(), "report": f"{report.current.status}; candidates: {', '.join(available) or 'none'}; source: {report.source}"})
        if not installable:
            lines.append(f"  Discovery only: {definition.channel_omission_reason()}")
        for notice in report.current.notices:
            lines.append(f"  Critical {notice.kind} notice: {notice.detail}")
            notices.append({"component": definition.id, "current": version, "platform": workspace.lock["platform"],
                            "identity": notice.identity, "kind": notice.kind, "detail": notice.detail,
                            "source": report.source, "checked-at": time.time(), "candidates": available if installable else []})
        for candidate in report.candidates:
            lines.append(f"  Candidate {candidate.version}: {candidate.status} {candidate.detail}; availability is not DevCapsule validation.")
            if candidate.status == "available" and installable:
                candidates.append(f"{definition.id}@{candidate.version}")
    atomic_write(path, render_toml({"checked-at": time.time(), "set": workspace.identity,
                                       "candidates": candidates, "notices": notices, "successful-checks": successes,
                                       "report": "\n".join(lines)}))
    return "\n".join(lines)


def launch_notices(start: Path, *, refresh: bool, report: Callable[[str], None] = print) -> list[dict[str, Any]]:
    """Best-effort daily discovery on interactive launch; offline cached fallback."""
    workspace = Workspace.load(start)
    path = workspace.state / "check.toml"
    saved = load_toml(path) if path.exists() else {}
    if refresh and (saved.get("set") != workspace.identity or time.time() - saved.get("checked-at", 0) >= 86400):
        report("Checking component channels for security or support notices…")
        result = check(start)
        if "check unavailable" in result:
            report(result)
        saved = load_toml(path)
    return [notice for notice in saved.get("notices", [])
            if notice["platform"] == workspace.lock["platform"]
            and workspace.lock["components"].get(notice["component"], {}).get("version") == notice["current"]
            and notice["kind"] in {"security", "end-of-support"}]


def notice_key(notice: Mapping[str, Any]) -> str:
    # A new advisory, revised explanation or new remedy deserves a new decision.
    return "critical-" + canonical_digest({key: value for key, value in notice.items() if key != "checked-at"})


def notice_decision(start: Path, notice: Mapping[str, Any], *, action: str | None = None) -> bool:
    """Return whether a notice is due; persist explicit choices only."""
    path = state_directory(start) / "reminders.toml"
    choices = load_toml(path) if path.exists() else {}
    key = notice_key(notice)
    if action is not None:
        choices[key] = -1 if action == "dismiss" else time.time() + 7 * 86400
        atomic_write(path, render_toml(choices))
    return choices.get(key, 0) != -1 and choices.get(key, 0) <= time.time()


def reminder(start: Path, *, action: str | None = None) -> str:
    workspace = Workspace.load(start)
    path = workspace.state / "check.toml"
    if not path.is_file():
        return "" if action is None else "No checked candidates. Run 'project versions check' first."
    report = load_toml(path)
    choices_path = workspace.state / "reminders.toml"
    choices = load_toml(choices_path) if choices_path.exists() else {}
    now = time.time()
    pending = []
    critical_candidates = {f"{notice['component']}@{version}" for notice in report.get("notices", [])
                           if workspace.lock.get("components", {}).get(notice["component"], {}).get("version") == notice["current"]
                           for version in notice["candidates"]}
    if action:
        for notice in report.get("notices", []):
            choices[notice_key(notice)] = -1 if action == "dismiss" else now + 7 * 86400
    for candidate in report.get("candidates", []):
        name, version = candidate.rsplit("@", 1)
        if workspace.lock.get("components", {}).get(name, {}).get("version") == version:
            continue
        if action:
            choices[candidate] = -1 if action == "dismiss" else now + 7 * 86400
        elif candidate not in critical_candidates and choices.get(candidate, 0) != -1 and choices.get(candidate, 0) <= now:
            pending.append(candidate)
            choices[candidate] = now + 7 * 86400
    atomic_write(choices_path, render_toml(choices))
    if action:
        return "Candidates dismissed until a different version is discovered." if action == "dismiss" else "Candidates deferred for seven days."
    if not pending:
        return ""
    return ("Previously checked component candidates: " + ", ".join(pending)
            + ". Metadata may be stale; run 'project versions check'. Use 'versions preview COMPONENT VERSION', 'versions dismiss', or 'versions defer'.")


def preview(start: Path, component: str, version: str, *, report: Callable[[str], None] = print) -> str:
    workspace = Workspace.load(start)
    definition = COMPONENTS.get(component)
    if definition is None or not isinstance(workspace.lock.get("components", {}).get(component), dict):
        raise CliError(f"{component!r} is not a selected component.")
    if component == workspace.lock["components"].get("interactive-surface"):
        raise CliError("IDE upgrades are outside this component-upgrade interface.")
    channel = definition.distribution_channel()
    if channel is None:
        raise CliError(f"{component}: {definition.channel_omission_reason() or 'no distribution channel declared'}")
    selection = channel.select(version, str(workspace.lock["platform"]))
    matrix = matrix_for(workspace.lock)
    if workspace.lock["platform"] not in selection.platforms:
        raise CliError("Candidate does not support the selected platform.")
    if selection.base_families and matrix.base_family(workspace.lock) not in selection.base_families:
        raise CliError("Candidate requires another base family; base upgrades need a separate reviewed change.")
    for dependency, required in selection.requires:
        actual = workspace.lock["components"].get(dependency, {}).get("version")
        if actual != required:
            raise CliError(f"Candidate requires {dependency} {required}; current version is {actual}. Preview/select that dependency explicitly first.")
    # The candidate is the whole persistent selection, so pins that a local
    # omission merely hides survive; checks run on what would actually execute.
    candidate = deepcopy(workspace.composition)
    candidate["components"][component] = deepcopy(dict(selection.metadata))
    # Check structural install contracts without downloading payloads. Published
    # SHA-512 identities are already exact; preparation additionally pins SHA-256.
    structural = _projection(workspace, candidate)
    _placeholder_hashes(structural)
    parse_locked_environment(structural)
    evidence, missing = _validation(_projection(workspace, candidate), workspace.checkout)
    if missing:
        candidate["unverified-combinations"] = "; ".join(missing)
    else:
        candidate.pop("unverified-combinations", None)
    # "from" is the execution identity; "selection" fingerprints the whole
    # composition the candidate replaces, including pins an omission hides.
    proposal = {"format": 1, "from": workspace.identity, "selection": canonical_digest(workspace.composition),
                "lock": render_toml(candidate), "component": component, "evidence": list(evidence), "unvalidated": list(missing)}
    identity = canonical_digest(proposal)
    atomic_write(workspace.state / "previews" / f"{identity}.toml", render_toml(proposal))
    report(f"Preview {identity}\n{component}: {workspace.lock['components'][component]['version']} -> {selection.metadata['version']}")
    report(_diff(workspace.composition, candidate))
    report(f"Distribution status: {selection.status} {selection.detail}; this is not validation evidence.")
    report(f"Base: {candidate['base']['reference']}; platform: {candidate['platform']}.")
    report("Other component versions and base are preserved. Dependencies: " + (str(selection.requires) if selection.requires else "no companion change declared"))
    for line in evidence:
        report("DevCapsule evidence: " + line)
    for line in missing:
        report("Not yet validated: " + line)
    for url in _download_urls(candidate["components"][component]):
        report("Required artifact (unless cached): " + url)
    report("Preparation downloads and builds before selecting for the next ordinary launch; current sessions continue unchanged.")
    report("Recovery: " + ("known-good sets available via 'versions rollback'." if _known(workspace) else "no known-good predecessor yet; successfully run the current set first."))
    report(f"Choose explicitly: devcapsule project versions select {identity}" + (" --unvalidated" if missing else ""))
    return identity


def _projection(workspace: Workspace, lock: Mapping[str, Any], checkout: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """The execution view of a persistent selection under the checkout's local choices."""
    local = LocalCapabilities.read(workspace.checkout if checkout is None else checkout)
    return usable_lock(CapabilityPolicy.read(workspace.manifest), lock, local)[0]


def _placeholder_hashes(value: dict[str, Any]) -> None:
    if "integrity" in value and "sha256" not in value:
        value["sha256"] = "0" * 64
    for item in value.values():
        if isinstance(item, dict):
            _placeholder_hashes(item)


def _download_urls(value: Mapping[str, Any]) -> list[str]:
    result = [str(value["url"])] if "url" in value else []
    for item in value.values():
        if isinstance(item, dict):
            result.extend(_download_urls(item))
    return result


def _pin_artifacts(value: dict[str, Any]) -> None:
    if "integrity" in value and "sha256" not in value:
        acquired = acquire_artifact(ArtifactSpec("channel", value["url"], "", integrity=value["integrity"]), cache_root())
        digest = sha256_file(acquired.path)
        destination = cache_root() / "artifacts" / "sha256" / digest
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(acquired.path, destination)
        value["sha256"] = digest
    for item in value.values():
        if isinstance(item, dict):
            _pin_artifacts(item)


def _pin_active_artifacts(workspace: Workspace, lock: dict[str, Any]) -> None:
    """Pin SHA-256 identities for the components that would execute, in place.

    The projection is pinned and its component entries are written back into
    ``lock``; omitted or unsupported entries are neither downloaded nor changed.
    """
    active = _projection(workspace, lock)
    _pin_artifacts(active)
    for name, metadata in active["components"].items():
        if isinstance(metadata, dict):
            lock["components"][name] = metadata


def _selection(workspace: Workspace, lock: dict[str, Any], *, follow: bool = False,
               base: Mapping[str, Any] | None = None,
               acquisitions: Sequence[tuple[str, str]] = (),
               authorize: Callable[[AuthorizationReview], bool] | None = None) -> ResolvedProject:
    checkout = deepcopy(workspace.checkout)
    if follow:
        checkout.pop("version-set", None)
    else:
        existing = checkout.get("version-set")
        digest = existing["recommendation-digest"] if existing else canonical_digest(workspace.recommendation())
        checkout["version-set"] = {"format": 1, "lock": render_toml(lock), "recommendation-digest": digest}
    lock = _projection(workspace, lock, checkout)
    declarations = authorization_declarations(workspace.manifest, lock)
    seen: set[str] = set()
    for name, value in acquisitions:
        declaration = declarations.get(name)
        if declaration is None or declaration.kind != "acquisition" or name in seen:
            raise CliError(f"{name!r} must name one candidate acquisition decision exactly once; host permissions use 'project config authorize'.")
        seen.add(name)
        checkout.setdefault("authorization", {})[name] = {
            "value": normalize_authorization_value(declaration, value),
            "recommendation-digest": declaration.recommendation_digest,
        }
    # Explicit software selection renews ONLY base/formation trust. Current
    # host grants, denials, directory and secret bindings are never replayed.
    # Existing vendor consent is required; changed license questions must be
    # answered via the ordinary authorize interface, not inferred here.
    if follow:
        reference, image_id = str(lock["base"]["reference"]), None
    elif base:
        reference, image_id = str(base["reference"]), base.get("image-id")
    else:
        prior_base = authorized_base_selection(workspace.lock, workspace.checkout, trust=home_trust())
        if prior_base is None:
            raise CliError("Authorize a base before selecting a version set.")
        reference, image_id = prior_base.reference, prior_base.local_image_identity
    answer: dict[str, Any] = {"reference": reference, "lock-digest": declarations["base-image"].recommendation_digest}
    if image_id:
        answer["reference"] = image_id
        answer["image-id"] = image_id
    checkout.setdefault("authorization", {})["base-image"] = answer
    config = Configuration(workspace.manifest, lock, checkout, load_settings())
    review = config.review()
    pending_acquisitions = [item for item in review.authorizations
                            if item.problem and declarations[item.name].kind == "acquisition"]
    if pending_acquisitions and authorize is not None:
        for item in pending_acquisitions:
            if not authorize(item):
                raise CliError("Candidate acquisition declined; the current selection is unchanged.")
            checkout.setdefault("authorization", {})[item.name] = {
                "value": True, "recommendation-digest": declarations[item.name].recommendation_digest,
            }
        config = Configuration(workspace.manifest, lock, checkout, load_settings())
        review = config.review()
        pending_acquisitions = []
    if pending_acquisitions:
        options = " ".join(f"--authorize {item.name} true" for item in pending_acquisitions)
        raise CliError(review.render(workspace.root) + "\nTo accept these acquisitions for the target set, repeat this version-set command with "
                       + options + ". Otherwise the current selection stays intact; no consent is inferred.")
    review.require_ready(workspace.root)
    resolution = config.resolve().document()
    return ResolvedProject(workspace.root, workspace.manifest, workspace.lock_path, lock,
                           workspace.input_path, checkout, workspace.output_path, resolution)


def _prepare_activate(workspace: Workspace, selected: ResolvedProject, report: Callable[[str], None]) -> None:
    report("Preparing exact version set; the current choice remains active until preparation succeeds.")
    realize_environment(selected, report=report)
    _retain(selected.lock, workspace.state, acquire=False)
    activate_configuration(selected.checkout_path, selected.checkout, selected.resolution)
    report(f"Selected {effective_set_id(selected.lock, selected.checkout)} for the next ordinary 'project run'. Existing sessions are unchanged.")


def select(start: Path, preview_id: str, *, unvalidated: bool = False, acquisitions: Sequence[tuple[str, str]] = (),
           authorize: Callable[[AuthorizationReview], bool] | None = None, report: Callable[[str], None] = print) -> None:
    workspace = Workspace.load(start)
    _safe_id(preview_id)
    proposal = load_toml(workspace.state / "previews" / f"{preview_id}.toml")
    if canonical_digest(proposal) != preview_id or proposal.get("format") != 1:
        raise CliError("Preview identity changed; preview again.")
    if proposal["from"] != workspace.identity or proposal.get("selection") != canonical_digest(workspace.composition):
        raise CliError("Selection changed since preview; preview again against the current set.")
    if proposal["unvalidated"] and not unvalidated:
        raise CliError("This set has not been validated by DevCapsule. Select with --unvalidated to try it deliberately.")
    lock = tomllib.loads(proposal["lock"])
    # Consent, downloads and pinning concern only what would execute. Entries an
    # omission hides, or that this reader cannot interpret, are carried unchanged.
    structural = _projection(workspace, lock)
    _placeholder_hashes(structural)
    prepared = _selection(workspace, structural, acquisitions=acquisitions, authorize=authorize)
    declarations = authorization_declarations(workspace.manifest, prepared.lock)
    accepted = [(name, "true" if prepared.checkout["authorization"][name]["value"] else "false")
                for name, declaration in declarations.items() if declaration.kind == "acquisition"]
    _pin_active_artifacts(workspace, lock)
    selected = _selection(workspace, lock, acquisitions=accepted)
    _prepare_activate(workspace, selected, report)


def _safe_id(identity: str) -> None:
    if len(identity) != 64 or any(c not in "0123456789abcdef" for c in identity):
        raise CliError("Expected the full 64-character version-set or preview identity.")


def record_success(selected: ResolvedProject, realized: RealizedEnvironment | None) -> None:
    """Only called after exit zero with the immutable pre-launch snapshot."""
    if realized is None:
        return  # Earlier history remains readable; it lacks a reproducible set.
    state = state_directory(selected.root)
    _retain(selected.lock, state, acquire=False)
    base = authorized_base_selection(selected.lock, selected.checkout, trust=home_trust())
    assert base is not None
    record: dict[str, Any] = {"lock": render_toml(selected.lock), "last-success": time.time(),
                             "base": {"reference": base.reference}}
    if base.local_image_identity:
        record["base"]["image-id"] = base.local_image_identity
    atomic_write(state / "known-good" / f"{effective_set_id(selected.lock, selected.checkout)}.toml", render_toml(record))


def _known(workspace: Workspace) -> list[tuple[str, dict[str, Any], dict[str, Any]]]:
    result = []
    for path in (workspace.state / "known-good").glob("*.toml"):
        document = load_toml(path)
        try:
            lock = tomllib.loads(document["lock"])
            if not isinstance(document.get("base"), dict) or not isinstance(document.get("last-success"), (int, float)):
                raise ValueError("missing base or success timestamp")
        except (KeyError, TypeError, ValueError) as exc:
            raise CliError(f"Cannot interpret known-good record {path}: {exc}. Inspect the record; current selection is unchanged.") from exc
        if set_id(lock, document.get("base", {}).get("image-id")) != path.stem:
            raise CliError(f"Known-good record was modified: {path}. Inspect it before recovery.")
        # A checkout may run as two platforms; only this platform's sets are its history.
        if lock.get("platform") != workspace.lock.get("platform"):
            continue
        result.append((path.stem, lock, document))
    return sorted(result, key=lambda entry: entry[2]["last-success"], reverse=True)


def history(start: Path) -> str:
    workspace = Workspace.load(start)
    entries = _known(workspace)
    lines = [f"{identity}{' (selected)' if identity == workspace.identity else ''}: exit zero at "
             + datetime.fromtimestamp(record["last-success"], timezone.utc).isoformat()
             for identity, _, record in entries]
    return "\n".join(lines) or "No known-good version set yet. Successfully run the current set first. Earlier configuration-only snapshots are not operational rollback sets."


def rollback(start: Path, identity: str | None = None, *, reacquire: bool = False,
             acquisitions: Sequence[tuple[str, str]] = (), report: Callable[[str], None] = print) -> None:
    workspace = Workspace.load(start)
    if identity is not None:
        _safe_id(identity)
    chosen = next((entry for entry in _known(workspace) if entry[0] == identity), None) if identity else next(
        (entry for entry in _known(workspace) if entry[0] != workspace.identity), None)
    if chosen is None:
        raise CliError("No known-good predecessor matches. Successfully launch a set first; failed or prepared sets are not recovery choices.")
    _, lock, record = chosen
    selected = _selection(workspace, lock, base=record["base"], acquisitions=acquisitions)
    missing = _restore_artifacts(lock, workspace.state)
    # Reuse the ordinary materializer's full identity checks, including current
    # launcher bytes. With no recovery downloads, missing exact resources fail.
    if not reacquire:
        from devcapsule.environment_realization import required_local_image
        from devcapsule.materialization import formation_descriptor, canonical_image_name, verify_materialized_image
        from devcapsule.runtime_artifact import runtime_artifact
        base = authorized_base_selection(lock, selected.checkout, trust=home_trust())
        assert base is not None
        try:
            details = required_local_image(base.reference)
            parsed = parse_locked_environment(lock)
            descriptor = formation_descriptor(platform=parsed.platform, base_identity=details.identity,
                artifact=parsed.artifact, ancillary_artifacts=parsed.ancillary_artifacts,
                recipe_id=parsed.recipe_id, recipe_version=parsed.recipe_version,
                component_id=parsed.component_id,
                runtime_sha256=sha256_file(runtime_artifact(Platform.parse(parsed.platform))))
            if missing:
                name = canonical_image_name(descriptor, parsed.component_id)
                verify_materialized_image(required_local_image(name), descriptor=descriptor, canonical_name=name)
        except CliError as exc:
            raise CliError(f"Exact local rollback resources are missing: {exc}. Current choice retained. Retry with --reacquire to attempt the exact downloads; availability is not guaranteed.") from exc
    _prepare_activate(workspace, selected, report)
    report("Software selection restored using current host permissions and state bindings. Vendor state/schema migrations are not reversed.")


def follow_project(start: Path, *, apply: bool = False, acquisitions: Sequence[tuple[str, str]] = (), report: Callable[[str], None] = print) -> None:
    workspace = Workspace.load(start)
    from devcapsule.configuration.capability_selection import selected_lock
    personal = deepcopy(workspace.checkout)
    personal.pop("version-set", None)
    lock = selected_lock(workspace.manifest, workspace.recommendation(), personal)
    report("Project recommendation diff:\n" + _diff(workspace.lock, lock))
    report("Following the project removes the local selection, retains current personal state and host decisions, and prepares for the next launch.")
    if apply:
        _prepare_activate(workspace, _selection(workspace, lock, follow=True, acquisitions=acquisitions), report)
    else:
        report("Apply explicitly: devcapsule project versions follow-project --apply")


def _diff(before: Mapping[str, Any], after: Mapping[str, Any], path: str = "version-set.lock") -> str:
    return "".join(difflib.unified_diff(render_toml(before).splitlines(True), render_toml(after).splitlines(True),
                                        fromfile="a/" + path, tofile="b/" + path)) or "No software selection difference."


def proposal(start: Path, output: Path) -> str:
    workspace = Workspace.load(start)
    if not any(identity == workspace.identity for identity, _, _ in _known(workspace)):
        raise CliError("No successful use of this set is recorded. Run it successfully before preparing an upstream proposal.")
    if selected_version_lock(workspace.checkout) is None:
        raise CliError("This checkout already follows the project recommendation.")
    if output.exists():
        raise CliError(f"Refusing to overwrite {output}; choose a new proposal path.")
    path = workspace.lock_path.relative_to(workspace.root).as_posix()
    # Diff against actual bytes so 'git apply' works even with lock comments.
    patch = "".join(difflib.unified_diff(workspace.lock_path.read_text().splitlines(True),
                                         render_toml(workspace.lock).splitlines(True), fromfile="a/" + path, tofile="b/" + path))
    evidence = "# Local zero-exit launch only; not comprehensive DevCapsule validation.\n"
    base = workspace.checkout.get("authorization", {}).get("base-image", {})
    if base.get("image-id"):
        evidence += f"# Local success used base override {base['image-id']}; this run did not prove the proposed project base.\n"
    atomic_write(output, evidence + patch)
    return f"Reviewable proposal: {output}. Review the complete diff (including upstream divergence), then use git apply and your normal PR process. No project files or remote state were changed."
