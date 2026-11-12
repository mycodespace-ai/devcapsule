"""Argparse-based command framework for the DevCapsule CLI.

This module replaces the Click helpers in ``devcapsule.commands.base`` as
commands migrate to the v027 command surface.  The division of labor is
deliberate:

- The framework owns the command *tree*: discovery-independent group dispatch,
  group help, hidden commands, group-scoped options such as
  ``project --path``, the carrier-option grammar shared by ``init``,
  ``run``, and the ``config`` family, and the ``--platform`` value shared by
  ``project init`` and ``images build``.
- :mod:`argparse` owns only *leaf* option parsing, declared per command in
  ``configure``.

Keeping the tree in plain code rather than argparse subparsers is what lets
group behavior stay inspectable: argparse subparsers cannot hide commands,
cannot scope options to a group cleanly, and format their own help.  Leaf
parsing stays declarative; a command that genuinely owns its whole argument
surface (the container runtime pass-through) may override :meth:`Command.invoke`
instead of forcing that surface through argparse.

Command modules under this framework contain no business logic: ``configure``
declares parameters, ``run`` translates the parsed namespace into one library
operation call and prints its report.  Policy, filesystem writes, and digest
computation belong to the operation layer, never here.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Any, ClassVar, Mapping, NoReturn, Sequence

from devcapsule.compat import CliError
from devcapsule.platforms import Platform, UnsupportedPlatformError


class UsageError(CliError):
    """A command-line usage failure; the CLI reports it on stderr and exits 2."""


class _LeafParser(argparse.ArgumentParser):
    """ArgumentParser that reports usage failures through :class:`UsageError`.

    argparse's default ``error`` prints and calls ``sys.exit(2)``; the CLI
    entry point owns process exit, so parse failures must surface as an
    exception it can map.  ``--help`` still raises ``SystemExit(0)`` through
    ``exit``, which the entry point translates to a return code.
    """

    def error(self, message: str) -> NoReturn:
        raise UsageError(f"{message}\n{self.format_usage().rstrip()}")


STABLE_JSON_HELP = (
    "Emit stable machine-readable JSON instead of text: schema-version 1, "
    "the contract the capsule web console reads."
)
"""Help text shared by the ``--json`` flags whose document shape is a contract."""


class Command:
    """One leaf command: declarative argparse options plus a ``run`` body.

    A command that hands part of its invocation to another program verbatim
    (``run [OPTIONS] -- DOCKER-RUN-OPTIONS``) sets ``passthrough_dest``:
    everything after the first standalone ``--`` bypasses argparse entirely
    and arrives untouched as that namespace attribute — the framework never
    interprets, reorders, or validates another program's surface.
    """

    name: ClassVar[str]
    help: ClassVar[str] = ""
    hidden: ClassVar[bool] = False
    passthrough_dest: ClassVar[str | None] = None
    passthrough_metavar: ClassVar[str] = "PASSTHROUGH-OPTIONS"

    @classmethod
    def configure(cls, parser: argparse.ArgumentParser) -> None:
        """Declare this command's options and arguments; default: none."""

    @classmethod
    def run(cls, arguments: argparse.Namespace, context: object | None) -> int:
        raise NotImplementedError

    @classmethod
    def invoke(cls, prog: str, argv: Sequence[str], context: object | None = None) -> int:
        tokens = list(argv)
        passthrough: list[str] = []
        if cls.passthrough_dest is not None and "--" in tokens:
            separator = tokens.index("--")
            tokens, passthrough = tokens[:separator], tokens[separator + 1 :]
        parser = _LeafParser(prog=prog, description=cls.help or None, allow_abbrev=False)
        cls.configure(parser)
        if cls.passthrough_dest is not None:
            generated = parser.format_usage().removeprefix("usage: ").rstrip()
            parser.usage = f"{generated} [-- {cls.passthrough_metavar}]"
        arguments = parser.parse_args(tokens)
        if cls.passthrough_dest is not None:
            setattr(arguments, cls.passthrough_dest, passthrough)
        return cls.run(arguments, context)


class Group:
    """One command group: group-scoped options, then dispatch to a subcommand.

    The group's own parser sees only the tokens before the first subcommand
    name (``argparse.REMAINDER`` freezes everything from the first positional
    token onward), so a group option can never capture a subcommand's option
    even when both declare the same name.
    """

    name: ClassVar[str]
    help: ClassVar[str] = ""
    hidden: ClassVar[bool] = False

    @classmethod
    def subcommands(cls) -> Mapping[str, type[Command] | type[Group]]:
        raise NotImplementedError

    @classmethod
    def configure(cls, parser: argparse.ArgumentParser) -> None:
        """Declare group-scoped options; default: none."""

    @classmethod
    def make_context(cls, arguments: argparse.Namespace, parent: object | None) -> object | None:
        """Build the context passed to subcommands; default: inherit the parent's."""

        return parent

    @classmethod
    def handle_empty(
        cls, arguments: argparse.Namespace, context: object | None, parser: argparse.ArgumentParser
    ) -> int:
        """Handle invocation without a subcommand; default: print help.

        A group that acts on its own (``bootstrap``) overrides this to run its
        default action with the group-scoped options already parsed.
        """

        print(parser.format_help(), end="")
        return 0

    @classmethod
    def resolve(cls, argv: Sequence[str]) -> type[Command] | type[Group] | None:
        """The command ``argv`` names, following nested groups; no side effects.

        Returns the leaf, the nested group when ``argv`` stops at one (it
        would print help), or ``None`` when ``argv`` fails the group's own
        option grammar, asks for help, or names an unknown subcommand at any
        level. Nothing is printed and nothing runs, so a group can apply a
        policy to the command it is about to dispatch (``project`` decides
        per command what the capsule may do) and leave the reporting of an
        unknown name to the dispatch itself.
        """
        parser = _GroupParser(
            prog=cls.name, allow_abbrev=False, add_help=False,
            subcommand_table=dict(cls.subcommands()),
        )
        cls.configure(parser)
        parser.add_argument("rest", nargs=argparse.REMAINDER, help=argparse.SUPPRESS)
        try:
            rest: list[str] = list(parser.parse_args(list(argv)).rest)
        except UsageError:
            return None
        if not rest:
            return cls
        subcommand = cls.subcommands().get(rest[0])
        if subcommand is None:
            return None
        if issubclass(subcommand, Group):
            return subcommand.resolve(rest[1:])
        return subcommand

    @classmethod
    def invoke(cls, prog: str, argv: Sequence[str], context: object | None = None) -> int:
        parser = _GroupParser(
            prog=prog,
            description=cls.help or None,
            allow_abbrev=False,
            usage=f"{prog} [OPTIONS] COMMAND [ARGS]...",
            subcommand_table=dict(cls.subcommands()),
        )
        cls.configure(parser)
        parser.add_argument("rest", nargs=argparse.REMAINDER, help=argparse.SUPPRESS)
        arguments = parser.parse_args(list(argv))
        child_context = cls.make_context(arguments, context)
        rest: list[str] = list(arguments.rest)
        if not rest:
            return cls.handle_empty(arguments, child_context, parser)
        subcommand_name, *tail = rest
        subcommand = cls.subcommands().get(subcommand_name)
        if subcommand is None:
            visible = ", ".join(
                sorted(name for name, entry in cls.subcommands().items() if not entry.hidden)
            )
            raise UsageError(f"{prog}: unknown command {subcommand_name!r}; commands: {visible}.")
        return subcommand.invoke(f"{prog} {subcommand_name}", tail, child_context)


class _GroupParser(_LeafParser):
    """Group parser whose help ends with the visible subcommand listing."""

    def __init__(self, *args: Any, subcommand_table: dict[str, type[Command] | type[Group]], **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._subcommand_table = subcommand_table

    def format_help(self) -> str:
        return super().format_help() + render_command_listing(self._subcommand_table)


def render_command_listing(commands: Mapping[str, Any]) -> str:
    """Render the ``Commands:`` block listing non-hidden entries with one-line help.

    Entries are read through their ``hidden`` and ``help`` attributes so the
    listing serves framework classes and, during the migration, bridged Click
    command classes alike.
    """

    visible = {
        name: entry
        for name, entry in sorted(commands.items())
        if not getattr(entry, "hidden", False)
    }
    if not visible:
        return ""
    width = max(len(name) for name in visible)
    lines = ["", "Commands:"]
    for name, entry in visible.items():
        help_text = getattr(entry, "help", "") or ""
        summary = help_text.strip().splitlines()[0] if help_text else ""
        lines.append(f"  {name.ljust(width)}  {summary}".rstrip())
    return "\n".join(lines) + "\n"


# The carrier grammar: every configuration mutation everywhere is one of
# ``--set NAME VALUE``, ``--bind NAME PROVIDER:VALUE``, or
# ``--authorize NAME VALUE [JUSTIFICATION]``, spelled with the node's one
# canonical name.  Commands that accept configuration answers declare these
# through ``add_carrier_options`` and read them back as typed
# ``CarrierAnswer`` values; whether a node exists, accepts the family, or
# requires the justification facet is the node registry's decision, not the
# parser's.

CARRIER_FAMILIES = ("set", "bind", "authorize")


@dataclass(frozen=True)
class CarrierAnswer:
    """One pre-answered configuration node from the command line."""

    family: str
    name: str
    value: str
    justification: str | None


def add_carrier_options(
    parser: argparse.ArgumentParser, *, families: Sequence[str] = CARRIER_FAMILIES
) -> None:
    """Declare the shared carrier options on one command's parser.

    argparse cannot declare "two or three tokens" directly, so each carrier is
    declared open-ended (``nargs='+'`` consumes tokens up to the next option)
    and :func:`carrier_answers` enforces the 2-or-3 arity with a precise
    message.  A value or justification never begins with ``-`` in this domain,
    so greedy consumption cannot swallow a following option.
    """

    for family in families:
        parser.add_argument(
            f"--{family}",
            dest=f"carrier_{family}",
            action="append",
            nargs="+",
            default=[],
            metavar=("NAME", "VALUE"),
            help=f"Answer one configuration node: --{family} NAME VALUE [JUSTIFICATION]; repeatable.",
        )


def carrier_answers(
    arguments: argparse.Namespace, *, families: Sequence[str] = CARRIER_FAMILIES
) -> tuple[CarrierAnswer, ...]:
    """Validate carrier arity and return the typed answers in family order."""

    answers: list[CarrierAnswer] = []
    for family in families:
        for tokens in getattr(arguments, f"carrier_{family}", []) or []:
            if len(tokens) < 2:
                raise UsageError(f"--{family} requires NAME VALUE; got only {tokens[0]!r}.")
            if len(tokens) > 3:
                unexpected = " ".join(tokens[3:])
                raise UsageError(
                    f"--{family} {tokens[0]} takes NAME VALUE and one optional JUSTIFICATION; "
                    f"unexpected trailing tokens: {unexpected!r}. "
                    "Quote a justification that contains spaces."
                )
            answers.append(
                CarrierAnswer(
                    family=family,
                    name=tokens[0],
                    value=tokens[1],
                    justification=tokens[2] if len(tokens) == 3 else None,
                )
            )
    return tuple(answers)


def capsule_platform_argument(value: str) -> Platform:
    """A ``--platform`` value: a capsule platform this host runs."""

    try:
        platform = Platform.parse(value)
        runnable = Platform.runnable()
    except UnsupportedPlatformError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc
    if platform not in runnable:
        names = ", ".join(str(member) for member in runnable)
        raise argparse.ArgumentTypeError(f"this host runs {names} capsules, not {platform}")
    return platform
