"""CLI adapter for links to the current capsule's existing content viewers."""
import argparse
import os
from pathlib import Path
from urllib.parse import quote, unquote, urlencode, urlsplit, urlunsplit

from devcapsule.commands.framework import Command
from devcapsule.compat import CliError

__all__ = ["COMMAND", "content_link"]


def content_link(value: str, *, project: Path, cwd: Path, console_url: str, token: str) -> str:
    """Format an existing console route; paths use Files and URLs retain their viewer."""
    origin = urlsplit(console_url)
    if (not console_url or any(ch.isspace() or ch == "\\" for ch in console_url)
            or origin.scheme not in ("http", "https") or not origin.hostname
            or origin.username is not None or origin.password is not None):
        raise ValueError("the current capsule must supply an HTTP(S) console URL")
    origin_key = (origin.scheme, origin.hostname, origin.port or (443 if origin.scheme == "https" else 80))
    target = urlsplit(value)
    fragment = ""
    if target.scheme or target.netloc:
        if (target.scheme not in ("http", "https") or not target.hostname
                or target.username is not None or target.password is not None
                or any(ch.isspace() or ch == "\\" for ch in value)):
            raise ValueError("supply a URL on the current console origin")
        target_key = (target.scheme, target.hostname, target.port or (443 if target.scheme == "https" else 80))
        if target_key != origin_key:
            raise ValueError("URL must use the current console origin")
        parts = unquote(target.path).split("/")
        if len(parts) < 2 or parts[1] not in ("files", "records", "presentations"):
            raise ValueError("URL must select the Files, Records or Presentations viewer")
        route = parts[1]
        relative = Path(*parts[2:])
        if ".." in parts or any(part.startswith(".") or part == "node_modules" for part in parts if part):
            raise ValueError("content must be visible within the console project")
        resolved = (project / relative).resolve()
        fragment = target.fragment
    else:
        route = "files"
        resolved = (cwd / value).resolve()
    relative = resolved.relative_to(project)
    if any(part.startswith(".") or part == "node_modules" for part in relative.parts):
        raise ValueError("content must be visible within the console project")
    if not resolved.exists():
        raise ValueError("content does not exist in the console project")
    suffix = "/" + quote(relative.as_posix(), safe="/") if relative.parts else ""
    return urlunsplit((origin.scheme, origin.netloc, f"/{route}{suffix}",
                       urlencode({"token": token}) if token else "", fragment))


class InstanceCommand(Command):
    name = "instance"
    help = "Get a web-console link to content in the running capsule."

    @classmethod
    def configure(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--get-link", required=True, metavar="PATH-OR-URL",
                            help="Project path (Files viewer) or current-console content URL.")

    @classmethod
    def run(cls, arguments: argparse.Namespace, context: object | None) -> int:
        if not os.environ.get("DEVCAPSULE_CONTAINER_NAME") or not os.environ.get("PROJECT_PATH"):
            raise CliError("instance --get-link runs inside the current capsule")
        token_path = Path(os.environ.get("DEVCAPSULE_CONSOLE_TOKEN_FILE") or "/run/devcapsule-console-token")
        try:
            token = token_path.read_text(encoding="utf-8").strip()
        except (OSError, UnicodeError):
            token = ""
        try:
            link = content_link(arguments.get_link, project=Path(os.environ["PROJECT_PATH"]).resolve(),
                                cwd=Path.cwd(), console_url=os.environ.get("DEVCAPSULE_CONSOLE_URL", ""), token=token)
        except (OSError, ValueError) as error:
            raise CliError(str(error)) from error
        if not token:
            print("Open the console first to establish a browser session; no readable run token was found.")
        print(link)
        return 0


COMMAND = InstanceCommand
