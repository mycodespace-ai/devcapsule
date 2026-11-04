from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from devcapsule.compat import CliError
from devcapsule.launch.pycharm._image_build import (
    PycharmImageBuildOptions,
    build_pycharm_image_spec,
    parse_pycharm_build_options,
)
from devcapsule.images.build import BuildxImageBuilder, ImageBuildSpec, normalize_pycharm_source, render_build_context
from devcapsule.platforms import Platform

pytestmark = pytest.mark.legacy


def test_parse_pycharm_build_options_rejects_missing_source(tmp_path: Path) -> None:
    with pytest.raises(CliError, match="does not exist"):
        parse_pycharm_build_options(
            pycharm=tmp_path / "missing.tar.gz",
            image="pycharm-isolated:latest",
            base_image="ubuntu:24.04",
            network="default",
            extra_apt_packages=(),
        )


def test_parse_pycharm_build_options_accepts_host_network(tmp_path: Path) -> None:
    source = tmp_path / "pycharm"
    source.mkdir()

    options = parse_pycharm_build_options(
        pycharm=source,
        image="pycharm-isolated:latest",
        base_image="ubuntu:24.04",
        network="host",
        extra_apt_packages=(),
    )

    assert options.network == "host"


def test_build_pycharm_image_spec_includes_runtime_assets_and_node_tooling(tmp_path: Path) -> None:
    source = tmp_path / "pycharm"
    source.mkdir()
    assets = tmp_path / "assets"
    (assets / "image-assets").mkdir(parents=True)
    for filename in ("entrypoint.sh", "bootstrap-project.sh", "check-runtime-deps.sh"):
        (assets / filename).write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    (assets / "image-assets" / "vibe-coding-process.md").write_text("vibe\n", encoding="utf-8")

    spec = build_pycharm_image_spec(
        PycharmImageBuildOptions(
            pycharm=source,
            image="example:latest",
            base_image="ubuntu:24.04",
            network="default",
            extra_apt_packages=("rsync",),
        ),
        pycharm_root=source,
        assets_root=assets,
    )
    plan = spec.build_plan()

    assert plan.base_image == "ubuntu:24.04"
    assert plan.image == "example:latest"
    assert "rsync" in plan.apt_packages
    assert any(copy.destination == "/opt/pycharm" and copy.source == source for copy in plan.directories)
    assert any(copy.destination == "/usr/local/bin/entrypoint.sh" for copy in plan.files)
    assert plan.entrypoint == ("/usr/bin/tini", "--", "/usr/local/bin/entrypoint.sh")
    assert ("devcapsule.builder", "python-on-whales") in plan.labels
    install_script = "\n".join(" ".join(step.args) for step in plan.exec_steps)
    assert "nodejs.org/dist/${node_version}" in install_script
    assert 'export PATH="/opt/node/current/bin:$PATH"' in install_script
    assert "@google/gemini-cli" not in install_script
    assert "SHASUMS256.txt" in install_script
    assert "gemini --version" not in install_script
    assert ( "PATH", "/opt/node/current/bin:${PATH}") in plan.env


def test_normalize_pycharm_source_requires_executable_launcher(tmp_path: Path) -> None:
    source = tmp_path / "pycharm"
    (source / "bin").mkdir(parents=True)
    launcher = source / "bin" / "pycharm.sh"
    launcher.write_text("#!/usr/bin/env bash\n", encoding="utf-8")

    with pytest.raises(CliError, match="executable bin/pycharm.sh"):
        normalize_pycharm_source(source, tmp_path / "work")


def test_render_build_context_includes_network_host_compatible_dockerfile_content(tmp_path: Path) -> None:
    source = tmp_path / "pycharm"
    source.mkdir()
    assets = tmp_path / "assets"
    (assets / "image-assets").mkdir(parents=True)
    for filename in ("entrypoint.sh", "bootstrap-project.sh", "check-runtime-deps.sh"):
        (assets / filename).write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    (assets / "image-assets" / "vibe-coding-process.md").write_text("vibe\n", encoding="utf-8")

    spec = build_pycharm_image_spec(
        PycharmImageBuildOptions(
            pycharm=source,
            image="example:latest",
            base_image="ubuntu:24.04",
            network="host",
            extra_apt_packages=("rsync",),
        ),
        pycharm_root=source,
        assets_root=assets,
    )

    rendered = render_build_context(spec.build_plan(), tmp_path / "context")
    dockerfile = rendered.dockerfile.read_text(encoding="utf-8")

    assert dockerfile.startswith("# syntax=docker/dockerfile:1\n")
    assert "FROM ubuntu:24.04" in dockerfile
    # The IDE tree is a named context read in place, never copied into the context root.
    assert "COPY --from=copy-dir-0 / /opt/pycharm/" in dockerfile
    assert rendered.named_contexts["copy-dir-0"] == source
    assert rendered.build_context_arguments() == [f"--build-context=copy-dir-0={source}"]
    assert not any(child.name.startswith("copy-dir") for child in (tmp_path / "context").iterdir())
    assert 'LABEL devcapsule.builder="python-on-whales"' in dockerfile
    assert 'ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/entrypoint.sh"]' in dockerfile


def test_buildx_builder_reuses_one_context_root_and_attaches_named_contexts(tmp_path: Path) -> None:
    """BuildKit keys incremental transfer on the context root's path: the same
    root every build, directories attached as named contexts, nothing copied."""
    from devcapsule.images.build import DirectoryComponent

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
    with patch("devcapsule.images.build.docker.build") as build:
        BuildxImageBuilder().build(ImageBuildSpec(image="result:test", base_image="sha256:base"),
                                    platform=Platform.LINUX_AMD64, network="none")
    used_context = build.call_args.args[0]
    assert used_context.name.startswith("devcapsule-buildx-context-") and not used_context.exists()
    assert build.call_args.kwargs["build_contexts"] == {}


def test_named_contexts_preserve_distinct_contribution_inputs(tmp_path: Path) -> None:
    from devcapsule.images.build import ContributionComponent, DirectoryComponent

    first, second = tmp_path / "first", tmp_path / "second"
    first.mkdir()
    second.mkdir()
    (first / "payload").write_bytes(b"first")
    (second / "payload").write_bytes(b"second")
    contributions = (
        ContributionComponent("ide", (DirectoryComponent(first, "/opt/ide"),), ("/opt/ide",)),
        ContributionComponent("tool", (DirectoryComponent(second, "/opt/tool"),), ("/opt/tool",)),
    )
    for order in (contributions, tuple(reversed(contributions))):
        spec = ImageBuildSpec("result:test", "base:test", order)
        rendered = render_build_context(spec.build_plan(), tmp_path / "context")
        assert rendered.named_contexts == {"ide-copy-dir-0": first, "tool-copy-dir-0": second}
        dockerfile = rendered.dockerfile.read_text()
        assert "COPY --from=ide-copy-dir-0 / /opt/ide/" in dockerfile
        assert "COPY --from=tool-copy-dir-0 / /opt/tool/" in dockerfile
        assert "COPY --link --from=ide /opt/ide /opt/ide" in dockerfile
        assert "COPY --link --from=tool /opt/tool /opt/tool" in dockerfile
    assert (first / "payload").read_bytes() == b"first"
    assert (second / "payload").read_bytes() == b"second"


def test_reused_context_preserves_sources_and_recovers_after_build_failure(tmp_path: Path) -> None:
    from devcapsule.images.build import DirectoryComponent

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
