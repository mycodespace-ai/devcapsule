"""Verified host-daemon path translation and staging for recursive dogfood."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import time
from typing import Mapping, Sequence

from devcapsule.launch.pycharm._launcher import SUDOERS_POLICY
from devcapsule.container_runtime.contract import RuntimePlan
from devcapsule.recursive_dogfood import (
    ContainerInspection,
    Mount,
    PreflightError,
    PreflightReport,
    WORKSPACE_RELATIVE_PATH,
    covering_mount,
    safe_child,
)


RUNTIME_PLAN_DESTINATION = "/etc/devcapsule/runtime-plan.json"
PASSWD_DESTINATION = "/etc/passwd"
GROUP_DESTINATION = "/etc/group"
SHADOW_DESTINATION = "/etc/shadow"
SUDOERS_DESTINATION = "/etc/sudoers.d/devcapsule-development-sudo"
XAUTHORITY_DESTINATION = "/tmp/.docker.xauth"
MAX_XAUTHORITY_BYTES = 1024 * 1024
OWNER_MARKER = ".devcapsule-e2e-owner.json"


class HostContextError(PreflightError):
    """A host-daemon mapping or staging operation is unsafe."""


class PathAccess(str, Enum):
    read = "read"
    write = "write"


class PathKind(str, Enum):
    directory = "directory"
    file = "file"
    socket = "socket"


@dataclass(frozen=True)
class MountRequirement:
    purpose: str
    container_path: Path
    access: PathAccess
    kind: PathKind


@dataclass(frozen=True)
class ApprovedMount:
    mount: Mount = field(repr=False)
    purposes: tuple[str, ...]


@dataclass(frozen=True)
class TranslatedPath:
    container_path: Path
    host_path: PurePosixPath = field(repr=False)
    mount_destination: str
    access: PathAccess
    kind: PathKind

    def to_mapping(self, *, show_host_paths: bool = False) -> dict[str, str]:
        return {
            "container_path": str(self.container_path),
            "host_path": str(self.host_path) if show_host_paths else "<redacted-host-path>",
            "mount_destination": self.mount_destination,
            "access": self.access.value,
            "kind": self.kind.value,
        }

    def __str__(self) -> str:
        return f"{self.container_path} -> <redacted-host-path>"


@dataclass(frozen=True)
class PlannedBindMount:
    source: TranslatedPath
    destination: str
    read_only: bool
    sensitive: bool = False

    def to_mapping(self, *, show_host_paths: bool = False) -> dict[str, str]:
        if self.sensitive and not show_host_paths:
            container_source = "<sensitive-staged-file>"
            destination = "<sensitive-container-destination>"
        else:
            container_source = str(self.source.container_path)
            destination = self.destination
        return {
            "container_source": container_source,
            "host_source": (
                str(self.source.host_path) if show_host_paths else "<redacted-host-path>"
            ),
            "successor_destination": destination,
            "mode": "ro" if self.read_only else "rw",
            "kind": self.source.kind.value,
        }


@dataclass(frozen=True)
class HostDaemonLaunchContext:
    """Approved mappings from the current container into the host daemon."""

    container: ContainerInspection = field(repr=False)
    persistent_home: Path
    workspace_root: Path
    approved_mounts: tuple[ApprovedMount, ...] = field(repr=False)

    @classmethod
    def for_recursive_dogfood(
        cls,
        preflight: PreflightReport,
        *,
        persistent_home: Path,
        project: Path,
        runtime_plan: Path,
        docker_socket: Path,
        x11_socket_directory: Path | None,
        xauthority: Path | None,
        state_paths: Sequence[Path] = (),
    ) -> HostDaemonLaunchContext:
        if not preflight.ready or preflight.container is None:
            raise HostContextError(
                "a successful recursive preflight with exact container evidence is required"
            )
        requirements = [
            MountRequirement("project", project, PathAccess.write, PathKind.directory),
            MountRequirement(
                "current-runtime-plan", runtime_plan, PathAccess.read, PathKind.file
            ),
            MountRequirement("host-docker", docker_socket, PathAccess.write, PathKind.socket),
        ]
        # Host X11 passthrough forwards the session socket and credential;
        # the contained display has neither (both None).
        if x11_socket_directory is not None:
            requirements.append(
                MountRequirement("x11", x11_socket_directory, PathAccess.read, PathKind.directory)
            )
        if xauthority is not None:
            requirements.append(MountRequirement("xauthority", xauthority, PathAccess.read, PathKind.file))
        requirements.extend(
            MountRequirement(
                f"state-{index}", path, PathAccess.write, PathKind.directory
            )
            for index, path in enumerate(state_paths)
        )
        return cls.from_requirements(
            preflight.container,
            persistent_home=persistent_home,
            requirements=requirements,
        )

    @classmethod
    def from_requirements(
        cls,
        container: ContainerInspection,
        *,
        persistent_home: Path,
        requirements: Sequence[MountRequirement],
    ) -> HostDaemonLaunchContext:
        home_requirement = MountRequirement(
            "persistent-home",
            persistent_home,
            PathAccess.write,
            PathKind.directory,
        )
        purposes: dict[str, set[str]] = {}
        selected_mounts: dict[str, Mount] = {}
        canonical_home: Path | None = None
        for requirement in (home_requirement, *requirements):
            canonical, mount = _validate_requirement(container.mounts, requirement)
            _validated_host_source(mount)
            selected_mounts[mount.destination] = mount
            purposes.setdefault(mount.destination, set()).add(requirement.purpose)
            if requirement.purpose == "persistent-home":
                canonical_home = canonical
        if canonical_home is None:  # pragma: no cover - constructed above.
            raise AssertionError("persistent home was not validated")
        approved = tuple(
            ApprovedMount(selected_mounts[destination], tuple(sorted(purposes[destination])))
            for destination in sorted(selected_mounts)
        )
        workspace = safe_child(canonical_home, WORKSPACE_RELATIVE_PATH)
        context = cls(container, canonical_home, workspace, approved)
        context.authorize_creation(workspace)
        return context

    def translate(
        self,
        container_path: Path,
        *,
        access: PathAccess,
        kind: PathKind,
    ) -> TranslatedPath:
        lexical = _absolute_container_path(container_path)
        try:
            canonical = lexical.resolve(strict=True)
        except OSError as exc:
            raise HostContextError(f"container path {lexical} is missing or inaccessible") from exc
        lexical_mount = _selected_mount(lexical, self.container.mounts, access=access)
        canonical_mount = _selected_mount(canonical, self.container.mounts, access=access)
        if lexical_mount.destination != canonical_mount.destination:
            raise HostContextError(
                f"container path {lexical} resolves across a Docker mount boundary"
            )
        approved = self._approved(canonical_mount.destination)
        _validate_kind(canonical, kind)
        if access is PathAccess.write and not os.access(canonical, os.W_OK):
            raise HostContextError(f"container path {lexical} is not writable by the current user")
        if access is PathAccess.read and kind is not PathKind.socket and not os.access(
            canonical, os.R_OK
        ):
            raise HostContextError(f"container path {lexical} is not readable by the current user")
        return _translation(canonical, approved.mount, access=access, kind=kind)

    def authorize_creation(self, container_path: Path) -> None:
        """Validate a not-yet-created path without mutating the filesystem."""

        lexical = _absolute_container_path(container_path)
        lexical_mount = _selected_mount(
            lexical,
            self.container.mounts,
            access=PathAccess.write,
        )
        self._approved(lexical_mount.destination)
        canonical = lexical.resolve(strict=False)
        canonical_mount = _selected_mount(
            canonical,
            self.container.mounts,
            access=PathAccess.write,
        )
        if lexical_mount.destination != canonical_mount.destination:
            raise HostContextError(
                f"future container path {lexical} resolves across a Docker mount boundary"
            )
        self._approved(canonical_mount.destination)
        existing = canonical
        while not existing.exists():
            if existing == existing.parent:
                raise HostContextError(f"future container path {lexical} has no existing parent")
            existing = existing.parent
        if not existing.is_dir() or not os.access(existing, os.W_OK | os.X_OK):
            raise HostContextError(
                f"future container path {lexical} has no writable containing directory"
            )

    def plan_bind(
        self,
        container_source: Path,
        successor_destination: str,
        *,
        read_only: bool,
        kind: PathKind,
        sensitive: bool = False,
    ) -> PlannedBindMount:
        destination = _absolute_successor_path(successor_destination)
        access = PathAccess.read if read_only else PathAccess.write
        source = self.translate(container_source, access=access, kind=kind)
        return PlannedBindMount(source, destination, read_only, sensitive)

    def to_mapping(self, *, show_host_paths: bool = False) -> dict[str, object]:
        return {
            "schema_version": 1,
            "container_id": self.container.identity,
            "persistent_home": str(self.persistent_home),
            "workspace_root": str(self.workspace_root),
            "approved_mounts": [
                {
                    "destination": item.mount.destination,
                    "source": (
                        item.mount.source if show_host_paths else "<redacted-host-path>"
                    ),
                    "mode": "rw" if item.mount.writable else "ro",
                    "purposes": list(item.purposes),
                }
                for item in self.approved_mounts
            ],
        }

    def _approved(self, destination: str) -> ApprovedMount:
        matches = [item for item in self.approved_mounts if item.mount.destination == destination]
        if len(matches) != 1:
            raise HostContextError(
                f"Docker mount {destination} was not explicitly approved for recursive E2E"
            )
        return matches[0]


@dataclass(frozen=True)
class StagedFile:
    name: str
    container_path: Path
    mode: int
    sensitive: bool
    requires_root_owner: bool = False


@dataclass(frozen=True)
class StagedLaunchFiles:
    files: tuple[StagedFile, ...]
    bind_mounts: tuple[PlannedBindMount, ...]

    def by_name(self) -> Mapping[str, StagedFile]:
        return {item.name: item for item in self.files}

    def to_mapping(self, *, show_host_paths: bool = False) -> dict[str, object]:
        return {
            "files": [
                {
                    "name": item.name,
                    "container_path": (
                        str(item.container_path)
                        if show_host_paths or not item.sensitive
                        else "<sensitive-staged-file>"
                    ),
                    "mode": f"0{item.mode:o}",
                    "requires_root_owner": item.requires_root_owner,
                }
                for item in self.files
            ],
            "bind_mounts": [
                item.to_mapping(show_host_paths=show_host_paths)
                for item in self.bind_mounts
            ],
        }


class RecursiveStagingArea:
    """One ownership-marked, host-backed set of transient launch inputs."""

    def __init__(
        self,
        context: HostDaemonLaunchContext,
        run_id: str,
        *,
        keep_on_failure: bool = False,
    ) -> None:
        if re.fullmatch(r"[0-9a-f]{16,64}", run_id) is None:
            raise HostContextError("recursive E2E run ID must contain 16 to 64 lowercase hex digits")
        self.context = context
        self.run_id = run_id
        self.keep_on_failure = keep_on_failure
        self.run_root = context.workspace_root / run_id
        self.staging_root = self.run_root / "staging"
        self._active = False

    def __enter__(self) -> RecursiveStagingArea:
        if self._active:
            raise HostContextError("recursive staging area is already active")
        self.context.authorize_creation(self.context.workspace_root)
        self.context.workspace_root.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.context.translate(
            self.context.workspace_root,
            access=PathAccess.write,
            kind=PathKind.directory,
        )
        self.context.authorize_creation(self.run_root)
        try:
            self.run_root.mkdir(mode=0o700)
        except FileExistsError as exc:
            raise HostContextError(f"recursive E2E run workspace already exists: {self.run_id}") from exc
        self.run_root.chmod(0o700)
        marker_created = False
        try:
            _write_exclusive(
                self.run_root / OWNER_MARKER,
                json.dumps(
                    {
                        "schema_version": 1,
                        "run_id": self.run_id,
                        "container_id": self.context.container.identity,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
                + b"\n",
                0o600,
            )
            marker_created = True
            self.staging_root.mkdir(mode=0o700)
            self.staging_root.chmod(0o700)
            self.context.translate(
                self.staging_root,
                access=PathAccess.write,
                kind=PathKind.directory,
            )
        except BaseException:
            if marker_created:
                self._remove_owned_root()
            else:
                self.run_root.rmdir()
            raise
        self._active = True
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        if exc is not None and self.keep_on_failure:
            return
        self.cleanup()

    @property
    def host_staging_root(self) -> PurePosixPath:
        self._require_active()
        return self.context.translate(
            self.staging_root,
            access=PathAccess.write,
            kind=PathKind.directory,
        ).host_path

    @property
    def ownership_marker(self) -> Path:
        """Path to the public ownership evidence guarding cleanup."""

        return self.run_root / OWNER_MARKER

    def prepare_launch_files(
        self,
        runtime_plan: RuntimePlan,
        *,
        xauthority: Path | None,
        host_docker_gid: int,
        sudo_gid: int | None = None,
        shadow_last_change: int | None = None,
    ) -> StagedLaunchFiles:
        self._require_active()
        identity = runtime_plan.identity
        user = _account_name(identity.user, "runtime user")
        if identity.uid <= 0 or identity.gid <= 0:
            raise HostContextError("recursive successor identity must be unprivileged")
        # A rootless daemon maps its host user's group to 0 in the capsule;
        # Docker Desktop can also expose a group-0 socket. Both are valid.
        if isinstance(host_docker_gid, bool) or not isinstance(host_docker_gid, int) or host_docker_gid < 0:
            raise HostContextError("host Docker group ID must be a non-negative integer")
        if sudo_gid is not None:
            _positive_id(sudo_gid, "development-sudo group ID")

        staged: list[StagedFile] = []
        binds: list[PlannedBindMount] = []

        runtime_path = self._write_text(
            "runtime-plan.json", runtime_plan.to_json() + "\n", 0o644
        )
        staged.append(StagedFile("runtime-plan", runtime_path, 0o644, False))
        binds.append(
            self.context.plan_bind(
                runtime_path,
                RUNTIME_PLAN_DESTINATION,
                read_only=True,
                kind=PathKind.file,
            )
        )

        passwd = "\n".join(
            [
                "root:x:0:0:root:/root:/bin/bash",
                f"{user}:x:{identity.uid}:{identity.gid}:DevCapsule User:{runtime_plan.home}:/bin/bash",
                "",
            ]
        )
        passwd_path = self._write_text("passwd", passwd, 0o644)
        staged.append(StagedFile("passwd", passwd_path, 0o644, False))
        binds.append(
            self.context.plan_bind(
                passwd_path, PASSWD_DESTINATION, read_only=True, kind=PathKind.file
            )
        )

        root_members = user if host_docker_gid == 0 else ""
        groups = [f"root:x:0:{root_members}", f"{user}:x:{identity.gid}:"]
        if host_docker_gid not in (0, identity.gid):
            groups.append(f"host-docker:x:{host_docker_gid}:{user}")
        if sudo_gid is not None:
            groups.append(f"ide-sudo:x:{sudo_gid}:{user}")
        group_path = self._write_text("group", "\n".join([*groups, ""]), 0o644)
        staged.append(StagedFile("group", group_path, 0o644, False))
        binds.append(
            self.context.plan_bind(
                group_path, GROUP_DESTINATION, read_only=True, kind=PathKind.file
            )
        )

        if xauthority is not None:
            xauthority_path = self._copy_xauthority(xauthority)
            staged.append(StagedFile("xauthority", xauthority_path, 0o600, True))
            binds.append(
                self.context.plan_bind(
                    xauthority_path,
                    XAUTHORITY_DESTINATION,
                    read_only=True,
                    kind=PathKind.file,
                    sensitive=True,
                )
            )

        if sudo_gid is not None:
            selected_day = int(time.time()) // 86400 if shadow_last_change is None else shadow_last_change
            if selected_day < 0:
                raise HostContextError("shadow last-change day must be non-negative")
            shadow = "\n".join(
                [
                    f"root:*:{selected_day}:0:99999:7:::",
                    f"{user}:*:{selected_day}:0:99999:7:::",
                    "",
                ]
            )
            shadow_path = self._write_text("shadow", shadow, 0o600)
            staged.append(StagedFile("shadow", shadow_path, 0o600, True))
            binds.append(
                self.context.plan_bind(
                    shadow_path,
                    SHADOW_DESTINATION,
                    read_only=True,
                    kind=PathKind.file,
                    sensitive=True,
                )
            )
            sudoers_directory = self.staging_root / "sudoers"
            sudoers_directory.mkdir(mode=0o700)
            sudoers_directory.chmod(0o700)
            policy_path = self._write_text("sudoers/policy", SUDOERS_POLICY, 0o440)
            staged.append(StagedFile("sudoers-policy", policy_path, 0o440, True, True))
            binds.append(
                self.context.plan_bind(
                    policy_path,
                    SUDOERS_DESTINATION,
                    read_only=True,
                    kind=PathKind.file,
                    sensitive=True,
                )
            )

        return StagedLaunchFiles(tuple(staged), tuple(binds))

    def cleanup(self) -> None:
        if not self.run_root.exists():
            self._active = False
            return
        self._remove_owned_root()
        self._active = False

    def _write_text(self, relative: str, value: str, mode: int) -> Path:
        path = safe_child(self.staging_root, Path(relative))
        _write_exclusive(path, value.encode("utf-8"), mode)
        return path

    def _copy_xauthority(self, source: Path) -> Path:
        translated = self.context.translate(
            source,
            access=PathAccess.read,
            kind=PathKind.file,
        )
        flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(translated.container_path, flags)
        try:
            payload = bytearray()
            while True:
                block = os.read(descriptor, 64 * 1024)
                if not block:
                    break
                payload.extend(block)
                if len(payload) > MAX_XAUTHORITY_BYTES:
                    raise HostContextError("Xauthority material exceeds the 1 MiB staging limit")
        finally:
            os.close(descriptor)
        destination = self.staging_root / "xauthority"
        _write_exclusive(destination, bytes(payload), 0o600)
        return destination

    def _remove_owned_root(self) -> None:
        workspace = self.context.workspace_root.resolve(strict=True)
        try:
            run_root = self.run_root.resolve(strict=True)
        except OSError as exc:
            raise HostContextError("owned recursive E2E run root is missing during cleanup") from exc
        if run_root.parent != workspace or run_root.name != self.run_id:
            raise HostContextError("refusing cleanup outside the exact recursive E2E workspace")
        if stat.S_ISLNK(self.run_root.lstat().st_mode):
            raise HostContextError("refusing cleanup of a symlinked recursive E2E run root")
        marker = self.ownership_marker
        try:
            marker_stat = marker.lstat()
            if not stat.S_ISREG(marker_stat.st_mode):
                raise HostContextError("recursive E2E ownership marker is not a regular file")
            value = json.loads(marker.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise HostContextError("recursive E2E ownership marker is absent or malformed") from exc
        expected = {
            "schema_version": 1,
            "run_id": self.run_id,
            "container_id": self.context.container.identity,
        }
        if value != expected:
            raise HostContextError("recursive E2E ownership marker does not match this run")
        shutil.rmtree(run_root)

    def _require_active(self) -> None:
        if not self._active:
            raise HostContextError("recursive staging area is not active")


def _validate_requirement(
    mounts: Sequence[Mount], requirement: MountRequirement
) -> tuple[Path, Mount]:
    if not requirement.purpose or "\x00" in requirement.purpose:
        raise HostContextError("mount requirement purpose must be non-empty")
    lexical = _absolute_container_path(requirement.container_path)
    try:
        canonical = lexical.resolve(strict=True)
    except OSError as exc:
        raise HostContextError(
            f"required {requirement.purpose} path is missing or inaccessible"
        ) from exc
    lexical_mount = _selected_mount(lexical, mounts, access=requirement.access)
    canonical_mount = _selected_mount(canonical, mounts, access=requirement.access)
    if lexical_mount.destination != canonical_mount.destination:
        raise HostContextError(
            f"required {requirement.purpose} path resolves across a Docker mount boundary"
        )
    if canonical_mount.kind != "bind":
        raise HostContextError(f"required {requirement.purpose} path must use a bind mount")
    _validate_kind(canonical, requirement.kind)
    return canonical, canonical_mount


def _selected_mount(path: Path, mounts: Sequence[Mount], *, access: PathAccess) -> Mount:
    try:
        selected = covering_mount(path, mounts, require_writable=access is PathAccess.write)
    except PreflightError as exc:
        raise HostContextError(str(exc)) from exc
    if selected.kind != "bind":
        raise HostContextError(f"container path {path} must use a bind mount")
    return selected


def _translation(
    canonical: Path,
    mount: Mount,
    *,
    access: PathAccess,
    kind: PathKind,
) -> TranslatedPath:
    destination = PurePosixPath(mount.destination)
    selected = PurePosixPath(str(canonical))
    try:
        relative = selected.relative_to(destination)
    except ValueError as exc:  # pragma: no cover - selected by covering_mount.
        raise HostContextError("canonical path is outside its selected Docker mount") from exc
    host_root = _validated_host_source(mount)
    host_path = host_root.joinpath(relative)
    if host_path != host_root and host_root not in host_path.parents:
        raise HostContextError("translated host path escapes its inspected mount source")
    return TranslatedPath(canonical, host_path, mount.destination, access, kind)


def _validated_host_source(mount: Mount) -> PurePosixPath:
    if "\x00" in mount.source:
        raise HostContextError("Docker mount source contains a NUL byte")
    source = PurePosixPath(mount.source)
    if not source.is_absolute() or ".." in source.parts or str(source) != mount.source:
        raise HostContextError("Docker mount source is not an absolute normalized host path")
    return source


def _absolute_container_path(path: Path) -> Path:
    if not path.is_absolute() or ".." in path.parts or "\x00" in str(path):
        raise HostContextError("container path must be absolute, normalized, and non-escaping")
    return path


def _absolute_successor_path(value: str) -> str:
    if "\x00" in value:
        raise HostContextError("successor destination contains a NUL byte")
    path = PurePosixPath(value)
    if not path.is_absolute() or ".." in path.parts or str(path) != value:
        raise HostContextError("successor destination must be absolute, normalized, and non-escaping")
    return value


def _validate_kind(path: Path, kind: PathKind) -> None:
    try:
        mode = path.stat().st_mode
    except OSError as exc:
        raise HostContextError(f"cannot inspect required {kind.value} path {path}") from exc
    matches = {
        PathKind.directory: stat.S_ISDIR(mode),
        PathKind.file: stat.S_ISREG(mode),
        PathKind.socket: stat.S_ISSOCK(mode),
    }
    if not matches[kind]:
        raise HostContextError(f"container path {path} is not a {kind.value}")


def _account_name(value: str, field: str) -> str:
    if re.fullmatch(r"[a-z_][a-z0-9_-]{0,31}", value) is None:
        raise HostContextError(f"{field} is not a safe local account name")
    return value


def _positive_id(value: int, field: str) -> None:
    if isinstance(value, bool) or value <= 0:
        raise HostContextError(f"{field} must be a positive integer")


def _write_exclusive(path: Path, payload: bytes, mode: int) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, mode)
    try:
        os.fchmod(descriptor, mode)
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:  # pragma: no cover - os.write either writes or raises.
                raise OSError("short write while creating staged file")
            view = view[written:]
    except BaseException:
        os.close(descriptor)
        path.unlink(missing_ok=True)
        raise
    else:
        os.close(descriptor)
