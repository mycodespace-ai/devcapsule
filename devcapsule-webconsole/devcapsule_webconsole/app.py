"""The FastAPI application: pages, their JSON, records, files, monitoring, decisions and notifications.

Writes stay in capsule state: decision answers, notifications read or
dismissed through the runtime CLI, and configuration requests the launcher
answers through its mounted channel. Every other route is ``GET``. The pages are static
files that fetch their facts from the ``/api`` routes, which run the
runtime CLI, read the capsule's processes and cgroup, list or read inside
the project mount, or read the decisions directory. The records page
renders any markdown file of the project in the browser, the files page
lists and serves the mounted project's files, and the presentation page lists
the folders that hold a ``presentation.json`` and shows one as slides beside
its recording, read through the raw route. The token gate wraps the whole application, static files included.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import ExitStack
import json
import mimetypes
from pathlib import Path
import re
from typing import Any, BinaryIO, Callable
from urllib.parse import quote

from fastapi import FastAPI, Query, Request, Response
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.background import BackgroundTask

from . import __version__
from . import monitor
from .cli import CommandError, CommandRefused, RuntimeCli
from .configuration import MAXIMUM_COMMAND_BYTES, ChannelError, ConfigurationChannel, parse_command, suggested_arguments
from .decisions import (
    KEY_PATTERN, MAXIMUM_ANSWER_BYTES, Decision, DecisionError, DecisionStore, answer_from_mapping,
)
from .security import (
    PathRefused, TokenGate, find_project_folders, list_project_directory, open_project_file, read_project_text,
)
from .settings import Settings

PAGES = {
    "/": "index.html",
    "/configuration": "configuration.html",
    "/versions": "versions.html",
    "/project": "project.html",
    "/processes": "processes.html",
    "/records": "records.html",
    "/files": "files.html",
    "/decisions": "decisions.html",
    "/notifications": "notifications.html",
}
# What a raw project file is served as when mimetypes.guess_type and the
# image/video/audio/text rules in raw_content_type would not give it across
# platforms. Markdown is text so a browser shows it; anything unknown is bytes
# a browser offers to save. SVG can contain active content; the raw route
# isolates every response below.
RAW_CONTENT_TYPES = {
    ".md": "text/markdown; charset=utf-8",
    ".txt": "text/plain; charset=utf-8",
    ".toml": "text/plain; charset=utf-8",
    ".yaml": "text/plain; charset=utf-8",
    ".yml": "text/plain; charset=utf-8",
    ".lock": "text/plain; charset=utf-8",
    ".cfg": "text/plain; charset=utf-8",
    ".ini": "text/plain; charset=utf-8",
    ".cjs": "text/plain; charset=utf-8",
    ".sh": "text/plain; charset=utf-8",
    ".log": "text/plain; charset=utf-8",
    ".xml": "text/plain; charset=utf-8",
    ".json": "application/json",
    ".pdf": "application/pdf",
    ".svg": "image/svg+xml",
    ".webp": "image/webp",
    ".mkv": "video/x-matroska",
    ".ogg": "audio/ogg",
    ".wav": "audio/wav",
}
RAW_CHUNK_BYTES = 64 * 1024
# The file whose presence makes a project folder a presentation (PRESENTATIONS.md).
PRESENTATION_FILE = "presentation.json"
RAW_SECURITY_HEADERS = {
    "Accept-Ranges": "bytes",
    "Content-Security-Policy": "sandbox; default-src 'none'; style-src 'unsafe-inline'",
    "X-Content-Type-Options": "nosniff",
}
_BYTE_RANGE_SPEC = re.compile(r"^([0-9]*)-([0-9]*)$")


def create_app(settings: Settings) -> FastAPI:
    app = FastAPI(title="DevCapsule web console", version=__version__, docs_url=None, redoc_url=None, openapi_url=None)
    app.state.settings = settings
    cli = RuntimeCli(settings.cli, settings.project)

    def document(read: Callable[[], dict[str, Any]]) -> JSONResponse:
        try:
            return JSONResponse(read())
        except CommandError as error:
            return JSONResponse(error.to_document(), status_code=502)

    for route, page in PAGES.items():
        app.add_api_route(route, _page(settings, page), methods=["GET"], include_in_schema=False)
    # One page for every record or directory: the script reads the path from the URL.
    app.add_api_route("/records/{record:path}", _page(settings, "records.html"), methods=["GET"], include_in_schema=False)
    app.add_api_route("/files/{path:path}", _page(settings, "files.html"), methods=["GET"], include_in_schema=False)
    # One page for the list of presentations and for each of them: the script
    # reads the folder from the URL, and its presentation.json, recording and
    # screenshots through the raw route.
    app.add_api_route("/presentations", _page(settings, "presentation.html"), methods=["GET"], include_in_schema=False)
    app.add_api_route("/presentations/{path:path}", _page(settings, "presentation.html"), methods=["GET"], include_in_schema=False)
    app.add_api_route("/decisions/{decision_id}", _page(settings, "decisions.html"), methods=["GET"], include_in_schema=False)

    @app.get("/filetree", include_in_schema=False)
    def filetree_root() -> RedirectResponse:
        return RedirectResponse(_files_redirect_target(), status_code=307)

    @app.get("/filetree/{path:path}", include_in_schema=False)
    def filetree_path(path: str) -> RedirectResponse:
        return RedirectResponse(_files_redirect_target(path), status_code=307)

    store = DecisionStore(settings.decisions)

    def decision_or_response(decision_id: str) -> Decision | PlainTextResponse:
        if KEY_PATTERN.fullmatch(decision_id) is None:
            return PlainTextResponse(f"no decision {decision_id!r}\n", status_code=404)
        try:
            return store.read_decision(decision_id)
        except FileNotFoundError:
            return PlainTextResponse(f"no decision {decision_id!r}\n", status_code=404)
        except DecisionError as error:
            return PlainTextResponse(f"decision {decision_id!r} does not follow the contract: {error}\n", status_code=422)

    @app.get("/api/decisions")
    def list_decisions() -> JSONResponse:
        entries: list[dict[str, Any]] = []
        for decision_id in store.list_ids():
            try:
                decision = store.read_decision(decision_id)
                answer = store.read_answer(decision)
            except FileNotFoundError:
                continue  # The asking agent discarded it after the directory scan.
            except DecisionError as error:
                entries.append({"id": decision_id, "title": None, "asked-by": None, "asked-at": None,
                                "items": None, "answered-at": None, "error": str(error)})
                continue
            entries.append({"id": decision.id, "title": decision.title, "asked-by": decision.asked_by,
                            "asked-at": decision.asked_at, "items": len(decision.items),
                            "answered-at": answer.answered_at if answer else None})
        return JSONResponse({"decisions": entries})

    @app.get("/api/decisions/{decision_id}")
    def show_decision(decision_id: str) -> Response:
        decision = decision_or_response(decision_id)
        if not isinstance(decision, Decision):
            return decision
        try:
            answer = store.read_answer(decision)
        except DecisionError as error:
            return PlainTextResponse(f"answer for {decision_id!r} does not follow the contract: {error}\n", status_code=422)
        return JSONResponse({"decision": decision.to_mapping(), "answer": answer.to_mapping() if answer else None})

    @app.post("/api/decisions/{decision_id}/answer")
    async def answer_decision(decision_id: str, request: Request) -> Response:
        """The console's one write: the human's answer, beside the decision.

        A same-origin request only: the token cookie is ``SameSite=Strict``,
        and the required ``Origin`` header must name this
        console. The body is validated against the decision before anything
        is written; a refusal writes nothing.
        """
        if not same_origin(request):
            return PlainTextResponse("the answer must come from the console's own origin\n", status_code=403)
        decision = decision_or_response(decision_id)
        if not isinstance(decision, Decision):
            return decision
        body = bytearray()
        async for chunk in request.stream():
            if len(body) + len(chunk) > MAXIMUM_ANSWER_BYTES:
                return PlainTextResponse("the answer is too large\n", status_code=413)
            body.extend(chunk)
        try:
            document = json.loads(body.decode("utf-8"))
        except (ValueError, RecursionError) as error:
            return PlainTextResponse(f"the answer must be a JSON document: {error}\n", status_code=422)
        try:
            answer = answer_from_mapping(decision, document)
        except DecisionError as error:
            return PlainTextResponse(f"the answer does not fit the decision: {error}\n", status_code=422)
        try:
            store.write_answer(answer)
        except OSError as error:
            return PlainTextResponse(f"cannot write the answer: {error}\n", status_code=500)
        return JSONResponse({"answer": answer.to_mapping()})

    @app.get("/api/notifications")
    def notifications(unread: bool = False) -> JSONResponse:
        """The checkout's notifications as the runtime CLI lists them, pending decisions merged in."""
        return document(lambda: cli.notifications(unread_only=unread, decisions=settings.decisions))

    def notification_action(action: str) -> Callable[[str, Request], Response]:
        """``read`` or ``dismiss`` one notification through the CLI: a write into capsule state, same origin only."""

        def act(notification_id: str, request: Request) -> Response:
            if not same_origin(request):
                return PlainTextResponse("the request must come from the console's own origin\n", status_code=403)
            if KEY_PATTERN.fullmatch(notification_id) is None:
                return PlainTextResponse(f"no notification {notification_id!r}\n", status_code=404)
            try:
                output = cli.act("checkout", "notifications", action, notification_id)
            except CommandRefused as error:
                return PlainTextResponse(error.reason + "\n", status_code=422)
            except CommandError as error:
                return JSONResponse(error.to_document(), status_code=502)
            return JSONResponse({"id": notification_id, "action": action, "output": output})

        return act

    app.add_api_route("/api/notifications/{notification_id}/read", notification_action("read"), methods=["POST"])
    app.add_api_route("/api/notifications/{notification_id}/dismiss", notification_action("dismiss"), methods=["POST"])

    @app.get("/api/identity")
    def identity() -> JSONResponse:
        return document(lambda: compose_identity(cli.information(), cli.versions()))

    channel = ConfigurationChannel(settings.configuration)

    @app.get("/api/configuration")
    def configuration() -> JSONResponse:
        """The listing: the runtime CLI's, which inside a capsule is the launcher's listing at launch.

        Each pending row carries ``request``, the config tokens its host
        command implies, for the page's prefilled form.
        """
        try:
            listing = cli.configuration()
        except CommandError as error:
            return JSONResponse(error.to_document(), status_code=502)
        for row in listing.get("rows", []) if isinstance(listing.get("rows"), list) else []:
            if isinstance(row, dict) and row.get("pending") and isinstance(row.get("command"), str):
                row["request"] = suggested_arguments(row["command"])
        listing["channel"] = channel.available
        return JSONResponse(listing)

    @app.get("/api/configuration/requests")
    def configuration_requests() -> JSONResponse:
        """The requests written this run and the launcher's result for each, in order."""
        try:
            return JSONResponse({"channel": channel.available, "requests": [item.to_mapping() for item in channel.requests()]})
        except (ChannelError, OSError) as error:
            return JSONResponse({"error": str(error)}, status_code=502)

    @app.post("/api/configuration/requests")
    async def configuration_request(request: Request) -> Response:
        """The console's write for the next launch: one request file the launcher answers.

        Same origin only, as the decision answer. The body is ``{"command":
        "<config tokens>"}``; the verb is checked here, the whole command by
        the launcher, which records, refuses or defers it.
        """
        if not same_origin(request):
            return PlainTextResponse("the request must come from the console's own origin\n", status_code=403)
        body = bytearray()
        async for chunk in request.stream():
            if len(body) + len(chunk) > MAXIMUM_COMMAND_BYTES:
                return PlainTextResponse("the request is too large\n", status_code=413)
            body.extend(chunk)
        try:
            document = json.loads(body.decode("utf-8"))
        except (ValueError, RecursionError) as error:
            return PlainTextResponse(f"the request must be a JSON document: {error}\n", status_code=422)
        command = document.get("command") if isinstance(document, dict) else None
        if not isinstance(command, str):
            return PlainTextResponse("the request names its command as a string\n", status_code=422)
        try:
            tokens = parse_command(command)
            written = channel.write_request(tokens)
        except ChannelError as error:
            return PlainTextResponse(f"{error}\n", status_code=422)
        except OSError as error:
            return PlainTextResponse(f"cannot write the request: {error}\n", status_code=500)
        return JSONResponse({"request": written.to_mapping()}, status_code=201)

    @app.get("/api/versions")
    def versions() -> JSONResponse:
        return document(cli.versions)

    @app.get("/api/project")
    def project() -> JSONResponse:
        return document(cli.information)

    @app.get("/api/processes")
    def processes() -> JSONResponse:
        return JSONResponse(monitor.processes())

    @app.get("/api/resources")
    def resources() -> JSONResponse:
        return JSONResponse(monitor.resources())

    @app.get("/api/project/tree")
    def project_tree(path: str = "") -> Response:
        """One directory of the mounted project: entries as lstat sees them, links unfollowed.

        Each regular file's entry carries ``type``, the media type the raw route
        serves it as, so the Files page asks here which files are video or
        audio and keeps no table of its own; ``type`` is null for other entries.
        """
        try:
            listing = list_project_directory(settings.project, path)
        except PathRefused as error:
            return PlainTextResponse(str(error) + "\n", status_code=403)
        except NotADirectoryError:
            return PlainTextResponse(f"{path!r} is not a directory in the project\n", status_code=404)
        except FileNotFoundError:
            return PlainTextResponse(f"no directory at {path!r} in the project\n", status_code=404)
        except OSError:
            return PlainTextResponse(f"cannot read {path!r} in the project\n", status_code=403)
        for entry in listing["entries"]:
            entry["type"] = raw_content_type(entry["name"]) if entry["kind"] == "file" else None
        return JSONResponse(listing)

    @app.get("/api/project/presentations")
    def project_presentations() -> JSONResponse:
        """The project's folders that hold a presentation, and whether the search visited every directory."""
        return JSONResponse(find_project_folders(settings.project, PRESENTATION_FILE))

    @app.get("/api/project/file")
    def project_file(path: str = Query(...)) -> PlainTextResponse:
        try:
            text = read_project_text(settings.project, path)
        except PathRefused as error:
            return PlainTextResponse(str(error) + "\n", status_code=403)
        except FileNotFoundError:
            return PlainTextResponse(f"no file at {path!r} in the project\n", status_code=404)
        except UnicodeDecodeError:
            return PlainTextResponse(f"{path!r} is not a UTF-8 text file\n", status_code=415)
        except OSError:
            return PlainTextResponse(f"cannot read {path!r} in the project\n", status_code=403)
        return PlainTextResponse(text)

    @app.get("/api/project/raw")
    def project_raw(request: Request, path: str = Query(...), download: str | None = None) -> Response:
        """A project file streamed in chunks, with single byte-range seeking and optional attachment download."""
        stack = ExitStack()
        try:
            stream, size = stack.enter_context(open_project_file(settings.project, path))
        except PathRefused as error:
            stack.close()
            return PlainTextResponse(str(error) + "\n", status_code=403)
        except FileNotFoundError:
            stack.close()
            return PlainTextResponse(f"no file at {path!r} in the project\n", status_code=404)
        except OSError:
            stack.close()
            return PlainTextResponse(f"cannot read {path!r} in the project\n", status_code=403)
        try:
            byte_range = _parse_byte_range(request.headers.get("range"), size)
        except _UnsatisfiableRange:
            stack.close()
            return Response(
                b"",
                status_code=416,
                headers={**RAW_SECURITY_HEADERS, "Content-Range": f"bytes */{size}"},
            )
        # An SVG is an image when embedded, but an active document when opened.
        # Isolate raw documents from the console origin and forbid their code,
        # subresources and forms. nosniff also prevents use as a script or style.
        headers = dict(RAW_SECURITY_HEADERS)
        if download == "1":
            headers["Content-Disposition"] = _attachment_disposition(path)
        if byte_range is None:
            start, length, status_code = 0, size, 200
        else:
            start, end = byte_range
            length = end - start + 1
            status_code = 206
            headers["Content-Range"] = f"bytes {start}-{end}/{size}"
        headers["Content-Length"] = str(length)
        cleanup = stack.pop_all()
        return StreamingResponse(
            _stream_file_slice(stream, start, length, cleanup),
            status_code=status_code,
            media_type=raw_content_type(path),
            headers=headers,
            background=BackgroundTask(cleanup.close),
        )

    app.mount("/static", StaticFiles(directory=str(settings.static_root)), name="static")
    app.add_middleware(TokenGate, token=settings.token)
    return app


def same_origin(request: Request) -> bool:
    """Exactly one ``Origin`` header naming this console, port included, no trailing slash."""
    return request.headers.getlist("origin") == [f"{request.url.scheme}://{request.url.netloc}"]


def _files_redirect_target(path: str = "") -> str:
    encoded = "/".join(quote(part, safe="") for part in path.split("/") if part)
    return f"/files/{encoded}" if encoded else "/files"


class _UnsatisfiableRange(ValueError):
    """A single ``bytes=`` range does not overlap the file."""


def _parse_byte_range(header: str | None, size: int) -> tuple[int, int] | None:
    if header is None:
        return None
    unit, separator, spec = header.strip().partition("=")
    if separator != "=" or unit.lower() != "bytes":
        return None
    if "," in spec:
        return None
    match = _BYTE_RANGE_SPEC.fullmatch(spec.strip())
    if match is None:
        raise _UnsatisfiableRange
    first_text, last_text = match.groups()
    if not first_text and not last_text:
        raise _UnsatisfiableRange
    if not first_text:
        suffix = int(last_text)
        if suffix == 0 or size == 0:
            raise _UnsatisfiableRange
        return max(0, size - suffix), size - 1
    first = int(first_text)
    if size == 0 or first >= size:
        raise _UnsatisfiableRange
    if not last_text:
        return first, size - 1
    last = int(last_text)
    if last < first:
        raise _UnsatisfiableRange
    return first, min(last, size - 1)


def _stream_file_slice(stream: BinaryIO, start: int, length: int, cleanup: ExitStack) -> Iterator[bytes]:
    try:
        if start:
            stream.seek(start)
        remaining = length
        while remaining > 0:
            chunk = stream.read(min(RAW_CHUNK_BYTES, remaining))
            if not chunk:
                break
            remaining -= len(chunk)
            yield chunk
    finally:
        cleanup.close()


def _attachment_disposition(path: str) -> str:
    basename = Path(path).name or "download"
    ascii_fallback = "".join(
        ch if 0x20 <= ord(ch) < 0x7F and ch not in {'"', "\\"} else "_"
        for ch in basename
    )
    encoded = quote(basename, encoding="utf-8", safe="!#$&+-.^_`|~")
    return f'attachment; filename="{ascii_fallback}"; filename*=UTF-8\'\'{encoded}'


def _page(settings: Settings, name: str) -> Callable[[], FileResponse]:
    def page() -> FileResponse:
        return FileResponse(settings.static_root / name, media_type="text/html")

    return page


def compose_identity(information: dict[str, Any], versions: dict[str, Any]) -> dict[str, Any]:
    """The home page's identity block from ``project info`` and ``versions show``.

    The version set is the running one inside a capsule and the selected one
    on a host; ``versions show`` names which through its ``context``.
    """
    version_set = versions.get("running") if versions.get("context") == "running capsule" else versions.get("selected")
    return {
        "context": information.get("context"),
        "project": information.get("project", {}),
        "checkout": information.get("checkout", {}),
        "base": information.get("base", {}),
        "version-set": {key: version_set.get(key) for key in ("identity", "origin")} if version_set else None,
        "console-version": __version__,
    }


def raw_content_type(path: str) -> str:
    """The media type for a raw project file, isolated by the raw route's CSP.

    HTML is served as plain text. SVG keeps its image type for illustrations;
    the response sandbox prevents an opened SVG from using the console origin.
    """
    suffix = "." + path.rsplit(".", 1)[-1].lower() if "." in path.rsplit("/", 1)[-1] else ""
    if suffix in RAW_CONTENT_TYPES:
        return RAW_CONTENT_TYPES[suffix]
    guessed, _ = mimetypes.guess_type(path)
    if guessed and (guessed.startswith("image/") or guessed.startswith("video/") or guessed.startswith("audio/")):
        return guessed
    if guessed and guessed.startswith("text/"):
        return "text/plain; charset=utf-8"
    return "application/octet-stream"
