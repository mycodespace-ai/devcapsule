"""Host IDE entry layer. prepare_host_ide reads the host and executes the pure plan."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tarfile
import tempfile
from urllib.request import HTTPSHandler, HTTPRedirectHandler, build_opener
import zipfile

from devcapsule.compat import CliError
from devcapsule.configuration.storage import atomic_write
from devcapsule.configuration.trust import HomeTrust
from devcapsule.host_ide import (
    EXTENSION, HostIdeInputs, acquisition_plan, attach_command, code_relative_path,
    https_origin, merge_settings, needs_extension, profile, release_archive, required_settings, require_trust, vscode_channel,
)
from devcapsule.platforms import HostOs, XdgHomes, architecture_key


class _HttpsRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        https_origin(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def prepare_host_ide(homes: XdgHomes, trust: HomeTrust, container_name: str,
                     project_mount: str, *, print_only: bool, environment: dict[str, str]) -> tuple[str, ...]:
    """Acquire if authorized, prepare the isolated profile, and return the attach command before Docker run."""
    host_os = HostOs.current()
    wsl = bool(environment.get("WSL_DISTRO_NAME") or environment.get("WSL_INTEROP"))
    relative = code_relative_path(host_os)
    root = homes.data / "host-ide" / "vscode"
    installed = tuple(path / relative for path in root.glob("*")
                      if not path.name.startswith(".") and (path / relative).is_file()
                      and os.access(path / relative, os.X_OK))
    inputs = HostIdeInputs(homes, host_os, architecture_key(platform.machine()), wsl,
                           shutil.which("code", path=environment.get("PATH", os.defpath)), installed, trust)
    plan = acquisition_plan(inputs, print_only=print_only)
    config = profile(homes)
    code = plan.code
    try:
        if code is None:
            assert plan.metadata_url is not None
            opener = build_opener(HTTPSHandler(), _HttpsRedirect())
            with opener.open(plan.metadata_url, timeout=60) as response:
                https_origin(response.geturl())
                archive = release_archive(json.load(response))
            require_trust(trust, vscode_channel(https_origin(archive.url)))
            destination = root / archive.version
            cache = homes.cache / "host-ide" / "vscode"
            cache.mkdir(parents=True, exist_ok=True)
            root.mkdir(parents=True, exist_ok=True)
            # Unique staging paths allow concurrent launches. A completed version
            # appears only after digest verification, extraction and CLI validation.
            with tempfile.TemporaryDirectory(prefix=".download-", dir=cache) as download:
                payload = Path(download) / "archive"
                digest = hashlib.sha256()
                with opener.open(archive.url, timeout=120) as response, payload.open("wb") as output:
                    https_origin(response.geturl())
                    while chunk := response.read(1024 * 1024):
                        digest.update(chunk)
                        output.write(chunk)
                if digest.hexdigest() != archive.sha256:
                    raise CliError("Host VS Code archive SHA-256 mismatch; nothing was installed.")
                with tempfile.TemporaryDirectory(prefix=".unpack-", dir=root) as staging:
                    unpacked = Path(staging) / "release"
                    unpacked.mkdir()
                    if host_os == HostOs.LINUX:
                        with tarfile.open(payload) as tar:
                            tar.extractall(unpacked, filter="data")
                        children = list(unpacked.iterdir())
                        source = children[0] if len(children) == 1 and children[0].is_dir() else unpacked
                    else:
                        # ditto preserves the app bundle's permissions and symlinks.
                        # Inspect member paths first; extraction never escapes staging.
                        with zipfile.ZipFile(payload) as zipped:
                            if any(Path(n).is_absolute() or ".." in Path(n).parts for n in zipped.namelist()):
                                raise CliError("Host VS Code archive contains an unsafe path.")
                        subprocess.run(["/usr/bin/ditto", "-x", "-k", str(payload), str(unpacked)], check=True)
                        source = unpacked
                    executable = source / relative
                    if not executable.is_file() or not os.access(executable, os.X_OK):
                        raise CliError("Host VS Code archive does not contain an executable code CLI.")
                    try:
                        source.rename(destination)
                    except OSError:
                        if not (destination / relative).is_file():
                            raise
            code = str(destination / relative)
        command = attach_command(code, config, container_name, project_mount)
        if print_only:
            return command
        config.extensions.mkdir(parents=True, exist_ok=True)
        settings = config.user_data / "User" / "settings.json"
        docker_os = ""
        if wsl:
            docker_os = subprocess.run(["docker", "info", "--format", "{{.OperatingSystem}}"],
                                       check=True, capture_output=True, text=True, env=environment).stdout
        original = settings.read_text(encoding="utf-8") if settings.exists() else ""
        merged = merge_settings(original, required_settings(wsl=wsl, docker_operating_system=docker_os))
        if merged != original:
            settings.parent.mkdir(parents=True, exist_ok=True)
            atomic_write(settings, merged)
        prefix = config.command(code)
        listed = subprocess.run([*prefix, "--list-extensions"], check=True, capture_output=True,
                                text=True, env=environment)
        if needs_extension(listed.stdout):
            subprocess.run([*prefix, "--install-extension", EXTENSION], check=True, env=environment)
        return command
    except (OSError, ValueError, tarfile.TarError, zipfile.BadZipFile, subprocess.CalledProcessError) as exc:
        raise CliError(f"Could not prepare host VS Code: {exc}") from exc
