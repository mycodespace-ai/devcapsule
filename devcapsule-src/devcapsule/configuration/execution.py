"""File adapter that admits a selected checkout before execution effects."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .file_formats import ProjectConfigurationError
from .model import Configuration
from .resolution import Resolution
from .review import ConfigurationReview
from .storage import (
    ResolvedProject,
    checkout_record_paths,
    load_checkout,
    load_resolution,
    load_settings,
    lock_for,
    manifest_for,
)


def fresh_resolved_project(project: Path) -> ResolvedProject:
    """Load one checkout and require its generated resolution to be fresh."""

    return ExecutionConfiguration.load(project).project


@dataclass(frozen=True)
class ExecutionConfiguration:
    """The single admission boundary before any project execution effects."""
    project: ResolvedProject
    review: ConfigurationReview
    stale_inputs: tuple[str, ...]

    @classmethod
    def load(cls, start: Path, *, force: bool = False) -> ExecutionConfiguration:
        root, manifest = manifest_for(start)
        lock_path, lock = lock_for(root, manifest)
        input_path, output_path = checkout_record_paths(manifest, root)
        if not input_path.is_file() or not output_path.is_file():
            raise ProjectConfigurationError("Local resolution is missing; run 'devcapsule project run'.")
        checkout = load_checkout(input_path, manifest, root)
        resolution = load_resolution(output_path)
        configuration = Configuration(manifest, lock, checkout, load_settings())
        plan = Resolution(resolution)
        review = configuration.review()
        # Keep the complete, path-qualified recovery advice at the CLI boundary.
        if force or not configuration.stale_inputs(plan):
            review.require_ready(root)
        stale = configuration.stale_inputs(plan)
        # An optional-only shared change can be reconciled without waiving
        # freshness for required tools, host decisions or personal answers.
        # The baseline digest is present only in readers of this contract.
        if stale and set(stale) <= {"manifest", "platform-lock"} and review.ready:
            candidate = configuration.resolve()
            baseline = candidate.document()["sources"].get("capability-baseline")
            if baseline and baseline == resolution["sources"].get("capability-baseline"):
                plan = candidate
                resolution = candidate.document()
        stale = configuration.accept(plan, force=force)
        selected = ResolvedProject(root, manifest, lock_path, lock, input_path, checkout, output_path, resolution)
        return cls(selected, review, stale)
