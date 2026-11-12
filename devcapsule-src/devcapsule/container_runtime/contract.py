"""Versioned, structured contract consumed inside a capsule."""

from __future__ import annotations

from dataclasses import dataclass, replace
import json
from pathlib import Path
import re
from typing import Any, Mapping

__all__ = [
    "CONTAINED_DISPLAY_TRANSPORT",
    "Component",
    "ComponentRuntimeTemplate",
    "ConsolePlan",
    "DISPLAY_TRANSPORTS",
    "DisplayPlan",
    "HOST_X11_DISPLAY_TRANSPORT",
    "INFRASTRUCTURE_FAILURE_EXIT_CODE",
    "Identity",
    "LogsPlan",
    "PersistenceContract",
    "RuntimePlan",
    "RuntimePlanError",
    "StateSlot",
    "StateSlotDeclaration",
]


INFRASTRUCTURE_FAILURE_EXIT_CODE = 70
"""The capsule's exit code when a supervised component died, not the IDE.

The supervisor returns it in place of the foreground child's status, and the
launcher reads it to tell a failed session from one the IDE ended; EX_SOFTWARE
in sysexits.h, outside the codes an IDE returns."""


class RuntimePlanError(ValueError):
    """The runtime plan is malformed or unsupported."""


def _required_string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value or "\x00" in value:
        raise RuntimePlanError(f"{field} must be a non-empty string")
    return value


def _required_choice(value: object, field: str, choices: set[str]) -> str:
    selected = _required_string(value, field)
    if selected not in choices:
        expected = ", ".join(sorted(choices))
        raise RuntimePlanError(f"{field} must be one of: {expected}")
    return selected


def _absolute_path(value: object, field: str) -> str:
    selected = _required_string(value, field)
    path = Path(selected)
    if not path.is_absolute() or ".." in path.parts:
        raise RuntimePlanError(f"{field} must be an absolute normalized container path")
    return selected


def _identifier(value: object, field: str) -> str:
    selected = _required_string(value, field)
    if re.fullmatch(r"[a-z0-9][a-z0-9._-]*", selected) is None:
        raise RuntimePlanError(f"{field} must be a lowercase stable identifier")
    return selected


@dataclass(frozen=True)
class Identity:
    uid: int
    gid: int
    user: str = "devcapsule"


@dataclass(frozen=True)
class StateSlot:
    name: str
    path: str


@dataclass(frozen=True)
class Component:
    id: str
    adapter: str
    configuration: Mapping[str, object]
    environment: Mapping[str, str]

    def slot_name(self, local_name: str) -> str:
        return f"{self.id}/{local_name}"


@dataclass(frozen=True)
class StateSlotDeclaration:
    name: str
    container_path: str
    kind: str
    sensitivity: str
    default_scope: str
    storage: str
    concurrent: bool
    owner: str
    permissions: str
    reconstructable: bool
    deletion_effect: str
    home_overlay: bool = False

    @classmethod
    def from_mapping(cls, value: object, field: str) -> StateSlotDeclaration:
        if not isinstance(value, dict):
            raise RuntimePlanError(f"{field} must be an object")
        name = _identifier(value.get("name"), f"{field}.name")
        concurrent = value.get("concurrent")
        if not isinstance(concurrent, bool):
            raise RuntimePlanError(f"{field}.concurrent must be a boolean")
        reconstructable = value.get("reconstructable")
        if not isinstance(reconstructable, bool):
            raise RuntimePlanError(f"{field}.reconstructable must be a boolean")
        home_overlay = value.get("home_overlay", False)
        if not isinstance(home_overlay, bool):
            raise RuntimePlanError(f"{field}.home_overlay must be a boolean")
        permissions = _required_string(value.get("permissions"), f"{field}.permissions")
        if len(permissions) != 4 or permissions[0] != "0" or any(character not in "01234567" for character in permissions):
            raise RuntimePlanError(f"{field}.permissions must be a four-digit octal string")
        return cls(
            name=name,
            container_path=_absolute_path(value.get("container_path"), f"{field}.container_path"),
            kind=_required_choice(value.get("kind"), f"{field}.kind", {"durable", "state", "cache"}),
            sensitivity=_required_choice(
                value.get("sensitivity"),
                f"{field}.sensitivity",
                {"ordinary", "personal", "credentials"},
            ),
            default_scope=_required_choice(
                value.get("default_scope"), f"{field}.default_scope", {"checkout", "project"}
            ),
            storage=_required_choice(
                value.get("storage"), f"{field}.storage", {"directory", "docker-volume"}
            ),
            concurrent=concurrent,
            owner=_required_choice(value.get("owner"), f"{field}.owner", {"runtime-user"}),
            permissions=permissions,
            reconstructable=reconstructable,
            deletion_effect=_required_string(value.get("deletion_effect"), f"{field}.deletion_effect"),
            home_overlay=home_overlay,
        )

    def to_mapping(self) -> dict[str, object]:
        value: dict[str, object] = {
            "name": self.name,
            "container_path": self.container_path,
            "kind": self.kind,
            "sensitivity": self.sensitivity,
            "default_scope": self.default_scope,
            "storage": self.storage,
            "concurrent": self.concurrent,
            "owner": self.owner,
            "permissions": self.permissions,
            "reconstructable": self.reconstructable,
            "deletion_effect": self.deletion_effect,
        }
        if self.home_overlay:
            value["home_overlay"] = True
        return value


@dataclass(frozen=True)
class PersistenceContract:
    home: str
    xdg: str
    state_slots: tuple[StateSlotDeclaration, ...]


CONTAINED_DISPLAY_TRANSPORT = "contained"
HOST_X11_DISPLAY_TRANSPORT = "host-x11"
DISPLAY_TRANSPORTS = frozenset({CONTAINED_DISPLAY_TRANSPORT, HOST_X11_DISPLAY_TRANSPORT})


@dataclass(frozen=True)
class DisplayPlan:
    """How the interactive surface gets a display, as the run manifest records it.

    ``contained``: the entrypoint starts the capsule's own X server and the
    noVNC bridge, which listens at ``listen_address``:``port`` inside the
    container and admits only requests carrying the token read from
    ``token_path``. ``host-x11``: the launcher bound the host X socket and
    credential into the capsule (the authorized passthrough); no listener, no
    token. A plan without a display section means ``host-x11``, which is what
    every plan meant before the section existed.
    """

    transport: str
    listen_address: str = ""
    port: int = 0
    token_path: str = ""

    @classmethod
    def contained(cls, listen_address: str, port: int, token_path: str) -> DisplayPlan:
        return cls(CONTAINED_DISPLAY_TRANSPORT, listen_address, port, token_path)

    @classmethod
    def host_x11(cls) -> DisplayPlan:
        return cls(HOST_X11_DISPLAY_TRANSPORT)

    @property
    def is_contained(self) -> bool:
        return self.transport == CONTAINED_DISPLAY_TRANSPORT

    @classmethod
    def from_mapping(cls, value: object, field: str) -> DisplayPlan:
        if not isinstance(value, dict):
            raise RuntimePlanError(f"{field} must be an object")
        transport = _required_choice(value.get("transport"), f"{field}.transport", set(DISPLAY_TRANSPORTS))
        if transport == HOST_X11_DISPLAY_TRANSPORT:
            extra = sorted(set(value) - {"transport"})
            if extra:
                raise RuntimePlanError(f"{field} for {transport} must not carry {', '.join(extra)}")
            return cls.host_x11()
        listen_address = _required_string(value.get("listen_address"), f"{field}.listen_address")
        if re.fullmatch(r"[0-9A-Za-z.:\-]+", listen_address) is None:
            raise RuntimePlanError(f"{field}.listen_address must be a host address")
        port = value.get("port")
        if not isinstance(port, int) or isinstance(port, bool) or not 1 <= port <= 65535:
            raise RuntimePlanError(f"{field}.port must be a TCP port number")
        token_path = _absolute_path(value.get("token_path"), f"{field}.token_path")
        return cls.contained(listen_address, port, token_path)

    def to_mapping(self) -> dict[str, object]:
        if not self.is_contained:
            return {"transport": self.transport}
        return {
            "transport": self.transport,
            "listen_address": self.listen_address,
            "port": self.port,
            "token_path": self.token_path,
        }


@dataclass(frozen=True)
class ConsolePlan:
    """The capsule web console, as the run manifest records it.

    The entrypoint starts the console beside the interactive surface, or
    alone in a headless capsule. It listens at ``listen_address``:``port``
    inside the container and admits only requests carrying the token read
    from ``token_path``, the same model as the contained display. A plan
    without a console section starts none, which is what every plan meant
    before the section existed.

    ``source_path``, when set, names a checkout of the console's own source
    inside the container; the entrypoint runs that source instead of the
    image's installed copy. The launcher sets it only for a DevCapsule
    checkout that carries ``devcapsule-webconsole/`` (the self-hosting
    exception), so an edit shows on the next run without a base release.
    """

    listen_address: str
    port: int
    token_path: str
    source_path: str = ""

    @classmethod
    def from_mapping(cls, value: object, field: str) -> ConsolePlan:
        if not isinstance(value, dict):
            raise RuntimePlanError(f"{field} must be an object")
        extra = sorted(set(value) - {"listen_address", "port", "token_path", "source_path"})
        if extra:
            raise RuntimePlanError(f"{field} must not carry {', '.join(extra)}")
        listen_address = _required_string(value.get("listen_address"), f"{field}.listen_address")
        if re.fullmatch(r"[0-9A-Za-z.:\-]+", listen_address) is None:
            raise RuntimePlanError(f"{field}.listen_address must be a host address")
        port = value.get("port")
        if not isinstance(port, int) or isinstance(port, bool) or not 1 <= port <= 65535:
            raise RuntimePlanError(f"{field}.port must be a TCP port number")
        token_path = _absolute_path(value.get("token_path"), f"{field}.token_path")
        source = value.get("source_path", "")
        source_path = "" if source == "" else _absolute_path(source, f"{field}.source_path")
        return cls(listen_address, port, token_path, source_path)

    def to_mapping(self) -> dict[str, object]:
        result: dict[str, object] = {
            "listen_address": self.listen_address,
            "port": self.port,
            "token_path": self.token_path,
        }
        if self.source_path:
            result["source_path"] = self.source_path
        return result


@dataclass(frozen=True)
class LogsPlan:
    """Where the session's logs live inside the capsule, as the run manifest records it.

    ``directory`` is a host-backed bind mount the launcher prepared, one per
    session, so the files outlive the container. The entrypoint writes the
    supervisor's log there and tees every child's output into its own file,
    ``devcapsule-<child>.log``; see ``devcapsule.logs``. A plan without a
    logs section writes no files, which is what every plan meant before the
    section existed: the console sees everything, nothing is kept.

    ``segment_bytes`` and ``rotations``, both or neither, ask the entrypoint
    to rotate every file with logrotate at that size, keeping that many
    older segments. Without them the files are cut at the runtime's fixed
    bound, which is what a plan from before rotation existed asks for.
    """

    directory: str
    segment_bytes: int = 0
    rotations: int = 0

    @property
    def rotates(self) -> bool:
        return self.segment_bytes > 0 and self.rotations > 0

    @classmethod
    def from_mapping(cls, value: object, field: str) -> LogsPlan:
        if not isinstance(value, dict):
            raise RuntimePlanError(f"{field} must be an object")
        extra = sorted(set(value) - {"directory", "segment_bytes", "rotations"})
        if extra:
            raise RuntimePlanError(f"{field} must not carry {', '.join(extra)}")
        directory = _absolute_path(value.get("directory"), f"{field}.directory")
        segment_bytes = value.get("segment_bytes", 0)
        rotations = value.get("rotations", 0)
        for name, number in (("segment_bytes", segment_bytes), ("rotations", rotations)):
            if not isinstance(number, int) or isinstance(number, bool) or number < 0:
                raise RuntimePlanError(f"{field}.{name} must be a non-negative integer")
        if ("segment_bytes" in value) != ("rotations" in value) or (segment_bytes > 0) != (rotations > 0):
            raise RuntimePlanError(f"{field}.segment_bytes and {field}.rotations go together")
        return cls(directory, segment_bytes, rotations)

    def to_mapping(self) -> dict[str, object]:
        result: dict[str, object] = {"directory": self.directory}
        if self.rotates:
            result["segment_bytes"] = self.segment_bytes
            result["rotations"] = self.rotations
        return result


@dataclass(frozen=True)
class ComponentRuntimeTemplate:
    version: int
    component: Component
    persistence: PersistenceContract

    @classmethod
    def from_mapping(cls, document: object) -> ComponentRuntimeTemplate:
        if not isinstance(document, dict):
            raise RuntimePlanError("component runtime template must be a JSON object")
        version = document.get("version")
        if version != 1:
            raise RuntimePlanError(f"unsupported component runtime template version: {version!r}")
        component_value = document.get("component")
        if not isinstance(component_value, dict):
            raise RuntimePlanError("component must be an object")
        component_id = _identifier(component_value.get("id"), "component.id")
        configuration = component_value.get("configuration", {})
        if not isinstance(configuration, dict):
            raise RuntimePlanError("component.configuration must be an object")
        environment = _environment_mapping(
            component_value.get("environment", {}), "component.environment"
        )
        persistence_value = component_value.get("persistence")
        if not isinstance(persistence_value, dict):
            raise RuntimePlanError("component.persistence must be an object")
        slots_value = persistence_value.get("state_slots", [])
        if not isinstance(slots_value, list):
            raise RuntimePlanError("component.persistence.state_slots must be an array")
        slots = tuple(
            StateSlotDeclaration.from_mapping(slot, f"component.persistence.state_slots[{index}]")
            for index, slot in enumerate(slots_value)
        )
        cls._validate_slots(slots)
        return cls(
            version=1,
            component=Component(
                component_id,
                _required_string(component_value.get("adapter"), "component.adapter"),
                configuration,
                environment,
            ),
            persistence=PersistenceContract(
                home=_required_choice(
                    persistence_value.get("home"),
                    "component.persistence.home",
                    {"available", "required"},
                ),
                xdg=_required_choice(
                    persistence_value.get("xdg"),
                    "component.persistence.xdg",
                    {"home-relative", "unused"},
                ),
                state_slots=slots,
            ),
        )

    @classmethod
    def from_json(cls, value: str) -> ComponentRuntimeTemplate:
        try:
            document = json.loads(value)
        except json.JSONDecodeError as error:
            raise RuntimePlanError(f"component runtime template is not valid JSON: {error.msg}") from error
        return cls.from_mapping(document)

    @staticmethod
    def _validate_slots(slots: tuple[StateSlotDeclaration, ...]) -> None:
        names: set[str] = set()
        for slot in slots:
            if slot.name in names:
                raise RuntimePlanError(f"duplicate component state slot: {slot.name}")
            names.add(slot.name)
        home = Path("/home/devcapsule")
        for index, slot in enumerate(slots):
            path = Path(slot.container_path)
            if path == home:
                raise RuntimePlanError(
                    f"component state slot {slot.name!r} may not claim the home directory itself"
                )
            if home in path.parents:
                if not slot.home_overlay:
                    raise RuntimePlanError(
                        f"component state slot {slot.name!r} is beneath persistent home and must declare home_overlay"
                    )
                # Ruled 2026-09-02: overlay slots are direct children of home.
                # A deeper mount makes the runtime create the intermediate
                # parent root-owned, walling off its siblings (see the
                # antigravity ~/.gemini/config bug record).
                if path.parent != home:
                    raise RuntimePlanError(
                        f"component state slot {slot.name!r} must be a direct child of home; "
                        "a deeper mount leaves a runtime-created root-owned parent"
                    )
            for other in slots[index + 1 :]:
                other_path = Path(other.container_path)
                if path == other_path or path in other_path.parents or other_path in path.parents:
                    raise RuntimePlanError(
                        f"component state slots {slot.name!r} and {other.name!r} have conflicting container paths"
                    )

    def logical_slot_name(self, local_name: str) -> str:
        return self.component.slot_name(local_name)

    def to_mapping(self) -> dict[str, object]:
        component: dict[str, object] = {
            "id": self.component.id,
            "adapter": self.component.adapter,
            "configuration": dict(self.component.configuration),
            "persistence": {
                "home": self.persistence.home,
                "xdg": self.persistence.xdg,
                "state_slots": [slot.to_mapping() for slot in self.persistence.state_slots],
            },
        }
        if self.component.environment:
            component["environment"] = dict(self.component.environment)
        return {
            "version": self.version,
            "component": component,
        }


@dataclass(frozen=True)
class RuntimePlan:
    version: int
    project_path: str
    home: str
    identity: Identity
    state_slots: tuple[StateSlot, ...]
    component: Component
    ancillary_components: tuple[Component, ...] = ()
    host_integrations: tuple[str, ...] = ()
    display: DisplayPlan | None = None
    console: ConsolePlan | None = None
    logs: LogsPlan | None = None

    @classmethod
    def for_component(
        cls,
        template: ComponentRuntimeTemplate,
        *,
        project_path: str,
        home: str,
        identity: Identity,
        ancillary_templates: tuple[ComponentRuntimeTemplate, ...] = (),
        include_ancillary_state: bool = True,
    ) -> RuntimePlan:
        templates = (template, *ancillary_templates)
        cls._validate_components(tuple(item.component for item in templates))
        cls._validate_formation_slots(templates)
        return cls(
            version=1,
            project_path=_absolute_path(project_path, "project_path"),
            home=_absolute_path(home, "home"),
            identity=identity,
            state_slots=tuple(
                StateSlot(item.logical_slot_name(slot.name), slot.container_path)
                for item in (templates if include_ancillary_state else (template,))
                for slot in item.persistence.state_slots
            ),
            component=template.component,
            ancillary_components=tuple(item.component for item in ancillary_templates),
        )

    @staticmethod
    def _validate_formation_slots(templates: tuple[ComponentRuntimeTemplate, ...]) -> None:
        """No two components in one formation may claim overlapping state paths.

        Each template validates its own slots; only here does the whole
        formation meet, so slot-inside-another-component's-slot and duplicate
        container paths are rejected here (ruled 2026-09-02: a slot never
        mounts inside another component's slot).
        """

        claimed: list[tuple[str, str, Path]] = [
            (item.component.id, slot.name, Path(slot.container_path))
            for item in templates
            for slot in item.persistence.state_slots
        ]
        for index, (component_id, name, path) in enumerate(claimed):
            for other_id, other_name, other_path in claimed[index + 1 :]:
                if component_id == other_id:
                    continue
                if path == other_path or path in other_path.parents or other_path in path.parents:
                    raise RuntimePlanError(
                        f"component state slots {component_id}/{name} and "
                        f"{other_id}/{other_name} claim overlapping container paths"
                    )

    @classmethod
    def from_json(cls, value: str) -> RuntimePlan:
        try:
            document = json.loads(value)
        except json.JSONDecodeError as error:
            raise RuntimePlanError(f"runtime plan is not valid JSON: {error.msg}") from error
        return cls.from_mapping(document)

    @classmethod
    def from_file(cls, path: str | Path) -> RuntimePlan:
        try:
            return cls.from_json(Path(path).read_text(encoding="utf-8"))
        except OSError as error:
            raise RuntimePlanError(f"cannot read runtime plan {path}: {error}") from error

    @classmethod
    def from_mapping(cls, document: object) -> RuntimePlan:
        if not isinstance(document, dict):
            raise RuntimePlanError("runtime plan must be a JSON object")
        version = document.get("version")
        if version != 1:
            raise RuntimePlanError(f"unsupported runtime plan version: {version!r}")
        identity_value = document.get("identity")
        if not isinstance(identity_value, dict):
            raise RuntimePlanError("identity must be an object")
        uid, gid = identity_value.get("uid"), identity_value.get("gid")
        if not isinstance(uid, int) or isinstance(uid, bool) or uid < 0:
            raise RuntimePlanError("identity.uid must be a non-negative integer")
        if not isinstance(gid, int) or isinstance(gid, bool) or gid < 0:
            raise RuntimePlanError("identity.gid must be a non-negative integer")
        slots_value = document.get("state_slots", [])
        if not isinstance(slots_value, list):
            raise RuntimePlanError("state_slots must be an array")
        slots: list[StateSlot] = []
        names: set[str] = set()
        for index, slot in enumerate(slots_value):
            if not isinstance(slot, dict):
                raise RuntimePlanError(f"state_slots[{index}] must be an object")
            name = _required_string(slot.get("name"), f"state_slots[{index}].name")
            if name in names:
                raise RuntimePlanError(f"duplicate state slot: {name}")
            names.add(name)
            slots.append(StateSlot(name, _absolute_path(slot.get("path"), f"state_slots[{index}].path")))
        component = cls._component_from_mapping(document.get("component"), "component")
        ancillary_value = document.get("ancillary_components", [])
        if not isinstance(ancillary_value, list):
            raise RuntimePlanError("ancillary_components must be an array")
        ancillary = tuple(
            cls._component_from_mapping(value, f"ancillary_components[{index}]")
            for index, value in enumerate(ancillary_value)
        )
        cls._validate_components((component, *ancillary))
        integrations_value = document.get("host_integrations", [])
        if not isinstance(integrations_value, list):
            raise RuntimePlanError("host_integrations must be an array")
        integrations = tuple(
            _identifier(value, f"host_integrations[{index}]")
            for index, value in enumerate(integrations_value)
        )
        if len(set(integrations)) != len(integrations):
            raise RuntimePlanError("host_integrations must not contain duplicates")
        display_value = document.get("display")
        display = None if display_value is None else DisplayPlan.from_mapping(display_value, "display")
        console_value = document.get("console")
        console = None if console_value is None else ConsolePlan.from_mapping(console_value, "console")
        logs_value = document.get("logs")
        logs = None if logs_value is None else LogsPlan.from_mapping(logs_value, "logs")
        prefixes = {item.id for item in (component, *ancillary)}
        for slot in slots:
            namespace, separator, local_name = slot.name.partition("/")
            if not separator or namespace not in prefixes:
                raise RuntimePlanError(
                    f"runtime state slot {slot.name!r} must be namespaced by a declared component"
                )
            _identifier(local_name, f"runtime state slot {slot.name!r}")
        return cls(
            version=1,
            project_path=_absolute_path(document.get("project_path"), "project_path"),
            home=_absolute_path(document.get("home"), "home"),
            identity=Identity(uid, gid, _required_string(identity_value.get("user", "devcapsule"), "identity.user")),
            state_slots=tuple(slots),
            component=component,
            ancillary_components=ancillary,
            host_integrations=integrations,
            display=display,
            console=console,
            logs=logs,
        )

    @staticmethod
    def _component_from_mapping(value: object, field: str) -> Component:
        if not isinstance(value, dict):
            raise RuntimePlanError(f"{field} must be an object")
        configuration = value.get("configuration", {})
        if not isinstance(configuration, dict):
            raise RuntimePlanError(f"{field}.configuration must be an object")
        return Component(
            _identifier(value.get("id"), f"{field}.id"),
            _required_string(value.get("adapter"), f"{field}.adapter"),
            configuration,
            _environment_mapping(value.get("environment", {}), f"{field}.environment"),
        )

    @staticmethod
    def _validate_components(components: tuple[Component, ...]) -> None:
        identifiers: set[str] = set()
        environment: dict[str, str] = {}
        for component in components:
            if component.id in identifiers:
                raise RuntimePlanError(f"duplicate runtime component: {component.id}")
            identifiers.add(component.id)
            for name, value in component.environment.items():
                previous = environment.get(name)
                if previous is not None and previous != value:
                    raise RuntimePlanError(
                        f"runtime components declare conflicting values for environment variable {name}"
                    )
                environment[name] = value

    def component_environment(self) -> dict[str, str]:
        result: dict[str, str] = {}
        for component in (self.component, *self.ancillary_components):
            result.update(component.environment)
        return result

    def slots_by_name(self) -> dict[str, str]:
        return {slot.name: slot.path for slot in self.state_slots}

    def with_host_integration(self, name: str) -> RuntimePlan:
        selected = _identifier(name, "host integration")
        return replace(
            self,
            host_integrations=tuple(sorted({*self.host_integrations, selected})),
        )

    def with_display(self, display: DisplayPlan) -> RuntimePlan:
        return replace(self, display=display)

    def with_console(self, console: ConsolePlan) -> RuntimePlan:
        return replace(self, console=console)

    def with_logs(self, logs: LogsPlan) -> RuntimePlan:
        return replace(self, logs=logs)

    def display_transport(self) -> str:
        """The transport this plan records; absent means host X11 passthrough."""

        return HOST_X11_DISPLAY_TRANSPORT if self.display is None else self.display.transport

    def to_mapping(self) -> dict[str, object]:
        component: dict[str, object] = {
            "id": self.component.id,
            "adapter": self.component.adapter,
            "configuration": dict(self.component.configuration),
        }
        if self.component.environment:
            component["environment"] = dict(self.component.environment)
        result: dict[str, object] = {
            "version": self.version,
            "project_path": self.project_path,
            "home": self.home,
            "identity": {
                "uid": self.identity.uid,
                "gid": self.identity.gid,
                "user": self.identity.user,
            },
            "state_slots": [
                {"name": slot.name, "path": slot.path} for slot in self.state_slots
            ],
            "component": component,
        }
        if self.ancillary_components:
            result["ancillary_components"] = [
                _runtime_component_mapping(item) for item in self.ancillary_components
            ]
        if self.host_integrations:
            result["host_integrations"] = list(self.host_integrations)
        if self.display is not None:
            result["display"] = self.display.to_mapping()
        if self.console is not None:
            result["console"] = self.console.to_mapping()
        if self.logs is not None:
            result["logs"] = self.logs.to_mapping()
        return result

    def to_json(self) -> str:
        return json.dumps(
            self.to_mapping(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )


def _environment_mapping(value: object, field: str) -> dict[str, str]:
    if not isinstance(value, dict):
        raise RuntimePlanError(f"{field} must be an object")
    environment: dict[str, str] = {}
    for name, raw_value in value.items():
        if not isinstance(name, str) or re.fullmatch(r"[A-Z_][A-Z0-9_]*", name) is None:
            raise RuntimePlanError(f"{field} names must be uppercase environment identifiers")
        environment[name] = _required_string(raw_value, f"{field}.{name}")
    return environment


def _runtime_component_mapping(component: Component) -> dict[str, object]:
    value: dict[str, object] = {
        "id": component.id,
        "adapter": component.adapter,
        "configuration": dict(component.configuration),
    }
    if component.environment:
        value["environment"] = dict(component.environment)
    return value
