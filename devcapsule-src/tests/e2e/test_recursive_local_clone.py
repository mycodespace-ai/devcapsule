"""Executable acceptance test for the recursive E2E local-clone protocol.

This module deliberately keeps the security rationale beside the operations it
constrains.  The milestone document states the outcome; these small protocol
methods make the exact Git, Docker, ownership, and cleanup behavior executable.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import stat
import subprocess
import sys
from typing import Any, Mapping, Sequence

import pytest

pytestmark = pytest.mark.legacy


EMBEDDED_PEX = Path("/opt/devcapsule/bin/devcapsule.pex")
OWNER_MARKER = ".devcapsule-e2e-owner.json"
FULL_REVISION = re.compile(r"[0-9a-f]{40}")
FULL_DOCKER_ID = re.compile(r"sha256:[0-9a-f]{64}")
REPO_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class RecursiveEnvironment:
    """Trusted current-container facts needed before the clone may mutate state."""

    docker: str
    docker_environment: Mapping[str, str]
    container_id: str
    image_id: str
    bootstrap_revision: str
    workspace_root: Path


@dataclass(frozen=True)
class SourceSelection:
    """One clean source worktree and the exact commit copied by local clone."""

    checkout: Path
    git_directory: Path
    revision: str


@dataclass(frozen=True)
class OwnedWorkspace:
    """One collision-safe run root that this test may remove exactly."""

    workspace_root: Path
    run_root: Path
    run_id: str
    container_id: str
    git_environment: Mapping[str, str]
    empty_hooks: Path

    @classmethod
    def create(
        cls,
        environment: RecursiveEnvironment,
    ) -> OwnedWorkspace:
        return cls.create_at(
            environment.workspace_root,
            owner_identity=environment.container_id,
        )

    @classmethod
    def create_at(
        cls,
        workspace_root: Path,
        *,
        owner_identity: str,
    ) -> OwnedWorkspace:
        # The host daemon can see only paths translated from approved mounts.
        # Keeping this temporary checkout below preflight's persistent-home
        # workspace makes it suitable for later Stage 4 host-daemon use too.
        workspace_root = workspace_root.resolve(strict=True)
        run_id = secrets.token_hex(16)
        run_root = workspace_root / run_id
        run_root.mkdir(mode=0o700)
        run_root.chmod(0o700)

        marker = run_root / OWNER_MARKER
        payload = {
            "schema_version": 1,
            "run_id": run_id,
            "container_id": owner_identity,
        }
        descriptor = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                json.dump(payload, stream, sort_keys=True, separators=(",", ":"))
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
        except BaseException:
            marker.unlink(missing_ok=True)
            run_root.rmdir()
            raise
        marker.chmod(0o600)

        private_directories = {
            "home": run_root / "xdg/home",
            "config": run_root / "xdg/config",
            "cache": run_root / "xdg/cache",
            "data": run_root / "xdg/data",
            "state": run_root / "xdg/state",
            "runtime": run_root / "xdg/runtime",
            "hooks": run_root / "empty-hooks",
        }
        for directory in private_directories.values():
            directory.mkdir(mode=0o700, parents=True)
            directory.chmod(0o700)

        # Git receives an allowlist, not the agent's ambient environment.  In
        # particular, local clone must not import credential helpers, askpass,
        # SSH agents, tokens, user templates, or LFS network behavior.
        git_environment = {
            "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            "HOME": str(private_directories["home"]),
            "XDG_CONFIG_HOME": str(private_directories["config"]),
            "XDG_CACHE_HOME": str(private_directories["cache"]),
            "XDG_DATA_HOME": str(private_directories["data"]),
            "XDG_STATE_HOME": str(private_directories["state"]),
            "XDG_RUNTIME_DIR": str(private_directories["runtime"]),
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_LFS_SKIP_SMUDGE": "1",
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
        }
        return cls(
            workspace_root=workspace_root,
            run_root=run_root,
            run_id=run_id,
            container_id=owner_identity,
            git_environment=git_environment,
            empty_hooks=private_directories["hooks"],
        )

    def cleanup(self) -> None:
        """Remove only the exact non-symlinked root carrying our marker."""

        workspace = self.workspace_root.resolve(strict=True)
        assert not stat.S_ISLNK(self.run_root.lstat().st_mode)
        resolved = self.run_root.resolve(strict=True)
        assert resolved.parent == workspace
        assert resolved.name == self.run_id
        marker = resolved / OWNER_MARKER
        assert stat.S_ISREG(marker.lstat().st_mode)
        assert json.loads(marker.read_text(encoding="utf-8")) == {
            "schema_version": 1,
            "run_id": self.run_id,
            "container_id": self.container_id,
        }
        shutil.rmtree(resolved)


class LocalCloneProtocol:
    """Small protocol steps kept separate so failures identify one boundary."""

    def __init__(self, source_checkout: Path) -> None:
        self.source_checkout = source_checkout.resolve(strict=True)
        self._redactions = {str(self.source_checkout): "<current-checkout>"}

    def inspect_recursive_environment(self) -> RecursiveEnvironment:
        """Prove this test is inside the authorized, self-inspectable capsule."""

        assert Path("/.dockerenv").is_file(), "recursive clone E2E must run inside Docker"
        assert os.geteuid() != 0, "recursive clone E2E must run as an unprivileged user"
        assert EMBEDDED_PEX.is_file(), f"embedded DevCapsule PEX is missing: {EMBEDDED_PEX}"

        docker = shutil.which("docker")
        assert docker is not None, "Docker CLI is required inside recursive dogfood"
        docker_host = os.environ.get("DOCKER_HOST", "")
        assert docker_host.startswith("unix://"), "DOCKER_HOST must select an explicit Unix socket"
        docker_socket = Path(docker_host.removeprefix("unix://"))
        assert docker_socket.exists() and stat.S_ISSOCK(docker_socket.stat().st_mode)

        container_name = os.environ.get("DEVCAPSULE_CONTAINER_NAME", "")
        assert container_name, "normal project launch must declare DEVCAPSULE_CONTAINER_NAME"
        docker_environment = {
            "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            "DOCKER_HOST": docker_host,
            "DOCKER_CONFIG": "/tmp/devcapsule-recursive-e2e-empty-docker-config",
        }
        server_version = self._run(
            [docker, "version", "--format", "{{.Server.Version}}"],
            environment=docker_environment,
        ).stdout.strip()
        assert server_version, "the explicitly authorized host daemon did not report a version"

        preflight = self._source_preflight()
        assert preflight.get("ready") is True, "source recursive preflight is not READY"
        build_info = self._embedded_build_info()
        bootstrap_revision = self._full_revision(
            build_info.get("source_revision"), "embedded distribution revision"
        )
        facts = self._mapping(preflight.get("facts"), "preflight facts")
        workspace_root = Path(self._string(facts.get("workspace"), "workspace root"))
        assert workspace_root.is_dir() and os.access(workspace_root, os.W_OK | os.X_OK)
        assert workspace_root.is_relative_to(Path.home().resolve(strict=True))

        # Inspect by the exact launcher-provided name, then make the immutable
        # container and image IDs authoritative.  We intentionally never print
        # the complete inspection because it may include mounted host sources
        # or explicitly delivered environment secrets.
        container = self._inspect_one(
            [docker, "container", "inspect", container_name], docker_environment
        )
        container_id = self._string(container.get("Id"), "current container ID")
        assert re.fullmatch(r"[0-9a-f]{64}", container_id)
        image_id = self._full_docker_id(container.get("Image"), "current image ID")
        state = self._mapping(container.get("State"), "current container state")
        assert state.get("Running") is True, "the current dogfood container is not running"

        image = self._inspect_one([docker, "image", "inspect", image_id], docker_environment)
        assert image.get("Id") == image_id
        config = self._mapping(image.get("Config"), "current image configuration")
        labels = self._mapping(config.get("Labels"), "current image labels")
        assert labels.get("devcapsule.image.managed") == "true"
        assert labels.get("devcapsule.image.kind") == "materialized"
        assert labels.get("devcapsule.source.revision") == bootstrap_revision
        assert labels.get("devcapsule.pex.sha256") == self._file_sha256(EMBEDDED_PEX)

        return RecursiveEnvironment(
            docker=docker,
            docker_environment=docker_environment,
            container_id=container_id,
            image_id=image_id,
            bootstrap_revision=bootstrap_revision,
            workspace_root=workspace_root,
        )

    def select_clean_source(self) -> SourceSelection:
        """Select exact clean HEAD without equating it to the older v024 PEX."""

        git = self._git_binary()
        root = Path(self._git(git, "rev-parse", "--show-toplevel").stdout.strip())
        assert root.resolve(strict=True) == self.source_checkout
        revision = self._full_revision(
            self._git(git, "rev-parse", "--verify", "HEAD^{commit}").stdout.strip(),
            "selected source revision",
        )
        status_output = self._git(
            git, "status", "--porcelain=v1", "--untracked-files=all"
        ).stdout
        assert not status_output, (
            "recursive local-clone E2E requires a clean source checkout; "
            "commit or remove every tracked and untracked change"
        )
        git_directory = Path(
            self._git(git, "rev-parse", "--absolute-git-dir").stdout.strip()
        ).resolve(strict=True)
        return SourceSelection(self.source_checkout, git_directory, revision)

    def clone_without_checkout(
        self,
        selection: SourceSelection,
        workspace: OwnedWorkspace,
    ) -> Path:
        """Copy Git objects locally without hard links, checkout, hooks, or network."""

        clone = workspace.run_root / "checkout"
        git = self._git_binary()
        # --local refuses URL transport and --no-hardlinks gives the clone its
        # own object files.  --no-checkout lets us install the empty hook policy
        # before materializing any selected-revision worktree files.
        self._run(
            [
                git,
                "-c",
                "protocol.file.allow=always",
                "-c",
                "credential.helper=",
                "-c",
                f"init.templateDir={workspace.empty_hooks}",
                "clone",
                "--local",
                "--no-hardlinks",
                "--no-checkout",
                "--no-recurse-submodules",
                "--",
                str(selection.checkout),
                str(clone),
            ],
            environment=workspace.git_environment,
        )
        assert clone.is_dir() and not clone.is_symlink()
        return clone

    def configure_checkout_safety(self, clone: Path, workspace: OwnedWorkspace) -> None:
        """Disable hooks before checkout and keep all Git configuration isolated."""

        git = self._git_binary()
        self._run(
            [git, "-C", str(clone), "config", "core.hooksPath", str(workspace.empty_hooks)],
            environment=workspace.git_environment,
        )

    def checkout_exact_revision(
        self,
        clone: Path,
        revision: str,
        workspace: OwnedWorkspace,
    ) -> None:
        """Materialize only the selected commit in detached-HEAD state."""

        self._run(
            [
                self._git_binary(),
                "-C",
                str(clone),
                "-c",
                "advice.detachedHead=false",
                "checkout",
                "--detach",
                revision,
            ],
            environment=workspace.git_environment,
        )

    def remove_local_origin(self, clone: Path, workspace: OwnedWorkspace) -> None:
        """Remove the path-bearing remote created by the filesystem clone."""

        self._run(
            [
                self._git_binary(),
                "-C",
                str(clone),
                "remote",
                "remove",
                "origin",
            ],
            environment=workspace.git_environment,
        )

    def verify_clone(
        self,
        clone: Path,
        selection: SourceSelection,
        workspace: OwnedWorkspace,
    ) -> None:
        """Prove exactness, independence, cleanliness, and credential exclusion."""

        self._verify_revision_and_configuration(clone, selection, workspace)
        self._verify_independent_object_database(clone, selection, workspace)
        self._verify_no_generated_or_credential_state(clone)
        self._verify_no_source_symlink(clone, selection.checkout)

    def _verify_revision_and_configuration(
        self,
        clone: Path,
        selection: SourceSelection,
        workspace: OwnedWorkspace,
    ) -> None:
        git = self._git_binary()
        head = self._run(
            [git, "-C", str(clone), "rev-parse", "HEAD"],
            environment=workspace.git_environment,
        ).stdout.strip()
        assert head == selection.revision
        symbolic = self._run(
            [git, "-C", str(clone), "symbolic-ref", "-q", "HEAD"],
            environment=workspace.git_environment,
            check=False,
        )
        assert symbolic.returncode == 1 and not symbolic.stdout
        status_output = self._run(
            [git, "-C", str(clone), "status", "--porcelain=v1", "--untracked-files=all"],
            environment=workspace.git_environment,
        ).stdout
        assert not status_output

        remotes = self._run(
            [git, "-C", str(clone), "remote"], environment=workspace.git_environment
        ).stdout.splitlines()
        assert not remotes
        local_config = self._run(
            [git, "-C", str(clone), "config", "--local", "--list"],
            environment=workspace.git_environment,
        ).stdout
        assert str(selection.checkout) not in local_config
        assert "credential.helper" not in local_config.lower()

    def _verify_independent_object_database(
        self,
        clone: Path,
        selection: SourceSelection,
        workspace: OwnedWorkspace,
    ) -> None:
        clone_objects = clone / ".git/objects"
        assert not (clone_objects / "info/alternates").exists()
        self._run(
            [self._git_binary(), "-C", str(clone), "fsck", "--full", "--no-progress"],
            environment=workspace.git_environment,
        )

        # A local clone may otherwise hard-link every loose object and pack.
        # Comparing all common object-store files makes --no-hardlinks an
        # observed filesystem property rather than merely an argument check.
        source_objects = selection.git_directory / "objects"
        source_files = self._object_files(source_objects)
        clone_files = self._object_files(clone_objects)
        common = sorted(source_files.keys() & clone_files.keys())
        assert common, "local clone produced no comparable independent Git object files"
        for relative in common:
            source_stat = source_files[relative].stat()
            clone_stat = clone_files[relative].stat()
            assert (source_stat.st_dev, source_stat.st_ino) != (
                clone_stat.st_dev,
                clone_stat.st_ino,
            ), f"local clone object unexpectedly shares an inode: {relative}"

    def _verify_no_generated_or_credential_state(self, clone: Path) -> None:
        forbidden = (
            clone / ".venv",
            clone / "devcapsule-src/.venv",
            clone / "devcapsule-src/.nox",
            clone / "devcapsule-src/dist",
            clone / ".git-credentials",
            clone / ".netrc",
            clone / ".ssh",
            clone / ".codex",
            clone / ".claude",
            clone / ".gemini",
        )
        assert not [path for path in forbidden if path.exists() or path.is_symlink()]
        hooks = clone / ".git/hooks"
        assert not hooks.exists() or not any(hooks.iterdir())

    @staticmethod
    def _verify_no_source_symlink(clone: Path, source: Path) -> None:
        for candidate in clone.rglob("*"):
            if not candidate.is_symlink():
                continue
            resolved = candidate.resolve(strict=False)
            assert resolved != source and not resolved.is_relative_to(source), (
                f"clone contains a symlink into the source checkout: {candidate.relative_to(clone)}"
            )

    def _source_preflight(self) -> Mapping[str, Any]:
        completed = self._run(
            [
                sys.executable,
                "-m",
                "devcapsule",
                "project",
                "--path",
                str(self.source_checkout),
                "recursive-e2e",
                "preflight",
                "--json",
            ],
            environment=os.environ,
        )
        value = json.loads(completed.stdout)
        return self._mapping(value, "source preflight report")

    def _embedded_build_info(self) -> Mapping[str, Any]:
        completed = self._run([str(EMBEDDED_PEX), "version", "--json"])
        value = json.loads(completed.stdout)
        return self._mapping(value, "embedded build information")

    @staticmethod
    def _file_sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _inspect_one(
        self,
        command: Sequence[str],
        environment: Mapping[str, str],
    ) -> Mapping[str, Any]:
        value = json.loads(self._run(command, environment=environment).stdout)
        assert isinstance(value, list) and len(value) == 1, "Docker returned ambiguous inspection"
        return self._mapping(value[0], "Docker inspection")

    def _git(self, git: str, *arguments: str) -> subprocess.CompletedProcess[str]:
        return self._run([git, "-C", str(self.source_checkout), *arguments])

    @staticmethod
    def _git_binary() -> str:
        git = shutil.which("git")
        assert git is not None, "Git is required for recursive local clone"
        return git

    def _run(
        self,
        command: Sequence[str],
        *,
        environment: Mapping[str, str] | None = None,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        completed = subprocess.run(
            list(command),
            check=False,
            capture_output=True,
            text=True,
            env=dict(environment) if environment is not None else None,
        )
        if check and completed.returncode != 0:
            rendered = " ".join(self._redact(part) for part in command)
            stdout = self._redact(completed.stdout.strip())
            stderr = self._redact(completed.stderr.strip())
            pytest.fail(
                f"command failed with exit {completed.returncode}: {rendered}\n"
                f"stdout: {stdout}\nstderr: {stderr}"
            )
        return completed

    def _redact(self, value: str) -> str:
        redacted = value
        for sensitive, replacement in self._redactions.items():
            redacted = redacted.replace(sensitive, replacement)
        return redacted

    @staticmethod
    def _object_files(root: Path) -> dict[Path, Path]:
        return {
            path.relative_to(root): path
            for path in root.rglob("*")
            if path.is_file() and "info" not in path.relative_to(root).parts
        }

    @staticmethod
    def _mapping(value: object, label: str) -> Mapping[str, Any]:
        assert isinstance(value, dict), f"{label} must be an object"
        return value

    @staticmethod
    def _string(value: object, label: str) -> str:
        assert isinstance(value, str) and value, f"{label} must be a non-empty string"
        return value

    @classmethod
    def _full_revision(cls, value: object, label: str) -> str:
        selected = cls._string(value, label)
        assert FULL_REVISION.fullmatch(selected), f"{label} must be a full Git revision"
        return selected

    @classmethod
    def _full_docker_id(cls, value: object, label: str) -> str:
        selected = cls._string(value, label)
        assert FULL_DOCKER_ID.fullmatch(selected), f"{label} must be an immutable Docker ID"
        return selected


@pytest.mark.e2e
@pytest.mark.recursive_e2e
def test_local_clone_protocol_from_recursive_dogfood() -> None:
    protocol = LocalCloneProtocol(REPO_ROOT)

    # Keep the orchestration readable: each line crosses and verifies one
    # meaningful boundary instead of hiding the protocol in one giant helper.
    environment = protocol.inspect_recursive_environment()
    selection = protocol.select_clean_source()
    workspace = OwnedWorkspace.create(environment)
    try:
        clone = protocol.clone_without_checkout(selection, workspace)
        protocol.configure_checkout_safety(clone, workspace)
        protocol.checkout_exact_revision(clone, selection.revision, workspace)
        protocol.remove_local_origin(clone, workspace)
        protocol.verify_clone(clone, selection, workspace)
    finally:
        workspace.cleanup()
    assert not workspace.run_root.exists()
