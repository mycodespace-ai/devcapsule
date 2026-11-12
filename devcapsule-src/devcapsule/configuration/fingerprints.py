"""Source fingerprints for a generated configuration checkpoint."""

from __future__ import annotations
from typing import Any, Mapping

from .capabilities import CapabilityPolicy, LocalCapabilities
from .file_formats import canonical_digest, legacy_lock, table, ProjectConfigurationError
from .manifest import configuration_manifest
from .home import HomeDefaults


def resolution_source_digests(
    manifest: Mapping[str, Any], lock: Mapping[str, Any], checkout: Mapping[str, Any],
    home: Mapping[str, Any] | None = None, *, policy: CapabilityPolicy | None = None,
) -> dict[str, str]:
    """The exact source digests a fresh generated resolution must record.

    The home's defaults are an input of the derived plan since
    0.3.0 rc4; without any, the plan records ``absent`` for them, as every
    earlier plan does, so an older plan stays fresh on a home that
    has set no default. ``policy`` is the launch's view of the manifest's
    policy when a launch departs from a requirement; the baseline then
    covers what that launch required, and the departure is in the plan.
    """

    defaults = HomeDefaults.read(home or {}).values
    result = {
        "manifest": canonical_digest(configuration_manifest(manifest)),
        "platform-lock": canonical_digest(lock),
        "checkout-input": canonical_digest(checkout),
        "home-config": canonical_digest(defaults) if defaults else "absent",
    }

    if policy is None:
        policy = CapabilityPolicy.read(manifest)
    if not legacy_lock(lock):
        baseline_policy = CapabilityPolicy(policy.required, (), policy.minimums)
        local = LocalCapabilities.read(checkout)
        providers = table(lock, "capability-providers")
        required = (*policy.required, *local.selected)
        if any(capability not in providers for capability in required):
            raise ProjectConfigurationError("Capability provider evidence is incomplete; resolve the selection again.")
        keep = {component for capability in required for component in providers[capability]}
        baseline = dict(lock)
        components = table(lock, "components")
        baseline["components"] = {key: value for key, value in components.items()
                                  if key in keep or key == "interactive-surface" and value in keep}
        declaration = configuration_manifest(manifest)
        declaration["capabilities"] = baseline_policy.document()
        result["capability-baseline"] = canonical_digest({
            "manifest": declaration,
            "lock": {key: baseline[key] for key in ("platform", "base", "image", "components", "materialization") if key in baseline},
        })
    return result
