"""Promote and verify release documentation; never mutate a Git ref.

All paths belong to this script's checkout unless --root selects a scratch
copy. Malformed manifests are refused, not repaired. Only promote writes;
check and published collect all unmet obligations. Notes needs only notes.md.
"""
from __future__ import annotations

import argparse
from collections.abc import Callable
import json
from pathlib import Path
import re
import subprocess
import sys
import tomllib
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
VERSION = re.compile(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)")
STATUSES = {"development", "supported", "deprecated", "unsupported"}
HEADER = (
    "# The documentation versions the website publishes; contract version 1.\n"
    "# Authoritative on main. Promote on the release branch before the final tag\n"
    "# and demote the previous ones, per the release runbook.\n"
)


class ManifestLoader(yaml.SafeLoader):
    """Refuse duplicate fields instead of silently selecting the last value."""

    def construct_mapping(self, node: yaml.MappingNode, deep: bool = False) -> dict:
        keys: set[str] = set()
        for key_node, _ in node.value:
            key = self.construct_object(key_node, deep=deep)
            if not isinstance(key, str) or key in keys:
                raise ValueError(f"versions.yaml: invalid or duplicate field {key!r}")
            keys.add(key)
        return super().construct_mapping(node, deep=deep)


class Folded(str):
    """The manifest notice retains its folded block style."""


class ManifestDumper(yaml.SafeDumper):
    pass


ManifestDumper.add_representer(
    Folded, lambda dumper, value: dumper.represent_scalar("tag:yaml.org,2002:str", value, style=">")
)


def require_version(value: str) -> str:
    if not VERSION.fullmatch(value):
        raise ValueError(f"Expected X.Y.Z release version, got {value!r}")
    return value


def read_manifest(root: Path) -> dict[str, Any]:
    data = yaml.load((root / "docs/versions.yaml").read_text(encoding="utf-8"), Loader=ManifestLoader)
    if not isinstance(data, dict):
        raise ValueError("versions.yaml: expected a mapping")
    if type(data.get("contract")) is not int or data["contract"] != 1:
        raise ValueError("versions.yaml: contract must be 1")
    for key in ("current", "notice"):
        if not isinstance(data.get(key), str) or not data[key].strip():
            raise ValueError(f"versions.yaml: {key} must be nonempty text")
    require_version(data["current"])
    entries = data.get("versions")
    if not isinstance(entries, list) or not entries:
        raise ValueError("versions.yaml: versions must be a nonempty list")
    seen: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("versions.yaml: each version must be a mapping")
        for key in ("version", "source", "status"):
            if not isinstance(entry.get(key), str) or not entry[key].strip():
                raise ValueError(f"versions.yaml: entry requires nonempty {key}")
        version = entry["version"]
        if version in seen:
            raise ValueError(f"versions.yaml: duplicate version {version}")
        seen.add(version)
        if version != "devel":
            require_version(version)
        if entry["status"] not in STATUSES:
            raise ValueError(f"versions.yaml: {version} has invalid status {entry['status']!r}")
        # The contract lets a listed candidate be ``development`` too; only
        # ``devel`` must be, since it is the one entry that never releases.
        if version == "devel" and entry["status"] != "development":
            raise ValueError("versions.yaml: devel must have status development")
        if version == "devel" and entry["source"] != "main":
            raise ValueError("versions.yaml: devel source must be main")
        for key in ("note", "source-version"):
            if key in entry and (not isinstance(entry[key], str) or not entry[key].strip()):
                raise ValueError(f"versions.yaml: {version} requires nonempty {key}")
        if "legacy" in entry and type(entry["legacy"]) is not bool:
            raise ValueError(f"versions.yaml: {version} legacy must be boolean")
    if "devel" not in seen:
        raise ValueError("versions.yaml: missing devel entry")
    return data


def promote(root: Path, version: str, holds: list[str]) -> list[str]:
    require_version(version)
    data = read_manifest(root)
    entries = data["versions"]
    if any(entry["version"] == version for entry in entries):
        raise ValueError(f"{version} is already listed")
    project = tomllib.loads((root / "devcapsule-src/pyproject.toml").read_text(encoding="utf-8"))
    if project.get("project", {}).get("version") != version:
        raise ValueError(f"pyproject.toml must declare {version}; run promote on its release branch")
    unknown = set(holds) - {entry["version"] for entry in entries}
    if unknown:
        raise ValueError(f"Unknown --hold version(s): {', '.join(sorted(unknown))}")
    if sum(entry["status"] == "supported" for entry in entries) > 1:
        raise ValueError("versions.yaml: more than one supported version")
    moves = [f"current: {data['current']} -> {version}"]
    transitions = {"supported": "deprecated", "deprecated": "unsupported"}
    for entry in entries:
        old = entry["status"]
        if entry["version"] not in holds and old in transitions:
            entry["status"] = transitions[old]
            moves.append(f"{entry['version']}: {old} -> {entry['status']}")
    if any(entry["status"] == "supported" for entry in entries):
        raise ValueError("--hold would leave two supported versions")
    devel_index = next(i for i, entry in enumerate(entries) if entry["version"] == "devel")
    entries[devel_index]["source-version"] = version
    entries.insert(devel_index + 1, {"version": version, "source": f"docs-{version}", "status": "supported"})
    data["current"] = version
    data["notice"] = Folded(data["notice"])
    rendered = HEADER + yaml.dump(data, Dumper=ManifestDumper, sort_keys=False, allow_unicode=True)
    (root / "docs/versions.yaml").write_text(rendered, encoding="utf-8")
    return moves + [f"{version}: added supported (docs-{version})", f"devel source-version: {version}"]


# A template placeholder is angle-bracketed prose, wrapped across lines or
# not, but never across a paragraph break; a URL autolink is not one.
PLACEHOLDER = re.compile(r"<(?![A-Za-z][A-Za-z0-9+.-]*:)(?:[^<>\n]|\n(?!\n))*>")
FENCED_BLOCK = re.compile(r"^(`{3,}|~{3,}).*?^\1[ \t]*$", re.MULTILINE | re.DOTALL)
# A span opens with a run of backticks and closes with a run of the same length.
CODE_SPAN = re.compile(r"(?P<fence>`+)(?:(?!(?P=fence)).)*?(?P=fence)(?!`)", re.DOTALL)


def prose_of(markdown: str) -> str:
    """The text outside fenced code blocks and code spans, where a placeholder would be.

    Angle brackets inside code are commands as the adopter types them,
    ``--path <checkout>`` in the 0.2.14 notes among them, never a template
    placeholder.
    """
    return CODE_SPAN.sub("", FENCED_BLOCK.sub("", markdown))


def notes(root: Path, version: str) -> str:
    require_version(version)
    path = root / f"engineering-docs/releases/v{version}/notes.md"
    text = path.read_text(encoding="utf-8")
    if PLACEHOLDER.search(prose_of(text)):
        raise ValueError(f"{path}: contains a <...> placeholder")
    lines = text.splitlines(keepends=True)
    if lines and lines[0].strip() == "---":
        end = next((i for i in range(1, len(lines)) if lines[i].strip() in {"---", "..."}), None)
        if end is None:
            raise ValueError(f"{path}: unclosed front matter")
        text = "".join(lines[end + 1:])
    if not text.strip():
        raise ValueError(f"{path}: release body is empty")
    return text


def check(root: Path, version: str) -> list[str]:
    require_version(version)
    errors: list[str] = []
    try:
        data = read_manifest(root)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        errors.append(str(exc))
    else:
        if data["current"] != version:
            errors.append(f"current must be {version}")
        entry = next((item for item in data["versions"] if item["version"] == version), None)
        if entry is None:
            errors.append(f"Missing version {version}")
        else:
            if entry["status"] != "supported":
                errors.append(f"{version} status must be supported")
            if entry["source"] != f"docs-{version}":
                errors.append(f"{version} source must be docs-{version}")
        for item in data["versions"]:
            if item["version"] != version and item["status"] == "supported":
                errors.append(f"{item['version']} must not also be supported")
    try:
        notes(root, version)
    except (OSError, ValueError) as exc:
        errors.append(str(exc))
    return errors


def github_release(tag: str) -> dict:
    result = subprocess.run(
        ["gh", "release", "view", tag, "--json", "isDraft,isPrerelease,assets"],
        cwd=ROOT, text=True, capture_output=True, check=False,
    )
    if result.returncode:
        raise ValueError(result.stderr.strip() or f"gh release view {tag} failed")
    return json.loads(result.stdout)


def published(root: Path, release: Callable[[str], dict]) -> list[str]:
    errors = []
    for entry in read_manifest(root)["versions"]:
        if entry["status"] == "development":
            continue
        version = entry["version"]
        try:
            state = release(f"v{version}")
            reasons = []
            if state.get("isDraft") is not False:
                reasons.append("draft or missing isDraft")
            if state.get("isPrerelease") is not False:
                reasons.append("prerelease or missing isPrerelease")
            if not any(asset.get("name") == "devcapsule.pex" for asset in state.get("assets", [])):
                reasons.append("missing devcapsule.pex")
            if reasons:
                errors.append(f"{version}: no published download ({'; '.join(reasons)})")
        except (OSError, ValueError) as exc:
            errors.append(f"{version}: no published download ({exc})")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("promote", "check", "notes", "published"):
        command = commands.add_parser(name)
        command.add_argument("--root", type=Path, default=ROOT, help="checkout or scratch root")
        if name != "published":
            command.add_argument("version")
        if name == "promote":
            command.add_argument("--hold", action="append", default=[])
    args = parser.parse_args(argv)
    try:
        if args.command == "promote":
            print("\n".join(promote(args.root, args.version, args.hold)))
        elif args.command == "notes":
            print(notes(args.root, args.version), end="")
        else:
            errors = check(args.root, args.version) if args.command == "check" else published(args.root, github_release)
            if errors:
                print("\n".join(errors), file=sys.stderr)
                return 1
            print(f"{args.command}: documentation obligations satisfied")
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
