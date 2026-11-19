"""Pure host IDE decisions: acquisition_plan, release_archive, profile, attach_command,
required_settings, merge_settings, needs_extension, headless, and readiness_commands.
Host observations and effects belong to commands._host_ide and the launcher entry point.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any, Mapping
from urllib.parse import quote, urlparse

from .compat import CliError
from .configuration.trust import Channel, HomeTrust
from .platforms import HostOs, XdgHomes

EXTENSION = "ms-vscode-remote.remote-containers"
TERMS = "https://code.visualstudio.com/license"


@dataclass(frozen=True)
class HostIdeInputs:
    homes: XdgHomes
    os: HostOs
    architecture: str
    wsl: bool
    path_code: str | None
    installed: tuple[Path, ...]
    trust: HomeTrust


@dataclass(frozen=True)
class AcquisitionPlan:
    code: str | None
    target: str | None
    metadata_url: str | None


@dataclass(frozen=True)
class Archive:
    version: str
    url: str
    sha256: str


@dataclass(frozen=True)
class Profile:
    user_data: Path
    extensions: Path

    def command(self, code: str) -> tuple[str, ...]:
        return (code, f"--user-data-dir={self.user_data}", f"--extensions-dir={self.extensions}")


def vscode_channel(origin: str = "https://vscode.download.prss.microsoft.com") -> Channel:
    """The existing Microsoft product trust, restricted to the requested HTTPS origin."""
    return Channel("vscode", "Microsoft", "Visual Studio Code", (origin,),
                   "the SHA-256 the launcher pins", TERMS, "vscode-download")


def _installed_version_key(path: Path, host_os: HostOs) -> tuple[tuple[int, ...], int, str, str]:
    """Order managed VS Code directories numerically so 1.10.0 beats 1.9.0."""
    relative_depth = len(code_relative_path(host_os).parts) - 1
    version_name = path.parents[relative_depth].name if relative_depth < len(path.parents) else path.name
    match = re.fullmatch(r"([0-9]+(?:\.[0-9]+)*)(?:[-+](.+))?", version_name)
    if match is None:
        return ((-1,), 0, "", version_name)
    numeric = tuple(int(part) for part in match.group(1).split("."))
    suffix = match.group(2)
    return (numeric, 1 if suffix is None else 0, suffix or "", version_name)


def acquisition_plan(inputs: HostIdeInputs, *, print_only: bool) -> AcquisitionPlan:
    """Prefer PATH, then a managed installation; never acquire a Linux IDE for WSL."""
    if inputs.path_code:
        return AcquisitionPlan(inputs.path_code, None, None)
    if inputs.wsl:
        raise CliError("host-ide on WSL2 needs Windows VS Code on PATH. Install VS Code on Windows, "
                       "enable its Add to PATH option, then reopen the WSL2 terminal and check 'code --version'.")
    if inputs.installed:
        newest = max(inputs.installed, key=lambda candidate: _installed_version_key(candidate, inputs.os))
        return AcquisitionPlan(str(newest), None, None)
    targets = {(HostOs.LINUX, "amd64"): "linux-x64", (HostOs.LINUX, "arm64"): "linux-arm64",
               (HostOs.DARWIN, "amd64"): "darwin", (HostOs.DARWIN, "arm64"): "darwin-arm64"}
    target = targets.get((inputs.os, inputs.architecture))
    if target is None:
        raise CliError(f"host-ide cannot acquire VS Code for {inputs.os}/{inputs.architecture}; install code on PATH.")
    if print_only:
        return AcquisitionPlan("code", target, None)
    require_trust(inputs.trust, vscode_channel())
    return AcquisitionPlan(None, target, f"https://update.code.visualstudio.com/api/update/{target}/stable/latest")


def require_trust(trust: HomeTrust, channel: Channel) -> None:
    """A download requires the existing product's terms and channel acceptance."""
    if not trust.covers(channel):
        raise CliError(f"Host VS Code acquisition needs channel trust for {', '.join(channel.origins)} "
                       f"and {TERMS}. Run 'devcapsule home trust accept vscode' or 'project run --trust vscode'.")


def https_origin(url: str) -> str:
    """Reject insecure or credential-bearing download URLs, including redirects."""
    parsed = urlparse(url)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username is not None
            or parsed.password is not None or any(c.isspace() for c in url)):
        raise CliError("Host VS Code download requires an HTTPS URL without credentials.")
    return f"https://{parsed.netloc}"


def release_archive(document: Mapping[str, Any]) -> Archive:
    """Accept only a path-safe release identity, HTTPS artifact and complete SHA-256."""
    version, url, digest = document.get("productVersion"), document.get("url"), document.get("sha256hash")
    if not isinstance(version, str) or re.fullmatch(r"[0-9]+(?:\.[0-9]+)+(?:[-+][A-Za-z0-9.-]+)?", version) is None:
        raise CliError("Host VS Code release metadata has no valid productVersion.")
    if not isinstance(url, str):
        raise CliError("Host VS Code release metadata has no URL.")
    https_origin(url)
    if not isinstance(digest, str) or re.fullmatch(r"[a-fA-F0-9]{64}", digest) is None:
        raise CliError("Host VS Code release metadata has no valid sha256hash.")
    return Archive(version, url, digest.lower())


def code_relative_path(host_os: HostOs) -> Path:
    """The vendor archive's CLI path after removing the Linux archive's top directory."""
    return Path("Visual Studio Code.app/Contents/Resources/app/bin/code" if host_os == HostOs.DARWIN else "bin/code")


def profile(homes: XdgHomes) -> Profile:
    root = homes.config / "host-ide" / "vscode"
    return Profile(root / "user-data", root / "extensions")


def required_settings(*, wsl: bool, docker_operating_system: str) -> dict[str, Any]:
    """Windows Code executes Docker in WSL only when the launcher uses a distro daemon."""
    return {"dev.containers.executeInWSL": "docker desktop" not in docker_operating_system.lower()} if wsl else {}


def merge_settings(text: str, required: Mapping[str, Any]) -> str:
    """Merge required values, accepting VS Code's comments and trailing commas; leave unrelated values intact."""
    # Preserve the original bytes when no setting needs changing. Strip JSONC
    # comments only outside strings before parsing; never interpret user code.
    tokens = r'"(?:\\.|[^"\\])*"|//[^\n]*|/\*[\s\S]*?\*/'
    cleaned = re.sub(tokens, lambda m: m[0] if m[0].startswith('"') else ' ', text)
    cleaned = re.sub(r'("(?:\\.|[^"\\])*"\s*)|,\s*(?=[}\]])', lambda m: m[1] or '', cleaned)
    try:
        settings = json.loads(cleaned) if cleaned.strip() else {}
    except ValueError as exc:
        raise CliError("Host VS Code settings.json is invalid; repair it before launching (file left unchanged).") from exc
    if not isinstance(settings, dict):
        raise CliError("Host VS Code settings.json must contain an object (file left unchanged).")
    if all(key in settings and settings[key] == value for key, value in required.items()):
        return text or "{}\n"
    return json.dumps({**settings, **required}, indent=2, ensure_ascii=False) + "\n"


def needs_extension(output: str) -> bool:
    return EXTENSION not in {line.strip().lower() for line in output.splitlines()}


def attach_command(code: str, config: Profile, container_name: str, project_mount: str) -> tuple[str, ...]:
    """Encode the container identity as UTF-8 hex and the mount as a URI path."""
    identity = json.dumps({"containerName": "/" + container_name.lstrip("/")}, separators=(",", ":"), ensure_ascii=False)
    uri = f"vscode-remote://attached-container+{identity.encode('utf-8').hex()}{quote(project_mount, safe='/')}"
    return (*config.command(code), "--new-window", "--folder-uri", uri)


def headless(host_os: HostOs, environment: Mapping[str, str], *, wsl: bool) -> bool:
    return host_os == HostOs.LINUX and not wsl and not (environment.get("DISPLAY") or environment.get("WAYLAND_DISPLAY"))


def readiness_commands(name: str, mount: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    return (("docker", "inspect", "-f", "{{.State.Running}}", name),
            ("docker", "exec", name, "test", "-d", mount))
