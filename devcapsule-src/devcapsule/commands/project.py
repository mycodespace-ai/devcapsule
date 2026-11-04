"""Project and checkout command subtree.

Command classes here declare parameters and print operation reports; policy
and artifact writes live in :mod:`devcapsule.configuration.operations` and the
modules it composes.  The configuration grammar is the settled v027 shape:
every mutation is ``VERB NAME VALUE`` with the node's one canonical name —
``set NAME VALUE``, ``bind NAME PROVIDER:VALUE``,
``authorize NAME VALUE [JUSTIFICATION]``, ``unset NAME`` — and ``init``
accepts the same spellings through its carrier options.  The standalone
``lock`` stub is retired: the platform lock is authored by ``init`` from the
embedded resolution matrix.
"""

from __future__ import annotations

import argparse
import getpass
import warnings
from dataclasses import dataclass, replace
import json
from pathlib import Path
import os
import subprocess
import sys
import termios
import shlex
from typing import Any, Callable, ClassVar, Mapping, Sequence

from devcapsule.launch.command_output import preparation_diagnostics
from devcapsule.commands.framework import (
    STABLE_JSON_HELP,
    Command,
    Group,
    add_carrier_options,
    capsule_platform_argument,
    carrier_answers,
)
from devcapsule.components.catalog import COMPONENTS
from devcapsule.commands._versions import VersionsGroup
from devcapsule.commands._upgrade_prompt import offer_upgrades
from devcapsule.commands._run_flow import RunFlags, launch_listing_document, load_launch_state, prepare_launch
from devcapsule.display_client import has_contained_display
from devcapsule.commands._software_approvals import (
    SOFTWARE_APPROVALS_GUIDE_URL,
    approve as approve_software,
    approve_command as software_approve_command,
    confirmation_key as _confirmation_key,
    offer_software_approvals,
    pending_for as pending_software_approvals_for,
)
from devcapsule.configuration.approvals import render_software_approvals, select_software_approvals
from devcapsule import notifications
from devcapsule import version_sets
from devcapsule import runtime_configuration
from devcapsule.runtime_configuration import CapsuleAccess
from devcapsule.compat import CliError, DecisionPending
import difflib
from devcapsule.configuration.capability_selection import lock_platform
from devcapsule.configuration.capabilities import CapabilityPolicy, LocalCapabilities
from devcapsule.configuration.console_requests import deferred_rows
from devcapsule.configuration.listing import Listing, assess_checkout
from devcapsule.configuration.values import LAUNCHER_VALUE_NAMES, legacy_memory_names, normalize_launcher_value
from devcapsule.configuration.docker_arguments import (
    arguments_path, read_arguments, replace_arguments, read_environment, update_environment, validate_name,
)
from devcapsule.docker_arguments import redact_environment
from devcapsule.configuration.history import (
    record_known_good_configuration,
)
from devcapsule.launch.pycharm import (
    DockerMode,
    PycharmRunOptions,
    PycharmRunError,
    reject_launcher_owned_docker_options,
    run_pycharm,
)
from devcapsule.configuration.review import (
    review_configuration,
)
from devcapsule.configuration.nodes import (
    PROVIDER_HOST_DIRECTORY,
    build_node_registry,
)
from devcapsule.environment_realization import realize_environment, required_local_image, omit_unavailable_optional
from devcapsule.materialization import ArtifactUnavailable
from devcapsule.display_client import select_display_transport
from devcapsule.images.contract import WebConsoleAvailability, web_console_availability
from devcapsule.materialization import ImageDetails, validate_base_image
from devcapsule.configuration.operations import (
    CheckoutRecord,
    InitializeRequest,
    ProvidedAnswer,
    apply_configuration_answers,
    initialize_project,
)
from devcapsule.project_runtime_plan import project_runtime_plan
from devcapsule.recursive_dogfood import (
    RECURSIVE_E2E_ENABLED_ENV,
    PreflightError,
    preflight_json,
    recursive_e2e_launch_environment,
    render_preflight,
    require_recursive_e2e_project,
    run_recursive_preflight,
)
from devcapsule.recursive_orchestrator import (
    RecursiveE2EError,
    RecursivePreflightFailed,
    run_recursive_e2e_dry_run,
)
from devcapsule.recursive_successor import (
    RecursiveSuccessorError,
    inspect_successor,
    SuccessorResult,
    launch_successor,
)
from devcapsule.configuration.authorization import (
    AuthorizationChoice,
    AuthorizationDeclaration,
    authorization_declarations,
    immutable_registry_reference,
    normalize_authorization_value,
    render_authorization_value,
)
from devcapsule.configuration.file_formats import (
    ProjectConfigurationError,
    render_checkout,
    render_toml_scalar,
)
from devcapsule.configuration.storage import (
    atomic_write,
    checkout_name_for,
    checkout_record_paths,
    config_root,
    discover_project,
    find_checkout_record,
    load_checkout,
    load_resolution,
    load_settings,
    lock_for,
    manifest_for,
    named_checkout_record_paths,
    registered_checkouts,
)
from devcapsule.configuration.bindings import (
    configuration_binding_declarations,
    managed_binding_path as _managed_binding_path,
)
from devcapsule.configuration.values import (
    configuration_value_declarations,
    normalize_configuration_value,
)
from devcapsule.configuration.freshness import (
    stale_resolution_inputs,
)


@dataclass(frozen=True)
class ProjectCommandContext:
    """What the ``project`` group selected for its subcommand.

    ``selected_path`` is the user's ``--path``; it always wins.
    ``capsule_root`` is the capsule's own project, set by the group when no
    ``--path`` was given, no project encloses the working directory, and the
    subcommand's :class:`CapsuleAccess` selects it; otherwise ``None``.
    """

    selected_path: Path | None
    capsule_root: Path | None = None

    def start_path(self) -> Path:
        return self.selected_path or self.capsule_root or Path(".")

    def target_path(self) -> Path:
        return self.start_path().expanduser().resolve()


def _project_context(context: object | None) -> ProjectCommandContext:
    assert isinstance(context, ProjectCommandContext)
    return context


class ProjectInfoCommand(Command):
    name = "info"
    capsule_access: ClassVar[CapsuleAccess] = CapsuleAccess.INSPECTS
    help = "Show project software, environment and persistent storage without changing state."

    @classmethod
    def configure(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--json", action="store_true", help="Print the information as JSON.")

    @classmethod
    def run(cls, arguments: argparse.Namespace, context: object | None) -> int:
        from devcapsule.project_information import project_information, render_information

        selected = _project_context(context)
        report = project_information(selected.start_path(), runtime_fallback=selected.selected_path is None)
        print(json.dumps(report, indent=2) if arguments.json else render_information(report))
        return 0


class ProjectDiagnoseCommand(Command):
    name = "diagnose"
    capsule_access: ClassVar[CapsuleAccess] = CapsuleAccess.INSPECTS
    help = "Capture a bounded session diagnostics snapshot and optional sanitized export bundle."

    @classmethod
    def configure(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--session",
            metavar="ID",
            help="Session ID to inspect; defaults to the active session, else the newest ended session.",
        )
        parser.add_argument(
            "--export",
            nargs="?",
            const="",
            default=None,
            metavar="PATH",
            help="Write a mode-0600 sanitized .tar.gz archive (to PATH, or the current directory when omitted).",
        )
        parser.add_argument(
            "--include-ide-logs",
            action="store_true",
            help="Include IDE-native logs in --export (excluded by default because they can contain project content).",
        )
        parser.add_argument("--json", dest="as_json", action="store_true", help=STABLE_JSON_HELP)

    @classmethod
    def run(cls, arguments: argparse.Namespace, context: object | None) -> int:
        from devcapsule.diagnostics import diagnose_project, render_diagnosis

        if arguments.include_ide_logs and arguments.export is None:
            raise ProjectConfigurationError("--include-ide-logs requires --export.")
        selected = _project_context(context)
        export_requested = arguments.export is not None
        export_path = Path(arguments.export) if arguments.export else None
        try:
            snapshot = diagnose_project(
                selected.start_path(),
                runtime_fallback=selected.selected_path is None,
                session_id=arguments.session,
                export_path=export_path,
                export_requested=export_requested,
                include_ide_logs=arguments.include_ide_logs,
            )
        except OSError as error:
            from devcapsule._redaction import redact_text
            from devcapsule.diagnostics import DiagnosticsError

            raise DiagnosticsError(f"Cannot capture or export diagnostics: {redact_text(str(error))}") from error
        print(json.dumps(snapshot, indent=2, sort_keys=True) if arguments.as_json else render_diagnosis(snapshot))
        return 0


class ProjectListCommand(Command):
    name = "list"
    capsule_access: ClassVar[CapsuleAccess] = CapsuleAccess.INDEPENDENT
    help = "List developer-owned checkout records from the XDG registry."

    @classmethod
    def run(cls, arguments: argparse.Namespace, context: object | None) -> int:
        # Without a supplied runtime context this is still the home's
        # registry enumeration, including in older/nested launcher capsules.
        runtime_context = (runtime_configuration.for_project(_project_context(context).start_path())
                           if runtime_configuration.CONTEXT_PATH.is_file() else None)
        if runtime_context is not None:
            identity = runtime_context.document["project"]
            print(f"Runtime project: {identity['creator']}/{identity['slug']}")
            print(f"Runtime checkout: {runtime_context.root}")
            print(f"Launcher checkout: {runtime_context.document['launcher-root']}")
            print("Only this capsule's checkout is selected here; list other checkouts through the launcher.")
            return 0
        records = registered_checkouts()
        if not records:
            print(f"No registered DevCapsule project checkouts found in {config_root() / 'projects'}.")
            return 0
        headers = ("PROJECT", "CHECKOUT", "PATH", "STATUS")
        rows = [
            (
                f"{record.project_creator}/{record.project_slug}",
                record.checkout_name,
                str(record.checkout_path),
                record.status,
            )
            for record in records
        ]
        widths = [max(len(header), *(len(row[index]) for row in rows)) for index, header in enumerate(headers)]
        print("  ".join(header.ljust(widths[index]) for index, header in enumerate(headers)))
        for row in rows:
            print("  ".join(value.ljust(widths[index]) for index, value in enumerate(row)))
        return 0


class ProjectInitCommand(Command):
    name = "init"
    capsule_access: ClassVar[CapsuleAccess] = CapsuleAccess.CREATES_HERE
    help = (
        "Initialize the project: the manifest with what it requires and offers, the platform "
        "lock, your own checkout record with your IDE and capabilities, and, once an IDE is chosen, "
        "a fresh resolution. New manifests use schema 2; rc3 and older launchers cannot read them."
    )

    @classmethod
    def configure(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--require", action="append", default=[], metavar="CAPABILITY",
            help="A capability every checkout must have, optionally NAME>=VERSION. Repeatable.",
        )
        parser.add_argument(
            "--offer", action="append", default=[], metavar="CAPABILITY",
            help="A capability the project offers and a developer may leave out, such as browser-automation. Repeatable.",
        )
        _add_owner_options(parser)
        parser.add_argument(
            "--platform", type=capsule_platform_argument, metavar="PLATFORM",
            help="Add the lock for this capsule platform, such as linux-arm64; the project then runs as it here. "
                 "Default: the platform this host runs the project as.",
        )
        _retired_option(parser, "--agent", "devcapsule project init --with CAPABILITY")
        parser.add_argument(
            "--regenerate",
            action="store_true",
            help="Rewrite the derived platform lock from the current embedded matrix; migrate a schema-1 manifest to schema 2, keeping its leading comment block.",
        )
        for flag, replacement in (("--need", "init --require CAPABILITY; config ide IDE or config add CAPABILITY"),
                                  ("--required", "init --require CAPABILITY"),
                                  ("--optional", "init --offer CAPABILITY"),
                                  ("--local", "config ide IDE or config add CAPABILITY"),
                                  ("--less-pedantic", "config authorize base-image IMAGE"),
                                  ("--sdk-major", "config require 'NAME>=VERSION'")):
            _retired_option(parser, flag, "devcapsule project " + replacement)
        add_carrier_options(parser)

    @classmethod
    def run(cls, arguments: argparse.Namespace, context: object | None) -> int:
        answers = tuple(
            ProvidedAnswer(
                family=answer.family,
                name=answer.name,
                value=answer.value,
                justification=answer.justification,
            )
            for answer in carrier_answers(arguments)
        )
        require, offer, ide, agents = _init_selection(arguments)
        report = initialize_project(
            InitializeRequest(
                directory=_project_context(context).target_path(),
                require=require,
                offer=offer,
                ide=ide,
                agents=agents,
                project_name=arguments.project_name,
                slug=arguments.slug,
                creator=arguments.creator,
                project_mount=arguments.project_mount,
                answers=answers,
                regenerate=arguments.regenerate,
                allow_unverified=arguments.allow_unverified,
                platform=arguments.platform,
            )
        )
        print(report.render())
        return 0


def _add_owner_options(parser: argparse.ArgumentParser) -> None:
    """The options ``init`` and ``wrap`` share: the owner's own checkout, the project's identity, the matrix escape."""
    parser.add_argument("--ide", metavar="IDE", help="Your IDE for this checkout: python-ide, frontend-ide, vscode-ide, java-ide, eclipse-ide or dotnet-ide; component names such as pycharm or vscode also work.")
    parser.add_argument("--with", dest="capabilities", action="append", default=[], metavar="CAPABILITY",
                        help="Add a capability for your checkout. Repeatable.")
    parser.add_argument("--name", dest="project_name", help="Project display name.")
    parser.add_argument("--slug", help="Project identity slug.")
    parser.add_argument("--creator", help="Project creator URL or email address.")
    parser.add_argument("--project-mount", help="In-container project mount path.")
    parser.add_argument(
        "--unverified",
        action="store_true",
        dest="allow_unverified",
        help=(
            "If no fully verified combination satisfies the requirements, resolve past "
            "the matrix with a gentle warning; the generated lock names every "
            "unverified combination."
        ),
    )


class ProjectWrapCommand(Command):
    name = "wrap"
    capsule_access: ClassVar[CapsuleAccess] = CapsuleAccess.CREATES_HERE
    help = (
        "Wrap a foreign repository: add it as a submodule with its Git directory embedded, require what "
        "you name, initialize or extend the manifest and lock, declare it under [sources], and write the "
        "wrapper's AGENTS.md and README.md. Repeatable for several repositories. Writes schema 2."
    )

    @classmethod
    def configure(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("url", metavar="URL", help="The repository to wrap: your fork when you mean to change it, the upstream when you mean to learn.")
        parser.add_argument("--path", metavar="NAME", help="The submodule's directory in the wrapper; default: the repository's name.")
        parser.add_argument("--upstream", metavar="URL", help="The upstream URL when URL is your fork of it; pull requests then go to the fork, never to the upstream.")
        parser.add_argument("--require", action="append", default=[], metavar="CAPABILITY",
                            help="A capability this source needs in every checkout, such as java, optionally NAME>=VERSION. Repeatable.")
        parser.add_argument("--java", metavar="LINE", help="The Java line this source builds with, such as 17; the guidance names it and the capsule selects it.")
        _add_owner_options(parser)
        add_carrier_options(parser)

    @classmethod
    def run(cls, arguments: argparse.Namespace, context: object | None) -> int:
        from devcapsule.wrap import WrapRequest, wrap_project
        from devcapsule.platforms import Platform
        from devcapsule.resolution_matrix import MATRICES
        matrix = MATRICES[Platform.current()]
        ide = matrix.canonical_name(arguments.ide) if arguments.ide is not None and arguments.ide.strip().lower() != "none" else None
        answers = tuple(
            ProvidedAnswer(family=answer.family, name=answer.name, value=answer.value, justification=answer.justification)
            for answer in carrier_answers(arguments)
        )
        report = wrap_project(
            WrapRequest(
                directory=_project_context(context).target_path(),
                url=arguments.url,
                path=arguments.path,
                upstream=arguments.upstream,
                require=tuple(arguments.require),
                java=arguments.java,
                ide=ide,
                agents=tuple(arguments.capabilities),
                project_name=arguments.project_name,
                slug=arguments.slug,
                creator=arguments.creator,
                project_mount=arguments.project_mount,
                answers=answers,
                allow_unverified=arguments.allow_unverified,
            )
        )
        print(report.render())
        return 0


def _init_selection(arguments: argparse.Namespace) -> tuple[tuple[str, ...], tuple[str, ...], str | None, tuple[str, ...]]:
    """Keep shared declarations separate from the checkout's selections."""
    from devcapsule.platforms import Platform
    from devcapsule.resolution_matrix import MATRICES
    matrix = MATRICES[Platform.current()]
    ide = matrix.canonical_name(arguments.ide) if arguments.ide is not None and arguments.ide.strip().lower() != "none" else None
    return tuple(arguments.require), tuple(arguments.offer), ide, tuple(arguments.capabilities)


class CheckoutRegisterCommand(Command):
    name = "register"
    capsule_access: ClassVar[CapsuleAccess] = CapsuleAccess.MUTATES
    help = "Register this checkout under a distinct home-owned name."

    @classmethod
    def configure(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("checkout_name", metavar="NAME")

    @classmethod
    def run(cls, arguments: argparse.Namespace, context: object | None) -> int:
        root, manifest = manifest_for(_project_context(context).start_path())
        selected_input = find_checkout_record(manifest, root)
        if selected_input is not None:
            raise ProjectConfigurationError(f"Checkout is already registered in {selected_input}.")
        input_path, output_path = named_checkout_record_paths(manifest, arguments.checkout_name)
        if input_path.exists() or output_path.exists():
            raise ProjectConfigurationError(
                f"Checkout name {arguments.checkout_name!r} is already in use under {input_path.parent}."
            )
        atomic_write(input_path, render_checkout(manifest, root, {}, {}))
        print(f"Registered checkout {arguments.checkout_name!r}: {input_path}")
        return 0


def _notification_store(context: object | None) -> "notifications.NotificationStore":
    """The checkout's store: its own state inside a capsule, its persistent home from the host."""
    selected = _project_context(context)
    try:
        return notifications.store_for(selected.selected_path)
    except (ProjectConfigurationError, OSError) as error:
        raise ProjectConfigurationError(f"Cannot locate this checkout's notifications: {error}") from error


def _render_notification_listing(document: dict[str, Any]) -> str:
    """The human form of the listing: one line per entry, a star marking unread."""
    entries = document["notifications"]
    if not entries:
        return f"No notifications under {document['directory']}.\n"
    lines = []
    for entry in entries:
        if "error" in entry:
            lines.append(f"  ! {entry['id']}: {entry['error']}")
            continue
        mark = "*" if entry["read-at"] is None else " "
        link = f"  {entry['link']}" if entry["link"] else ""
        lines.append(f"{mark} {entry['posted-at']}  {entry['kind']:<10}  {entry['id']}  {entry['title']}{link}")
    return f"{document['unread']} unread of {len(entries)}; * marks unread.\n" + "\n".join(lines) + "\n"


class NotificationsListCommand(Command):
    name = "list"
    capsule_access: ClassVar[CapsuleAccess] = CapsuleAccess.INDEPENDENT
    help = "List this checkout's notifications and its unanswered decisions, newest first."

    @classmethod
    def configure(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--unread", action="store_true", help="Only the entries not yet read.")
        parser.add_argument("--json", dest="as_json", action="store_true", help=STABLE_JSON_HELP)

    @classmethod
    def run(cls, arguments: argparse.Namespace, context: object | None) -> int:
        try:
            document = notifications.listing_document(_notification_store(context), unread_only=arguments.unread)
        except notifications.NotificationError as error:
            raise ProjectConfigurationError(str(error)) from error
        print(json.dumps(document, indent=2, sort_keys=True) if arguments.as_json
              else _render_notification_listing(document), end="")
        return 0


class NotificationsPostCommand(Command):
    name = "post"
    capsule_access: ClassVar[CapsuleAccess] = CapsuleAccess.INDEPENDENT
    help = "Post a notification to this checkout's human; capsule state only, never a record."

    @classmethod
    def configure(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--kind", required=True, help="Lowercase letters, digits and hyphens; 'decision' is reserved.")
        parser.add_argument("--title", required=True)
        parser.add_argument("--summary", default="", help="Markdown shown under the title.")
        parser.add_argument("--link", default="", help="A web console path to open, such as /records/README.md.")
        parser.add_argument("--posted-by", dest="posted_by", default="", help="Who posts; default $USER or 'unknown'.")
        parser.add_argument("--json", dest="as_json", action="store_true", help=STABLE_JSON_HELP)

    @classmethod
    def run(cls, arguments: argparse.Namespace, context: object | None) -> int:
        store = _notification_store(context)
        try:
            posted = store.post(kind=arguments.kind, title=arguments.title, summary=arguments.summary,
                                link=arguments.link, posted_by=arguments.posted_by or os.environ.get("USER") or "unknown")
        except notifications.NotificationError as error:
            raise ProjectConfigurationError(f"Cannot post the notification: {error}") from error
        print(json.dumps(posted.to_mapping(), indent=2, sort_keys=True) if arguments.as_json
              else f"Posted {posted.id}: {store.path(posted.id)}")
        return 0


class NotificationsReadCommand(Command):
    name = "read"
    capsule_access: ClassVar[CapsuleAccess] = CapsuleAccess.INDEPENDENT
    help = "Mark a notification read; a decision is read by answering it."

    @classmethod
    def configure(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("notification_id", metavar="ID")

    @classmethod
    def run(cls, arguments: argparse.Namespace, context: object | None) -> int:
        try:
            read = _notification_store(context).mark_read(arguments.notification_id)
        except notifications.NotificationError as error:
            raise ProjectConfigurationError(str(error)) from error
        print(f"Read {read.id} at {read.read_at}")
        return 0


class NotificationsDismissCommand(Command):
    name = "dismiss"
    capsule_access: ClassVar[CapsuleAccess] = CapsuleAccess.INDEPENDENT
    help = "Remove a notification; a decision is removed by the agent that asked it."

    @classmethod
    def configure(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("notification_id", metavar="ID")

    @classmethod
    def run(cls, arguments: argparse.Namespace, context: object | None) -> int:
        try:
            _notification_store(context).dismiss(arguments.notification_id)
        except notifications.NotificationError as error:
            raise ProjectConfigurationError(str(error)) from error
        print(f"Dismissed {arguments.notification_id}")
        return 0


class NotificationsGroup(Group):
    name = "notifications"
    help = "What this checkout's environment tells its human: list, post, read, dismiss."

    @classmethod
    def subcommands(cls) -> Mapping[str, type[Command] | type[Group]]:
        return {
            NotificationsListCommand.name: NotificationsListCommand,
            NotificationsPostCommand.name: NotificationsPostCommand,
            NotificationsReadCommand.name: NotificationsReadCommand,
            NotificationsDismissCommand.name: NotificationsDismissCommand,
        }


class CheckoutDecisionsCommand(Command):
    """``project checkout decisions ...``: the web console's decision tools, from one CLI.

    The decision document is the console's contract (``DECISIONS.md`` in
    its source), and the tools that build, check and hand off one live in
    the console's package, which is not in the runtime PEX by the work
    order's binding decision. Inside a capsule the console is installed in
    the base, or mounted from the checkout under the self-hosting
    exception; this command runs that module, so an agent sees one CLI.
    Outside a capsule it says where the module is.
    """

    name = "decisions"
    capsule_access: ClassVar[CapsuleAccess] = CapsuleAccess.INDEPENDENT
    help = "Build, check or hand off a decision document with the capsule's web console tools."

    @classmethod
    def configure(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("arguments", nargs=argparse.REMAINDER, metavar="SUBCOMMAND ...",
                            help="from-table, check or hand-off with their arguments, as "
                                 "`python -m devcapsule_webconsole.decisions` takes them.")

    @classmethod
    def run(cls, arguments: argparse.Namespace, context: object | None) -> int:
        from devcapsule.console_tools import console_decisions_command

        command = console_decisions_command(arguments.arguments)
        try:
            return subprocess.run(command, check=False).returncode
        except OSError as error:
            raise CliError(f"cannot run the console's decision tools: {error}") from error


class CheckoutGroup(Group):
    name = "checkout"
    help = "This local checkout: register its name, its notifications, its decisions."

    @classmethod
    def subcommands(cls) -> Mapping[str, type[Command] | type[Group]]:
        return {
            CheckoutRegisterCommand.name: CheckoutRegisterCommand,
            NotificationsGroup.name: NotificationsGroup,
            CheckoutDecisionsCommand.name: CheckoutDecisionsCommand,
        }


def _retired_command(name: str, replacement: str) -> type[Command]:
    class RetiredCommand(Command):
        hidden = True
        capsule_access: ClassVar[CapsuleAccess] = CapsuleAccess.INDEPENDENT

        @classmethod
        def invoke(cls, prog: str, argv: Sequence[str], context: object | None = None) -> int:
            raise ProjectConfigurationError(f"{prog} is retired; use 'devcapsule project {replacement}'.")

    RetiredCommand.name = name
    return RetiredCommand


class _RetiredOption(argparse.Action):
    def __call__(self, parser: argparse.ArgumentParser, namespace: argparse.Namespace,
                 values: Any, option_string: str | None = None) -> None:
        raise ProjectConfigurationError(f"{parser.prog} {option_string} is retired; use '{self.const}'.")


def _retired_option(parser: argparse.ArgumentParser, flag: str, replacement: str) -> None:
    parser.add_argument(flag, action=_RetiredOption, nargs=0, const=replacement, help=argparse.SUPPRESS)


ConfigResolveCommand = _retired_command("resolve", "run")


@dataclass(frozen=True)
class CheckoutDocuments:
    """Everything the listing of one checkout is computed from, loaded without writing."""

    root: Path
    manifest: dict[str, Any]
    manifest_path: Path
    shared_lock: dict[str, Any]
    lock_path: Path
    composed_lock: dict[str, Any]
    checkout: dict[str, Any]
    input_path: Path | None
    resolution_path: Path | None
    home: dict[str, Any]
    saved_environment: dict[str, str | None]

    @property
    def registered(self) -> bool:
        return self.input_path is not None and self.input_path.is_file()

    @property
    def checkout_name(self) -> str:
        return checkout_name_for(self.manifest, self.input_path) if self.input_path is not None else "(unregistered)"

    def render_identity(self) -> str:
        identity = self.manifest["project"]
        lines = [
            f"Project: {identity['name']} ({identity['creator']}/{identity['slug']})",
            f"Checkout: {self.root}",
            f"Checkout name: {self.checkout_name}",
        ]
        lines.append(f"Checkout record: {self.input_path}" if self.registered else
                     "Checkout record: none yet; the first 'devcapsule project run' creates it")
        return "\n".join(lines)

    def resolution_state(self) -> str:
        """The generated resolution's state: fresh, stale with the drifted inputs, or missing."""
        if self.resolution_path is None or not self.resolution_path.is_file():
            return "missing"
        resolved = load_resolution(self.resolution_path)
        if resolved.get("status") == "unresolved":
            return "missing"
        try:
            from devcapsule.configuration.capability_selection import effective_lock
            selected = effective_lock(self.manifest, self.composed_lock, self.checkout, warn=False)
            from devcapsule.configuration.storage import manifest_source_digest
            stale = stale_resolution_inputs(self.manifest, selected, self.checkout, resolved, self.home,
                                            source_digest=manifest_source_digest(self.root))
        except ProjectConfigurationError as exc:
            return f"unreadable ({exc})"
        return "stale: " + ", ".join(stale) if stale else "fresh"


def _load_checkout_documents(context: object | None) -> CheckoutDocuments | runtime_configuration.RuntimeConfiguration:
    """Load the documents behind the listing; inside a capsule, the runtime context is the whole answer.

    Nothing is written: an unregistered checkout is listed from an empty
    record, and a checkout without an IDE from the shared lock alone.
    """
    start = _project_context(context).start_path()
    runtime_context = runtime_configuration.for_project(start)
    if runtime_context is not None:
        return runtime_context
    root, manifest = manifest_for(start)
    from devcapsule.configuration.storage import composition_for, recommendation_lock_for, interrupted_activation
    record = find_checkout_record(manifest, root)
    if record is not None and interrupted_activation(record):
        raise ProjectConfigurationError(
            "A checkout activation needs recovery; run 'devcapsule project run'. Inspection writes nothing."
        )
    lock_path, composed, checkout = composition_for(root, manifest)
    _shared_path, shared = recommendation_lock_for(root, manifest)
    record = find_checkout_record(manifest, root)
    input_path: Path | None = record
    resolution_path: Path | None = None
    if record is None:
        try:
            input_path, resolution_path = checkout_record_paths(manifest, root)
        except ProjectConfigurationError:
            input_path = None  # another checkout of this project holds the default record
    else:
        from devcapsule.configuration.storage import resolved_record_path
        resolution_path = resolved_record_path(record)
    saved: dict[str, str | None] = {}
    if record is not None:
        saved = read_environment(arguments_path(record))
    return CheckoutDocuments(root, manifest, root / ".devcapsule" / "devcapsule.toml", shared, lock_path, composed,
                             checkout, input_path, resolution_path, load_settings(), saved)


def _assess(documents: CheckoutDocuments) -> Listing:
    from devcapsule.configuration.authorization import authorized_base_selection
    from devcapsule.configuration.trust import HomeTrust
    from devcapsule.configuration.storage import project_platform
    from devcapsule.resolution_matrix import MATRICES, known_base_image
    matrix = MATRICES[project_platform(documents.root)]
    answers = documents.checkout.get("authorization", {})
    base_answer = answers.get("base-image", {}) if isinstance(answers, dict) else {}
    base_reference = base_answer.get("reference") if isinstance(base_answer, dict) else None
    base_reference = base_reference or documents.composed_lock.get("base", {}).get("reference")
    try:
        selection = authorized_base_selection(documents.composed_lock, documents.checkout, required=False,
                                              trust=HomeTrust.read(documents.home))
    except ProjectConfigurationError:
        selection = None  # The listing reports an invalid or stale selection below.
    if selection is not None:
        base_reference = selection.reference
    base = known_base_image(str(base_reference))
    surfaces = {name: matrix.resolve_provider(name) or name for name in matrix.ide_capabilities()}
    from devcapsule.configuration.capability_selection import inspection_capabilities, inspection_providers
    access_lock, versions = inspection_capabilities(documents.manifest, documents.composed_lock, documents.checkout)
    providers = inspection_providers(documents.manifest, documents.composed_lock, documents.checkout)
    listing = assess_checkout(
        documents.manifest, documents.shared_lock, documents.composed_lock, documents.checkout,
        home_path=config_root(), home=documents.home, saved_environment=documents.saved_environment,
        surfaces=surfaces, project=documents.root, registered=documents.registered,
        access_lock=access_lock, capability_versions=versions,
        capability_providers=providers,
        base_display=base.contract.display if base is not None else None,
    )
    return Listing(listing.rows + tuple(deferred_rows(documents.input_path, documents.root)), listing.notes)


class ConfigShowCommand(Command):
    name = "show"
    capsule_access: ClassVar[CapsuleAccess] = CapsuleAccess.INSPECTS
    help = "Show every choice of this checkout: the value the next launch uses, its source, and what is pending. Writes nothing."

    @classmethod
    def configure(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--json", dest="as_json", action="store_true", help=STABLE_JSON_HELP)

    @classmethod
    def run(cls, arguments: argparse.Namespace, context: object | None) -> int:
        loaded = _load_checkout_documents(context)
        if isinstance(loaded, runtime_configuration.RuntimeConfiguration):
            return _show_inside_capsule(loaded, arguments.as_json)
        listing = _assess(loaded)
        if arguments.as_json:
            identity = loaded.manifest["project"]
            document = {
                **listing.document(),
                "context": "host selection (next launch)",
                "project": {"creator": identity["creator"], "slug": identity["slug"]},
                "checkout": {"name": loaded.checkout_name, "launcher-path": str(loaded.root),
                             "input": str(loaded.input_path) if loaded.input_path else None},
            }
            print(json.dumps(document, indent=2, sort_keys=True))
            return 0
        print(loaded.render_identity())
        print("")
        print(listing.render())
        print("")
        print(listing.render_pending())
        return 0


def _show_inside_capsule(loaded: runtime_configuration.RuntimeConfiguration, as_json: bool) -> int:
    """Inside a capsule: the launcher's listing at launch and the console's requests since (answer 16)."""
    from devcapsule.commands._console_channel import read_channel
    view = read_channel(runtime_configuration.CHANNEL_PATH) if runtime_configuration.CHANNEL_PATH.is_dir() else None
    if view is None:
        print(json.dumps(loaded.configuration_document(), indent=2, sort_keys=True) if as_json
              else loaded.configuration_report())
        return 0
    checkout = view.listing.get("checkout")
    identity = loaded.document["project"]
    if (not isinstance(checkout, dict) or checkout.get("launcher-path") != loaded.document["launcher-root"]
            or checkout.get("name") != loaded.checkout_name
            or view.listing.get("project") != {key: identity[key] for key in ("creator", "slug")}):
        raise ProjectConfigurationError("The channel listing belongs to another checkout; inspect configuration on the host.")
    command = loaded.launcher_command(["config", "show"])
    if as_json:
        print(json.dumps({**view.listing, "context": "running capsule: the launcher's listing at launch", "at": view.at,
                          "console-requests": list(view.requests), "launcher-command": command},
                         indent=2, sort_keys=True))
        return 0
    checkout = view.listing.get("checkout", {})
    print(f"Checkout: {checkout.get('launcher-path', loaded.document['launcher-root'])} ({checkout.get('name', loaded.checkout_name)})")
    print(f"At launch, {view.at}:")
    print(Listing.from_document(view.listing).render())
    print("")
    if view.requests:
        print("Pending, next launch (asked on the console since launch):")
        for item in view.requests:
            result = item.get("result")
            outcome = f"{result['status']}: {result['text']}" if isinstance(result, dict) else "waiting for the launcher"
            print(f"  {item['id']}: {item['statement'] or '(unreadable request)'}\n      {outcome}")
    else:
        print("Nothing asked on the console since launch.")
    print(f"To change the next launch: the console's configuration page, or on the host: {command}")
    return 0


ConfigListCommand = _retired_command("list", "config show")


def _set_value(record: CheckoutRecord, manifest: dict[str, Any], name: str, value: str) -> str:
    """Record one value answer; return the line that says what was recorded.

    ``memory`` and ``cpus`` are the launcher's and need no declaration; a
    declared value is validated against its declaration; ``default`` forgets
    the checkout's answer so the value follows the project and the
    home again (answer 13 of the work order); ``none`` keeps an
    optional declared value out of the capsule.
    """
    keyword = value.strip().lower()
    aliases = legacy_memory_names(manifest)
    if name in aliases:
        raise ProjectConfigurationError(
            f"{name!r} is the project's old name for the memory limit; set it with 'devcapsule project config set memory SIZE'."
        )
    if name in LAUNCHER_VALUE_NAMES:
        aliases = aliases if name == "memory" else ()
        if keyword == "default":
            record.values.pop(name, None)
            record.omitted_values.discard(name)
            for alias in aliases:
                record.values.pop(alias, None)
                record.omitted_values.discard(alias)
            return f"Forgot {name} for this checkout; it follows the project's recommendation, then the home default."
        if keyword == "none":
            raise ProjectConfigurationError(f"{name} has no 'none'; 'default' forgets your answer, or set a value.")
        record.set_value(name, normalize_launcher_value(name, value))
        for alias in aliases:
            record.values.pop(alias, None)
            record.omitted_values.discard(alias)
        return f"Set {name} = {record.values[name]} for this checkout."
    declarations = configuration_value_declarations(manifest)
    if name not in declarations and keyword == "default" and (name in record.values or name in record.omitted_values):
        record.values.pop(name, None)
        record.omitted_values.discard(name)
        return f"Forgot the obsolete value {name} for this checkout."
    if name not in declarations:
        available = ", ".join(sorted((*LAUNCHER_VALUE_NAMES, *(key for key in declarations if key not in aliases)))) or "memory, cpus"
        close = difflib.get_close_matches(name, available.split(", "), n=1, cutoff=0.6)
        hint = f" Did you mean {close[0]!r}?" if close else ""
        raise ProjectConfigurationError(f"No value named {name!r} on this project;{hint} values: {available}.")
    if keyword == "default":
        removed = record.values.pop(name, None)
        record.omitted_values.discard(name)
        if removed is None and "recommended" not in declarations[name]:
            return f"{name} has no recorded answer for this checkout; nothing changed."
        return f"Forgot {name} for this checkout; it follows the project's recommendation."
    if keyword == "none":
        if declarations[name].get("required", False):
            raise ProjectConfigurationError(f"Configuration value {name!r} is mandatory and cannot be 'none'; record a value instead.")
        record.omit_value(name)
        return f"Set {name} = none (explicitly absent from the runtime configuration)."
    record.set_value(name, normalize_configuration_value(manifest, name, value))
    return f"Set {name} = {render_toml_scalar(record.values[name])} for this checkout."


class ConfigSetCommand(Command):
    name = "set"
    capsule_access: ClassVar[CapsuleAccess] = CapsuleAccess.MUTATES
    help = ("Set a value for this checkout: memory (6GiB, 6g), cpus (4), or a value the project declares. "
            "'default' forgets your answer and follows the project and the home again.")

    @classmethod
    def configure(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("node_name", metavar="NAME", help="memory, cpus, or a declared value's name.")
        parser.add_argument("value", metavar="VALUE", help="The value, or 'default'.")

    @classmethod
    def run(cls, arguments: argparse.Namespace, context: object | None) -> int:
        root, manifest = manifest_for(_project_context(context).start_path())
        record = CheckoutRecord(manifest, root)
        print(_set_value(record, manifest, arguments.node_name, arguments.value))
        record.write()
        print(f"Checkout record: {record.input_path}")
        print("The next 'devcapsule project run' uses it.")
        return 0


def _managed_arguments_path(context: object | None) -> Path:
    """The saved arguments of the registered checkout record for this project.

    The record is located, never loaded: the saved-argument commands edit no
    checkout record, so they must not recover an interrupted activation either.
    """
    root, manifest = manifest_for(_project_context(context).start_path())
    input_path, _resolution_path = checkout_record_paths(manifest, root)
    if not input_path.is_file():
        raise ProjectConfigurationError("Initialize or register this checkout before setting its environment.")
    return arguments_path(input_path)


def _hidden_value_prompt() -> str:
    if not sys.stdin.isatty():
        raise ProjectConfigurationError("A terminal is required for the hidden value prompt; give VALUE, or --from-host.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", getpass.GetPassWarning)
            return getpass.getpass("Value: ")
    except (getpass.GetPassWarning, EOFError):
        raise ProjectConfigurationError("Cannot read a hidden value from this terminal.") from None


class ConfigEnvSetCommand(Command):
    name = "set"
    capsule_access: ClassVar[CapsuleAccess] = CapsuleAccess.MUTATES
    help = ("Save an environment variable for this checkout, privately: VALUE, or a hidden prompt without it; "
            "--from-host passes the host's variable through at each launch instead.")

    @classmethod
    def configure(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("key", metavar="NAME")
        parser.add_argument("value", metavar="VALUE", nargs="?")
        parser.add_argument("--from-host", action="store_true", dest="from_host",
                            help="Save only the variable name; Docker reads its value from the host at each launch.")

    @classmethod
    def run(cls, arguments: argparse.Namespace, context: object | None) -> int:
        path = _managed_arguments_path(context)
        validate_name(arguments.key)
        if arguments.from_host:
            if arguments.value is not None:
                raise ProjectConfigurationError("Give VALUE or --from-host, not both.")
            update_environment(path, arguments.key, None, from_host=True)
            print(f"{arguments.key} is taken from the host's environment at each launch of this checkout.")
            return 0
        value = arguments.value if arguments.value is not None else _hidden_value_prompt()
        update_environment(path, arguments.key, value)
        print(f"Saved {arguments.key} for this checkout, privately. The next 'devcapsule project run' uses it.")
        return 0


class ConfigEnvUnsetCommand(Command):
    name = "unset"
    capsule_access: ClassVar[CapsuleAccess] = CapsuleAccess.MUTATES
    help = "Remove a saved or passed-through environment variable from this checkout."

    @classmethod
    def configure(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("key", metavar="NAME")

    @classmethod
    def run(cls, arguments: argparse.Namespace, context: object | None) -> int:
        update_environment(_managed_arguments_path(context), arguments.key, None)
        print(f"Removed {arguments.key} from this checkout's environment. A running capsule is unchanged.")
        return 0


class ConfigEnvListCommand(Command):
    name = "list"
    # Host-owned file is deliberately not mounted into the running capsule.
    capsule_access: ClassVar[CapsuleAccess] = CapsuleAccess.MUTATES
    help = "List this checkout's environment variables by name, never their values."

    @classmethod
    def configure(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--json", dest="as_json", action="store_true", help=STABLE_JSON_HELP)

    @classmethod
    def run(cls, arguments: argparse.Namespace, context: object | None) -> int:
        path = _managed_arguments_path(context)
        saved = read_environment(path)
        if arguments.as_json:
            print(json.dumps({"path": str(path), "names": sorted(saved),
                              "from-host": sorted(name for name, value in saved.items() if value is None)}, sort_keys=True))
            return 0
        print(f"Docker arguments file: {path}")
        if not saved:
            print("No environment variables for this checkout.")
        for name in sorted(saved):
            print(f"{name}  ({'from the host' if saved[name] is None else 'saved'})")
        return 0


class ConfigEnvGroup(Group):
    name = "env"
    help = "This checkout's environment variables: set (saved privately, or from the host), unset, list."

    @classmethod
    def subcommands(cls) -> Mapping[str, type[Command] | type[Group]]:
        return {"set": ConfigEnvSetCommand, "unset": ConfigEnvUnsetCommand, "list": ConfigEnvListCommand}


class ConfigDockerArgsSetCommand(Command):
    name = "set"
    capsule_access: ClassVar[CapsuleAccess] = CapsuleAccess.MUTATES
    help = "Replace this checkout's saved 'docker run' options with the tokens after '--'."
    passthrough_dest = "docker_options"
    passthrough_metavar = "DOCKER-RUN-OPTIONS"

    @classmethod
    def run(cls, arguments: argparse.Namespace, context: object | None) -> int:
        options = list(arguments.docker_options)
        if not options:
            raise ProjectConfigurationError("Give the Docker options after '--'; 'docker-args clear' removes the saved ones.")
        _validate_extra_docker_args(options)
        replace_arguments(_managed_arguments_path(context), options)
        print("Saved the Docker options for this checkout. The next 'devcapsule project run' passes them.")
        return 0


class ConfigDockerArgsListCommand(Command):
    name = "list"
    capsule_access: ClassVar[CapsuleAccess] = CapsuleAccess.MUTATES
    help = "List the saved 'docker run' options, environment values masked."

    @classmethod
    def configure(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--json", dest="as_json", action="store_true", help=STABLE_JSON_HELP)

    @classmethod
    def run(cls, arguments: argparse.Namespace, context: object | None) -> int:
        path = _managed_arguments_path(context)
        options = redact_environment(read_arguments(path))
        if arguments.as_json:
            print(json.dumps({"path": str(path), "arguments": options}, sort_keys=True))
        else:
            print(f"Docker arguments file: {path}")
            print(shlex.join(options) if options else "No saved Docker options.")
        return 0


class ConfigDockerArgsClearCommand(Command):
    name = "clear"
    capsule_access: ClassVar[CapsuleAccess] = CapsuleAccess.MUTATES
    help = "Remove every saved 'docker run' option, the environment variables among them."

    @classmethod
    def run(cls, arguments: argparse.Namespace, context: object | None) -> int:
        replace_arguments(_managed_arguments_path(context), [])
        print("Removed the saved Docker options. A running capsule is unchanged.")
        return 0


class ConfigDockerArgsGroup(Group):
    name = "docker-args"
    help = "Extra 'docker run' options saved for this checkout: set (after '--'), list, clear."

    @classmethod
    def subcommands(cls) -> Mapping[str, type[Command] | type[Group]]:
        return {"set": ConfigDockerArgsSetCommand, "list": ConfigDockerArgsListCommand, "clear": ConfigDockerArgsClearCommand}


ConfigSetEnvCommand = _retired_command("set-env", "config env set")
ConfigUnsetEnvCommand = _retired_command("unset-env", "config env unset")
ConfigListEnvCommand = _retired_command("list-env", "config env list")
ConfigSetExtraDockerArgsCommand = _retired_command("set-extra-docker-args", "config docker-args set")
ConfigListExtraDockerArgsCommand = _retired_command("list-extra-docker-args", "config docker-args list")
ConfigRemoveExtraDockerArgsCommand = _retired_command("remove-extra-docker-args", "config docker-args clear")


def _validate_extra_docker_args(options: list[str]) -> None:
    try:
        reject_launcher_owned_docker_options(options)
    except PycharmRunError as exc:
        raise ProjectConfigurationError(str(exc)) from exc


class ConfigBindCommand(Command):
    name = "bind"
    capsule_access: ClassVar[CapsuleAccess] = CapsuleAccess.MUTATES
    help = "Bind a declared logical resource to a developer-owned provider (PROVIDER:VALUE)."

    @classmethod
    def configure(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("node_name", metavar="NAME")
        parser.add_argument(
            "value",
            metavar="PROVIDER:VALUE",
            help="host-directory:PATH for state, host-environment:VARIABLE for a declared secret.",
        )

    @classmethod
    def run(cls, arguments: argparse.Namespace, context: object | None) -> int:
        name = arguments.node_name
        root, manifest = manifest_for(_project_context(context).start_path())
        _lock_path, lock = lock_for(root, manifest)
        registry = build_node_registry(manifest, lock)
        provider, raw_value = registry.split_bind_value(name, arguments.value)
        node = registry.node(name)

        record = CheckoutRecord(manifest, root)
        apply_configuration_answers((ProvidedAnswer("bind", name, arguments.value),), manifest, lock, record)
        record.write()
        if provider == PROVIDER_HOST_DIRECTORY:
            source = Path(record.directory_bindings[name])
            declaration = node.declaration
            print(
                f"WARNING: exposing host directory read-write for {name}: {source} -> "
                f"{declaration.container_path}",
                file=sys.stderr,
            )
            print(f"Sensitivity: {declaration.sensitivity}", file=sys.stderr)
            if not declaration.concurrent:
                print(
                    "Concurrency: exclusive; do not share this binding with a concurrent capsule.",
                    file=sys.stderr,
                )
            print(f"Bound {name} to host directory: {source}")
        else:
            print(
                f"WARNING: {raw_value} will be visible to every process in the capsule "
                "and through Docker container inspection while it runs.",
                file=sys.stderr,
            )
            print(f"Bound {name} to host environment variable: {raw_value}")
        print(f"Checkout input: {record.input_path}")
        print("The next 'devcapsule project run' uses it.")
        return 0


class ConfigApproveCommand(Command):
    name = "approve"
    capsule_access: ClassVar[CapsuleAccess] = CapsuleAccess.MUTATES
    help = (
        "Approve new versions of vendor software you approved before, after the project's "
        "lock changed; the vendors and their terms are unchanged. Lists what is pending; "
        "NAME... or --all records the approvals. The resolution is regenerated "
        "when no software approvals remain."
    )

    @classmethod
    def configure(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("names", metavar="NAME", nargs="*", help="an authorization name from the list")
        parser.add_argument("--all", action="store_true", help="approve every pending software update")

    @classmethod
    def run(cls, arguments: argparse.Namespace, context: object | None) -> int:
        root, manifest = manifest_for(_project_context(context).start_path())
        if arguments.all and arguments.names:
            raise ProjectConfigurationError("--all cannot be combined with NAME.")
        approvals = pending_software_approvals_for(root, manifest)
        if approvals is None:
            raise ProjectConfigurationError(
                "The pending decisions are not all software approvals; review them one by one: "
                + shlex.join(["devcapsule", "project", "--path", str(root), "config", "resolve"])
            )
        if not approvals:
            print("No software approvals are pending for this checkout.")
            return 0
        for line in render_software_approvals(approvals):
            print(line)
        if not arguments.all and not arguments.names:
            print(f"Approve with: {software_approve_command(root)}, or name the ones to approve.")
            print(f"Software approvals: {SOFTWARE_APPROVALS_GUIDE_URL}")
            return 1
        selected = approvals if arguments.all else select_software_approvals(approvals, tuple(arguments.names))
        approve_software(root, manifest, selected)
        return 0


def _forget_authorization(root: Path, manifest: dict[str, Any], name: str) -> Path:
    """Remove the recorded answer for one host access or consent; the row returns to its default."""
    record = CheckoutRecord(manifest, root)
    legacy = record.host.pop(name, None)
    removed = record.authorization.pop(name, legacy)
    if removed is None:
        raise ProjectConfigurationError(f"{name!r} has no recorded answer for this checkout.")
    record.write()
    return record.input_path


class ConfigForgetCommand(Command):
    name = "forget"
    capsule_access: ClassVar[CapsuleAccess] = CapsuleAccess.MUTATES
    help = "Forget your recorded answer for a host access or a consent; the next launch uses the default, or asks again."

    @classmethod
    def configure(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("node_name", metavar="NAME")

    @classmethod
    def run(cls, arguments: argparse.Namespace, context: object | None) -> int:
        root, manifest = manifest_for(_project_context(context).start_path())
        input_path = _forget_authorization(root, manifest, arguments.node_name)
        print(f"Forgot {arguments.node_name} for this checkout.")
        print(f"Checkout record: {input_path}")
        print("The next 'devcapsule project run' uses it.")
        return 0


class ConfigDenyCommand(Command):
    name = "deny"
    capsule_access: ClassVar[CapsuleAccess] = CapsuleAccess.MUTATES
    help = "Deny a host access for this checkout, recorded: network, docker-daemon, development-sudo, host-browser, host-x11."

    @classmethod
    def configure(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("node_name", metavar="NAME")

    @classmethod
    def run(cls, arguments: argparse.Namespace, context: object | None) -> int:
        name = arguments.node_name
        root, manifest = manifest_for(_project_context(context).start_path())
        _lock_path, lock = _lock_for_answers(root, manifest)
        declarations = authorization_declarations(manifest, lock)
        declaration = declarations.get(name)
        if declaration is None or declaration.required:
            available = ", ".join(sorted(key for key, item in declarations.items() if not item.required)) or "none"
            raise ProjectConfigurationError(f"{name!r} is not a host access that can be denied; deniable: {available}.")
        record = CheckoutRecord(manifest, root)
        record.authorize(declaration, normalize_authorization_value(declaration, "none"))
        record.write()
        print(f"Denied {name} for this checkout: {render_authorization_value(normalize_authorization_value(declaration, 'none'))}.")
        print(f"Checkout record: {record.input_path}")
        print("The next 'devcapsule project run' uses it.")
        return 0


def _lock_for_answers(root: Path, manifest: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    """The checkout's effective lock when it has an IDE, else the composed one: host answers need no IDE."""
    from devcapsule.configuration.storage import composition_for
    try:
        return lock_for(root, manifest)
    except ProjectConfigurationError:
        path, composed, _checkout = composition_for(root, manifest)
        return path, composed


ConfigUnsetCommand = _retired_command("unset", "config set NAME default', 'config forget NAME' or 'config unbind NAME")


class ConfigTrustListCommand(Command):
    name = "list"
    capsule_access: ClassVar[CapsuleAccess] = CapsuleAccess.INSPECTS
    help = "The channels this project's software comes through and whether this home trusts each."

    @classmethod
    def configure(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--json", dest="as_json", action="store_true", help=STABLE_JSON_HELP)

    @classmethod
    def run(cls, arguments: argparse.Namespace, context: object | None) -> int:
        from devcapsule.configuration.derivation import load_state
        from devcapsule.configuration.storage import load_trust, settings_path
        from devcapsule.configuration.trust import HomeTrust, channels_for
        root, manifest = manifest_for(_project_context(context).start_path())
        lock = load_state(root, manifest).composed_lock()
        trust = HomeTrust.read(load_trust())
        channels = channels_for(lock)
        rows: list[dict[str, Any]] = [
            {"channel": channel.id, "vendor": channel.vendor, "product": channel.product,
             "origins": list(channel.origins), "terms-url": channel.terms_url,
             "integrity": channel.integrity, "accepted": trust.channels.get(channel.id),
             "trusted": trust.covers(channel), "note": channel.note} for channel in channels.values()]
        for channel_id, entry in trust.channels.items():
            if channel_id not in channels:
                rows.append({"channel": channel_id, "vendor": entry["vendor"], "product": "", "origins": entry["origins"],
                             "terms-url": entry["terms-url"], "integrity": entry["integrity"], "accepted": entry,
                             "trusted": bool(entry["integrity"]), "note": "not used by this checkout"})
        if arguments.as_json:
            print(json.dumps({"schema-version": 1, "path": str(settings_path()), "channels": rows}, indent=2, sort_keys=True))
            return 0
        print(f"Trust record: {settings_path()}")
        print(f"Scope: this DevCapsule home, {config_root()}. Anyone who uses this home uses this acceptance.")
        for row in rows:
            state = "trusted" if row["trusted"] else ("not covered" if row["accepted"] else "not yet")
            origins = ", ".join(str(item) for item in row["origins"]) or "the lock"
            terms = f"; terms {row['terms-url']}" if row["terms-url"] else ""
            print(f"{row['channel']:<18} {state:<11} {row['vendor']} — {row['product'] or '(not used by this checkout)'}; "
                  f"from {origins}; integrity {row['integrity'] or 'not recorded'}{terms}")
            if row["accepted"] and not row["trusted"]:
                entry = row["accepted"]
                print(f"{'':<18} Accepted origins: {', '.join(entry['origins'])}; "
                      f"integrity {entry['integrity'] or 'not recorded'}; terms {entry['terms-url'] or 'none'}")
            if row["note"]:
                print(f"{'':<18} {row['note']}")
        return 0


class ConfigConsoleListCommand(Command):
    name = "list"
    capsule_access: ClassVar[CapsuleAccess] = CapsuleAccess.INSPECTS
    help = "The widenings asked on the console during a run, awaiting your confirmation on the host."

    @classmethod
    def configure(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--json", dest="as_json", action="store_true", help=STABLE_JSON_HELP)

    @classmethod
    def run(cls, arguments: argparse.Namespace, context: object | None) -> int:
        from devcapsule.configuration.console_requests import console_requests_path, deferred_requests
        root, manifest = manifest_for(_project_context(context).start_path())
        record = find_checkout_record(manifest, root)
        requests = deferred_requests(record) if record is not None else []
        if arguments.as_json:
            print(json.dumps({"schema-version": 1, "path": str(console_requests_path(record)) if record else None,
                              "requests": [item.document() for item in requests]}, indent=2, sort_keys=True))
            return 0
        if not requests:
            print("No console request awaits confirmation for this checkout.")
            return 0
        for item in requests:
            print(f"{item.id}  asked {item.requested}: {item.statement}")
        print("Apply one: devcapsule project config console apply ID; discard one: ... console discard ID")
        return 0


class ConfigConsoleApplyCommand(Command):
    name = "apply"
    capsule_access: ClassVar[CapsuleAccess] = CapsuleAccess.MUTATES
    help = "Run a console request as its command and forget it."

    @classmethod
    def configure(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("request", metavar="ID", help="As 'console list' names it.")

    @classmethod
    def run(cls, arguments: argparse.Namespace, context: object | None) -> int:
        from devcapsule.commands._console_channel import apply_deferred
        root, manifest = manifest_for(_project_context(context).start_path())
        record = find_checkout_record(manifest, root)
        if record is None:
            raise ProjectConfigurationError("This checkout has no record, so no console request awaits it.")
        status, output = apply_deferred(root, record, arguments.request)
        if output:
            print(output)
        if status == 0:
            print(f"Applied and forgot the console request {arguments.request}.")
        return status


class ConfigConsoleDiscardCommand(Command):
    name = "discard"
    capsule_access: ClassVar[CapsuleAccess] = CapsuleAccess.MUTATES
    help = "Forget a console request without applying it."

    @classmethod
    def configure(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("request", metavar="ID", help="As 'console list' names it.")

    @classmethod
    def run(cls, arguments: argparse.Namespace, context: object | None) -> int:
        from devcapsule.commands._console_channel import discard_deferred
        root, manifest = manifest_for(_project_context(context).start_path())
        record = find_checkout_record(manifest, root)
        if record is None:
            raise ProjectConfigurationError("This checkout has no record, so no console request awaits it.")
        discard_deferred(record, arguments.request)
        print(f"Discarded the console request {arguments.request}.")
        return 0


class ConfigConsoleGroup(Group):
    name = "console"
    help = "The console's requests that widen the next launch, kept for your confirmation: list, apply, discard."

    @classmethod
    def subcommands(cls) -> Mapping[str, type[Command] | type[Group]]:
        return {"list": ConfigConsoleListCommand, "apply": ConfigConsoleApplyCommand, "discard": ConfigConsoleDiscardCommand}


class ConfigTrustGroup(Group):
    name = "trust"
    help = "Whether this home trusts the channels used by this project."

    @classmethod
    def subcommands(cls) -> Mapping[str, type[Command] | type[Group]]:
        return {"list": ConfigTrustListCommand}


class ConfigUnbindCommand(Command):
    name = "unbind"
    capsule_access: ClassVar[CapsuleAccess] = CapsuleAccess.MUTATES
    help = "Return a state directory or a secret input to its managed default."

    @classmethod
    def configure(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("node_name", metavar="NAME")

    @classmethod
    def run(cls, arguments: argparse.Namespace, context: object | None) -> int:
        name = arguments.node_name
        root, manifest = manifest_for(_project_context(context).start_path())
        record = CheckoutRecord(manifest, root)
        removed = (record.directory_bindings.pop(name, None) or record.environment_bindings.pop(name, None)
                   or record.state.pop(name, None))
        if removed is None:
            raise ProjectConfigurationError(f"{name!r} is not bound for this checkout.")
        record.write()
        print(f"Unbound {name} for this checkout; the managed default applies.")
        print(f"Checkout record: {record.input_path}")
        print("The next 'devcapsule project run' uses it.")
        return 0


class ConfigAuthorizeCommand(Command):
    name = "authorize"
    capsule_access: ClassVar[CapsuleAccess] = CapsuleAccess.MUTATES
    help = (
        "Authorize project-recommended host access or select an exact inspected "
        "local DevCapsule base."
    )

    @classmethod
    def configure(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("node_name", metavar="NAME", nargs="?")
        parser.add_argument("value", metavar="VALUE", nargs="?")
        parser.add_argument("justification", metavar="JUSTIFICATION", nargs="?")
        parser.add_argument(
            "--all-recommended",
            action="store_true",
            help="Preview every recommendation and authorize all only after the y key is pressed.",
        )

    @classmethod
    def run(cls, arguments: argparse.Namespace, context: object | None) -> int:
        name = arguments.node_name
        value = arguments.value
        root, manifest = manifest_for(_project_context(context).start_path())
        _lock_path, lock = _lock_for_answers(root, manifest)
        declarations = authorization_declarations(manifest, lock)
        if arguments.all_recommended:
            if name is not None or value is not None:
                raise ProjectConfigurationError(
                    "--all-recommended cannot be combined with an authorization NAME or VALUE."
                )
            return _authorize_all_recommended(root, manifest, declarations)
        if name is None or value is None:
            raise ProjectConfigurationError(
                "Provide NAME VALUE, or use --all-recommended for interactive bulk authorization."
            )
        if arguments.justification is not None:
            # The justification facet belongs to recommendation authoring at
            # init; an already-declared recommendation carries its own.
            raise ProjectConfigurationError(
                "A justification is recorded when the project owner authors the recommendation "
                "at 'devcapsule project init'; it does not apply to authorizing this checkout."
            )
        declaration = declarations.get(name)
        if declaration is None:
            available = ", ".join(sorted(declarations)) or "none"
            raise ProjectConfigurationError(
                f"Authorization {name!r} is not declared by this project and lock; "
                f"declared authorizations: {available}."
            )
        local_base_identity: str | None = None
        local_base_value = (
            name == "base-image"
            and value.strip().lower() not in {"default", "none"}
            and value != declaration.recommended_value
        )
        if local_base_value:
            try:
                immutable_registry_reference(value)
            except ProjectConfigurationError:
                pass
            else:
                # A different published digest needs its own project-reviewed
                # recommendation. Only a daemon-local selection is exempt.
                normalize_authorization_value(declaration, value)
            platform_name = lock.get("platform")
            if not isinstance(platform_name, str) or not platform_name:
                raise ProjectConfigurationError("Platform lock must name its target platform.")
            local_base = required_local_image(value)
            validate_base_image(
                local_base,
                platform=platform_name,
                expected_identity=None,
            )
            normalized: str | bool = value
            local_base_identity = local_base.identity
        else:
            normalized = normalize_authorization_value(declaration, value)

        record = CheckoutRecord(manifest, root)
        input_path = record.input_path
        record.authorize(declaration, normalized, local_base_identity)
        record.write()
        authorized_value = render_authorization_value(normalized)
        if local_base_identity is None and declaration.display_value is not None:
            authorized_value = declaration.display_value
        print(f"Authorized {name} for this checkout: {authorized_value}")
        if local_base_identity is not None:
            print(f"Local image ID: {local_base_identity}")
            print(
                "This developer-owned selection overrides the published base recommendation "
                "for this checkout."
            )
        elif declaration.project_recommended:
            print(f"The project's reason: {declaration.description}")
        else:
            print(f"What this grants: {declaration.description}")
        print(f"Checkout record: {input_path}")
        if name == "base-image":
            print(
                "This consent applies to the exact recorded image, by digest or by local image "
                "identity, and stays valid while the lock recommends that image."
            )
            if local_base_identity is None:
                print("DevCapsule's published bases are trusted once for the whole home instead: "
                      "'devcapsule home trust accept devcapsule-base'.")
        print("The next 'devcapsule project run' uses it.")
        return 0


class _OwnerEnvironmentCommand(Command):
    """One owner verb over the environment the project asks of each developer."""

    name = "env"
    capsule_access: ClassVar[CapsuleAccess] = CapsuleAccess.MUTATES
    verb: ClassVar[str] = ""
    help = ""

    @classmethod
    def configure(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("names", nargs="+", metavar="NAME", help="An environment variable name such as POSTGRES_HOST.")
        if cls.verb != "drop":
            parser.add_argument("--because", metavar="REASON", help="The reason a developer reads when asked for the value.")
        parser.add_argument("--preview", action="store_true", help="Validate and show the result; write nothing.")

    @classmethod
    def run(cls, arguments: argparse.Namespace, context: object | None) -> int:
        from devcapsule.configuration import owner_commands
        start = _project_context(context).start_path()
        if cls.verb == "drop":
            print(owner_commands.drop_environment(start, arguments.names, preview=arguments.preview))
        elif cls.verb == "require":
            print(owner_commands.require_environment(start, arguments.names, because=arguments.because, preview=arguments.preview))
        else:
            print(owner_commands.offer_environment(start, arguments.names, because=arguments.because, preview=arguments.preview))
        return 0


def _owner_group(verb: str, help_text: str, tool_help: str, env_help: str) -> type[Command]:
    class OwnerCommand(Command):
        name = verb
        help = help_text + " Use env NAME for environment declarations. Owner edits write schema 2; rc3 and older launchers cannot read it."
        capsule_access: ClassVar[CapsuleAccess] = CapsuleAccess.MUTATES

        @classmethod
        def configure(cls, parser: argparse.ArgumentParser) -> None:
            parser.add_argument("names", nargs="+", metavar="CAPABILITY")
            if verb != "drop":
                parser.add_argument("--because", metavar="REASON")
            parser.add_argument("--preview", action="store_true")
            parser.add_argument("--unverified", action="store_true", dest="allow_unverified")

        @classmethod
        def run(cls, arguments: argparse.Namespace, context: object | None) -> int:
            from devcapsule.configuration import owner_commands
            names = arguments.names
            command: type[Command]
            if names[0] == "env":
                if len(names) == 1:
                    raise ProjectConfigurationError("env needs at least one environment variable name.")
                arguments.names = names[1:]
                command = type("EnvironmentCommand", (_OwnerEnvironmentCommand,), {"verb": verb})
                return command.run(arguments, context)
            if names[0] == "tool":
                raise ProjectConfigurationError(f"config {verb} tool is retired; use 'devcapsule project config {verb} CAPABILITY'.")
            print(owner_commands.edit_capabilities(_project_context(context).start_path(), verb, names,
                  because=getattr(arguments, "because", None), preview=arguments.preview,
                  allow_unverified=arguments.allow_unverified))
            return 0

    OwnerCommand.__name__ = f"Config{verb.title()}Command"
    return OwnerCommand


ConfigRequireGroup = _owner_group(
    "require", "Project owners: what every checkout must have.",
    "Require tools, regenerating the lock; each name declares a capability.",
    "Require environment variables every developer supplies, privately, before the first launch.",
)
ConfigOfferGroup = _owner_group(
    "offer", "Project owners: what a developer may take or leave.",
    "Offer tools a developer may omit; the lock pins them.",
    "Offer environment variables a developer may supply.",
)
ConfigDropGroup = _owner_group(
    "drop", "Project owners: remove a requirement or an offer.",
    "Drop tools from the project's requirements and offers, with their minimum versions.",
    "Drop environment declarations from the project.",
)


class ConfigRecommendCommand(Command):
    name = "recommend"
    capsule_access: ClassVar[CapsuleAccess] = CapsuleAccess.MUTATES
    help = (
        "Project owners: recommend a capability's provider, an IDE, a memory limit, a CPU count, or a host access "
        "(network host, docker-daemon host-socket, development-sudo true, host-browser true) with the reason; "
        "'none' removes the recommendation. Writes schema 2; rc3 and older launchers cannot read it."
    )

    @classmethod
    def configure(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("recommendation", metavar="NAME", help="A capability for a provider recommendation, or ide, memory, cpus, network, docker-daemon, development-sudo, host-browser.")
        parser.add_argument("value", metavar="VALUE", help="The recommended value, or none.")
        parser.add_argument("--because", metavar="REASON", help="The reason a developer reads; required for a host access.")
        parser.add_argument("--preview", action="store_true", help="Validate and show the result; write nothing.")

    @classmethod
    def run(cls, arguments: argparse.Namespace, context: object | None) -> int:
        from devcapsule.configuration import owner_commands
        print(owner_commands.recommend(_project_context(context).start_path(), arguments.recommendation,
                                       arguments.value, because=arguments.because, preview=arguments.preview))
        return 0


ConfigNeedCommand = _retired_command("need", "config require CAPABILITY; config ide IDE or config add CAPABILITY for this checkout")


class ConfigCheckCommand(Command):
    name = "check"
    capsule_access: ClassVar[CapsuleAccess] = CapsuleAccess.INSPECTS
    help = ("Validate the project's contract and this checkout without writing or launching; "
            "exit 3 naming each pending decision and its command, for scripts.")

    @classmethod
    def configure(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--manifest", type=Path, help="Candidate manifest; defaults to the project's manifest.")
        parser.add_argument("--lock", type=Path, help="Candidate platform lock; defaults to this platform's lock.")
        parser.add_argument("--json", dest="as_json", action="store_true", help=STABLE_JSON_HELP)

    @classmethod
    def run(cls, arguments: argparse.Namespace, context: object | None) -> int:
        from devcapsule.configuration.capability_commands import check
        contract = check(_project_context(context).start_path(), manifest_path=arguments.manifest, lock_path=arguments.lock)
        if arguments.manifest is not None or arguments.lock is not None:
            print(json.dumps({"contract": contract.splitlines()[0], "context": "candidate contract"})
                  if arguments.as_json else contract)
            return 0
        loaded = _load_checkout_documents(context)
        if isinstance(loaded, runtime_configuration.RuntimeConfiguration):
            note = "Host decisions cannot be assessed inside this capsule; run config check with the host launcher."
            print(json.dumps({**loaded.configuration_document(), "contract": contract.splitlines()[0], "notes": [note]})
                  if arguments.as_json else contract + "\n" + note)
            return 0
        listing = _assess(loaded)
        if arguments.as_json:
            print(json.dumps({**listing.document(), "contract": contract.splitlines()[0]}, indent=2, sort_keys=True))
        else:
            print(contract)
        if listing.pending:
            raise DecisionPending(listing.render_pending())
        if not arguments.as_json:
            print("Nothing is pending for this checkout.")
        return 0


def _local_selection(context: object | None) -> tuple[Path, dict[str, Any], LocalCapabilities, dict[str, str]]:
    """The checkout's current selection and the catalog's IDE names, for the selection verbs."""
    from devcapsule.configuration.storage import project_platform
    from devcapsule.resolution_matrix import MATRICES
    root, manifest = manifest_for(_project_context(context).start_path())
    record = find_checkout_record(manifest, root)
    current = LocalCapabilities.read(load_checkout(record, manifest, root)) if record is not None else LocalCapabilities()
    matrix = MATRICES[project_platform(root)]
    surfaces = {name: matrix.resolve_provider(name) or name for name in matrix.ide_capabilities()}
    return root, manifest, current, surfaces


def _capability_name(value: str, names: Mapping[str, str], kind: str) -> str:
    candidate = value.strip()
    by_component = {component: name for name, component in names.items()}
    candidate = by_component.get(candidate, candidate)
    if candidate not in names:
        raise ProjectConfigurationError(f"Unknown {kind} {value!r}; choose one of {', '.join(sorted(names))}.")
    return candidate


def _replace_selection(root: Path, selected: tuple[str, ...], without: tuple[str, ...] | None, allow_unverified: bool,
                       providers: Mapping[str, str] | None = None) -> None:
    from devcapsule.configuration.capability_commands import configure
    configure(root, local=list(selected), without=None if without is None else list(without), allow_unverified=allow_unverified, providers=providers)


class ConfigIdeCommand(Command):
    name = "ide"
    capsule_access: ClassVar[CapsuleAccess] = CapsuleAccess.MUTATES
    help = "Choose this checkout's IDE: python-ide, frontend-ide, vscode-ide, java-ide, eclipse-ide or dotnet-ide."

    @classmethod
    def configure(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("ide", metavar="IDE")
        parser.add_argument("--unverified", action="store_true", dest="allow_unverified",
                            help="Accept a combination the matrix has not validated; the record says so.")

    @classmethod
    def run(cls, arguments: argparse.Namespace, context: object | None) -> int:
        from devcapsule.configuration.derivation import load_state
        root, manifest, current, surfaces = _local_selection(context)
        ide = _capability_name(arguments.ide, surfaces, "IDE")
        selected = tuple(sorted({*(name for name in current.selected if name not in surfaces), ide}))
        providers = {name: value for name, value in current.providers.items() if name not in surfaces or name == ide}
        _replace_selection(root, selected, None, arguments.allow_unverified, providers)
        composed = load_state(root, manifest).composed_lock()
        provider = composed.get("components", {}).get("interactive-surface") or surfaces[ide]
        print(f"Your IDE for this checkout: {ide} ({provider}).")
        print("The next 'devcapsule project run' uses it.")
        return 0


class ConfigAgentGroup(Group):
    name = "agent"
    hidden = True

    @classmethod
    def subcommands(cls) -> Mapping[str, type[Command] | type[Group]]:
        return {"add": _retired_command("add", "config add CAPABILITY"),
                "remove": _retired_command("remove", "config omit CAPABILITY")}


class ConfigToolGroup(Group):
    name = "tool"
    hidden = True

    @classmethod
    def subcommands(cls) -> Mapping[str, type[Command] | type[Group]]:
        return {"omit": _retired_command("omit", "config omit CAPABILITY"),
                "restore": _retired_command("restore", "config restore CAPABILITY")}


class ConfigAddCommand(Command):
    name = "add"
    help = "Add a capability the project did not declare to this checkout."
    capsule_access: ClassVar[CapsuleAccess] = CapsuleAccess.MUTATES

    @classmethod
    def configure(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("capability", metavar="CAPABILITY")
        parser.add_argument("--unverified", action="store_true", dest="allow_unverified")

    @classmethod
    def run(cls, arguments: argparse.Namespace, context: object | None) -> int:
        from devcapsule.configuration.derivation import load_state, Selection
        from devcapsule.configuration.capability_commands import configure
        root, manifest = manifest_for(_project_context(context).start_path())
        state = load_state(root, manifest)
        policy = CapabilityPolicy.read(manifest)
        current = LocalCapabilities.read(state.checkout)
        selection = Selection(current, state.surfaces)
        name = state.matrix.canonical_name(arguments.capability)
        from devcapsule.configuration.capability_selection import known_policy_names
        declared = {canonical: name for name, canonical in known_policy_names(policy, state.matrix).items()}
        if cls.name == "add":
            if state.matrix.is_ide(name):
                raise ProjectConfigurationError(f"Choose an IDE with 'config ide {name}'.")
            if name in declared:
                raise ProjectConfigurationError(f"{name!r} is already declared by the project; use 'config restore {name}' if omitted.")
            selection.extra.add(name)
        elif cls.name == "omit":
            required = {state.matrix.canonical_name(item) for item in policy.required}
            if name in required and declared.get(name) not in policy.optional:
                raise ProjectConfigurationError(f"Required capability {name!r} cannot be omitted.")
            if name in declared:
                selection.without.add(declared[name])
                selection.extra.discard(name)
            elif name in selection.extra:
                selection.extra.remove(name)
                selection.providers.pop(name, None)
            else:
                raise ProjectConfigurationError(f"{name!r} is neither offered nor added to this checkout.")
        else:
            if name not in declared or declared[name] not in policy.optional:
                raise ProjectConfigurationError(f"{name!r} is not offered by the project.")
            selection.without.discard(declared[name])
        local = selection.local()
        print(configure(root, local=local.selected, without=local.without, providers=local.providers,
                        allow_unverified=arguments.allow_unverified))
        return 0


class ConfigOmitCommand(ConfigAddCommand):
    name = "omit"
    help = "Omit an offered capability or remove a checkout addition."
    capsule_access: ClassVar[CapsuleAccess] = CapsuleAccess.MUTATES


class ConfigRestoreCommand(ConfigAddCommand):
    name = "restore"
    help = "Restore a capability offered by the project."
    capsule_access: ClassVar[CapsuleAccess] = CapsuleAccess.MUTATES


class ConfigUseCommand(Command):
    name = "use"
    help = "Choose a capability's provider; default follows the project or catalog."
    capsule_access: ClassVar[CapsuleAccess] = CapsuleAccess.MUTATES

    @classmethod
    def configure(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("capability", metavar="CAPABILITY")
        parser.add_argument("component", metavar="COMPONENT|default")
        parser.add_argument("--unverified", action="store_true", dest="allow_unverified")

    @classmethod
    def run(cls, arguments: argparse.Namespace, context: object | None) -> int:
        from devcapsule.configuration.derivation import load_state, Selection
        from devcapsule.configuration.capability_commands import configure
        from devcapsule.configuration.manifest_document import Recommendations
        root, manifest = manifest_for(_project_context(context).start_path())
        state = load_state(root, manifest)
        selection = Selection(LocalCapabilities.read(state.checkout), state.surfaces)
        selection.use(state.matrix, CapabilityPolicy.read(manifest), Recommendations.read(manifest),
                      arguments.capability, arguments.component)
        print(configure(root, providers=selection.providers, allow_unverified=arguments.allow_unverified))
        return 0


class ConfigCapabilitiesCommand(Command):
    name = "capabilities"
    hidden = True
    capsule_access: ClassVar[CapsuleAccess] = CapsuleAccess.MUTATES
    help = "Recover an interrupted manifest/lock transaction."

    @classmethod
    def configure(cls, parser: argparse.ArgumentParser) -> None:
        for flag, replacement in (("--local", "config ide IDE or config add CAPABILITY"),
                                  ("--without", "config omit CAPABILITY or config restore CAPABILITY"),
                                  ("--required", "config require CAPABILITY"),
                                  ("--optional", "config offer CAPABILITY"),
                                  ("--sdk-major", "config require 'NAME>=VERSION'")):
            _retired_option(parser, flag, "devcapsule project " + replacement)
        parser.add_argument("--recover", action="store_true", help="Finish or undo an interrupted shared configuration edit.")

    @classmethod
    def run(cls, arguments: argparse.Namespace, context: object | None) -> int:
        from devcapsule.configuration.capability_commands import recover
        from devcapsule.configuration.storage import discover_project
        if not arguments.recover:
            raise ProjectConfigurationError("Use 'devcapsule project config capabilities --recover' for recovery; use 'config show' to inspect.")
        root = _project_context(context).start_path().expanduser().resolve()
        recover(root if (root / ".devcapsule/.capability-transaction.toml").exists() else discover_project(root))
        print("Configuration transaction recovered (or none pending).")
        return 0


class ConfigGroup(Group):
    name = "config"
    help = "This checkout's choices and the project's contract: show what the next launch uses, change one thing, check."

    @classmethod
    def subcommands(cls) -> Mapping[str, type[Command] | type[Group]]:
        return {
            ConfigShowCommand.name: ConfigShowCommand,
            ConfigListCommand.name: ConfigListCommand,
            ConfigCheckCommand.name: ConfigCheckCommand,
            ConfigIdeCommand.name: ConfigIdeCommand,
            ConfigAddCommand.name: ConfigAddCommand,
            ConfigOmitCommand.name: ConfigOmitCommand,
            ConfigRestoreCommand.name: ConfigRestoreCommand,
            ConfigUseCommand.name: ConfigUseCommand,
            ConfigAgentGroup.name: ConfigAgentGroup,
            ConfigToolGroup.name: ConfigToolGroup,
            ConfigSetCommand.name: ConfigSetCommand,
            ConfigAuthorizeCommand.name: ConfigAuthorizeCommand,
            ConfigDenyCommand.name: ConfigDenyCommand,
            ConfigForgetCommand.name: ConfigForgetCommand,
            ConfigBindCommand.name: ConfigBindCommand,
            ConfigUnbindCommand.name: ConfigUnbindCommand,
            ConfigTrustGroup.name: ConfigTrustGroup,
            ConfigConsoleGroup.name: ConfigConsoleGroup,
            ConfigEnvGroup.name: ConfigEnvGroup,
            ConfigDockerArgsGroup.name: ConfigDockerArgsGroup,
            ConfigApproveCommand.name: ConfigApproveCommand,
            ConfigResolveCommand.name: ConfigResolveCommand,
            ConfigRequireGroup.name: ConfigRequireGroup,
            ConfigOfferGroup.name: ConfigOfferGroup,
            ConfigDropGroup.name: ConfigDropGroup,
            ConfigRecommendCommand.name: ConfigRecommendCommand,
            # The 0.3.0 rc3 spellings, hidden, each naming its replacement.
            ConfigCapabilitiesCommand.name: ConfigCapabilitiesCommand,
            ConfigNeedCommand.name: ConfigNeedCommand,
            ConfigUnsetCommand.name: ConfigUnsetCommand,
            ConfigSetEnvCommand.name: ConfigSetEnvCommand,
            ConfigUnsetEnvCommand.name: ConfigUnsetEnvCommand,
            ConfigListEnvCommand.name: ConfigListEnvCommand,
            ConfigSetExtraDockerArgsCommand.name: ConfigSetExtraDockerArgsCommand,
            ConfigListExtraDockerArgsCommand.name: ConfigListExtraDockerArgsCommand,
            ConfigRemoveExtraDockerArgsCommand.name: ConfigRemoveExtraDockerArgsCommand,
        }


class StateAdoptCommand(Command):
    name = "adopt"
    capsule_access: ClassVar[CapsuleAccess] = CapsuleAccess.MUTATES
    help = "Adopt an existing host directory for a declared state slot."

    @classmethod
    def configure(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("slot")
        parser.add_argument("--from", dest="source", type=Path, required=True)

    @classmethod
    def run(cls, arguments: argparse.Namespace, context: object | None) -> int:
        slot = arguments.slot
        root, manifest = manifest_for(_project_context(context).start_path())
        lock_path, lock = lock_for(root, manifest)
        declarations = configuration_binding_declarations(lock, source=str(lock_path))
        if slot not in declarations:
            available = ", ".join(sorted(declarations))
            raise ProjectConfigurationError(
                f"State resource {slot!r} is not declared by the selected components; "
                f"declared resources: {available}."
            )
        source = arguments.source.expanduser().resolve()
        if not source.is_dir():
            raise ProjectConfigurationError(f"State source is not a directory: {source}")
        record = CheckoutRecord(manifest, root)
        if slot in record.directory_bindings:
            raise ProjectConfigurationError(
                f"State resource {slot!r} is already configuration-bound; it cannot also be adopted."
            )
        record.state[slot] = str(source)
        record.write()
        print(f"Adopted {slot}: {source}")
        print("The next 'devcapsule project run' uses it.")
        return 0


class StateGroup(Group):
    name = "state"
    help = "Inspect and adopt checkout-scoped persistent state."

    @classmethod
    def subcommands(cls) -> Mapping[str, type[Command] | type[Group]]:
        return {StateAdoptCommand.name: StateAdoptCommand}


def _add_runtime_plan_options(parser: argparse.ArgumentParser, *, host_paths: bool = True) -> None:
    parser.add_argument(
        "--runtime-plan",
        type=Path,
        default=Path("/etc/devcapsule/runtime-plan.json"),
        help="External runtime plan mounted into the current capsule.",
    )
    parser.add_argument(
        "--json", dest="as_json", action="store_true", help="Emit stable machine-readable JSON."
    )
    if host_paths:
        parser.add_argument(
            "--show-host-paths",
            action="store_true",
            help="Include sensitive host mount sources after an explicit warning.",
        )


class RecursivePreflightCommand(Command):
    name = "preflight"
    capsule_access: ClassVar[CapsuleAccess] = CapsuleAccess.INDEPENDENT
    help = "Check recursive dogfood readiness for this capsule."

    @classmethod
    def configure(cls, parser: argparse.ArgumentParser) -> None:
        _add_runtime_plan_options(parser)

    @classmethod
    def run(cls, arguments: argparse.Namespace, context: object | None) -> int:
        root = _recursive_project_root(_project_context(context))
        _warn_for_host_path_disclosure(arguments.show_host_paths)
        report = run_recursive_preflight(root, runtime_plan_path=arguments.runtime_plan)
        print(
            preflight_json(report, show_host_paths=arguments.show_host_paths)
            if arguments.as_json
            else render_preflight(report, show_host_paths=arguments.show_host_paths)
        )
        return 0 if report.ready else 1


class RecursiveRunCommand(Command):
    name = "run"
    capsule_access: ClassVar[CapsuleAccess] = CapsuleAccess.INDEPENDENT
    help = "Run the recursive dogfood E2E dry run."

    @classmethod
    def configure(cls, parser: argparse.ArgumentParser) -> None:
        _add_runtime_plan_options(parser)
        parser.add_argument(
            "--keep-on-failure",
            action="store_true",
            help="Preserve only this run's ownership-marked workspace after failure.",
        )

    @classmethod
    def run(cls, arguments: argparse.Namespace, context: object | None) -> int:
        root = _recursive_project_root(_project_context(context))
        _warn_for_host_path_disclosure(arguments.show_host_paths)
        try:
            result = run_recursive_e2e_dry_run(
                root,
                runtime_plan_path=arguments.runtime_plan,
                keep_on_failure=arguments.keep_on_failure,
            )
        except RecursivePreflightFailed as exc:
            print(
                preflight_json(exc.report, show_host_paths=arguments.show_host_paths)
                if arguments.as_json
                else render_preflight(exc.report, show_host_paths=arguments.show_host_paths)
            )
            return 1
        except RecursiveE2EError as exc:
            raise ProjectConfigurationError(str(exc)) from exc
        mapping = result.to_mapping(show_host_paths=arguments.show_host_paths)
        print(
            result.to_json(show_host_paths=arguments.show_host_paths)
            if arguments.as_json
            else json.dumps(mapping, ensure_ascii=False, indent=2, sort_keys=True)
        )
        return 0


class RecursiveLaunchSuccessorCommand(Command):
    name = "launch-successor"
    capsule_access: ClassVar[CapsuleAccess] = CapsuleAccess.INDEPENDENT
    help = "Launch a successor capsule from a retained materialization run."

    @classmethod
    def configure(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--run-id", required=True, help="Existing retained materialization run ID.")
        _add_runtime_plan_options(parser, host_paths=False)

    @classmethod
    def run(cls, arguments: argparse.Namespace, context: object | None) -> int:
        root = _recursive_project_root(_project_context(context))

        def report(result: SuccessorResult) -> None:
            # Printed once the successor runs and its inspection passed; the
            # command then stays attached until the container exits, like
            # `project run`. The successor's own output is in the run's log.
            print(result.to_json() if arguments.as_json else json.dumps(result.to_mapping(), indent=2, sort_keys=True), flush=True)

        try:
            result = launch_successor(
                root, arguments.run_id, runtime_plan_path=arguments.runtime_plan, on_running=report
            )
        except RecursiveSuccessorError as exc:
            raise ProjectConfigurationError(str(exc)) from exc
        report(result)
        return 0 if result.exit_code == 0 else (result.exit_code or 1)


class RecursiveInspectSuccessorCommand(Command):
    name = "inspect-successor"
    capsule_access: ClassVar[CapsuleAccess] = CapsuleAccess.INDEPENDENT
    help = "Independently inspect a retained successor against its expected plan."

    @classmethod
    def configure(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--run-id", required=True, help="Existing retained successor run ID.")
        parser.add_argument(
            "--json", dest="as_json", action="store_true", help="Emit stable machine-readable JSON."
        )

    @classmethod
    def run(cls, arguments: argparse.Namespace, context: object | None) -> int:
        try:
            result = inspect_successor(arguments.run_id)
        except RecursiveSuccessorError as exc:
            raise ProjectConfigurationError(str(exc)) from exc
        print(result.to_json() if arguments.as_json else json.dumps(result.to_mapping(), indent=2, sort_keys=True))
        return 0


class RecursiveE2EGroup(Group):
    name = "recursive-e2e"
    help = "Run DevCapsule's project-specific recursive dogfood validation."

    @classmethod
    def subcommands(cls) -> Mapping[str, type[Command] | type[Group]]:
        return {
            RecursivePreflightCommand.name: RecursivePreflightCommand,
            RecursiveRunCommand.name: RecursiveRunCommand,
            RecursiveLaunchSuccessorCommand.name: RecursiveLaunchSuccessorCommand,
            RecursiveInspectSuccessorCommand.name: RecursiveInspectSuccessorCommand,
        }


# The authorization nodes whose run-once answers feed the launch plan; every
# other authorization (base-image, acquisitions) is inherently persistent.
_RUN_ONCE_AUTHORIZATIONS = ("docker-daemon", "network", "development-sudo", "host-browser", "host-x11")


class ProjectRunCommand(Command):
    name = "run"
    capsule_access: ClassVar[CapsuleAccess] = CapsuleAccess.MUTATES
    help = (
        "Run the project: derive the plan from the project, this home and this checkout, "
        "ask for unresolved choices and consent, and launch. Configuration flags apply to this launch only; "
        "--save records IDE, capability, provider, memory, CPU, environment and host-access answers. Everything after '--' is handed "
        "verbatim to 'docker run', except the options the launcher composes (--network, --memory, "
        "--cpus, --shm-size, ...), which are refused with the config command named. Without a "
        "terminal, a pending decision ends the command with status 3, naming each with its flag."
    )
    passthrough_dest = "docker_options"
    passthrough_metavar = "DOCKER-RUN-OPTIONS"

    @classmethod
    def configure(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--ide", metavar="IDE", help="The IDE for this launch: python-ide, frontend-ide, vscode-ide, java-ide, eclipse-ide or dotnet-ide.")
        parser.add_argument("--with", dest="with_capabilities", action="append", default=[], metavar="CAPABILITY", help="Add a capability for this launch; repeatable.")
        parser.add_argument("--use", action="append", default=[], metavar="CAPABILITY=COMPONENT", help="Choose a provider for this launch; repeatable.")
        _retired_option(parser, "--agent", "devcapsule project run --with CAPABILITY")
        parser.add_argument("--memory", metavar="SIZE", help="The memory limit for this launch, such as 6GiB or 6g.")
        parser.add_argument("--cpus", metavar="N", help="The CPU count for this launch.")
        parser.add_argument("--env", action="append", default=[], metavar="NAME[=VALUE]",
                            help="An environment variable for this launch: NAME=VALUE, or NAME taken from the host.")
        parser.add_argument("--trust", action="append", default=[], metavar="CHANNEL",
                            help="Accept a channel for this home across projects; saved when all required answers are complete. Repeatable; see config trust list.")
        parser.add_argument("--save", action="store_true", help="Save configuration flags after all required answers are complete, before launching.")
        parser.add_argument("--unverified", action="store_true", dest="allow_unverified", help=argparse.SUPPRESS)
        parser.add_argument(
            "--no-recursive-e2e",
            action="store_true",
            help="Disable DevCapsule recursive-E2E readiness for this launch.",
        )
        parser.add_argument("--name", dest="container_name", metavar="NAME", help="The container's name for this launch.")
        parser.add_argument("--no-update-check", action="store_true",
                            help="Skip the daily interactive distribution refresh; cached critical notices still allow a decision.")
        parser.add_argument("--print-command", action="store_true",
                            help="Prepare and print the Docker command without launching; inline extra environment values are redacted and comments identify transient dependencies.")
        parser.add_argument("--force", action="store_true",
                            help="Launch with the IDE given by --ide although the project requires another IDE: this launch only, "
                                 "warned and recorded as a departure from the project's contract; the requirement and the saved IDE "
                                 "stay unchanged. Consent, artifact integrity and real dependencies are still checked.")
        _retired_option(parser, "--force-config", "devcapsule project run")
        add_carrier_options(parser, families=("set", "authorize"))

    @classmethod
    def run(cls, arguments: argparse.Namespace, context: object | None) -> int:
        if not arguments.print_command:
            return cls._run(arguments, context)
        commands: list[str] = []
        # Keep both Python narration and inherited child-process output off
        # stdout. Emit only after preparation and its cleanup have succeeded.
        with preparation_diagnostics():
            result = cls._run(arguments, context, command_report=commands.append)
        if result == 0:
            for command in commands:
                sys.stdout.write(command)
        return result

    @classmethod
    def _run(cls, arguments: argparse.Namespace, context: object | None,
             command_report: Callable[[str], None] | None = None) -> int:
        start = _project_context(context).start_path()
        flags = _run_flags(arguments, manifest_for(start)[1])
        if flags.ide is not None or flags.force:
            load_launch_state(start, flags)
        # The bulk offer reviews and saves the checkout's ordinary selection.
        # A departed launch instead reviews its actual environment in prepare_launch;
        # that staged review still requires all software approvals and channel trust.
        if command_report is None and not flags.force and not offer_software_approvals(start):
            print("Launch cancelled; no session was started.")
            return 1
        # The saved Docker arguments and the raw options are validated before
        # anything is asked, so a bad file refuses the launch before a question.
        docker_options = list(arguments.docker_options)
        if docker_options:
            try:
                reject_launcher_owned_docker_options(docker_options)
            except PycharmRunError as exc:
                raise ProjectConfigurationError(str(exc)) from exc
        root, manifest = manifest_for(start)
        existing_record = find_checkout_record(manifest, root)
        if existing_record is not None:
            _validate_extra_docker_args(read_arguments(arguments_path(existing_record)))
        prepared = prepare_launch(start, flags, print_only=command_report is not None)
        for note in prepared.notes:
            print(note)
        for departure in prepared.selected.departures:
            launched = prepared.selected.lock.get("components", {}).get("interactive-surface")
            print(f"WARNING: --force sets aside the project's required IDE {departure.capability} for this launch; "
                  f"{departure.replacement} ({launched}) runs. The project's requirement and this checkout's saved IDE "
                  "are unchanged; the next plain launch uses them.", file=sys.stderr)
        saved_docker_args = read_arguments(arguments_path(prepared.selected.checkout_path))
        _validate_extra_docker_args(saved_docker_args)
        if command_report is None and not offer_upgrades(prepared.selected.root, refresh=not arguments.no_update_check):
            print("Launch cancelled; no session was started.")
            return 1
        # An upgrade may have changed the selection: derive again from the record.
        if command_report is None:
            # Saved flags are now record inputs. Reapply only launch overrides,
            # including terminal "once" answers, when checking the new selection.
            again = RunFlags(allow_unverified=flags.allow_unverified) if flags.save else flags
            # Trust accepted the channel shown in the first review. Never
            # replay that acceptance against a different channel after an upgrade.
            again = replace(again, save=False, trust=(), authorize=tuple(
                (name, render_authorization_value(value)) for name, value in prepared.host_overrides.items()
            ))
            prepared.selected = prepare_launch(start, again, interactive=False).selected
        selected = prepared.selected
        review = review_configuration(selected.manifest, selected.lock, selected.checkout,
                                      prepared.home if command_report is not None else load_settings())
        root, manifest, lock = selected.root, selected.manifest, selected.lock
        input_path, output_path = selected.checkout_path, selected.resolution_path
        checkout, resolved = selected.checkout, selected.resolution
        overrides, memory_override, cpus_override = prepared.host_overrides, prepared.memory_override, prepared.cpus_override
        # Capture before launching: a later session completion cannot certify
        # edits or a successor selection made while this session was running.
        captured_files = {} if command_report is not None else {
            input_path.name: input_path.read_bytes(), output_path.name: output_path.read_bytes()
        }
        try:
            notice = version_sets.reminder(root) if command_report is None else None
            if notice:
                print(notice)
        except (OSError, CliError):
            pass  # Optional cached reminders never gate an offline launch.
        authorizations = review.resolved_authorizations()
        host_access = review.effective_host(overrides)
        host_x11_answer = host_access.host_x11
        display_transport: str | None = None
        web_console: WebConsoleAvailability | None = None

        def prepare_display(base: ImageDetails) -> None:
            nonlocal display_transport, web_console
            if host_x11_answer is None and not has_contained_display(base.labels):
                # Answer 4 of the CLI UX work order: host X11 only by explicit
                # consent, on a base that has no contained desktop too.
                allow = AuthorizationChoice("host-x11", "true", "").command(root)
                raise DecisionPending(
                    "this base has no contained desktop (before recipe 8); the IDE can only show on your host's "
                    "X session, which hands the capsule your session credential. Allow it for this checkout: "
                    f"{allow}, or for this launch: --authorize host-x11 true. No capsule was started."
                )
            display_transport = _select_display_transport(
                base.labels, host_x11_answer=host_x11_answer
            )
            web_console = web_console_availability(base.labels)

        runtime = resolved["runtime"]
        component = runtime["component"]
        image = runtime.get("image")
        checkout_runtime_plan = None
        use_image_process = False
        image_labels: Mapping[str, str] = {}
        realized = None
        degraded_download = False
        if isinstance(lock.get("base"), dict) and isinstance(lock.get("materialization"), dict):
            while True:
                try:
                    if command_report is not None and flags.trust:
                        from devcapsule.configuration.trust import HomeTrust
                        realized = realize_environment(selected, report=print, prepare_base=prepare_display,
                                                       trust=HomeTrust.read(prepared.home))
                    else:
                        realized = realize_environment(selected, report=print, prepare_base=prepare_display)
                    break
                except ArtifactUnavailable as exc:
                    smaller = omit_unavailable_optional(selected, exc.url)
                    if smaller is None:
                        raise
                    omitted = set(selected.lock["components"]) - set(smaller.lock["components"])
                    print(f"Warning: optional tools {', '.join(sorted(omitted))} unavailable: {exc}; continuing without those enhancements.", file=sys.stderr)
                    selected = smaller
                    lock, checkout, resolved = selected.lock, selected.checkout, selected.resolution
                    review = review_configuration(manifest, lock, checkout, load_settings())
                    authorizations = review.resolved_authorizations()
                    degraded_download = True
            image = realized.image.reference
            image_labels = realized.image.labels
            checkout_runtime_plan = project_runtime_plan(selected, realized.locked)
            use_image_process = True
            action = "Materialized" if realized.created else "Reused"
            print(f"{action} canonical environment: {image}")
        if not isinstance(image, str) or not image:
            raise ProjectConfigurationError(
                f"The resolved {component} environment has no runnable image."
            )
        memory_limit = runtime.get("memory-limit-bytes")
        cpus = runtime.get("cpus")
        # Bindings convey host access too. A launch must recheck ordinary
        # runtime choices, but never resurrect a removed mapping or secret.
        state = dict(checkout.get("state", {}).get("adopted", {}))
        state.update(review.bindings)
        secret_environment = review.secret_bindings
        if memory_override is not None:
            memory_limit = memory_override
        if cpus_override is not None:
            cpus = cpus_override
        selected_docker_daemon = host_access.docker_daemon
        selected_sudo = host_access.development_sudo
        selected_network = host_access.network
        selected_host_browser = host_access.host_browser
        if arguments.no_recursive_e2e:
            selected_docker_daemon = "none"
            selected_sudo = False
            selected_network = "bridge"
        if display_transport is None:
            display_transport = _select_display_transport(
                image_labels, host_x11_answer=host_x11_answer
            )
        if web_console is None:
            web_console = web_console_availability(image_labels)
        recursive_environment = recursive_e2e_launch_environment(
            root,
            docker_daemon=str(selected_docker_daemon),
            disabled=arguments.no_recursive_e2e,
        )
        readiness = recursive_environment.get(RECURSIVE_E2E_ENABLED_ENV)
        if readiness is not None:
            if readiness == "1":
                print("Recursive E2E readiness: enabled for this DevCapsule launch.")
            elif arguments.no_recursive_e2e:
                print(
                    "Recursive E2E readiness: disabled for this launch; host Docker, "
                    "host networking, and development sudo were downgraded."
                )
            else:
                print(
                    "Recursive E2E readiness: unavailable because host Docker access is not authorized."
                )
        if saved_docker_args or docker_options or prepared.environment_tokens:
            # Single-instance options the launcher composes are refused —
            # docker would keep the passthrough occurrence and silently
            # override the resolved plan. Everything else is deliberate
            # stepping outside the plan; show what is being handed to Docker,
            # masking inline environment values.
            print(
                "WARNING: passing raw docker run options outside the resolved plan: "
                + " ".join(redact_environment([*saved_docker_args, *prepared.environment_tokens, *docker_options])),
                file=sys.stderr,
            )
        # PyCharm still travels through the launcher's named state fields;
        # every other surface's state comes from its runtime-plan slots.
        # Migrating PyCharm onto the generic slot path is a recorded follow-up.
        interactive_state_mounts: dict[str, tuple[Path, str]] = {}
        pycharm_state = {
            name: Path(state[f"pycharm/{name}"]) if f"pycharm/{name}" in state else None
            for name in ("config", "plugins", "system", "log", "cache")
        }
        if component != "pycharm":
            if checkout_runtime_plan is None:
                raise ProjectConfigurationError(
                    f"The {component} surface requires lock formation inputs; "
                    "regenerate the lock with 'devcapsule project init'."
                )
            pycharm_state = dict.fromkeys(pycharm_state)
            interactive_state_mounts = _component_state_mounts(
                root,
                lock,
                state,
                checkout_runtime_plan,
                {checkout_runtime_plan.component.id},
            )
        exit_code = run_pycharm(
            PycharmRunOptions(
                project=root,
                inherit_legacy_configuration=False,
                command_report=command_report,
                project_mount=str(runtime["project-mount"]),
                image=image,
                name=arguments.container_name,
                persistent_home=Path(state["home"]) if "home" in state else None,
                ide_config=pycharm_state["config"],
                plugins=pycharm_state["plugins"],
                ide_system=pycharm_state["system"],
                ide_log=pycharm_state["log"],
                tool_cache=pycharm_state["cache"],
                interactive_state_mounts=interactive_state_mounts,
                docker_mode=DockerMode.host if selected_docker_daemon == "host-socket" else DockerMode.none,
                enable_sudo=selected_sudo,
                network_mode=selected_network,
                memory_limit_bytes=memory_limit,
                cpus=cpus if isinstance(cpus, int) else None,
                runtime_plan=checkout_runtime_plan,
                launch_configuration=runtime_configuration.LaunchConfiguration.capture(
                    selected, version_sets.effective_set_id(lock, checkout), launch_listing_document(selected)),
                use_image_process=use_image_process,
                additional_state_mounts=_component_state_mounts(
                    root,
                    lock,
                    state,
                    checkout_runtime_plan,
                    set()
                    if checkout_runtime_plan is None
                    else {item.id for item in checkout_runtime_plan.ancillary_components},
                ),
                additional_environment=recursive_environment,
                secret_environment=tuple(sorted(secret_environment.values())),
                extra_docker_args=["--pull=never", *saved_docker_args, *prepared.environment_tokens, *docker_options],
                project_state=None,
                enable_host_browser=selected_host_browser,
                display_transport=display_transport,
                web_console=web_console,
                capsule_platform=lock_platform(lock),
            )
        )
        if command_report is not None:
            return exit_code  # Printing is never evidence of successful use.
        if exit_code == 0 and selected.departures:
            # A departed launch satisfied the developer, not the project:
            # it is no known-good generation and no proven version set.
            print("Not recorded as known-good: this launch departed from the project's required IDE.")
            return exit_code
        if exit_code == 0 and not degraded_download:
            # D-0008: a zero exit proves this configuration; record it as a
            # known-good generation unless identical content already exists.
            # Recording failure must never fail the successful run.
            try:
                recorded = record_known_good_configuration(
                    manifest, input_path, output_path, captured_files=captured_files
                )
                version_sets.record_success(selected, realized)
                if "version-set" in checkout:
                    print("Local use succeeded. Optionally prepare an upstream proposal with 'project versions propose PATH'.")
            except (OSError, CliError) as exc:
                print(
                    f"Warning: could not record the known-good configuration: {exc}",
                    file=sys.stderr,
                )
            else:
                if recorded is not None:
                    print(f"Recorded known-good configuration: {recorded}")
        return exit_code


def _select_display_transport(image_labels: Mapping[str, str], *, host_x11_answer: object) -> str:
    """Choose the display transport for this run and say why, once."""

    transport, reason = select_display_transport(image_labels, host_x11_answer=host_x11_answer)
    print(reason)
    return transport


def _run_flags(arguments: argparse.Namespace, manifest: Mapping[str, Any]) -> RunFlags:
    """The run's flags, with the rc3 carriers ``--set`` and ``--authorize`` folded in.

    ``--authorize NODE VALUE`` is the host-access flag of section 3.7;
    ``--set memory|cpus VALUE`` is the rc3 spelling of ``--memory`` and
    ``--cpus``. Every flag applies to this launch only unless ``--save``.
    """
    authorize: list[tuple[str, str]] = []
    memory = arguments.memory
    cpus = arguments.cpus
    for answer in carrier_answers(arguments, families=("set", "authorize")):
        if answer.justification is not None:
            raise ProjectConfigurationError(
                "A justification is recorded when the project owner recommends a host access; "
                "it does not apply to a launch."
            )
        if answer.family == "authorize":
            if not arguments.save and answer.name not in _RUN_ONCE_AUTHORIZATIONS:
                raise ProjectConfigurationError(
                    f"Authorization {answer.name!r} cannot be answered for one launch; "
                    "the host accesses can: " + ", ".join(_RUN_ONCE_AUTHORIZATIONS) + "."
                )
            authorize.append((answer.name, answer.value))
        else:
            name = "memory" if answer.name in legacy_memory_names(manifest) else answer.name
            if name == "memory":
                memory = answer.value
            elif name == "cpus":
                cpus = answer.value
            else:
                raise ProjectConfigurationError(
                    f"Configuration value {answer.name!r} has no run-once launch effect; "
                    "record it with 'devcapsule project config set'. Run-once values: --memory, --cpus."
                )
            print(f"Note: --set {answer.name} is --{name} now.", file=sys.stderr)
    uses = []
    for value in arguments.use:
        capability, separator, component = value.partition("=")
        if not separator or not capability or not component or "=" in component:
            raise ProjectConfigurationError("--use takes CAPABILITY=COMPONENT (or CAPABILITY=default).")
        uses.append((capability, component))
    flags = RunFlags(
        ide=arguments.ide, capabilities=tuple(arguments.with_capabilities),
        providers=tuple(uses), memory=memory, cpus=cpus,
        environment=tuple(arguments.env), authorize=tuple(authorize), trust=tuple(arguments.trust),
        save=arguments.save, allow_unverified=arguments.allow_unverified, force=arguments.force,
    )
    return flags


class ProjectCommand(Group):
    name = "project"
    help = "Initialize, list, configure, and run DevCapsule project checkouts."

    @classmethod
    def configure(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--path",
            dest="selected_path",
            type=Path,
            help="Project root or descendant; defaults to discovery from the current directory.",
        )

    @classmethod
    def make_context(cls, arguments: argparse.Namespace, parent: object | None) -> object | None:
        """Select the project and apply the subcommand's capsule access.

        The subcommand is resolved first, without side effects: an unknown
        name, help, or a bare nested group gets a plain context and the
        dispatch reports it as it would outside a capsule. For a known leaf,
        its declared :class:`CapsuleAccess` decides whether the capsule's own
        project is selected when none encloses the working directory, and
        whether the command is refused inside the capsule in favour of the
        launcher.
        """
        context = ProjectCommandContext(arguments.selected_path)
        tokens: list[str] = list(arguments.rest)
        parsed_tokens = tokens[:tokens.index("--")] if "--" in tokens else tokens
        if any(token in {"-h", "--help"} for token in parsed_tokens):
            return context
        leaf = cls.resolve(tokens)
        if leaf is None or issubclass(leaf, Group):
            return context
        # Retired flags name their replacement even inside a capsule, before
        # launcher access checks. Values after the Docker separator stay literal.
        if leaf in (ProjectInitCommand, ProjectRunCommand, ConfigCapabilitiesCommand):
            prefix_length = 2 if leaf is ConfigCapabilitiesCommand else 1
            parser = argparse.ArgumentParser(prog="devcapsule project " + " ".join(tokens[:prefix_length]))
            leaf.configure(parser)
            retired = {flag: action for action in parser._actions if isinstance(action, _RetiredOption)
                       for flag in action.option_strings}
            for token in parsed_tokens[prefix_length:]:
                flag = token.partition("=")[0]
                if flag in retired:
                    retired[flag](parser, argparse.Namespace(), None, flag)
        if leaf in (ConfigRequireGroup, ConfigOfferGroup, ConfigDropGroup) and tokens[2:3] == ["tool"]:
            raise ProjectConfigurationError(f"config {tokens[1]} tool is retired; use 'devcapsule project config {tokens[1]} CAPABILITY'.")
        access = _capsule_access(leaf)
        if access.selects_capsule_project and context.selected_path is None:
            context = replace(context, capsule_root=runtime_configuration.capsule_project_root(Path(".")))
        if access.needs_launcher:
            runtime_configuration.require_launcher(context.start_path(), tokens)
        return context

    @classmethod
    def subcommands(cls) -> Mapping[str, type[Command] | type[Group]]:
        return {
            ProjectInfoCommand.name: ProjectInfoCommand,
            ProjectDiagnoseCommand.name: ProjectDiagnoseCommand,
            ProjectListCommand.name: ProjectListCommand,
            ProjectInitCommand.name: ProjectInitCommand,
            ProjectWrapCommand.name: ProjectWrapCommand,
            CheckoutGroup.name: CheckoutGroup,
            ConfigGroup.name: ConfigGroup,
            VersionsGroup.name: VersionsGroup,
            StateGroup.name: StateGroup,
            RecursiveE2EGroup.name: RecursiveE2EGroup,
            ProjectRunCommand.name: ProjectRunCommand,
        }


def _capsule_access(leaf: type[Command]) -> CapsuleAccess:
    """The access a ``project`` leaf declares for itself.

    Every leaf of the tree declares one explicitly, which
    ``test_project_commands`` checks by walking the tree; an inherited or
    missing declaration is a programming error, never a default.
    """
    access = leaf.__dict__.get("capsule_access")
    if not isinstance(access, CapsuleAccess):
        raise AssertionError(f"{leaf.__name__} declares no capsule access.")
    return access


def _recursive_project_root(context: ProjectCommandContext) -> Path:
    root = discover_project(context.start_path())
    try:
        return require_recursive_e2e_project(root)
    except PreflightError as exc:
        raise ProjectConfigurationError(str(exc)) from exc


def _warn_for_host_path_disclosure(show_host_paths: bool) -> None:
    if show_host_paths:
        print(
            "WARNING: debug output includes raw host filesystem mappings; "
            "do not share it unsanitized.",
            file=sys.stderr,
        )


def _authorize_all_recommended(
    root: Path,
    manifest: dict[str, Any],
    declarations: dict[str, AuthorizationDeclaration],
) -> int:
    # Bulk authorization covers what the project and lock actually recommend;
    # home-capability defaults are individual decisions and must never
    # ride along in an "authorize everything recommended" stroke.
    declarations = {
        name: declaration
        for name, declaration in declarations.items()
        if declaration.project_recommended
    }
    if not declarations:
        raise ProjectConfigurationError("This project and lock declare no authorization recommendations.")

    record = CheckoutRecord(manifest, root)
    input_path = record.input_path

    print(f"The following authorizations will be granted for checkout {root}:")
    for name, declaration in sorted(declarations.items()):
        rendered = _authorization_display_value(declaration)
        print(f"- {name}: {rendered}")
        print(f"  Justification: {declaration.description}")
        print(f"  Recommendation digest: {declaration.recommendation_digest}")
    if not sys.stdin.isatty():
        raise ProjectConfigurationError(
            "--all-recommended requires an interactive terminal; authorize each exact value "
            "individually in non-interactive workflows."
        )
    print("Press y to authorize every recommendation; any other key cancels: ", end="", flush=True)
    try:
        accepted = _confirmation_key() == "y"
    except (EOFError, OSError, termios.error) as exc:
        print("")
        raise ProjectConfigurationError(f"Cannot read authorization confirmation key: {exc}") from exc
    print("")
    if not accepted:
        print("Authorization cancelled; no changes written.")
        return 1

    for declaration in declarations.values():
        record.authorize(declaration, declaration.recommended_value)
    record.write()
    print(f"Authorized {len(declarations)} recommendations for this checkout.")
    print(f"Checkout input: {input_path}")
    print("Run 'devcapsule project run' before materialization or launch.")
    return 0


def _authorization_display_value(declaration: AuthorizationDeclaration) -> str:
    return declaration.display_value or render_authorization_value(declaration.recommended_value)


def _component_state_mounts(
    root: Path,
    lock: dict[str, Any],
    configured_state: dict[str, Any],
    runtime_plan: Any,
    component_ids: set[str],
) -> dict[str, tuple[Path, str]]:
    if runtime_plan is None:
        return {}
    declarations = configuration_binding_declarations(lock)
    mounts: dict[str, tuple[Path, str]] = {}
    for name, declaration in declarations.items():
        if declaration.component_id not in component_ids:
            continue
        configured = configured_state.get(name)
        source = (
            Path(str(configured)).expanduser().resolve()
            if configured is not None
            else _managed_binding_path(root, declaration)
        )
        source.mkdir(parents=True, exist_ok=True, mode=0o700)
        if configured is None:
            source.chmod(0o700)
            _seed_component_state(source, declaration)
        mounts[name] = (source, declaration.container_path)
    return mounts


def _seed_component_state(source: Path, declaration: Any) -> None:
    """Place a component's declared default files into its managed slot.

    Written as the invoking user before the daemon mounts the slot. JSON
    seeds may fill missing keys; explicit values always survive. Adopted
    directories never reach here (see the caller).
    """

    definition = COMPONENTS.get(str(declaration.component_id))
    if definition is None:
        return
    for seed in definition.state_seeds():
        if seed.slot != declaration.slot_name:
            continue
        target = source / seed.relative_path
        # A developer may link settings elsewhere. Do not follow or replace
        # those links, including dangling links and linked parent directories.
        relative_parts = Path(seed.relative_path).parts
        if any(source.joinpath(*relative_parts[:i]).is_symlink()
               for i in range(1, len(relative_parts) + 1)):
            print(f"Warning: leaving linked component settings unchanged: {target}", file=sys.stderr)
            continue
        if target.exists():
            if not seed.merge_missing_json:
                continue
            try:
                settings = json.loads(target.read_text(encoding="utf-8"))
                defaults = json.loads(seed.content)
                if not isinstance(settings, dict):
                    raise ValueError("expected a JSON object")
                if _fill_missing_settings(settings, defaults):
                    atomic_write(target, json.dumps(settings, indent=2) + "\n")
            except (ValueError, OSError) as exc:
                # Do not echo file contents: settings may include credentials.
                print(
                    f"Warning: leaving component settings unchanged: {target} "
                    f"({type(exc).__name__}); repair the JSON object to apply defaults.",
                    file=sys.stderr,
                )
            continue
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        atomic_write(target, seed.content)


def _fill_missing_settings(settings: dict[str, Any], defaults: dict[str, Any]) -> bool:
    """Add missing JSON keys in memory; reject incompatible object structure."""
    changed = False
    for key, value in defaults.items():
        if key not in settings:
            settings[key] = value
            changed = True
        elif isinstance(value, dict):
            if not isinstance(settings[key], dict):
                raise ValueError(f"expected an object for {key}")
            changed = _fill_missing_settings(settings[key], value) or changed
    return changed



COMMAND = ProjectCommand
