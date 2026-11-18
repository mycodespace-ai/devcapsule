"""Graphviz release discovery from a caller-supplied GitLab release reader.

Public operations: ``GraphvizDiscovery.check`` reports stable upstream
availability. The caller supplies the effect; parsing never acquires software.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from devcapsule.compat import CliError
from devcapsule.components.channels import ChannelReport, ChannelVersion
from devcapsule.components.discovery import exact_version

__all__ = ["GraphvizDiscovery", "SOURCE"]

SOURCE = "https://gitlab.com/api/v4/projects/4207231/releases/permalink/latest"


@dataclass(frozen=True)
class GraphvizDiscovery:
    """Read one official stable release through the supplied metadata reader."""

    read_release: Callable[[], Mapping[str, Any]]

    def check(self, current: str, platform: str) -> ChannelReport:
        """Report a newer stable release, without treating availability as support."""
        if platform not in {"linux-amd64", "linux-arm64"}:
            raise CliError(f"No Graphviz discovery adapter for {platform}.")
        try:
            release = self.read_release()
            latest = exact_version(release["tag_name"])
            installed = exact_version(current)
            if release.get("upcoming_release") is True:
                raise ValueError("upcoming Graphviz release is not stable")
            candidates = ((ChannelVersion(latest, "available"),)
                          if tuple(map(int, latest.split("."))) > tuple(map(int, installed.split("."))) else ())
            return ChannelReport(
                SOURCE,
                ChannelVersion(current, "available" if latest == current else "unknown",
                               "Upstream availability does not establish installed-version support."),
                candidates,
            )
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise CliError(f"Graphviz discovery unavailable at {SOURCE}: {exc}") from exc
