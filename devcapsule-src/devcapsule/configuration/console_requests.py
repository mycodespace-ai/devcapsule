"""The console's deferred requests: widenings asked on the console, kept until the user confirms them on the host.

The contract and the classification are :mod:`console_channel`. A deferred
request lives in a ``requests.json`` keyed by the checkout's canonical path
and project identity, independently of its registration name, under the launcher's
config root, in a tree beside the Docker-arguments files so the mounted
records directory never exposes it. Each is a pending, soft decision of the
checkout's listing: ``run`` asks it at the terminal, ``config show`` lists
it with the confirming command, ``config console`` applies or discards it.
"""

from __future__ import annotations

from pathlib import Path
import hashlib
import shlex
from typing import Sequence

from .console_channel import MAXIMUM_DOCUMENT_BYTES, DeferredRequest, parse_deferred, read_document, render_deferred
from .file_formats import ProjectConfigurationError
from .listing import Decision, ListingRow
from .storage import atomic_write, config_root, load_toml

__all__ = ["console_requests_path", "deferred_requests", "deferred_rows", "request_rows", "write_deferred"]


def console_requests_path(checkout_record: Path) -> Path:
    """Where the console's deferred requests for ``checkout_record`` live, outside the mounted records tree."""
    relative = checkout_record.relative_to(config_root() / "projects")
    # Bind to the canonical checkout path, not a reusable registration name.
    root = Path(load_toml(checkout_record)["checkout"]["path"]).resolve()
    identity = hashlib.sha256(str(root).encode("utf-8")).hexdigest()
    project = Path(*relative.parts[:2])
    return config_root() / "console-requests" / project / identity / "requests.json"


def deferred_requests(checkout_record: Path) -> list[DeferredRequest]:
    if not checkout_record.is_file():
        return []
    path = console_requests_path(checkout_record)
    if not path.is_file():
        return []
    return parse_deferred(read_document(path), str(path))


def write_deferred(checkout_record: Path, requests: Sequence[DeferredRequest]) -> Path:
    """Write the requests, or remove the file when none remain."""
    path = console_requests_path(checkout_record)
    if requests:
        text = render_deferred(requests)
        if len(text.encode("utf-8")) > MAXIMUM_DOCUMENT_BYTES:
            raise ProjectConfigurationError("The console request queue is full; apply or discard pending requests on the host.")
        atomic_write(path, text)
    else:
        path.unlink(missing_ok=True)
    return path


def deferred_rows(checkout_record: Path | None, project: Path | None) -> list[ListingRow]:
    """The deferred requests as listing rows: pending, soft, each with its confirming command."""
    if checkout_record is None:
        return []
    try:
        requests = deferred_requests(checkout_record)
    except (ProjectConfigurationError, ValueError) as exc:
        return [ListingRow("console", "*", "invalid", str(exc), "repair or remove the console-requests file", "")]
    return request_rows(requests, project)


def request_rows(requests: Sequence[DeferredRequest], project: Path | None) -> list[ListingRow]:
    """``requests`` as listing rows, each a soft decision whose command applies it on the host.

    ``project`` is the project's directory, for the command; None leaves the
    command to the working directory.
    """
    rows: list[ListingRow] = []
    context = ["--path", str(project)] if project is not None else []
    for item in requests:
        command = shlex.join(["devcapsule", "project", *context, "config", "console", "apply", item.id])
        rows.append(ListingRow(
            "console", item.id, "-", f"console request at {item.requested}",
            f"confirm or discard: {item.statement}", command,
            Decision("console", item.id, item.statement, command, reason=item.requested),
        ))
    return rows
