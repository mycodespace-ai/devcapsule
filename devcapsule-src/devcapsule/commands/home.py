"""Commands for the configuration home, independent of project discovery."""
from __future__ import annotations

import argparse
from typing import Mapping

from devcapsule.commands.framework import Command, Group
from devcapsule.configuration.file_formats import ProjectConfigurationError
from devcapsule.configuration.storage import load_settings, settings_path, settings_source, write_settings
from devcapsule.configuration.trust import HomeTrust
from devcapsule.configuration.home_channels import known_channels
from devcapsule.configuration.home import HomeDefaults
from devcapsule.configuration.values import LAUNCHER_VALUE_NAMES
from devcapsule.platforms import XdgHomes


def _print_channels(document: Mapping) -> None:
    trust = HomeTrust.read(document)
    for channel_id, entry in sorted(trust.channels.items()):
        print(f"{channel_id}: {entry['vendor']} — {entry['product']}; "
              f"from {', '.join(entry['origins'])}; accepted {entry['accepted']}")
    if not trust.channels:
        print("No accepted channels.")


class HomeShowCommand(Command):
    name = "show"
    help = "Show this home's path, settings, defaults and accepted channels."

    @classmethod
    def run(cls, arguments: argparse.Namespace, context: object | None) -> int:
        document = load_settings()
        homes = XdgHomes.from_environment()
        print(f"DevCapsule home: {homes.config}")
        print(f"Chosen by: {homes.chosen_by}")
        source = settings_source()
        if source != settings_path():
            print(f"Settings read from the launcher of this capsule, mounted read-only: {source}")
            print("This home has no settings of its own yet; a write creates them here and takes over.")
        for name in ("devcapsule-settings-schema-version", "minimum-devcapsule"):
            print(f"{name}: {document.get(name, '(not recorded)')}")
        defaults = HomeDefaults.read(document).values
        print("Defaults: " + (", ".join(f"{name} = {value}" for name, value in sorted(defaults.items())) or "none"))
        _print_channels(document)
        return 0


class HomeTrustListCommand(Command):
    name = "list"
    help = "The channels accepted by this DevCapsule home, across all projects."

    @classmethod
    def run(cls, arguments: argparse.Namespace, context: object | None) -> int:
        _print_channels(load_settings())
        return 0


class HomeTrustAcceptCommand(Command):
    name = "accept"
    help = "Accept one channel for every version and project launched from this home."

    @classmethod
    def configure(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("channel", metavar="CHANNEL")
        parser.add_argument("--yes", action="store_true", help="Accept without the confirmation question.")

    @classmethod
    def run(cls, arguments: argparse.Namespace, context: object | None) -> int:
        document = load_settings()
        channels = known_channels()
        channel = channels.get(arguments.channel)
        if channel is None:
            raise ProjectConfigurationError(f"Unknown channel {arguments.channel!r}; known channels: {', '.join(sorted(channels))}.")
        print(channel.statement(settings_path().parent))
        if channel.note:
            print(channel.note)
        if not arguments.yes:
            try:
                answer = input("Accept for this DevCapsule home? [y/N]: ").strip().lower()
            except EOFError:
                answer = ""
            if answer not in {"y", "yes"}:
                print("Not accepted.")
                return 0
        trust = HomeTrust.read(document).with_channel(channel)
        path = write_settings({"trust": trust.document()})
        print(f"Recorded for this DevCapsule home: {path}")
        return 0


class HomeTrustWithdrawCommand(Command):
    name = "withdraw"
    help = "Remove a channel's acceptance from this home for future launches."

    @classmethod
    def configure(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("channel", metavar="CHANNEL")

    @classmethod
    def run(cls, arguments: argparse.Namespace, context: object | None) -> int:
        document = load_settings()
        trust = HomeTrust.read(document)
        if arguments.channel not in trust.channels:
            print(f"No acceptance recorded for {arguments.channel} in this home.")
            return 0
        path = write_settings({"trust": trust.without(arguments.channel).document()})
        print(f"Withdrew {arguments.channel} for this DevCapsule home: {path}")
        return 0


class HomeDefaultCommand(Command):
    name = "default"
    help = "Set this home's memory or cpus default; 'none' removes it."

    @classmethod
    def configure(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("name", metavar="NAME")
        parser.add_argument("value", metavar="VALUE")

    @classmethod
    def run(cls, arguments: argparse.Namespace, context: object | None) -> int:
        document = load_settings()
        if arguments.name not in LAUNCHER_VALUE_NAMES:
            raise ProjectConfigurationError("This home has defaults for memory and cpus only.")
        removing = arguments.value.strip().lower() == "none"
        defaults = HomeDefaults.read(document).with_value(arguments.name, None if removing else arguments.value)
        path = write_settings(defaults.document())
        print(f"Removed the home default for {arguments.name}." if removing else
              f"Home default {arguments.name} = {defaults.values[arguments.name]}.")
        print(f"Home settings: {path}")
        return 0


class HomeTrustGroup(Group):
    name = "trust"
    help = "List, accept or withdraw the channels this home trusts."

    @classmethod
    def subcommands(cls) -> Mapping[str, type[Command] | type[Group]]:
        return {"list": HomeTrustListCommand, "accept": HomeTrustAcceptCommand, "withdraw": HomeTrustWithdrawCommand}


class HomeGroup(Group):
    name = "home"
    help = "This DevCapsule home: what it trusts, its defaults, where it is."

    @classmethod
    def subcommands(cls) -> Mapping[str, type[Command] | type[Group]]:
        return {"show": HomeShowCommand, "trust": HomeTrustGroup, "default": HomeDefaultCommand}


COMMAND = HomeGroup
