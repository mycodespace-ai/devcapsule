"""How this host names and locates things (D-0006).

This module owns the project's friction with the host platform: OS-specific
and environment-specific conventions. Code belongs here if and only if it
expresses how the host names or locates things by OS or environment
convention — and would therefore change only when those conventions or the
supported-platform set change, never when product features change. Feature
code that merely consumes environment variables stays with its feature.

The module is terminal in the package's dependency graph: it imports nothing
of DevCapsule's.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import os
from pathlib import Path
import platform as host_platform
from typing import Mapping

__all__ = ["HostOs", "Platform", "UnsupportedPlatformError", "XdgHomes", "architecture_key", "host_architecture"]


class UnsupportedPlatformError(ValueError):
    """A platform key outside the supported set; the message is displayable."""


def architecture_key(machine: str) -> str:
    """A CPU architecture as a machine or a Docker daemon reports it, in the platform keys' spelling."""

    lowered = machine.lower()
    return {"x86_64": "amd64", "aarch64": "arm64"}.get(lowered, lowered)


def host_architecture() -> str:
    """This host's CPU architecture in the platform keys' spelling."""

    return architecture_key(host_platform.machine())


class HostOs(StrEnum):
    """The host operating system, for the mechanisms that differ by host.

    Locks never carry it: capsules are Linux on every host, and the lock
    names the capsule platform (``Platform``). On macOS the container runtime
    is Docker Desktop's virtual machine; its conventions, observed on Docker
    Desktop 29.3.1, are the properties below, which feature code consults
    instead of asking which host it is on.
    """

    LINUX = "linux"
    DARWIN = "darwin"

    @classmethod
    def current(cls) -> HostOs:
        system = host_platform.system().lower()
        try:
            return cls(system)
        except ValueError:
            supported = ", ".join(member.value for member in cls)
            raise UnsupportedPlatformError(
                f"Unsupported host operating system {system!r}; supported: {supported}."
            ) from None

    @property
    def docker_socket_gid(self) -> int | None:
        """The group owning the Docker socket inside a container, when the host decides it.

        Docker Desktop presents its socket as ``root:root``, mode 0660, in every
        container, whatever the Mac file's owner. None on Linux, where the host
        socket file's own group applies.
        """

        return 0 if self is HostOs.DARWIN else None

    @property
    def host_network_reachable(self) -> bool:
        """Whether a listener on Docker's host network is reachable from this host.

        Docker Desktop's host network is its virtual machine's, out of the Mac's reach.
        """

        return self is HostOs.LINUX

    @property
    def binds_unix_sockets(self) -> bool:
        """Whether a host Unix socket can be bind-mounted into a container.

        Docker Desktop rewrites the source under ``/socket_mnt`` and refuses it.
        """

        return self is HostOs.LINUX

    @property
    def chown_reaches_bind_mounts(self) -> bool:
        """Whether root in a container can change a bind-mounted host file's owner.

        Docker Desktop shares Mac files as the Mac user; a chown inside is refused.
        """

        return self is HostOs.LINUX


# The capsule platforms each host runs, native first. A Linux host runs its
# own platform; Apple Silicon runs linux-arm64 natively and linux-amd64 under
# Docker Desktop's emulation; an Intel Mac runs linux-amd64.
_CAPSULE_PLATFORMS_OF_HOST: Mapping[tuple[HostOs, str], tuple[str, ...]] = {
    (HostOs.LINUX, "amd64"): ("linux-amd64",),
    (HostOs.LINUX, "arm64"): ("linux-arm64",),
    (HostOs.DARWIN, "arm64"): ("linux-arm64", "linux-amd64"),
    (HostOs.DARWIN, "amd64"): ("linux-amd64",),
}

# The platform whose executables carry each ELF e_machine value.
_PLATFORM_OF_ELF_MACHINE: Mapping[int, str] = {0x3E: "linux-amd64", 0xB7: "linux-arm64"}


class Platform(StrEnum):
    """The supported capsule platforms and their wire format.

    A platform is what capsules run as, not what the launcher runs on: a
    Mac launches Linux capsules. Members are the single authority on what
    capsule platforms DevCapsule supports; values are the wire format
    serialized into lock filenames, lock documents, and artifact tables.
    Because committed locks carry these values, members are append-only and
    never renamed.

    A client never constructs a key from parts. Host detection gives
    ``current()`` (the platform this host runs natively) and ``runnable()``
    (every platform it runs); ``parse()`` gives the platform a lock records,
    and ``of_elf_machine()`` the one an executable is for.
    Which platform a project runs as is the configuration's question
    (``configuration.storage.project_platform``), answered from its locks.
    """

    LINUX_AMD64 = "linux-amd64"
    LINUX_ARM64 = "linux-arm64"

    @classmethod
    def current(cls) -> Platform:
        """The platform this host runs natively, and a new project's unless the developer chooses another."""

        return cls.runnable()[0]

    @classmethod
    def runnable(cls) -> tuple[Platform, ...]:
        """Every platform this host runs capsules as, native first."""

        host_os, architecture = HostOs.current(), host_architecture()
        keys = _CAPSULE_PLATFORMS_OF_HOST.get((host_os, architecture), (f"{host_os}-{architecture}",))
        return tuple(cls.parse(key) for key in keys)

    @classmethod
    def of_elf_machine(cls, machine: int) -> Platform | None:
        """The platform an ELF executable of ``machine`` runs on, or None for another architecture."""

        key = _PLATFORM_OF_ELF_MACHINE.get(machine)
        return cls(key) if key is not None else None

    @property
    def architecture(self) -> str:
        return self.value.split("-", 1)[1]

    @property
    def docker_platform(self) -> str:
        """Docker's spelling of this platform, as ``--platform`` takes it."""

        return self.value.replace("-", "/", 1)

    def emulated_docker_platform(self, daemon_architecture: str) -> str | None:
        """The platform every run, build and pull names to a daemon that emulates this one.

        A Docker daemon of ``daemon_architecture`` defaults to its own
        architecture, so it must be told this platform when the two differ.
        None when it runs this platform natively and is told nothing.
        """

        return self.docker_platform if daemon_architecture != self.architecture else None

    def docker_platform_args(self, daemon_architecture: str) -> list[str]:
        """``emulated_docker_platform`` as the option of a ``docker run`` command line."""

        emulated = self.emulated_docker_platform(daemon_architecture)
        return [f"--platform={emulated}"] if emulated is not None else []

    @classmethod
    def parse(cls, key: str) -> Platform:
        """The member a lock's recorded platform key names."""

        try:
            return cls(key)
        except ValueError:
            supported = ", ".join(member.value for member in cls)
            raise UnsupportedPlatformError(
                f"Unsupported platform {key!r}; supported platforms: {supported}."
            ) from None


@dataclass(frozen=True)
class XdgHomes:
    """DevCapsule's user-scoped directories per the XDG base-directory spec.

    The one derivation of the convention: each directory honors its
    ``XDG_*_HOME`` override and falls back to the specified default under
    ``HOME``, always scoped by a ``devcapsule`` segment.
    """

    config: Path
    data: Path
    state: Path
    cache: Path
    chosen_by: str = field(default="default", compare=False)

    @classmethod
    def from_environment(cls, env: Mapping[str, str] | None = None) -> XdgHomes:
        values = os.environ if env is None else env
        named = values.get("DEVCAPSULE_CONFIG_HOME")
        if named:
            root = Path(named).expanduser().resolve()
            return cls(root, root / "data", root / "state", root / "cache", "DEVCAPSULE_CONFIG_HOME")
        home = Path(values.get("HOME", "~")).expanduser()

        def scoped(variable: str, *default: str) -> Path:
            return Path(values.get(variable) or home.joinpath(*default)) / "devcapsule"

        return cls(
            config=scoped("XDG_CONFIG_HOME", ".config"),
            data=scoped("XDG_DATA_HOME", ".local", "share"),
            state=scoped("XDG_STATE_HOME", ".local", "state"),
            cache=scoped("XDG_CACHE_HOME", ".cache"),
            chosen_by="XDG_CONFIG_HOME" if values.get("XDG_CONFIG_HOME") else "default",
        )
