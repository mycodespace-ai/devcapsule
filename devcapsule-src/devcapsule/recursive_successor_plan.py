"""Machine-readable expected Docker plan for the recursive successor.

Stage 6 requires the independent inspector to compare a launched successor
against the complete plan that was actually requested rather than against a few
spot-checked fields. The plan is derived from the translated ``docker run``
arguments, retained beside the run manifest, and replayed by a later
``inspect-successor`` process.

Daemon-side bind sources are host paths. They are retained so the inspector can
prove that each mount still resolves to the exact translated source, but they
never reach ordinary evidence or an error message: ``to_mapping`` redacts them
unless host paths are explicitly requested.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from typing import Any, Mapping, Sequence


REDACTED_HOST_PATH = "<redacted-host-path>"

_VALUE_FLAGS = frozenset(
    {
        "--cap-add",
        "--cap-drop",
        "--env",
        "--group-add",
        "--ipc",
        "--label",
        "--memory",
        "--mount",
        "--name",
        "--network",
        "--pids-limit",
        "--platform",
        "--restart",
        "--security-opt",
        "--tmpfs",
        "--user",
        "--workdir",
    }
)
_BOOLEAN_FLAGS = frozenset({"--detach", "--privileged", "--read-only", "--rm", "-i"})
# Flags that describe how Docker obtains the image rather than the resulting
# container. They are deliberately not part of the comparable plan.
_IGNORED_FLAGS = frozenset({"--pull"})


class SuccessorPlanError(Exception):
    """A successor plan could not be derived, retained, or matched."""


@dataclass(frozen=True)
class ExpectedMount:
    """One planned mount, keyed by its destination inside the successor."""

    destination: str
    kind: str
    read_only: bool
    source: str = field(repr=False, default="")

    def to_mapping(self, *, show_host_paths: bool = False) -> dict[str, Any]:
        return {
            "destination": self.destination,
            "kind": self.kind,
            "mode": "ro" if self.read_only else "rw",
            "source": self.source if show_host_paths else REDACTED_HOST_PATH,
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> ExpectedMount:
        mode = _required_string(value, "mode")
        if mode not in ("ro", "rw"):
            raise SuccessorPlanError("retained expected plan has an invalid mount mode")
        return cls(
            destination=_required_string(value, "destination"),
            kind=_required_string(value, "kind"),
            read_only=mode == "ro",
            source=_required_string(value, "source"),
        )


@dataclass(frozen=True)
class ExpectedSuccessorPlan:
    """The complete comparable Docker plan requested for one successor."""

    name: str
    image_reference: str
    image_identity: str
    working_dir: str
    user: str
    group_add: tuple[str, ...]
    labels: Mapping[str, str]
    image_labels: Mapping[str, str]
    environment: Mapping[str, str]
    secret_environment: tuple[str, ...]
    mounts: tuple[ExpectedMount, ...]
    tmpfs: Mapping[str, str]
    network_mode: str
    ipc_mode: str
    pids_limit: int | None
    memory_limit_bytes: int | None
    read_only_root: bool
    privileged: bool
    cap_add: tuple[str, ...]
    cap_drop: tuple[str, ...]
    security_opt: tuple[str, ...]
    runtime_plan_destination: str
    runtime_plan_digest: str
    # The planned ``--platform`` (``linux/amd64``), when the daemon emulates the
    # capsule platform; None when the image's own platform is the daemon's.
    platform: str | None = None

    def to_mapping(self, *, show_host_paths: bool = False) -> dict[str, Any]:
        mapping = {
            "schema_version": 1,
            "name": self.name,
            "image_reference": self.image_reference,
            "image_identity": self.image_identity,
            "working_dir": self.working_dir,
            "user": self.user,
            "group_add": list(self.group_add),
            "labels": dict(self.labels),
            "image_labels": dict(self.image_labels),
            "environment": dict(self.environment),
            "secret_environment": list(self.secret_environment),
            "mounts": [
                mount.to_mapping(show_host_paths=show_host_paths) for mount in self.mounts
            ],
            "tmpfs": dict(self.tmpfs),
            "network_mode": self.network_mode,
            "ipc_mode": self.ipc_mode,
            "pids_limit": self.pids_limit,
            "memory_limit_bytes": self.memory_limit_bytes,
            "read_only_root": self.read_only_root,
            "privileged": self.privileged,
            "cap_add": list(self.cap_add),
            "cap_drop": list(self.cap_drop),
            "security_opt": list(self.security_opt),
            "runtime_plan_destination": self.runtime_plan_destination,
            "runtime_plan_digest": self.runtime_plan_digest,
        }
        # Only an emulated plan carries the key, so a native plan's digest is
        # the one a launcher without emulation computed for it.
        if self.platform is not None:
            mapping["platform"] = self.platform
        return mapping

    def to_json(self, *, show_host_paths: bool = False) -> str:
        return json.dumps(
            self.to_mapping(show_host_paths=show_host_paths),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    def digest(self) -> str:
        """Return the SHA-256 of the exact retained plan, host sources included."""

        return hashlib.sha256(self.to_json(show_host_paths=True).encode("utf-8")).hexdigest()

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> ExpectedSuccessorPlan:
        if value.get("schema_version") != 1:
            raise SuccessorPlanError("retained expected plan has an unsupported schema version")
        mounts = value.get("mounts")
        if not isinstance(mounts, list):
            raise SuccessorPlanError("retained expected plan has no mount set")
        return cls(
            name=_required_string(value, "name"),
            image_reference=_required_string(value, "image_reference"),
            image_identity=_required_string(value, "image_identity"),
            working_dir=_required_string(value, "working_dir"),
            user=_required_string(value, "user"),
            group_add=_string_tuple(value.get("group_add")),
            labels=_string_mapping(value.get("labels"), "labels"),
            image_labels=_string_mapping(value.get("image_labels"), "image_labels"),
            environment=_string_mapping(value.get("environment"), "environment"),
            secret_environment=_string_tuple(value.get("secret_environment")),
            mounts=tuple(ExpectedMount.from_mapping(_object(entry)) for entry in mounts),
            tmpfs=_string_mapping(value.get("tmpfs"), "tmpfs"),
            network_mode=_required_string(value, "network_mode"),
            ipc_mode=_required_string(value, "ipc_mode"),
            pids_limit=_optional_int(value.get("pids_limit"), "pids_limit"),
            memory_limit_bytes=_optional_int(value.get("memory_limit_bytes"), "memory_limit_bytes"),
            read_only_root=_required_bool(value, "read_only_root"),
            privileged=_required_bool(value, "privileged"),
            cap_add=_string_tuple(value.get("cap_add")),
            cap_drop=_string_tuple(value.get("cap_drop")),
            security_opt=_string_tuple(value.get("security_opt")),
            runtime_plan_destination=_required_string(value, "runtime_plan_destination"),
            runtime_plan_digest=_required_string(value, "runtime_plan_digest"),
            platform=_optional_string(value.get("platform"), "platform"),
        )

    @classmethod
    def from_docker_args(
        cls,
        docker_args: Sequence[str],
        *,
        image_reference: str,
        image_identity: str,
        image_labels: Mapping[str, str],
        runtime_plan_destination: str,
        runtime_plan_digest: str,
    ) -> ExpectedSuccessorPlan:
        """Derive the comparable plan from exactly the translated launch arguments."""

        parsed = _parse_docker_args(docker_args)
        environment: dict[str, str] = {}
        secret_environment: list[str] = []
        for value in parsed.repeated("--env"):
            name, separator, assigned = value.partition("=")
            if not name:
                raise SuccessorPlanError("planned environment entry has no name")
            if separator:
                environment[name] = assigned
            else:
                # Pass-through entries forward whatever the host holds. Their
                # values are never planned, compared, or recorded.
                secret_environment.append(name)
        mounts = tuple(
            sorted(
                (_parsed_mount(value) for value in parsed.repeated("--mount")),
                key=lambda mount: mount.destination,
            )
        )
        destinations = [mount.destination for mount in mounts]
        if len(set(destinations)) != len(destinations):
            raise SuccessorPlanError("planned mounts contain a duplicate destination")
        if runtime_plan_destination not in set(destinations):
            raise SuccessorPlanError("planned mounts do not include the checkout runtime plan")
        labels: dict[str, str] = {}
        for value in parsed.repeated("--label"):
            name, separator, assigned = value.partition("=")
            if not name or not separator:
                raise SuccessorPlanError("planned label is not a name=value pair")
            labels[name] = assigned
        # The materialized image's own identity labels are inherited by the
        # container. Pinning every one of them proves the successor carries the
        # expected formation, base, and component lineage rather than a
        # look-alike image that merely answers to the same reference.
        managed_labels = {
            name: value
            for name, value in image_labels.items()
            if name.startswith("devcapsule.")
        }
        for required in ("devcapsule.materialization.identity", "devcapsule.materialization.base-identity"):
            if not managed_labels.get(required):
                raise SuccessorPlanError(f"canonical environment declares no {required}")
        return cls(
            name=parsed.single("--name"),
            image_reference=image_reference,
            image_identity=image_identity,
            working_dir=parsed.single("--workdir"),
            user=parsed.single("--user"),
            group_add=tuple(sorted(parsed.repeated("--group-add"))),
            labels=labels,
            image_labels=managed_labels,
            environment=environment,
            secret_environment=tuple(sorted(secret_environment)),
            mounts=mounts,
            tmpfs={
                destination: options
                for destination, options in (
                    _parsed_tmpfs(value) for value in parsed.repeated("--tmpfs")
                )
            },
            network_mode=parsed.single("--network"),
            ipc_mode=parsed.single("--ipc"),
            pids_limit=_optional_int(parsed.optional("--pids-limit"), "--pids-limit"),
            memory_limit_bytes=_optional_int(parsed.optional("--memory"), "--memory"),
            read_only_root=parsed.flag("--read-only"),
            privileged=parsed.flag("--privileged"),
            cap_add=tuple(sorted(parsed.repeated("--cap-add"))),
            cap_drop=tuple(sorted(parsed.repeated("--cap-drop"))),
            security_opt=tuple(sorted(parsed.repeated("--security-opt"))),
            runtime_plan_destination=runtime_plan_destination,
            runtime_plan_digest=runtime_plan_digest,
            platform=parsed.optional("--platform"),
        )


def compare_inspection(
    plan: ExpectedSuccessorPlan,
    inspection: Mapping[str, Any],
) -> dict[str, str]:
    """Compare one ``docker inspect`` result against the complete expected plan.

    Every failure raises with a destination-level message so that neither host
    sources nor pass-through environment values reach retained evidence.
    """

    config = _section(inspection, "Config")
    host_config = _section(inspection, "HostConfig")
    state = _section(inspection, "State")

    if inspection.get("Name") != f"/{plan.name}":
        raise SuccessorPlanError("successor name does not match the deterministic run name")
    if inspection.get("Image") != plan.image_identity:
        raise SuccessorPlanError("successor image ID does not match materialization evidence")
    # The image ID fixes the architecture; where the daemon also reports the
    # platform it ran, an emulated plan must have run as the one it named.
    descriptor = inspection.get("ImageManifestDescriptor")
    reported = descriptor.get("platform") if isinstance(descriptor, Mapping) else None
    if plan.platform is not None and isinstance(reported, Mapping):
        if f"{reported.get('os')}/{reported.get('architecture')}" != plan.platform:
            raise SuccessorPlanError("successor platform does not match the planned --platform")
    if config.get("Image") != plan.image_reference:
        raise SuccessorPlanError("successor image reference does not match the canonical environment")

    labels = _string_mapping(config.get("Labels"), "Config.Labels")
    for name, value in sorted(plan.labels.items()):
        if labels.get(name) != value:
            raise SuccessorPlanError(f"successor label {name!r} does not match the expected plan")
    for name, value in sorted(plan.image_labels.items()):
        if labels.get(name) != value:
            raise SuccessorPlanError(
                f"successor image label {name!r} does not match the canonical environment"
            )

    if config.get("User") != plan.user:
        raise SuccessorPlanError("successor runtime user does not match the expected plan")
    if config.get("WorkingDir") != plan.working_dir:
        raise SuccessorPlanError("successor working directory does not match the expected plan")

    environment = _environment(config.get("Env"))
    for name, value in sorted(plan.environment.items()):
        if name not in environment:
            raise SuccessorPlanError(f"successor environment is missing {name!r}")
        if environment[name] != value:
            raise SuccessorPlanError(
                f"successor environment value for {name!r} does not match the expected plan"
            )

    _compare_mounts(plan, inspection)

    if str(host_config.get("NetworkMode")) != plan.network_mode:
        raise SuccessorPlanError("successor network mode does not match the expected plan")
    if str(host_config.get("IpcMode")) != plan.ipc_mode:
        raise SuccessorPlanError("successor IPC mode does not match the expected plan")
    if bool(host_config.get("Privileged")) != plan.privileged:
        raise SuccessorPlanError("successor privileged state does not match the expected plan")
    if bool(host_config.get("ReadonlyRootfs")) != plan.read_only_root:
        raise SuccessorPlanError("successor root filesystem mode does not match the expected plan")
    for key, expected in (
        ("CapAdd", plan.cap_add),
        ("CapDrop", plan.cap_drop),
        ("SecurityOpt", plan.security_opt),
        ("GroupAdd", plan.group_add),
    ):
        if _sorted_strings(host_config.get(key)) != expected:
            raise SuccessorPlanError(f"successor {key} does not match the expected plan")
    if _limit(host_config.get("Memory")) != _limit(plan.memory_limit_bytes):
        raise SuccessorPlanError("successor memory limit does not match the expected plan")
    if _limit(host_config.get("PidsLimit")) != _limit(plan.pids_limit):
        raise SuccessorPlanError("successor PID limit does not match the expected plan")

    restart = _section(host_config, "RestartPolicy", required=False)
    if str(restart.get("Name", "")) not in ("", "no"):
        raise SuccessorPlanError("successor declares an unplanned restart policy")
    if _limit(inspection.get("RestartCount")) != 0:
        raise SuccessorPlanError("successor has restarted since launch")
    if state.get("Running") is not True:
        raise SuccessorPlanError("successor is not running")

    return {
        "container_identity": "pass",
        "image_identity": "pass",
        "labels": "pass",
        "formation_identity": "pass",
        "runtime_identity": "pass",
        "environment": "pass",
        "mounts": "pass",
        "security_settings": "pass",
        "resource_limits": "pass",
        "restart_policy": "pass",
        "running": "pass",
    }


def _compare_mounts(plan: ExpectedSuccessorPlan, inspection: Mapping[str, Any]) -> None:
    entries = inspection.get("Mounts")
    if entries is None:
        entries = []
    if not isinstance(entries, list):
        raise SuccessorPlanError("successor inspection has a malformed mount set")
    attached: dict[str, Mapping[str, Any]] = {}
    ephemeral: set[str] = set()
    for entry in entries:
        observed = _object(entry)
        destination = str(observed.get("Destination", ""))
        if not destination:
            raise SuccessorPlanError("successor inspection has a mount without a destination")
        if str(observed.get("Type")) == "tmpfs":
            ephemeral.add(destination)
            continue
        if destination in attached:
            raise SuccessorPlanError(f"successor mount {destination} is declared more than once")
        attached[destination] = observed

    expected = {mount.destination: mount for mount in plan.mounts}
    missing = sorted(set(expected) - set(attached))
    if missing:
        raise SuccessorPlanError(f"successor is missing planned mounts: {', '.join(missing)}")
    unplanned = sorted(set(attached) - set(expected))
    if unplanned:
        raise SuccessorPlanError(f"successor has unplanned mounts: {', '.join(unplanned)}")

    for destination, mount in sorted(expected.items()):
        entry = attached[destination]
        if str(entry.get("Type")) != mount.kind:
            raise SuccessorPlanError(f"successor mount {destination} has an unplanned type")
        if bool(entry.get("RW")) is mount.read_only:
            raise SuccessorPlanError(
                f"successor mount {destination} does not match its planned read-only mode"
            )
        if mount.kind == "bind" and str(entry.get("Source", "")) != mount.source:
            raise SuccessorPlanError(
                f"successor mount {destination} does not resolve to the retained translated source"
            )

    tmpfs = _string_mapping(_section(inspection, "HostConfig").get("Tmpfs"), "HostConfig.Tmpfs")
    if tmpfs != dict(plan.tmpfs):
        raise SuccessorPlanError("successor tmpfs set does not match the expected plan")
    unplanned_ephemeral = sorted(ephemeral - set(plan.tmpfs))
    if unplanned_ephemeral:
        raise SuccessorPlanError(
            f"successor has unplanned tmpfs mounts: {', '.join(unplanned_ephemeral)}"
        )


@dataclass(frozen=True)
class _ParsedArgs:
    values: Mapping[str, tuple[str, ...]]
    flags: frozenset[str]

    def repeated(self, flag: str) -> tuple[str, ...]:
        return self.values.get(flag, ())

    def optional(self, flag: str) -> str | None:
        found = self.repeated(flag)
        if not found:
            return None
        if len(found) != 1:
            raise SuccessorPlanError(f"planned launch repeats {flag}")
        return found[0]

    def single(self, flag: str) -> str:
        found = self.optional(flag)
        if found is None:
            raise SuccessorPlanError(f"planned launch does not declare {flag}")
        return found

    def flag(self, name: str) -> bool:
        return name in self.flags


def _parse_docker_args(docker_args: Sequence[str]) -> _ParsedArgs:
    values: dict[str, list[str]] = {}
    flags: set[str] = set()
    index = 0
    while index < len(docker_args):
        argument = docker_args[index]
        name, separator, inline = argument.partition("=")
        if name in _IGNORED_FLAGS:
            index += 1
            continue
        if name in _VALUE_FLAGS:
            if separator:
                values.setdefault(name, []).append(inline)
                index += 1
                continue
            if index + 1 >= len(docker_args):
                raise SuccessorPlanError(f"planned launch flag {name} has no value")
            values.setdefault(name, []).append(docker_args[index + 1])
            index += 2
            continue
        if argument in _BOOLEAN_FLAGS:
            flags.add(argument)
            index += 1
            continue
        raise SuccessorPlanError(f"planned launch uses an unmodelled Docker flag: {argument}")
    return _ParsedArgs({flag: tuple(found) for flag, found in values.items()}, frozenset(flags))


def _parsed_mount(value: str) -> ExpectedMount:
    fields = value.split(",")
    selected: dict[str, str] = {}
    read_only = False
    for entry in fields:
        if entry in ("ro", "readonly"):
            read_only = True
            continue
        key, separator, assigned = entry.partition("=")
        if not separator:
            raise SuccessorPlanError("planned mount has an unmodelled field")
        if key in ("readonly", "ro"):
            read_only = assigned.lower() in ("1", "true")
            continue
        selected[key] = assigned
    kind = selected.get("type", "")
    if kind not in ("bind", "volume"):
        raise SuccessorPlanError("planned mount has an unmodelled type")
    destination = selected.get("dst") or selected.get("destination") or selected.get("target")
    if not destination:
        raise SuccessorPlanError("planned mount has no destination")
    source = selected.get("src") or selected.get("source") or ""
    if kind == "bind" and not source:
        raise SuccessorPlanError("planned bind mount has no source")
    return ExpectedMount(destination=destination, kind=kind, read_only=read_only, source=source)


def _parsed_tmpfs(value: str) -> tuple[str, str]:
    destination, separator, options = value.partition(":")
    if not destination:
        raise SuccessorPlanError("planned tmpfs entry has no destination")
    return destination, options if separator else ""


def _environment(value: Any) -> dict[str, str]:
    if value is None:
        return {}
    if not isinstance(value, list):
        raise SuccessorPlanError("successor inspection has a malformed environment")
    environment: dict[str, str] = {}
    for entry in value:
        if not isinstance(entry, str):
            raise SuccessorPlanError("successor inspection has a malformed environment entry")
        name, _separator, assigned = entry.partition("=")
        environment[name] = assigned
    return environment


def _section(value: Mapping[str, Any], name: str, *, required: bool = True) -> Mapping[str, Any]:
    section = value.get(name)
    if section is None and not required:
        return {}
    if not isinstance(section, Mapping):
        raise SuccessorPlanError(f"successor inspection has no usable {name} section")
    return section


def _object(value: Any) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise SuccessorPlanError("successor inspection has a malformed object entry")
    return value


def _sorted_strings(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list) or any(not isinstance(entry, str) for entry in value):
        raise SuccessorPlanError("successor inspection has a malformed string list")
    return tuple(sorted(value))


def _string_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list) or any(not isinstance(entry, str) for entry in value):
        raise SuccessorPlanError("retained expected plan has a malformed string list")
    return tuple(value)


def _string_mapping(value: Any, name: str) -> dict[str, str]:
    if value is None:
        return {}
    if not isinstance(value, Mapping) or any(
        not isinstance(key, str) or not isinstance(entry, str) for key, entry in value.items()
    ):
        raise SuccessorPlanError(f"{name} is not a string mapping")
    return dict(value)


def _required_string(value: Mapping[str, Any], name: str) -> str:
    found = value.get(name)
    if not isinstance(found, str):
        raise SuccessorPlanError(f"retained expected plan has no usable {name}")
    return found


def _required_bool(value: Mapping[str, Any], name: str) -> bool:
    found = value.get(name)
    if not isinstance(found, bool):
        raise SuccessorPlanError(f"retained expected plan has no usable {name}")
    return found


def _optional_string(value: Any, name: str) -> str | None:
    if value is not None and (not isinstance(value, str) or not value):
        raise SuccessorPlanError(f"retained expected plan has no usable {name}")
    return value


def _optional_int(value: Any, name: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise SuccessorPlanError(f"{name} is not an integer")
    try:
        return int(value)
    except ValueError as exc:
        raise SuccessorPlanError(f"{name} is not an integer") from exc


def _limit(value: Any) -> int:
    """Return a comparable limit where Docker reports absence as 0."""

    if value is None:
        return 0
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise SuccessorPlanError("successor inspection has a malformed numeric limit")
    try:
        return int(value)
    except ValueError as exc:
        raise SuccessorPlanError("successor inspection has a malformed numeric limit") from exc
