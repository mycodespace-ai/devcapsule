"""The launcher's side of the console's configuration channel: watch, apply, defer, and the deferred store.

The contract is :mod:`devcapsule.configuration.console_channel`. While a
capsule runs, a watcher thread sweeps the mounted directory for complete
request files and answers each with a result file. An applied request runs
the config command as the command line would, in a child process, so its
validation, its output and its exit status are the command's own and no
output crosses into the launcher's terminal. A deferred request is kept in
the checkout's console-requests file under the launcher's config root, a
sibling tree of the Docker-arguments files, until the user confirms or
discards it on the host.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
import os
import signal
from pathlib import Path
import subprocess
import sys
import threading
import uuid
from typing import Any, Callable, Mapping, Sequence

from devcapsule.configuration.console_channel import (
    CHANNEL_FORMAT,
    LISTING_FILE,
    REQUEST_SUFFIX,
    RESULT_SUFFIX,
    DeferredRequest,
    Disposition,
    classify,
    now,
    parse_request,
    read_document,
    request_id,
    result_document,
    statement,
    write_complete,
)
from devcapsule.configuration.console_requests import deferred_requests, write_deferred
from devcapsule.configuration.file_formats import ProjectConfigurationError
from devcapsule.configuration.listing import Listing

__all__ = ["ChannelView", "ChannelWatcher", "ConfigRunner", "apply_deferred", "child_environment", "discard_deferred",
           "handle_request", "read_channel", "render_running_listing", "run_command", "run_config",
           "running_listing_document", "sweep"]

ConfigRunner = Callable[..., tuple[int, str]]
"""Runs ``config ARGUMENTS`` for a project: ``run(root, arguments, host_confirmed=False)`` gives the command's
status and its output. :func:`run_config` is the one the launcher uses; a test passes its own."""

INHERITED_VARIABLES = frozenset({"HOME", "PATH", "LANG", "TMPDIR", "DEVCAPSULE_CONFIG_HOME", "XDG_CONFIG_HOME",
                                 "XDG_DATA_HOME", "XDG_STATE_HOME", "XDG_CACHE_HOME", "XDG_RUNTIME_DIR"})
"""What a command run for the console inherits of the launcher's environment, with every ``LC_`` variable."""

_log = logging.getLogger("devcapsule.console-channel")
COMMAND_TIMEOUT_SECONDS = 120.0
SWEEP_INTERVAL_SECONDS = 1.0


def _config_command(root: Path, arguments: Sequence[str]) -> list[str]:
    if tuple(arguments[:2]) in (("trust", "accept"), ("trust", "withdraw")):
        confirmation = ["--yes"] if arguments[1] == "accept" else []
        return [sys.executable, "-m", "devcapsule", "home", *arguments, *confirmation]
    return [sys.executable, "-m", "devcapsule", "project", "--path", str(root), "config", *arguments]


def child_environment(environment: Mapping[str, str], *, host_confirmed: bool = False) -> dict[str, str]:
    """The environment of a command run for the console, from the launcher's own ``environment``.

    The child needs the host record locations, not credentials, Python
    injection settings, or anything else of the launcher's shell: only
    :data:`INHERITED_VARIABLES` and the ``LC_`` variables pass. With
    ``host_confirmed`` the human ran the command on the host themselves, and
    it keeps their Docker context and other host configuration, as an
    ordinary CLI invocation does: everything passes.
    """
    if host_confirmed:
        return dict(environment)
    return {key: value for key, value in environment.items() if key in INHERITED_VARIABLES or key.startswith("LC_")}


def run_command(command: Sequence[str], environment: Mapping[str, str], timeout: float) -> tuple[int, str]:
    """Run ``command`` as its own process; its exit status and its output, standard error included, stripped.

    The child has no input, no controlling terminal of the launcher's and a
    session of its own. One that has not finished after ``timeout`` seconds
    is killed with every process of its session, and the result is status 1
    with a line saying so. A command that cannot be started is status 1 with
    the reason.
    """
    try:
        with subprocess.Popen(list(command), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              text=True, errors="replace", stdin=subprocess.DEVNULL, start_new_session=True,
                              cwd="/", env=dict(environment)) as child:
            try:
                output, _ = child.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                # A descendant inherits the output pipe. Killing only its parent would
                # let it finish its write and keep communicate() waiting for that pipe.
                os.killpg(child.pid, signal.SIGKILL)
                child.communicate()
                return 1, f"the command did not finish within {timeout:g} seconds"
            return child.returncode, output.strip()
    except OSError as exc:
        return 1, f"cannot run the configuration command: {exc}"


def run_config(root: Path, arguments: Sequence[str], *, host_confirmed: bool = False) -> tuple[int, str]:
    """Run ``config ARGUMENTS`` for the project at ``root`` as its own process; the status and the combined output."""
    return run_command(_config_command(root, arguments), child_environment(os.environ, host_confirmed=host_confirmed),
                       COMMAND_TIMEOUT_SECONDS)


def handle_request(root: Path, checkout_record: Path, request_path: Path, *, stopping: bool = False,
                   run: ConfigRunner | None = None) -> dict[str, Any]:
    """Answer one request file with its result file; the result document.

    ``run`` runs the command of a request that is applied at once; left
    out, it is :func:`run_config`.
    """
    identifier = request_id(request_path)
    try:
        document = read_document(request_path)
        arguments = parse_request(document, request_path.name)
    except ProjectConfigurationError as exc:
        result = result_document("refused", str(exc))
        write_complete(request_path.with_name(identifier + RESULT_SUFFIX), result)
        return result
    disposition, reason = classify(arguments)
    if stopping and disposition is Disposition.APPLY:
        disposition = Disposition.DEFER
    if disposition is Disposition.APPLY:
        status, output = (run or run_config)(root, arguments)
        if status == 0:
            result = result_document("recorded", f"Recorded for the next launch. This running capsule is unchanged.\n{output or statement(arguments)}")
        else:
            result = result_document("refused", output or f"{statement(arguments)} exited with status {status}")
    elif disposition is Disposition.DEFER:
        asked = document.get("requested") if isinstance(document, dict) else None
        requested = asked if isinstance(asked, str) and asked else now()
        kept = deferred_requests(checkout_record)
        # Older consoles reuse their sequence after a launch. Keep both
        # requests, with a fresh host id, instead of replacing pending input.
        stored_id = identifier
        if any(item.id == stored_id for item in kept):
            stored_id = f"000000-request-{uuid.uuid4().hex}"
        kept.append(DeferredRequest(stored_id, requested, tuple(arguments)))
        write_deferred(checkout_record, kept)
        result = result_document(
            "deferred",
            f"Saved request {stored_id}: {statement(arguments)}. "
            + ("The launcher is stopping. " if stopping else "This command can widen access. ")
            + "Nothing has been applied. Confirm on the host at the next 'devcapsule project run', "
            f"or use 'devcapsule project config console apply {stored_id}'.",
            requested,
        )
    else:
        result = result_document("refused", reason)
    write_complete(request_path.with_name(identifier + RESULT_SUFFIX), result)
    return result


def sweep(directory: Path, root: Path, checkout_record: Path, *, stop: threading.Event | None = None,
          run: ConfigRunner | None = None) -> int:
    """Answer every complete request in ``directory`` that has no result yet; how many were answered.

    Once ``stop`` is set, a request that would be applied is kept for the
    host's confirmation instead. ``run`` is as for :func:`handle_request`.
    """
    answered = 0
    try:
        names = sorted(path for path in directory.iterdir() if path.name.endswith(REQUEST_SUFFIX))
    except OSError:
        return 0
    for request_path in names:
        try:
            identifier = request_id(request_path)
        except ProjectConfigurationError:
            continue  # not the contract's name; a file the console did not write
        if request_path.with_name(identifier + RESULT_SUFFIX).exists():
            continue
        try:
            handle_request(root, checkout_record, request_path, stopping=stop is not None and stop.is_set(), run=run)
        except Exception as exc:  # noqa: BLE001 - one bad request never stops the watcher
            _log.warning("console request %s: %s", request_path.name, exc)
            try:
                write_complete(request_path.with_name(identifier + RESULT_SUFFIX),
                               result_document("refused", f"the launcher could not handle it: {exc}"))
            except OSError:
                pass
        answered += 1
    return answered


class ChannelWatcher:
    """A thread sweeping the channel directory while the capsule runs; ``stop`` sweeps once more."""

    def __init__(self, directory: Path, root: Path, checkout_record: Path,
                 interval: float = SWEEP_INTERVAL_SECONDS, run: ConfigRunner | None = None) -> None:
        self.directory = directory
        self.root = root
        self.checkout_record = checkout_record
        self.interval = interval
        self.run = run
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="devcapsule-console-channel", daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        # Only the worker drains. A second sweep here could run the same
        # command concurrently after a timed-out join.
        self._thread.join()

    def _run(self) -> None:
        while not self._stop.wait(self.interval):
            sweep(self.directory, self.root, self.checkout_record, stop=self._stop, run=self.run)
        sweep(self.directory, self.root, self.checkout_record, stop=self._stop, run=self.run)


def apply_deferred(root: Path, checkout_record: Path, identifier: str, *, run: ConfigRunner | None = None) -> tuple[int, str]:
    """Run the deferred request ``identifier`` as its command, and forget it; the command's status and output.

    The command is run as confirmed on the host, with the request's tokens
    exactly as kept. A command that fails leaves the request awaiting. ``run``
    is as for :func:`handle_request`.
    """
    requests = deferred_requests(checkout_record)
    match = next((item for item in requests if item.id == identifier), None)
    if match is None:
        raise ProjectConfigurationError(f"No console request {identifier!r} awaits confirmation for this checkout.")
    status, output = (run or run_config)(root, match.arguments, host_confirmed=True)
    if status == 0:
        write_deferred(checkout_record, [item for item in requests if item.id != identifier])
    return status, output


def discard_deferred(checkout_record: Path, identifier: str) -> None:
    requests = deferred_requests(checkout_record)
    if all(item.id != identifier for item in requests):
        raise ProjectConfigurationError(f"No console request {identifier!r} awaits confirmation for this checkout.")
    write_deferred(checkout_record, [item for item in requests if item.id != identifier])


@dataclass(frozen=True)
class ChannelView:
    """What the capsule reads from the mounted directory: the launch-time listing and the requests since."""

    at: str
    listing: dict[str, Any]
    requests: tuple[dict[str, Any], ...]


def read_channel(directory: Path) -> ChannelView:
    """Read a mounted channel; a missing or invalid launch listing is an explicit error."""
    from devcapsule.configuration.console_channel import parse_listing
    listing_path = directory / LISTING_FILE
    if not listing_path.exists() and not listing_path.is_symlink():
        raise ProjectConfigurationError("Configuration channel has no launch listing; inspect configuration on the host.")
    at, listing = parse_listing(read_document(listing_path))
    requests: list[dict[str, Any]] = []
    for request_path in sorted(path for path in directory.iterdir() if path.name.endswith(REQUEST_SUFFIX)):
        try:
            identifier = request_id(request_path)
            document = read_document(request_path)
            arguments = parse_request(document, request_path.name)
        except ProjectConfigurationError as exc:
            requests.append({"id": request_path.name, "arguments": [], "statement": "", "requested": "",
                             "result": {"format": CHANNEL_FORMAT, "status": "refused", "text": str(exc), "at": ""}})
            continue
        result_path = request_path.with_name(identifier + RESULT_SUFFIX)
        result = None
        if result_path.exists() or result_path.is_symlink():
            try:
                result = read_document(result_path)
                if (not isinstance(result, dict) or result.get("format") != CHANNEL_FORMAT
                        or result.get("status") not in ("recorded", "refused", "deferred")
                        or not isinstance(result.get("text"), str)):
                    raise ProjectConfigurationError("Unreadable result; inspect configuration on the host.")
            except (ProjectConfigurationError, OSError) as exc:
                result = {"format": CHANNEL_FORMAT, "status": "unknown",
                          "text": f"Cannot read the launcher result: {exc}. Inspect configuration on the host before retrying.", "at": ""}
        requests.append({"id": identifier, "arguments": arguments, "statement": statement(arguments),
                         "requested": str(document.get("requested", "")), "result": result})
    return ChannelView(at, listing, tuple(requests))


def _require_this_checkout(view: ChannelView, launcher_root: str, checkout_name: str, project: Mapping[str, Any]) -> None:
    """Refuse a listing that the launcher wrote for another checkout than the one this capsule runs."""
    checkout = view.listing.get("checkout")
    if (not isinstance(checkout, dict) or checkout.get("launcher-path") != launcher_root
            or checkout.get("name") != checkout_name
            or view.listing.get("project") != {key: project[key] for key in ("creator", "slug")}):
        raise ProjectConfigurationError("The channel listing belongs to another checkout; inspect configuration on the host.")


def running_listing_document(view: ChannelView, *, launcher_root: str, checkout_name: str, project: Mapping[str, Any],
                             launcher_command: str) -> dict[str, Any]:
    """What ``config show --json`` prints inside a running capsule: the launch-time listing and the requests since.

    ``launcher_root``, ``checkout_name`` and ``project`` say which checkout
    this capsule runs; a listing written for another is refused.
    ``launcher_command`` is the host command that shows the configuration.
    """
    _require_this_checkout(view, launcher_root, checkout_name, project)
    return {**view.listing, "context": "running capsule: the launcher's listing at launch", "at": view.at,
            "console-requests": list(view.requests), "launcher-command": launcher_command}


def render_running_listing(view: ChannelView, *, launcher_root: str, checkout_name: str, project: Mapping[str, Any],
                           launcher_command: str) -> str:
    """What ``config show`` prints inside a running capsule; the arguments are those of :func:`running_listing_document`."""
    _require_this_checkout(view, launcher_root, checkout_name, project)
    checkout = view.listing.get("checkout", {})
    lines = [f"Checkout: {checkout.get('launcher-path', launcher_root)} ({checkout.get('name', checkout_name)})",
             f"At launch, {view.at}:", Listing.from_document(view.listing).render(), ""]
    if view.requests:
        lines.append("Pending, next launch (asked on the console since launch):")
        for item in view.requests:
            result = item.get("result")
            outcome = f"{result['status']}: {result['text']}" if isinstance(result, dict) else "waiting for the launcher"
            lines.append(f"  {item['id']}: {item['statement'] or '(unreadable request)'}\n      {outcome}")
    else:
        lines.append("Nothing asked on the console since launch.")
    lines.append(f"To change the next launch: the console's configuration page, or on the host: {launcher_command}")
    return "\n".join(lines)
