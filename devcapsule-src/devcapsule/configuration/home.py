"""The home's own configuration: defaults that apply to every project here.

The CLI UX redesign work order of 2026-10-24, answer 6: the launcher owns
the container's memory limit and CPU count. Each has a home default,
set once with ``home default NAME VALUE`` and kept in
the configuration home's ``settings.toml``; a project may recommend a
value, and a checkout may set its own. The precedence is the checkout's
answer, then the project's recommendation, then the home default,
then no limit at all.

This module is pure: it validates and renders the document. Reading and
writing the file belongs to :mod:`storage`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from .file_formats import ProjectConfigurationError, table
from .values import LAUNCHER_VALUE_NAMES, normalize_launcher_value

__all__ = ["HomeDefaults"]



@dataclass(frozen=True)
class HomeDefaults:
    """The launcher-owned values this home applies when neither a checkout nor a project says."""

    values: dict[str, str | int] = field(default_factory=dict)

    @classmethod
    def read(cls, document: Mapping[str, Any]) -> HomeDefaults:
        defaults = table(document, "defaults")
        unknown = sorted(set(defaults) - set(LAUNCHER_VALUE_NAMES))
        if unknown:
            raise ProjectConfigurationError(
                "The home configuration defaults " + ", ".join(unknown)
                + "; the launcher owns " + ", ".join(LAUNCHER_VALUE_NAMES) + "."
            )
        values = {name: normalize_launcher_value(name, defaults[name], field_name=f"home default {name}")
                  for name in LAUNCHER_VALUE_NAMES if name in defaults}
        return cls(values)

    def with_value(self, name: str, value: str | int | None) -> HomeDefaults:
        """A copy with ``name`` set, or removed when ``value`` is None."""
        values = dict(self.values)
        if value is None:
            values.pop(name, None)
        else:
            values[name] = normalize_launcher_value(name, value, field_name=f"home default {name}")
        return HomeDefaults(values)

    def document(self) -> dict[str, Any]:
        return {"defaults": dict(sorted(self.values.items()))}

