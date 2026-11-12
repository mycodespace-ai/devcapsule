"""Locate the exact launcher artifact to deliver into a formation."""

from __future__ import annotations

import os
from pathlib import Path
import sys

from devcapsule.build_info import BuildInfo, BuildInfoError, current_build_info, read_pex_build_info
from devcapsule.compat import CliError
from devcapsule.platforms import HostOs, Platform

RUNTIME_PEX_ENV = "DEVCAPSULE_RUNTIME_PEX"

_MACH_O_MAGICS = (b"\xcf\xfa\xed\xfe", b"\xce\xfa\xed\xfe", b"\xca\xfe\xba\xbe")
_UNKNOWN_REVISION = "unknown"


def runtime_artifact(capsule_platform: Platform) -> Path:
    """The DevCapsule executable a launch delivers into a ``capsule_platform`` capsule.

    A packaged launcher delivers itself when it runs on the capsule platform
    (D-0009). A launcher that cannot, such as a macOS executable launching
    Linux capsules, delivers the runtime ``DEVCAPSULE_RUNTIME_PEX`` names: one
    executable, or a directory holding one per capsule platform as
    ``devcapsule-<platform>``. A source-form launcher names its built runtime
    the same way. A delivered runtime that is not the launcher's own bytes
    must be the launcher's build: the same version, and the same source
    revision wherever both record one (R-RUNTIME-001).
    """

    # scie preserves the executable's path in SCIE; PEX points to the original
    # archive too. sys.argv[0] alone can name the extracted console script.
    own_variable = os.environ.get("SCIE") or os.environ.get("PEX")
    own = _resolved(own_variable) if own_variable else None
    named = os.environ.get(RUNTIME_PEX_ENV)
    if own is not None and _runs_in(own, capsule_platform):
        delivered = own
    elif named:
        delivered = _named_runtime(Path(named).expanduser(), capsule_platform)
    else:
        delivered = own or _resolved(sys.argv[0])
    try:
        delivered_build = read_pex_build_info(delivered)
    except BuildInfoError as exc:
        raise CliError(
            "Environment materialization needs a DevCapsule PEX. Run the built PEX, "
            "or build with 'nox -s pex' and set DEVCAPSULE_RUNTIME_PEX to its path "
            "when running from source."
        ) from exc
    if not _runs_in(delivered, capsule_platform):
        raise CliError(
            f"{delivered} is {_describe(executable_platform(delivered))} and cannot run inside "
            f"{capsule_platform} capsules. Set {RUNTIME_PEX_ENV} to a {capsule_platform} DevCapsule "
            f"executable of the same version, or to a directory holding it as devcapsule-{capsule_platform}."
        )
    if delivered != own:
        _require_same_build(delivered, delivered_build, current_build_info())
    return delivered


def executable_platform(path: Path) -> Platform | HostOs | None:
    """What a native executable runs on, from its header.

    The ``Platform`` of an ELF executable of a known architecture,
    ``HostOs.LINUX`` for one of another architecture, ``HostOs.DARWIN`` for any
    Mach-O file, and None for anything else, such as a plain PEX archive.
    """

    try:
        with path.open("rb") as handle:
            header = handle.read(20)
    except OSError:
        return None
    if header[:4] in _MACH_O_MAGICS:
        return HostOs.DARWIN
    if header[:4] == b"\x7fELF" and len(header) >= 20:
        machine = int.from_bytes(header[18:20], "little" if header[5] == 1 else "big")
        return Platform.of_elf_machine(machine) or HostOs.LINUX
    return None


def _runs_in(path: Path, capsule_platform: Platform) -> bool:
    """Whether the executable at ``path`` runs inside ``capsule_platform`` capsules.

    A plain PEX bundles native wheels for the machine it was built on, so it
    counts as the capsule platform's only on a Linux host, whose one capsule
    platform is its own.
    """

    runs_on = executable_platform(path)
    if runs_on is None:
        return HostOs.current() is HostOs.LINUX and Platform.runnable() == (capsule_platform,)
    return runs_on == capsule_platform


def _named_runtime(named: Path, capsule_platform: Platform) -> Path:
    if not named.is_dir():
        return _resolved(str(named))
    candidate = named / f"devcapsule-{capsule_platform}"
    if not candidate.is_file():
        raise CliError(
            f"{RUNTIME_PEX_ENV} names {named}, which holds no devcapsule-{capsule_platform}: this launch "
            f"runs a {capsule_platform} capsule. Put a {capsule_platform} DevCapsule executable of the same "
            f"version there, or a directory holding it as devcapsule-{capsule_platform}."
        )
    return _resolved(str(candidate))


def _require_same_build(delivered: Path, delivered_build: BuildInfo, launcher_build: BuildInfo) -> None:
    revisions = (delivered_build.source_revision, launcher_build.source_revision)
    revisions_differ = _UNKNOWN_REVISION not in revisions and revisions[0] != revisions[1]
    if delivered_build.version != launcher_build.version or revisions_differ:
        raise CliError(
            f"{delivered} is DevCapsule {delivered_build.version} from {delivered_build.source_revision}, "
            f"but this launcher is {launcher_build.version} from {launcher_build.source_revision}. The runtime "
            "a launch delivers runs the plan this launcher writes, so it must be the same build: rebuild "
            f"it from the launcher's commit and point {RUNTIME_PEX_ENV} at it."
        )


def _describe(runs_on: Platform | HostOs | None) -> str:
    if runs_on is HostOs.DARWIN:
        return "a macOS executable"
    if runs_on is HostOs.LINUX:
        return "a Linux executable of an architecture no capsule platform names"
    if runs_on is None:
        return "a plain PEX built for another machine"
    return f"a {runs_on} executable"


def _resolved(selected: str) -> Path:
    return Path(selected).expanduser().resolve()
