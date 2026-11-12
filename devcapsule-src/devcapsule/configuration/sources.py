"""The wrapped sources a project declares: foreign repositories it holds as submodules.

A wrapper project (the wrapped-projects work order of 2026-11-02) keeps the
DevCapsule configuration in a small repository of the developer's own and
the foreign code as Git submodules of it.  The manifest names each wrapped
source under ``[sources."<path>"]``, keyed by the submodule's path, and holds
only what DevCapsule adds: the origin URL stays in ``.gitmodules``, where Git
keeps it true.

* ``upstream``, when present, says the submodule's origin is the developer's
  fork of that upstream: changes and pull requests go to the origin, the
  upstream is read-only.  Absent, the origin is the upstream itself and the
  intent is to learn; nothing is pushed anywhere.
* ``java`` names the Java line the source builds with, ``"17"``: the
  project-level requirement stays the capability, and this key says which
  line, because a requirement knows only ``NAME>=VERSION`` and a 25 would
  satisfy ``>=17`` while the source's build rejects it.

This module is pure: it validates and renders the table.  Whether a line is
installed in the capsule is the runtime's question, asked at launch.  A
launcher older than this field reads the table as an extension and carries
it, which is what R-CONFIG-001 asks of a new declaration.
"""

from __future__ import annotations

from dataclasses import dataclass
import posixpath
import re
from typing import Any, Mapping

from .file_formats import ProjectConfigurationError, table

__all__ = ["WrappedSource", "WrappedSources", "has_control_characters", "java_line", "source_path"]

# The keys this launcher knows in a source entry; others are tolerated and
# carried, so a newer owner's field does not make the manifest unreadable.
SOURCE_KEYS = frozenset({"upstream", "java"})

# A Java line is the feature release number, as the vendors name a JDK.
JAVA_LINE_PATTERN = re.compile(r"^[1-9][0-9]*$")


def has_control_characters(value: str) -> bool:
    """Whether the text carries a control character, which no path, URL or guidance line may."""
    return any(ord(character) < 0x20 or character == "\x7f" for character in value)


def source_path(value: object, *, field_name: str) -> str:
    """Validate a submodule path as the manifest keys it: relative, inside the wrapper, in POSIX form."""
    if not isinstance(value, str) or not value or "\\" in value or has_control_characters(value):
        raise ProjectConfigurationError(f"{field_name}: a source path is a relative POSIX path such as RobotCode2025Public; found {value!r}.")
    if value.startswith("/") or value != posixpath.normpath(value) or value == "." or value.split("/")[0] == "..":
        raise ProjectConfigurationError(f"{field_name}: a source path stays inside the wrapper and carries no '.' or '..' segments; found {value!r}.")
    return value


def java_line(value: object, *, field_name: str) -> str:
    """Validate a Java line as a feature release number such as ``"17"``."""
    if not isinstance(value, str) or JAVA_LINE_PATTERN.fullmatch(value) is None:
        raise ProjectConfigurationError(f"{field_name}: a Java line is the feature release number as a string, such as \"17\"; found {value!r}.")
    return value


@dataclass(frozen=True)
class WrappedSource:
    """One wrapped source as declared: its path, its upstream when the origin is a fork, its Java line."""

    path: str
    upstream: str | None = None
    java: str | None = None

    @property
    def intent(self) -> str:
        """What the developer means to do with the source, in the words the guidance uses."""
        return "change it in your fork; pull requests go to the fork's origin, never to the upstream" if self.upstream else "learn from it; it is read-only, nothing is pushed"

    def document(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        if self.upstream is not None:
            result["upstream"] = self.upstream
        if self.java is not None:
            result["java"] = self.java
        return result


@dataclass(frozen=True)
class WrappedSources:
    """The ``[sources]`` table, validated, sorted by path."""

    entries: tuple[WrappedSource, ...] = ()

    @classmethod
    def read(cls, manifest: Mapping[str, Any]) -> WrappedSources:
        """Read ``[sources."<path>"]`` entries; unknown keys inside an entry are tolerated."""
        sources = table(manifest, "sources")
        entries: list[WrappedSource] = []
        for key, entry in sources.items():
            field_name = f"sources.{key}"
            path = source_path(key, field_name=field_name)
            if not isinstance(entry, dict):
                raise ProjectConfigurationError(f"{field_name} must be a table with optional 'upstream' and 'java' keys.")
            upstream = entry.get("upstream")
            if upstream is not None and (not isinstance(upstream, str) or not upstream.strip() or has_control_characters(upstream)):
                raise ProjectConfigurationError(f"{field_name}.upstream must be the upstream repository's URL, on one line.")
            java = entry.get("java")
            if java is not None:
                java = java_line(java, field_name=f"{field_name}.java")
            entries.append(WrappedSource(path, upstream, java))
        return cls(tuple(sorted(entries, key=lambda source: source.path)))

    @property
    def paths(self) -> tuple[str, ...]:
        return tuple(source.path for source in self.entries)

    def get(self, path: str) -> WrappedSource | None:
        return next((source for source in self.entries if source.path == path), None)

    def java_lines(self) -> tuple[str, ...]:
        """The distinct Java lines the sources name, in order; one line means the capsule can select it for everyone."""
        return tuple(dict.fromkeys(source.java for source in self.entries if source.java is not None))

    def document(self, *, previous: Mapping[str, Any] | None = None) -> dict[str, Any]:
        """The ``[sources]`` table; unknown keys of ``previous`` entries survive an edit."""
        result: dict[str, Any] = {}
        for source in self.entries:
            carried = previous.get(source.path, {}) if previous else {}
            extra = {key: value for key, value in carried.items() if key not in SOURCE_KEYS} if isinstance(carried, dict) else {}
            result[source.path] = {**source.document(), **extra}
        return result
