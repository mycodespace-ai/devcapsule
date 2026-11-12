"""Make ordinary launches aware that they may be running inside a container.

A DevCapsule launch normally runs on the host, where a bind source written by
the launcher means the same thing to the Docker daemon as it does to the
launching process. That assumption breaks when the launcher itself runs inside
a container whose Docker CLI is pointed at the *host* daemon: the daemon
resolves bind sources in the host filesystem, where the launcher's own paths do
not exist.

Docker does not report that as an error. It creates a missing bind source as an
empty directory, so an IDE launched this way silently opens an empty project
instead of the developer's code.

This module detects that situation and translates each bind source through the
current container's own mount table, so the daemon receives the host path that
actually backs it. When a bind source is not backed by any mount, translation
is impossible and the launch fails loudly rather than silently producing an
empty directory.

The daemon's architecture is the other fact about it a launch needs: a daemon
of another architecture than the capsule platform runs it under emulation.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import json
from pathlib import Path, PurePosixPath
import re
import subprocess

from devcapsule.recursive_dogfood import (
    CONTAINER_NAME_ENV,
    ContainerInspection,
    PreflightError,
    identify_current_container,
    parse_container_inspection,
    self_overlay_upper_directory,
)


CONTAINER_MARKER = Path("/.dockerenv")
MOUNTINFO = Path("/proc/self/mountinfo")
DEFAULT_DOCKER_SOCKET = Path("/var/run/docker.sock")
_MOUNTINFO_FIELDS = 5


class HostDaemonError(Exception):
    """A containerized launch cannot be translated for the host Docker daemon."""


def in_container(marker: Path = CONTAINER_MARKER) -> bool:
    """Return whether this process is running inside a Docker container."""

    return marker.is_file()


def docker_socket(env: Mapping[str, str]) -> Path:
    """Return the Unix socket this process's Docker CLI talks to."""

    host = env.get("DOCKER_HOST", "")
    if host.startswith("unix://"):
        return Path(host[len("unix://") :])
    return DEFAULT_DOCKER_SOCKET


def socket_is_external(socket: Path, mountinfo: Path = MOUNTINFO) -> bool:
    """Return whether the Docker socket was bind-mounted in from outside.

    A socket mounted into this container belongs to a daemon that lives outside
    it, so that daemon resolves paths in a different filesystem. A daemon
    running *inside* this container (docker-in-docker) creates its socket as an
    ordinary file, which is not a mount point and needs no translation.
    """

    try:
        content = mountinfo.read_text(encoding="utf-8")
    except OSError:
        return False
    target = str(socket)
    for line in content.splitlines():
        fields = line.split(" ")
        if len(fields) > _MOUNTINFO_FIELDS and _unescape(fields[4]) == target:
            return True
    return False


def requires_translation(env: Mapping[str, str]) -> bool:
    """Return whether this launch must translate bind sources for the daemon."""

    return in_container() and socket_is_external(docker_socket(env))


def current_container(env: Mapping[str, str]) -> ContainerInspection:
    """Identify this container through the daemon, or fail loudly."""

    declared = env.get(CONTAINER_NAME_ENV)
    if declared:
        listed = [declared]
    else:
        result = _docker(["container", "list", "--quiet", "--filter", "status=running"], env)
        listed = result.stdout.split()
        if not listed:
            raise HostDaemonError(
                "This launcher is running inside a container against an external Docker "
                "daemon, but that daemon reports no running containers, so this container's "
                "own mounts cannot be resolved. Bind sources would be created as empty "
                f"directories. Set {CONTAINER_NAME_ENV} to this container's name and retry."
            )
    result = _docker(["container", "inspect", *listed], env)
    try:
        raw = json.loads(result.stdout)
        if not isinstance(raw, list) or not raw:
            raise PreflightError("Docker returned an empty container inspection set")
        inspections = tuple(parse_container_inspection(item) for item in raw)
        return identify_current_container(
            inspections,
            expected_name=declared,
            self_upper_directory=self_overlay_upper_directory(),
        )
    except (json.JSONDecodeError, PreflightError) as exc:
        raise HostDaemonError(
            "This launcher is running inside a container against an external Docker "
            f"daemon, but its own container identity is {exc}. Bind sources cannot be "
            "translated to host paths and would be created as empty directories. Set "
            f"{CONTAINER_NAME_ENV} to this container's name and retry."
        ) from exc


def translate_bind_sources(
    docker_args: Sequence[str],
    container: ContainerInspection,
) -> list[str]:
    """Rewrite every ``--mount`` bind source into its host-side equivalent."""

    translated = list(docker_args)
    for index, value in enumerate(translated[:-1]):
        if value != "--mount":
            continue
        fields = translated[index + 1].split(",")
        if "type=bind" not in fields:
            continue
        positions = [position for position, field in enumerate(fields) if field.startswith("src=")]
        if len(positions) != 1:
            raise HostDaemonError("A planned bind mount does not declare exactly one source.")
        position = positions[0]
        source = Path(fields[position].removeprefix("src="))
        fields[position] = f"src={host_path(source, container)}"
        translated[index + 1] = ",".join(fields)
    return translated


def is_host_backed(path: Path, container: ContainerInspection) -> bool:
    """Return whether a container path maps to a host path the daemon can read."""

    try:
        host_path(path, container)
    except HostDaemonError:
        return False
    return True


def host_path(source: Path, container: ContainerInspection) -> PurePosixPath:
    """Map one container path to the host path backing it, or fail loudly."""

    selected = PurePosixPath(str(source))
    candidates = [
        mount
        for mount in container.mounts
        if selected == PurePosixPath(mount.destination)
        or PurePosixPath(mount.destination) in selected.parents
    ]
    if not candidates:
        raise HostDaemonError(
            f"This launch runs inside a container against an external Docker daemon, and "
            f"{source} is not backed by any mount of this container. The daemon would "
            f"create an empty directory there instead of using your files. Mount that path "
            f"into this container, or run the launch from the host."
        )
    depth = max(len(PurePosixPath(mount.destination).parts) for mount in candidates)
    deepest = [mount for mount in candidates if len(PurePosixPath(mount.destination).parts) == depth]
    if len(deepest) != 1:
        raise HostDaemonError(
            f"Container path {source} has ambiguous mount mappings, so its host path cannot "
            "be determined safely."
        )
    mount = deepest[0]
    relative = selected.relative_to(PurePosixPath(mount.destination))
    return PurePosixPath(mount.source).joinpath(relative)


def _docker(arguments: Sequence[str], env: Mapping[str, str]) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        ["docker", *arguments],
        check=False,
        env=dict(env),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip()
        raise HostDaemonError(
            "This launcher is running inside a container against an external Docker daemon, "
            "but that daemon rejected container inspection, so bind sources cannot be "
            "translated to host paths." + (f" Docker reported: {detail}" if detail else "")
        )
    return completed


def _unescape(value: str) -> str:
    return re.sub(r"\\([0-7]{3})", lambda match: chr(int(match.group(1), 8)), value)


def daemon_architecture() -> str:
    """The Docker daemon's CPU architecture, in the platform keys' spelling.

    Emulation is the daemon's, not the launcher's: Docker Desktop on Apple
    Silicon is arm64 whether the launcher runs natively on the Mac or inside
    an emulated amd64 capsule granted the daemon. This host's architecture
    when the daemon does not answer.
    """
    from devcapsule.platforms import architecture_key, host_architecture

    try:
        completed = subprocess.run(
            ["docker", "version", "--format", "{{.Server.Arch}}"],
            capture_output=True, text=True, timeout=30, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return host_architecture()
    reported = completed.stdout.strip()
    return architecture_key(reported) if completed.returncode == 0 and reported else host_architecture()
