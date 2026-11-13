"""Conservative generic graphics defaults used by GUI capsules."""

from __future__ import annotations

from typing import Mapping

__all__ = ["DEFAULTS", "environment"]

DEFAULTS = {
    "NO_AT_BRIDGE": "1",
    "LIBGL_ALWAYS_SOFTWARE": "1",
    "MESA_LOADER_DRIVER_OVERRIDE": "llvmpipe",
    "LIBGL_DRI3_DISABLE": "1",
}


def environment(existing: Mapping[str, str]) -> dict[str, str]:
    return {key: existing.get(key, value) for key, value in DEFAULTS.items()}
