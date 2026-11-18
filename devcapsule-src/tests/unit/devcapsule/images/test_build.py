"""Unit tests of ``devcapsule/images/build.py``: how the buildx builder lays out its build context.

``docker.build`` is a fake; the contexts are directories under ``tmp_path``.
"""
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from devcapsule.compat import CliError
from devcapsule.images.build import (
    BuildxImageBuilder, DirectoryComponent, FileComponent, FileGroupComponent,
    ImageBuildSpec, render_build_context,
)
from devcapsule.platforms import Platform


def test_grouped_inputs_copy_in_one_layer_and_keep_their_permissions(tmp_path: Path) -> None:
    """Many build inputs stage in one copy, preserving contents and explicit modes."""
    source = tmp_path / "source"
    source.write_bytes(b"verified artifact")
    spec = ImageBuildSpec("result:test", "base:test", (FileGroupComponent((
        FileComponent(source, "/opt/tool/.build/source.tar.gz", 0o644),
        FileComponent(source, "/opt/tool/.build/dependency.deb", 0o600),
    )),))
    context = tmp_path / "context"
    rendered = render_build_context(spec.build_plan(), context)
    dockerfile = rendered.dockerfile.read_text()
    assert dockerfile.count("COPY ") == 1
    tree = context / "file-group-0/opt/tool/.build"
    assert (tree / "source.tar.gz").read_bytes() == (tree / "dependency.deb").read_bytes() == b"verified artifact"
    assert (tree / "source.tar.gz").stat().st_mode & 0o777 == 0o644
    assert (tree / "dependency.deb").stat().st_mode & 0o777 == 0o600


def test_grouped_inputs_stage_directories_any_image_user_can_enter(tmp_path: Path) -> None:
    """Under a umask that denies group and others, every staged directory is still world-searchable,
    so an exported parent stays usable by the capsule user."""
    source = tmp_path / "source"
    source.write_bytes(b"verified artifact")
    spec = ImageBuildSpec("result:test", "base:test", (FileGroupComponent((
        FileComponent(source, "/opt/tool/.build/source.tar.gz", 0o644),
    )),))
    context = tmp_path / "context"
    # The umask is the precondition: under the usual 022 a plain mkdir already yields 0755.
    previous = os.umask(0o077)
    try:
        render_build_context(spec.build_plan(), context)
    finally:
        os.umask(previous)
    root = context / "file-group-0"
    staged = [root, root / "opt", root / "opt/tool", root / "opt/tool/.build"]
    assert [path.stat().st_mode & 0o7777 for path in staged] == [0o755] * 4


def test_grouped_inputs_refuse_two_files_at_one_destination(tmp_path: Path) -> None:
    """Two grouped inputs cannot silently replace one another at the same image path."""
    source = tmp_path / "source"
    source.write_bytes(b"input")
    spec = ImageBuildSpec("result:test", "base:test", (FileGroupComponent((
        FileComponent(source, "/opt/tool/.build/input.deb"),
        FileComponent(source, "/opt/tool/.build/input.deb"),
    )),))
    with pytest.raises(CliError, match="Invalid or repeated"):
        render_build_context(spec.build_plan(), tmp_path / "context")


@pytest.mark.parametrize("destination", ["/../escape", "/"])
def test_grouped_inputs_refuse_destinations_outside_the_staged_tree(tmp_path: Path, destination: str) -> None:
    """A grouped file cannot escape its build-context directory or overwrite its root."""
    source = tmp_path / "source"
    source.write_bytes(b"input")
    spec = ImageBuildSpec("result:test", "base:test", (FileGroupComponent((FileComponent(source, destination),)),))
    with pytest.raises(CliError, match="Invalid or repeated"):
        render_build_context(spec.build_plan(), tmp_path / "context")


def test_buildx_builder_reuses_one_context_root_and_attaches_named_contexts(tmp_path: Path) -> None:
    """BuildKit keys incremental transfer on the context root's path: the same
    root every build, directories attached as named contexts, nothing copied."""

    context_root = tmp_path / "build-contexts" / "context"
    tree = tmp_path / "tree"
    tree.mkdir()
    (tree / "big.bin").write_bytes(b"x" * 1024)
    spec = ImageBuildSpec(image="result:test", base_image="sha256:base",
                          components=(DirectoryComponent(tree, "/opt/tree"),))
    with patch("devcapsule.images.build.docker.build") as build:
        BuildxImageBuilder(context_root=context_root).build(spec, platform=Platform.LINUX_AMD64, network="none")
        (context_root / "stale-from-last-build").write_text("x")
        BuildxImageBuilder(context_root=context_root).build(spec, platform=Platform.LINUX_AMD64, network="host")
    first, second = build.call_args_list
    assert first.args[0] == context_root and second.args[0] == context_root
    assert first.kwargs["build_contexts"] == {"copy-dir-0": str(tree)}
    assert first.kwargs["network"] == "none" and first.kwargs["allow"] == []
    assert second.kwargs["allow"] == ["network.host"]
    assert sorted(child.name for child in context_root.iterdir()) == ["Dockerfile"]  # cleared each build
    assert (tmp_path / "build-contexts" / "context.lock").is_file()
    assert not (context_root / "copy-dir-0").exists()


def test_buildx_builder_without_a_root_uses_a_temporary_context(tmp_path: Path) -> None:
    """A builder without a context root builds from a temporary directory it removes afterwards."""
    with patch("devcapsule.images.build.docker.build") as build:
        BuildxImageBuilder().build(ImageBuildSpec(image="result:test", base_image="sha256:base"),
                                    platform=Platform.LINUX_AMD64, network="none")
    used_context = build.call_args.args[0]
    assert used_context.name.startswith("devcapsule-buildx-context-") and not used_context.exists()
    assert build.call_args.kwargs["build_contexts"] == {}


def test_reused_context_preserves_sources_and_recovers_after_build_failure(tmp_path: Path) -> None:
    """A failed build leaves its sources intact, and the next build in the same context starts from a cleared directory."""

    source = tmp_path / "source"
    source.mkdir()
    (source / "payload").write_text("keep")
    context = tmp_path / "context"
    context.mkdir()
    (context / "stale-link").symlink_to(source, target_is_directory=True)
    spec = ImageBuildSpec("result:test", "base:test", (DirectoryComponent(source, "/opt/tool"),))
    with patch("devcapsule.images.build.docker.build", side_effect=OSError("build failed")):
        with pytest.raises(CliError, match="build failed"):
            BuildxImageBuilder(context).build(spec, platform=Platform.LINUX_AMD64)
    with patch("devcapsule.images.build.docker.build") as build:
        BuildxImageBuilder(context).build(spec, platform=Platform.LINUX_AMD64)
    assert build.call_count == 1
    assert (source / "payload").read_text() == "keep"
    assert sorted(path.name for path in context.iterdir()) == ["Dockerfile"]
