"""``project wrap``: a foreign repository as a submodule of a wrapper project, declared and explained.

The wrapped-projects work order of 2026-11-02: a developer gives DevCapsule
a repository that is not theirs and carries no DevCapsule configuration, and
works on it in a capsule without imposing anything on it.  The configuration
lives in a small wrapper repository of their own; the foreign code is a Git
submodule of it.  ``wrap`` does, in order:

1. adds the submodule, with its Git directory embedded in the tree the
   capsule mounts, so it works inside the capsule on the first run;
2. requires the capabilities the developer names: the launcher infers
   nothing from a foreign tree (owner's ruling of 2026-11-02); how the
   source is built is settled inside the capsule, by the agent with the
   developer, and the guidance says so;
3. initializes the manifest and lock as ``init`` would, or extends an
   existing manifest with what was named;
4. declares the source under ``[sources."<path>"]``;
5. writes the wrapper's ``AGENTS.md`` and ``README.md``, regenerated from the
   manifest on every wrap, so an agent and a human each know what is foreign,
   under whose control, how to build it and which Java to use.

A rerun after an interruption finishes what was left: a submodule already
added at the path from the same URL is kept, not refused.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import shutil
import subprocess
from typing import Any, Mapping, TextIO

from devcapsule.compat import CliError
from devcapsule.configuration.file_formats import ProjectConfigurationError
from devcapsule.configuration.manifest import current_manifest
from devcapsule.configuration.operations import InitializeReport, InitializeRequest, ProvidedAnswer, initialize_project
from devcapsule.configuration.owner_commands import declare_source, require_tools
from devcapsule.configuration.sources import WrappedSource, WrappedSources, source_path
from devcapsule.configuration.storage import load_toml

__all__ = ["WrapRequest", "WrapReport", "wrap_project", "GUIDANCE_MARKER", "render_agents", "render_readme"]

# The first line of every file wrap writes: the one it may rewrite.
GUIDANCE_MARKER = "<!-- Written by `devcapsule project wrap`; regenerated on every wrap. Keep your own notes in another file. -->"

# Where the capsule's base image keeps each Java line, by the stable name the
# runtime guarantees across base updates (design of 2026-11-02, section 2).
JAVA_HOME_ROOT = "/opt/java"


@dataclass(frozen=True)
class WrapRequest:
    """Everything ``devcapsule project wrap`` collected from its command line."""

    directory: Path
    url: str
    path: str | None = None
    upstream: str | None = None
    # What the source needs, as the developer names it: project capabilities
    # every checkout must have, and the Java line the source builds with.
    require: tuple[str, ...] = ()
    java: str | None = None
    # The owner's own checkout, as for init: never in the manifest.
    ide: str | None = None
    agents: tuple[str, ...] = ()
    project_name: str | None = None
    slug: str | None = None
    creator: str | None = None
    project_mount: str | None = None
    answers: tuple[ProvidedAnswer, ...] = ()
    allow_unverified: bool = False
    interactive: bool | None = None


@dataclass(frozen=True)
class WrapReport:
    """What one wrap did, in the order it did it."""

    path: str
    submodule_action: str
    initialized: InitializeReport | None
    capability_lines: tuple[str, ...]
    source_line: str
    guidance: tuple[str, ...]
    next_steps: tuple[str, ...]

    def render(self) -> str:
        lines = [self.submodule_action]
        if self.initialized is not None:
            lines.append(self.initialized.render())
        lines.extend(self.capability_lines)
        lines.append(self.source_line)
        lines.extend(self.guidance)
        lines.append("Next: " + " ".join(self.next_steps))
        return "\n".join(lines)


def wrap_project(request: WrapRequest, *, input_stream: TextIO | None = None, output_stream: TextIO | None = None) -> WrapReport:
    """Wrap one repository into the project at ``request.directory``; see the module docstring for the steps."""
    root = request.directory.expanduser().resolve()
    _require_repository_root(root)
    path = source_path(request.path if request.path is not None else _repository_name(request.url), field_name="--path")
    # Validate source metadata before Git or initialization writes anything.
    WrappedSources.read({"sources": {path: WrappedSource(path, request.upstream, request.java).document()}})
    submodule_action = _add_submodule(root, request.url, path)
    manifest_path = root / ".devcapsule" / "devcapsule.toml"
    initialized: InitializeReport | None = None
    capability_lines: list[str] = []
    needed = tuple(dict.fromkeys(request.require))
    if not manifest_path.is_file():
        try:
            initialized = initialize_project(
                InitializeRequest(directory=root, require=needed, ide=request.ide, agents=request.agents,
                                  project_name=request.project_name, slug=request.slug, creator=request.creator,
                                  project_mount=request.project_mount, answers=request.answers,
                                  allow_unverified=request.allow_unverified, interactive=request.interactive),
                input_stream=input_stream, output_stream=output_stream,
            )
        except (CliError, KeyboardInterrupt) as exc:
            raise ProjectConfigurationError(
                f"Initialization did not finish: {exc or 'interrupted'}. The submodule {path} remains. "
                "Rerun wrap with the missing answers; if configuration files already exist, complete 'project init' first."
            ) from exc
    else:
        manifest = current_manifest(load_toml(manifest_path), manifest_path).document()
        declared = {name.partition(">=")[0] for name in manifest["capabilities"].get("required", [])}
        missing = tuple(name for name in needed if name not in declared)
        if missing:
            capability_lines.append(require_tools(root, missing, allow_unverified=request.allow_unverified).splitlines()[0])
    source_line = declare_source(root, path, upstream=request.upstream, java=request.java).splitlines()[0]
    manifest = current_manifest(load_toml(manifest_path), manifest_path).document()
    guidance = _write_guidance(root, manifest)
    next_steps = ("Review the changes, commit them (the submodule, .gitmodules, .devcapsule/, AGENTS.md, README.md),",
                  "then 'devcapsule project run' opens the capsule.")
    return WrapReport(path, submodule_action, initialized, tuple(capability_lines), source_line, guidance, next_steps)


def _require_repository_root(root: Path) -> None:
    completed = _git(root, "rev-parse", "--show-toplevel", check=False)
    if completed.returncode != 0:
        raise ProjectConfigurationError(f"{root} is not a Git repository; 'git init' there first, then wrap.")
    top = Path(completed.stdout.strip()).resolve()
    if top != root:
        raise ProjectConfigurationError(f"Wrap at the repository's top level, {top}, where the manifest lives; {root} is inside it.")


def _repository_name(url: str) -> str:
    """The last path segment of a Git URL without ``.git``: ``RobotCode2025Public`` from its GitHub URL."""
    trimmed = url.rstrip("/")
    name = trimmed.rsplit("/", 1)[-1].rsplit(":", 1)[-1]
    name = name[:-4] if name.endswith(".git") else name
    if not name:
        raise ProjectConfigurationError(f"Cannot name a directory after {url!r}; give --path NAME.")
    return name


def _add_submodule(root: Path, url: str, path: str) -> str:
    """Add the submodule unless the same one already stands at ``path``; embed its Git directory either way."""
    target = root / path
    if any(part.is_symlink() for part in (target, *target.parents) if part != root and root in part.parents):
        raise ProjectConfigurationError(f"{target} passes through a symlink; give a path inside the wrapper without symlinks.")
    registered = _registered_url(root, path)
    if registered is not None:
        if registered != url:
            raise ProjectConfigurationError(f"{path} is registered with a different URL ({registered}); give another --path.")
        if not (target / ".git").exists():
            _git(root, "submodule", "update", "--init", "--", path)
        action = f"Kept the submodule {path}, already added from {url}"
    elif target.exists():
        raise ProjectConfigurationError(f"{target} exists and is not a submodule added from {url}; inspect any partial clone, then give another --path.")
    else:
        try:
            _git(root, "submodule", "add", "--", url, path)
        except ProjectConfigurationError as exc:
            raise ProjectConfigurationError(
                f"{exc}. Git may have left a partial submodule at {path}; no files were removed. "
                "Rerun wrap if the submodule was registered; otherwise inspect the path, .gitmodules and Git's modules directory before retrying."
            ) from exc
        action = f"Added the submodule {path} from {url}"
    return action + ("; its Git directory is embedded in the tree." if _embed_git_directory(root, path) else ".")


def _embed_git_directory(root: Path, path: str) -> bool:
    """Move ``.git/modules/<path>`` into ``<path>/.git`` so the capsule, which mounts the project tree alone, sees it.

    ``git submodule add`` leaves the submodule's Git directory under the
    superproject's ``.git`` and a one-line gitfile in the submodule; a bind
    mount of the project tree then carries a dangling pointer.  Returns
    whether a move happened.
    """
    gitfile = root / path / ".git"
    if gitfile.is_dir():
        return False
    # Ask the submodule: its registered name can differ from its path, and
    # a linked wrapper worktree has its own Git directory.
    module = Path(_git(root / path, "rev-parse", "--absolute-git-dir").stdout.strip())
    if not module.is_dir():
        raise ProjectConfigurationError(f"The submodule's Git directory is neither at {gitfile} nor at {module}; cannot embed it.")
    gitfile.unlink()
    shutil.move(str(module), str(gitfile))
    # Edit the file, not the repository: ``core.worktree`` still points at the
    # old location relative to the old Git directory, and discovery through
    # it would fail before the command ran.
    _git(root, "config", "--file", str(gitfile / "config"), "--unset", "core.worktree")
    return True


def _git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True)
    if check and completed.returncode != 0:
        raise ProjectConfigurationError(f"git {' '.join(args)} failed: {completed.stderr.strip() or completed.stdout.strip()}")
    return completed


def _write_guidance(root: Path, manifest: Mapping[str, Any]) -> tuple[str, ...]:
    """Write AGENTS.md and README.md from the manifest; a file without the marker is the owner's and is left alone."""
    sources = WrappedSources.read(manifest)
    origins = {source.path: _origin(root, source.path) for source in sources.entries}
    lines: list[str] = []
    for name, text in (("AGENTS.md", render_agents(manifest, sources, origins)), ("README.md", render_readme(manifest, sources, origins))):
        target = root / name
        if target.is_file() and target.read_text(encoding="utf-8").splitlines()[:1] != [GUIDANCE_MARKER]:
            lines.append(f"Kept your {name}; it does not carry the wrap marker. Add the wrapped sources to it yourself.")
            continue
        target.write_text(text, encoding="utf-8")
        lines.append(f"Wrote {name}.")
    return tuple(lines)


def _origin(root: Path, path: str) -> str:
    return _registered_url(root, path) or "(not in .gitmodules)"


def _registered_url(root: Path, path: str) -> str | None:
    """Find a submodule by its path, which need not equal its Git section name."""
    completed = _git(root, "config", "--null", "-f", ".gitmodules", "--get-regexp", r"^submodule\..*\.path$", check=False)
    for record in completed.stdout.split("\x00"):
        key, separator, value = record.partition("\n")
        if separator and value == path:
            url = _git(root, "config", "--null", "-f", ".gitmodules", key[:-4] + "url", check=False)
            # A registered path without a URL must not become a new add.
            return url.stdout.removesuffix("\x00") if url.returncode == 0 else ""
    return None


def _plain(value: str) -> str:
    """External text on one line: a control character becomes U+FFFD, so it cannot open a heading or a line of its own."""
    return "".join("\ufffd" if ord(character) < 0x20 or character == "\x7f" else character for character in value)


def _code_span(value: str) -> str:
    """External text as a Markdown code span, readable raw by an agent and inert when rendered.

    A code span cannot start a heading, a list or HTML; the file is read raw
    by agents, so the text inside stays exactly the path or URL they must
    use, never an entity.  A run of backticks inside is fenced by a longer run.
    """
    value = _plain(value)
    runs = [len(run) for run in re.findall(r"`+", value)]
    fence = "`" * (max(runs, default=0) + 1)
    padding = " " if value.startswith("`") or value.endswith("`") else ""
    return f"{fence}{padding}{value}{padding}{fence}"


def _java_lines(source: WrappedSource) -> list[str]:
    if source.java is None:
        return ["- How this source is built, tested and run is not settled yet. Find out with the user, from its own",
                "  files, before assuming; do not write the answer into the source."]
    home = f"{JAVA_HOME_ROOT}/{source.java}"
    return [f"- Builds with Java {source.java}. Before any build, test or run in this directory, select it:",
            "", "  ```bash", f'  export JAVA_HOME={home}; export PATH="$JAVA_HOME/bin:$PATH"', "  ```"]


def render_agents(manifest: Mapping[str, Any], sources: WrappedSources, origins: Mapping[str, str]) -> str:
    """The wrapper's AGENTS.md: agent-neutral, regenerated from the manifest."""
    name = _plain(manifest["project"]["name"])
    lines = [GUIDANCE_MARKER, f"# Agent Instructions: {name}", "",
             "This repository is a DevCapsule wrapper. It holds the DevCapsule configuration under",
             "`.devcapsule/` and foreign repositories as Git submodules. The code to work on lives in",
             "the submodules; the wrapper only sets up the environment around them.", "",
             "## Wrapped sources", ""]
    for source in sources.entries:
        lines.extend([f"### {_code_span(source.path)}", "", f"- Origin: {_code_span(origins.get(source.path, ''))}",
                      f"- Intent: {source.intent}." + (f" Upstream: {_code_span(source.upstream)}." if source.upstream else "")])
        lines.extend(_java_lines(source))
        lines.append("")
    lines.extend(["## Rules", "",
                  "1. Never push to, or open a pull request against, a source whose intent is to learn.",
                  "   A fork's origin takes the changes; its upstream never does, unless its maintainers ask.",
                  "2. Write nothing inside a wrapped source that is not the change you were asked for: no",
                  "   DevCapsule files, no IDE files, no notes. The wrapper holds the configuration.",
                  "3. Build, test and run each source with its own tool, from its own directory, with the Java",
                  "   line named above selected first.",
                  "4. Changes to the wrapper itself (the manifest, these files) are ordinary commits here.",
                  "5. A fresh clone of this wrapper needs `git submodule update --init` before anything else.", ""])
    return "\n".join(lines)


def render_readme(manifest: Mapping[str, Any], sources: WrappedSources, origins: Mapping[str, str]) -> str:
    """The wrapper's README.md for a person: what this is and how to start."""
    name = _plain(manifest["project"]["name"])
    lines = [GUIDANCE_MARKER, f"# {name}", "",
             "A DevCapsule wrapper: the development environment for the repositories below, which",
             "are not this repository's own code and carry no DevCapsule configuration of their own.", "",
             "## Start", "", "```bash", "git clone --recurse-submodules <this repository>",
             "devcapsule project run", "```", "",
             "An existing clone without the submodules: `git submodule update --init`.", "",
             "## Wrapped sources", ""]
    for source in sources.entries:
        lines.extend([f"### {_code_span(source.path)}", "", f"- Origin: {_code_span(origins.get(source.path, ''))}",
                      f"- Intent: {source.intent}." + (f" Upstream: {_code_span(source.upstream)}." if source.upstream else "")])
        lines.extend(_java_lines(source))
        lines.append("")
    return "\n".join(lines)
