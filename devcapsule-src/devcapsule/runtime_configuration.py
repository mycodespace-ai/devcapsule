"""Read-only configuration access for the project hosted by this runtime.

The launcher owns checkout records and recovery. A capsule receives their
containing directory read-only plus an immutable description of this launch.
Host paths are identities here, not paths to resolve in the container.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
import json
import os
from pathlib import Path
import shlex
from typing import Any, Mapping, Sequence

from devcapsule.configuration.file_formats import ConfigurationFileKind, ProjectConfigurationError, validate_file_format, render_toml, selected_version_lock
from devcapsule.configuration.storage import ResolvedProject, checkout_name_for, checkout_record_name, discover_project, load_toml, manifest_for, recommendation_lock_for


HOME_PATH = Path("/etc/devcapsule/home")

CONTEXT_PATH = Path("/etc/devcapsule/launch-context.json")
CONFIGURATION_PATH = Path("/etc/devcapsule/checkout")
CHANNEL_PATH = Path("/run/devcapsule-configuration")
"""The console's configuration channel, mounted writable for the run; :mod:`devcapsule.configuration.console_channel`."""


class CapsuleAccess(Enum):
    """How a ``project`` subcommand treats the capsule's own project.

    Inside a capsule the launcher's records are mounted read-only and the
    launch context names the capsule's project. The owner's rule of
    2026-10-01: every ``project`` subcommand finds that project from any
    working directory, even one outside the project tree such as ``/opt``;
    the read-only ones answer from the runtime context, the mutating ones
    name the launcher command to run outside. Two kinds of command act
    where they are invoked instead: ``init`` creates a project in the
    working directory, and ``list`` and ``recursive-e2e`` have no project to
    select. Every leaf of the ``project`` tree declares one of these; the
    group applies it before dispatch, after the subcommand is known.
    """

    INSPECTS = "inspects"
    """Selects the capsule's project and answers read-only."""
    MUTATES = "mutates"
    """Selects the capsule's project and is refused for it; the launcher runs it."""
    CREATES_HERE = "creates-here"
    """Never selects; refused when the working directory is the capsule's project."""
    INDEPENDENT = "independent"
    """Never selects, never refused: its own contract."""

    @property
    def selects_capsule_project(self) -> bool:
        return self in {CapsuleAccess.INSPECTS, CapsuleAccess.MUTATES}

    @property
    def needs_launcher(self) -> bool:
        return self in {CapsuleAccess.MUTATES, CapsuleAccess.CREATES_HERE}


@dataclass(frozen=True)
class LaunchConfiguration:
    directory: Path
    document: dict[str, Any]
    # The listing ``run`` computed for this launch, written into the channel
    # for the capsule's own ``config show``; absent for a legacy launch.
    listing: dict[str, Any] | None = None

    @classmethod
    def capture(cls, selected: ResolvedProject, identity: str, listing: dict[str, Any] | None = None) -> LaunchConfiguration:
        from devcapsule.project_information import configured_information

        from devcapsule.configuration.storage import config_root
        checkout_name = checkout_name_for(selected.manifest, selected.checkout_path)
        return cls(selected.checkout_path.parent, {
            "format": 1, "project": deepcopy(selected.manifest["project"]),
            "configuration-home": str(config_root().resolve()),
            "launcher-root": str(selected.root),
            "runtime-root": selected.resolution["runtime"]["project-mount"],
            "checkout-file": selected.checkout_path.name,
            # The mount hides whether this file came from the named directory.
            "checkout-name": checkout_name,
            "info": configured_information(
                selected.root, selected.manifest, selected.lock, selected.checkout,
                checkout_name=checkout_name),
            "running": {"identity": identity, "lock": deepcopy(selected.lock),
                        "origin": "local selection" if selected_version_lock(selected.checkout) else "project recommendation",
                        "base": deepcopy(selected.checkout.get("authorization", {}).get("base-image", {}))},
        }, listing)


@dataclass(frozen=True)
class RuntimeConfiguration:
    document: dict[str, Any]

    @property
    def root(self) -> Path:
        return Path(self.document["runtime-root"])

    @property
    def checkout_path(self) -> Path:
        return CONFIGURATION_PATH / self.document["checkout-file"]

    @property
    def checkout_name(self) -> str:
        """Use the launch context's name, or infer it from the mounted filename.

        Older contexts lack ``checkout-name``. Strip ``.checkout.toml`` from
        their filename, except that ``devcapsule.checkout.toml`` means
        ``default``. The mount hides whether that file was a named checkout
        called ``devcapsule``, so the fallback cannot distinguish the two.
        """
        name = self.document.get("checkout-name")
        return name if isinstance(name, str) else checkout_record_name(self.checkout_path)

    def launcher_command(self, arguments: Sequence[str]) -> str:
        return shlex.join(["devcapsule", "project", "--path", self.document["launcher-root"], *arguments])

    def current(self) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        """Read the next-launch selection without repair or host path validation."""
        root, manifest = manifest_for(self.root)
        identity = self.document["project"]
        if any(manifest["project"][key] != identity[key] for key in ("creator", "slug")):
            raise ProjectConfigurationError("Project identity changed since launch; inspect it with the launcher.")
        if self.checkout_path.with_suffix(".activation.toml").exists():
            raise ProjectConfigurationError("A launcher activation is in progress or needs recovery; retry after the launcher finishes. Runtime inspection never repairs host records.")
        checkout = load_toml(self.checkout_path)
        validate_file_format(checkout, ConfigurationFileKind.checkout, self.checkout_path)
        if checkout.get("checkout", {}).get("path") != self.document["launcher-root"]:
            raise ProjectConfigurationError("Mounted checkout record does not match this launch's checkout identity.")
        if any(checkout.get("project", {}).get(key) != identity[key] for key in ("creator", "slug")):
            raise ProjectConfigurationError("Mounted checkout record does not match this launch's project identity.")
        lock = selected_version_lock(checkout)
        if lock is None:
            _, lock = recommendation_lock_for(root, manifest)
        from .configuration.capability_selection import selected_lock
        return manifest, selected_lock(manifest, lock, checkout), checkout

    def _recorded_checkout(self) -> dict[str, Any]:
        """The mounted checkout record for the next launch, without the
        version-set selection, which ``versions show`` reports."""
        _, _, checkout = self.current()
        return {key: value for key, value in checkout.items() if key != "version-set"}

    def configuration_document(self) -> dict[str, Any]:
        """The ``config show --json`` document inside a capsule: schema
        version 1, the same facts as ``configuration_report`` prints.

        The record's host paths and permissions are the launcher's recorded
        choices, not observations of this session; ``rows`` are absent because
        the launcher's table is computed against the host, not here.
        """
        return {
            "schema-version": 1,
            "context": "running capsule (next launch, read-only)",
            "project": {key: self.document["project"][key] for key in ("creator", "slug")},
            "checkout": {"name": self.checkout_name,
                         "launcher-path": self.document["launcher-root"],
                         "runtime-path": self.document["runtime-root"],
                         "record": self._recorded_checkout()},
            "launcher-command": self.launcher_command(["config", "show"]),
        }

    def configuration_report(self) -> str:
        shown = self._recorded_checkout()
        return ("Runtime context: read-only launcher configuration for the next launch.\n"
                "Host paths and permissions below are recorded choices, not observations of this running session.\n"
                "Use 'devcapsule project versions show' for running and next-launch software.\n\n"
                + render_toml(shown)
                + "\nTo change configuration, use the launcher outside this capsule: "
                + self.launcher_command(["config", "show"]))


def capsule_project_root(start: Path) -> Path | None:
    """The capsule's project, when no project encloses ``start`` and this runtime names one.

    ``None`` outside a capsule, or when ``start`` lies inside a project, which
    is then the selected one: a project nested inside the capsule keeps its own
    identity and is launched from here. An older capsule without the mounted
    context raises the same diagnosis as inspection does.
    """
    try:
        discover_project(start)
        return None
    except ProjectConfigurationError:
        pass
    context = for_project(start, fallback=True)
    return None if context is None else context.root


def for_project(start: Path, *, fallback: bool = False) -> RuntimeConfiguration | None:
    """Runtime for its own project; still a launcher for separate nested projects."""
    discovered = True
    try:
        root = discover_project(start)
    except ProjectConfigurationError:
        discovered = False
        root = start.expanduser().resolve()
    # Older capsules have the project/name environment but no mounted context.
    # Do not pretend their project recommendation describes the running image.
    declared = os.environ.get("PROJECT_PATH") if os.environ.get("DEVCAPSULE_CONTAINER_NAME") else None
    if not CONTEXT_PATH.is_file():
        if declared and (root == Path(declared).resolve() or (fallback and not discovered)):
            raise ProjectConfigurationError(
                "This capsule has no launcher configuration mount. Relaunch this project from outside "
                "the capsule with the updated DevCapsule launcher, then retry. Its running versions "
                "cannot be inferred from the project recommendation."
            )
        return None
    try:
        document = json.loads(CONTEXT_PATH.read_text())
        if not isinstance(document, dict) or document.get("format") != 1:
            raise ValueError("unsupported launch context format")
        for key in ("launcher-root", "runtime-root"):
            if not isinstance(document.get(key), str) or not Path(document[key]).is_absolute():
                raise ValueError(f"{key} must be an absolute path")
        if root != Path(document["runtime-root"]).resolve() and not (fallback and not discovered):
            return None
        name = document.get("checkout-file")
        if not isinstance(name, str) or Path(name).name != name or not name.endswith(".checkout.toml"):
            raise ValueError("invalid checkout record name")
        if "checkout-name" in document:
            checkout_name = document["checkout-name"]
            if not isinstance(checkout_name, str) or not checkout_name or "/" in checkout_name or "\\" in checkout_name:
                raise ValueError("invalid checkout name")
        project, running = document["project"], document["running"]
        if not isinstance(project, dict) or not all(isinstance(project.get(key), str) for key in ("creator", "slug")):
            raise ValueError("missing project identity")
        if not isinstance(running, dict) or not isinstance(running.get("base"), dict):
            raise ValueError("missing running version set")
        if not isinstance(running.get("identity"), str) or running.get("origin") not in {"local selection", "project recommendation"}:
            raise ValueError("invalid running version-set identity/origin")
        validate_file_format(running["lock"], ConfigurationFileKind.lock, CONTEXT_PATH)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise ProjectConfigurationError(f"Cannot read runtime launch context: {exc}. Relaunch with the updated launcher.") from exc
    return RuntimeConfiguration(document)


def require_launcher(start: Path, arguments: Sequence[str]) -> None:
    context = for_project(start)
    if context is not None:
        raise ProjectConfigurationError(
            "This command needs launcher-owned configuration or state. Inside this capsule that "
            "configuration is read-only. Run outside the capsule: " + context.launcher_command(arguments)
        )


def mounted_settings_path(env: Mapping[str, str] | None = None) -> Path | None:
    """The launcher's settings as this capsule sees them: None outside a capsule or under a named home.

    The capsule's own home, its data, state and cache among them, stays in
    its own XDG directories; a launcher run inside the capsule writes there.
    Only the launcher's settings are mounted, read-only.
    """
    from devcapsule.platforms import XdgHomes
    if CONTEXT_PATH.is_file() and XdgHomes.from_environment(env).chosen_by != "DEVCAPSULE_CONFIG_HOME":
        return HOME_PATH / "settings.toml"
    return None
