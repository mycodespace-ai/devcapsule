"""Scheduled observation and static status generation; diagnoses stay authored."""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from typing import Any

from devcapsule.build_info import current_build_info
from devcapsule.components.catalog import COMPONENTS
from devcapsule.component_status import Advisory, StatusFeed, text_field


def generate(policy: dict[str, Any], previous: dict[str, Any], *, revision: str,
             now: datetime | None = None, probe: bool = True) -> dict[str, Any]:
    """The feed for ``policy``: its authored advisories, and the vendors' answers when ``probe`` holds.

    Without probing, nothing leaves the machine and the feed carries no observations; that is the
    snapshot ``scripts/build-pex.sh`` packages into a launcher as its last fallback.
    """
    now = now or datetime.now(timezone.utc)
    if policy.get("format") != 1 or not isinstance(policy.get("advisories"), list):
        raise ValueError("expected format-1 authored compatibility policy")
    for advisory in policy["advisories"]:
        Advisory.parse(advisory)
    probes = policy["probes"]
    if {probe["component"] for probe in probes} != set(COMPONENTS):
        raise ValueError("every catalog component needs a probe")
    observations: list[dict[str, Any]] = []
    keys = set()
    for row_probe in (probes if probe else []):
        name, platform, version = (text_field(row_probe[key]) for key in ("component", "platform", "version"))
        definition = COMPONENTS[name]
        adapter = definition.discovery_adapter_id()
        key = (name, adapter, platform, version)
        if key in keys:
            raise ValueError("duplicate probe")
        keys.add(key)
        old: dict[str, Any] = next((row for row in previous.get("observations", [])
                    if (row.get("component"), row.get("adapter"), row.get("platform"), row.get("current")) == key), {})
        row: dict[str, Any] = {"component": name, "adapter": adapter, "platform": platform, "current": version,
               "checked_at": now.isoformat()}
        try:
            channel = definition.discovery_channel()
            if channel is None:
                raise ValueError("no discovery adapter")
            report = channel.check(version, platform)
            row.update(result="ok", source=report.source, last_success_at=now.isoformat(), consecutive_failures=0,
                       candidates=[item.version for item in report.candidates], current_status=report.current.status,
                       detail=report.current.detail)
        except Exception as exc:
            # One broken adapter must not suppress other observations or the
            # maintained diagnoses. A failure count is evidence, not diagnosis.
            row.update(result="inconclusive", consecutive_failures=int(old.get("consecutive_failures", 0)) + 1,
                       error=type(exc).__name__, detail=str(exc)[:2000])
            if old.get("last_success_at"):
                row["last_success_at"] = old["last_success_at"]
        observations.append(row)
    feed = {"format": 1, "generated_at": now.isoformat(), "expires_at": (now + timedelta(days=3)).isoformat(),
            "source_revision": text_field(revision), "cli_version": current_build_info().version,
            "advisories": policy["advisories"], "observations": observations}
    StatusFeed.parse(feed)
    return feed


def _cell(value: Any) -> str:
    # Escape remote text as Markdown text, not links/HTML/terminal controls.
    text = " ".join(str(value).split())
    return "".join(char if char.isalnum() or char in " .:/@_-" else f"&#{ord(char)};" for char in text)


def render_page(feed: dict[str, Any]) -> str:
    lines = ["# DevCapsule component update status", "",
             f"Generated: {feed['generated_at']}. Valid until: {feed['expires_at']}.", "",
             "If that deadline has passed, this page is stale. Probe success only establishes that the named adapter could read metadata from this runner. "
             "It does not certify installed software, security coverage, installation, or every released CLI.", "",
             f"Source revision: `{feed['source_revision']}`. Probe CLI: `{feed['cli_version']}`.", "",
             "[Machine-readable compatibility contract v1](compatibility-v1.json)", "",
             "## Observations", "",
             "| Component / adapter | Platform / baseline | Result | Candidates | Last successful probe | Consecutive failures | Detail |",
             "|---|---|---|---|---|---|---|"]
    for row in feed["observations"]:
        cells = [row["component"] + " / " + row["adapter"], row["platform"] + " / " + row["current"], row["result"],
                 ", ".join(row.get("candidates", [])) or "—", row.get("last_success_at", "never"),
                 row["consecutive_failures"], row.get("detail", "")]
        lines.append("| " + " | ".join(_cell(cell) for cell in cells) + " |")
    lines.extend(["", "## Maintained diagnoses", "",
                  "A failed probe alone never creates an upgrade recommendation. Diagnoses below are reviewed separately and apply only to their named adapters, CLI versions and platforms.", ""])
    if not feed["advisories"]:
        lines.append("No maintained diagnoses. This does not establish that every client can check for updates.")
    for value in feed["advisories"]:
        item = Advisory.parse(value)
        expired = item.expires_at <= datetime.fromisoformat(feed["generated_at"])
        lines.extend([f"### {_cell(item.component)}: {_cell(item.status)}" + (" (review expired)" if expired else ""), "",
                      _cell(item.message), "",
                      f"Adapters: {_cell(', '.join(item.adapters))}; CLI versions: {_cell(', '.join(item.cli_versions))}; platforms: {_cell(', '.join(item.platforms))}.", "",
                      f"Reviewed: {item.reviewed_at.isoformat()}; expires: {item.expires_at.isoformat()}.", "",
                      f"[Issue and workarounds]({item.issue_url})", ""])
        if item.fixed_in:
            lines.extend([f"Released fix: DevCapsule {_cell(item.fixed_in)}. Updating the CLI restores discovery; it does not itself upgrade the component.", ""])
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--previous", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--without-probes", action="store_true",
                        help="Write the authored advisories only, asking no vendor; the launcher's built-in snapshot.")
    arguments = parser.parse_args()
    previous = json.loads(arguments.previous.read_text()) if arguments.previous and arguments.previous.exists() else {}
    feed = generate(json.loads(arguments.policy.read_text()), previous, revision=arguments.revision,
                    probe=not arguments.without_probes)
    arguments.output.mkdir(parents=True, exist_ok=True)
    (arguments.output / "compatibility-v1.json").write_text(json.dumps(feed, indent=2) + "\n")
    (arguments.output / "README.md").write_text(render_page(feed))
    for row in feed["observations"]:
        print(f"{row['component']}: {row['result']}")


if __name__ == "__main__":
    main()
