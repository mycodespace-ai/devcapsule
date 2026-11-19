"""Launch-only terminal substitution. Public operations: validate_surface, runtime_lock."""
from copy import deepcopy
import tomllib
from typing import Any, Mapping

from devcapsule.resolution_matrix import ResolutionMatrix
from .file_formats import ProjectConfigurationError


def validate_surface(lock: Mapping[str, Any]) -> None:
    """Only a resolved VS Code selection supports this first host IDE slice."""
    surface = lock.get("components", {}).get("interactive-surface")
    if surface != "vscode":
        raise ProjectConfigurationError(f"host-ide currently supports vscode only; selected interactive-surface is {surface!r}.")


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
    if terminal.get("unverified-combinations"):
        result["unverified-combinations"] = terminal["unverified-combinations"]
    return result
