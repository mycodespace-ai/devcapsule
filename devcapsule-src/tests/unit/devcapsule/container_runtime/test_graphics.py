"""Unit tests of ``devcapsule/container_runtime/graphics.py``: the graphics defaults of a GUI capsule."""

from __future__ import annotations

from devcapsule.container_runtime.graphics import DEFAULTS, environment


def test_environment_is_the_defaults_for_a_process_that_sets_none() -> None:
    """With no graphics variable set, ``environment`` is every default: no accessibility bridge, software rendering through llvmpipe, no DRI3."""
    assert environment({}) == {
        "NO_AT_BRIDGE": "1",
        "LIBGL_ALWAYS_SOFTWARE": "1",
        "MESA_LOADER_DRIVER_OVERRIDE": "llvmpipe",
        "LIBGL_DRI3_DISABLE": "1",
    }


def test_environment_preserves_a_value_the_process_already_sets() -> None:
    """A graphics variable already set keeps its value; the others take their defaults."""
    result = environment({"LIBGL_ALWAYS_SOFTWARE": "0"})

    assert result["LIBGL_ALWAYS_SOFTWARE"] == "0"
    assert result["NO_AT_BRIDGE"] == DEFAULTS["NO_AT_BRIDGE"]


def test_environment_names_only_the_graphics_variables() -> None:
    """A variable that is no graphics default is not in the result."""
    assert "PATH" not in environment({"PATH": "/usr/bin"})
