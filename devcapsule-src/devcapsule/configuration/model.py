"""Configuration admission and resolution as values, independent of CLI effects.

The representation boundary accepts decoded documents and exports a resolution
for persistence. Between those boundaries, callers inspect, resolve and admit
configuration values. Inputs and exported documents are owned copies: observing
or resolving a configuration cannot edit its inputs or another configuration.

Host-directory existence checks remain part of assessment. Docker/image identity
verification, persistence and launch belong to the operation adapters.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import tomllib
from typing import Any, Mapping

from devcapsule.components.catalog import INTERACTIVE_SURFACES

from .capabilities import RequirementDeparture
from .authorization import locked_base_reference
from .file_formats import ConfigurationFileKind, ProjectConfigurationError, canonical_digest, validate_file_format, table
from .freshness import stale_resolution_inputs
from .manifest import current_manifest
from .resolution import Resolution, render_resolution
from .review import ConfigurationReview, review_configuration


class Configuration:
    """An owned snapshot of project policy, platform selection and local decisions.

    Operations are observers: resolve returns a new plan, accept returns its
    stale-input set or refuses, and review returns an independently owned view.
    Editing and file identity/path selection remain separate adapter contracts.
    """

    def __init__(self, manifest: Mapping[str, Any], lock: Mapping[str, Any],
                 checkout: Mapping[str, Any], home: Mapping[str, Any] | None = None, *,
                 departures: tuple[RequirementDeparture, ...] = ()) -> None:
        # The manifest as given is the file's own schema; a checkpoint from
        # before scoped digests recorded its whole digest, kept for freshness.
        self._manifest = current_manifest(manifest, Path("manifest")).document()
        try:
            self._source_digest: str | None = canonical_digest(dict(manifest))
        except ProjectConfigurationError:
            self._source_digest = None
        self._lock = deepcopy(dict(lock))
        self._checkout = deepcopy(dict(checkout))
        self._home = deepcopy(dict(home or {}))
        # The launch's named departures from the project's contract; the
        # resolution says which requirement it set aside, so no record of
        # the launch claims the project was satisfied.
        self._departures = tuple(departures)
        validate_file_format(self._lock, ConfigurationFileKind.lock, "platform lock")
        validate_file_format(self._checkout, ConfigurationFileKind.checkout, "checkout")
        if "base" in self._lock:
            locked_base_reference(self._lock)
        identity = table(self._checkout, "project")
        if any(identity.get(key) != self._manifest["project"][key] for key in ("creator", "slug")):
            raise ProjectConfigurationError("Checkout does not match the project's creator and slug.")
        from .capabilities import CapabilityPolicy, LocalCapabilities
        policy = CapabilityPolicy.read(self._manifest).departing(self._departures)
        LocalCapabilities.read(self._checkout).validate(policy)
        if policy.minimums and table(self._checkout, "authorization", "base-image").get("image-id"):
            raise ProjectConfigurationError("A local base override cannot establish the project's minimum-version guarantee; select the pinned project base.")
        self._review = review_configuration(self._manifest, self._lock, self._checkout, self._home)

    def review(self) -> ConfigurationReview:
        return deepcopy(self._review)

    def resolve(self) -> Resolution:
        """Derive one complete plan, or refuse without changing the snapshot."""
        component = self._lock.get("components", {}).get("interactive-surface")
        image = self._lock.get("image", {}).get("reference")
        has_formation = "base" in self._lock and "materialization" in self._lock
        if component not in INTERACTIVE_SURFACES or (not image and not has_formation):
            raise ProjectConfigurationError(
                "Choose your IDE for this checkout with 'devcapsule project config ide IDE'; "
                "a known interactive surface and image/formation are required."
            )
        # require_ready is rendered by the file/CLI adapter with its actual path.
        return Resolution(tomllib.loads(render_resolution(
            self._manifest, self._lock, self._checkout, self._review, self._home, departures=self._departures,
        )))

    def stale_inputs(self, resolution: Resolution) -> tuple[str, ...]:
        return stale_resolution_inputs(self._manifest, self._lock, self._checkout, resolution.document(), self._home,
                                       source_digest=self._source_digest)

    def accept(self, resolution: Resolution, *, force: bool = False) -> tuple[str, ...]:
        """Admit a saved plan. Force waives freshness only, never validity.

        The result names waived inputs; an empty tuple means ordinary admission.
        A caller must use review().effective_host() for current permissions even
        when explicitly admitting an old plan with force.
        """
        stale = self.stale_inputs(resolution)
        if stale and not force:
            raise ProjectConfigurationError(
                f"Local resolution is stale ({', '.join(stale)}); run 'devcapsule project run'."
            )
        if not self._review.ready:
            raise ProjectConfigurationError("Cannot consume an incomplete configuration review.")
        if resolution.component != self._lock["components"]["interactive-surface"]:
            raise ProjectConfigurationError("Resolved surface differs from the lock; run 'devcapsule project run'.")
        if not stale and not resolution.same_meaning_as(self.resolve()):
            raise ProjectConfigurationError(
                "Generated resolution does not match its inputs; run 'devcapsule project run'."
            )
        return stale
