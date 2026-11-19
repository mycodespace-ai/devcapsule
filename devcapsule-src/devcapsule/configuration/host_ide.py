"""Launch-only terminal substitution.

Public operations: validate_surface, runtime_lock, split_surface_requested,
apply_host_ide_surface.
"""
from copy import deepcopy
from dataclasses import replace
import tomllib
from typing import Any, Mapping, Sequence

from devcapsule.resolution_matrix import MATRICES, ResolutionMatrix
from .authorization import authorization_declarations, host_ide_enabled, normalize_authorization_value
from .capability_selection import lock_platform
from .file_formats import ProjectConfigurationError
from .storage import ResolvedProject


def validate_surface(lock: Mapping[str, Any]) -> None:
    """Only a resolved VS Code selection supports this first host IDE slice."""
    surface = lock.get("components", {}).get("interactive-surface")
    if surface != "vscode":
        raise ProjectConfigurationError(f"host-ide currently supports vscode only; selected interactive-surface is {surface!r}.")


def _merge_unverified(existing: object, incoming: object) -> str | None:
    """Combine semicolon-separated experimental edge notes without losing or duplicating entries."""
    notes: list[str] = []
    for raw in (existing, incoming):
        if isinstance(raw, str):
            for entry in raw.split(";"):
                cleaned = entry.strip()
                if cleaned and cleaned not in notes:
                    notes.append(cleaned)
    return "; ".join(notes) if notes else None


def runtime_lock(lock: Mapping[str, Any], matrix: ResolutionMatrix, *, allow_unverified: bool = False) -> dict[str, Any]:
    """Replace only the container surface and its recipe, retaining the selected base and tools."""
    validate_surface(lock)
    terminal = tomllib.loads(matrix.resolve(["xfce4-terminal"], allow_unverified=allow_unverified).render_lock())
    if lock.get("platform") != terminal.get("platform") or matrix.base_family(lock) != matrix.base_family(terminal):
        raise ProjectConfigurationError("host-ide has no xfce4-terminal pin for this lock's platform and base family.")
    result = deepcopy(dict(lock))
    result["components"].pop("vscode")
    result["components"]["interactive-surface"] = "xfce4-terminal"
    result["components"]["xfce4-terminal"] = deepcopy(terminal["components"]["xfce4-terminal"])
    result["materialization"] = deepcopy(terminal["materialization"])
    merged = _merge_unverified(lock.get("unverified-combinations"), terminal.get("unverified-combinations"))
    if merged:
        result["unverified-combinations"] = merged
    return result


def split_surface_requested(
    manifest: Mapping[str, Any],
    lock: Mapping[str, Any],
    checkout: Mapping[str, Any],
    authorize_flags: Sequence[tuple[str, str]],
) -> bool:
    """Resolve whether a launch uses split host IDE mode before software-approval offers."""
    overrides = [value for name, value in authorize_flags if name == "host-ide"]
    if not overrides:
        return host_ide_enabled(checkout)
    declaration = authorization_declarations(manifest, lock).get("host-ide")
    if declaration is None:
        return False
    return bool(normalize_authorization_value(declaration, overrides[-1]))


def apply_host_ide_surface(selected: ResolvedProject, *, allow_unverified: bool = False) -> ResolvedProject:
    """Substitute xfce4-terminal into a resolved selection while retaining other components."""
    lock = runtime_lock(selected.lock, MATRICES[lock_platform(selected.lock)], allow_unverified=allow_unverified)
    resolved = deepcopy(selected.resolution)
    resolved["runtime"]["component"] = "xfce4-terminal"
    return replace(selected, lock=lock, resolution=resolved)
