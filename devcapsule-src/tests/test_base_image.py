from __future__ import annotations

import json
from email.message import Message
from pathlib import Path
from unittest.mock import MagicMock, Mock
import urllib.error
from zipfile import ZipFile

import pytest

from devcapsule.images.base import (
    NVIDIA_CUDA_ROOT_IMAGE,
    BaseImageBuildOptions,
    build_base_image,
    build_base_image_spec,
    verify_public_github_revision,
)
from devcapsule.build_info import BuildInfo
from devcapsule.compat import CliError
from devcapsule.images.build import render_build_context
from devcapsule.images.tooling import MAVEN_VERSION, TEMURIN_VERSION
from devcapsule.platforms import Platform

pytestmark = pytest.mark.legacy


def pex_fixture(
    path: Path,
    *,
    revision: str = "a" * 40,
    public: bool = True,
    build_mnemonic: str = "v026",
) -> Path:
    repository = "https://github.com/example/devcapsule" if public else "unknown"
    source_url = f"{repository}/commit/{revision}" if public else "unknown"
    with ZipFile(path, "w") as archive:
        archive.writestr(
            ".deps/devcapsule-0.1.0-py3-none-any.whl/devcapsule/_build_info.json",
            json.dumps(
                {
                    "schema_version": 2,
                    "version": "0.1.0",
                    "build_mnemonic": build_mnemonic,
                    "source_repository": repository,
                    "source_revision": revision,
                    "source_url": source_url,
                }
            ),
        )
    return path


def test_base_image_exports_independent_tooling_without_runtime(tmp_path: Path) -> None:
    pex = pex_fixture(tmp_path / "devcapsule.pex")
    options = BaseImageBuildOptions(pex, "test-base:latest", source_revision="a" * 40)

    plan = build_base_image_spec(options).build_plan()
    context = tmp_path / "context"
    context.mkdir()
    dockerfile = render_build_context(plan, context).dockerfile.read_text(encoding="utf-8")

    assert plan.base_image == "ubuntu:24.04"
    assert "python3" in plan.apt_packages
    assert "tini" in plan.apt_packages
    assert "gosu" in plan.apt_packages
    assert "/opt/pycharm" not in dockerfile
    assert "JetBrains" not in dockerfile
    assert "nodejs.org/dist/${node_version}" in dockerfile
    assert ("JAVA_HOME", "/opt/java/current") in plan.env
    assert ("MAVEN_HOME", "/opt/maven/current") in plan.env
    assert (
        "PATH",
        "/opt/maven/current/bin:/opt/java/current/bin:/opt/node/current/bin:${PATH}",
    ) in plan.env
    assert "downloads.claude.ai/claude-code-releases" not in dockerfile
    assert "adoptium/temurin25-binaries" in dockerfile
    assert "downloads.apache.org/maven" in dockerfile
    assert "@google/gemini-cli" not in dockerfile
    assert "gemini --version" not in dockerfile
    # The base carries no boot contract (owner ruling 2026-09-05): every
    # formation's materialization recipe sets its own ENTRYPOINT/CMD.
    assert "ENTRYPOINT" not in dockerfile
    assert "CMD" not in dockerfile
    assert ("devcapsule.image.managed", "true") in plan.labels
    assert ("devcapsule.metadata.version", "1") in plan.labels
    assert ("devcapsule.image.kind", "base") in plan.labels
    assert ("devcapsule.image.canonical-name", "test-base:latest") in plan.labels
    assert ("devcapsule.base.recipe", "ubuntu-24.04") in plan.labels
    assert ("devcapsule.base.recipe-version", "11") in plan.labels
    # Recipe 10 installs the web console from the runtime's own verified
    # revision, as an independently cached contribution (R-CONSOLE-001);
    # recipe 11 rebuilds it with the monitor's dependency.
    webconsole = next(stage for stage in plan.stages if stage.name == "webconsole")
    assert webconsole.exports == ("/opt/devcapsule-webconsole",)
    (install,) = webconsole.plan.exec_steps
    script = install.args[-1]
    assert 'git -C "$checkout" fetch -q --depth 1 "$source_repository" "$source_revision"' in script
    assert 'source_repository=https://github.com/example/devcapsule' in script
    assert f'source_revision={"a" * 40}' in script
    assert 'test "$(git -C "$checkout" rev-parse HEAD)" = "$source_revision"' in script
    assert "--require-hashes -r \"$subproject/requirements.txt\"" in script
    assert "--require-hashes -r \"$subproject/requirements-build.txt\"" in script
    assert "--no-deps --no-build-isolation \"$subproject\"" in script
    assert "python3 -m venv \"/opt/devcapsule-webconsole/venv\"" in script
    assert ("devcapsule.base.webconsole", "/opt/devcapsule-webconsole") in plan.labels
    # Recipe 8 ships the contained display stack and says so, which is how
    # the launcher decides the capsule needs no host X session; recipe 9
    # adds the panel.
    for package in ("tigervnc-standalone-server", "xfonts-base", "novnc", "python3-websockify", "openbox", "tint2"):
        assert package in plan.apt_packages
    assert ("devcapsule.base.display", "contained") in plan.labels
    # Recipe 5 adds the redistributable PostgreSQL client so projects can
    # declare the postgresql-client component instead of acquiring a client.
    assert "postgresql-client" in plan.apt_packages
    assert ("devcapsule.component.postgresql-client.license", "PostgreSQL") in plan.labels
    assert ("devcapsule.base.recipe-status", "ready") in plan.labels
    assert not plan.files
    assert ("devcapsule.base.runtime", "launcher-supplied") in plan.labels
    assert not any(key.startswith("devcapsule.pex.") for key, _value in plan.labels)
    assert ("devcapsule.source.repository", "https://github.com/example/devcapsule") in plan.labels
    assert ("devcapsule.source.revision", "a" * 40) in plan.labels
    assert (
        "devcapsule.source.url",
        f"https://github.com/example/devcapsule/commit/{'a' * 40}",
    ) in plan.labels
    assert ("org.opencontainers.image.source", "https://github.com/example/devcapsule") in plan.labels
    assert ("org.opencontainers.image.revision", "a" * 40) in plan.labels
    assert ("org.opencontainers.image.version", "v026") in plan.labels
    assert ("devcapsule.component.temurin.version", TEMURIN_VERSION) in plan.labels
    assert ("devcapsule.component.maven.version", MAVEN_VERSION) in plan.labels
    assert (
        "devcapsule.component.temurin.license",
        "GPL-2.0-with-classpath-exception",
    ) in plan.labels
    assert ("devcapsule.component.maven.license", "Apache-2.0") in plan.labels


def test_nvidia_cuda_recipe_keeps_developer_baseline_and_is_marked_wip(tmp_path: Path) -> None:
    pex = pex_fixture(tmp_path / "devcapsule.pex")
    options = BaseImageBuildOptions(
        pex, "test-cuda-base:latest", source_revision="a" * 40, recipe="nvidia-cuda-devel"
    )

    plan = build_base_image_spec(options).build_plan()

    assert plan.base_image == NVIDIA_CUDA_ROOT_IMAGE
    assert "python3" in plan.apt_packages
    assert "gdb" in plan.apt_packages
    assert "tini" in plan.apt_packages
    install_script = "\n".join(" ".join(step.args) for step in plan.exec_steps)
    assert "@google/gemini-cli" not in install_script
    assert ("devcapsule.base.recipe", "nvidia-cuda-devel") in plan.labels
    assert ("devcapsule.base.recipe-status", "wip") in plan.labels
    assert ("devcapsule.base.gpu.vendor", "nvidia") in plan.labels
    assert ("devcapsule.base.cuda.version", "12.8.1") in plan.labels


def test_recipe_root_image_can_be_overridden(tmp_path: Path) -> None:
    pex = pex_fixture(tmp_path / "devcapsule.pex")
    options = BaseImageBuildOptions(
        pex,
        "test-cuda-base:latest",
        root_image="local/cuda:test",
        source_revision="a" * 40,
        recipe="nvidia-cuda-devel",
    )

    plan = build_base_image_spec(options).build_plan()

    assert plan.base_image == "local/cuda:test"
    assert ("devcapsule.base.recipe", "nvidia-cuda-devel") in plan.labels


def test_base_image_build_forwards_host_network_to_buildx(tmp_path: Path) -> None:
    pex = pex_fixture(tmp_path / "devcapsule.pex")
    options = BaseImageBuildOptions(pex, "test-base:latest", source_revision="a" * 40)
    builder = Mock()
    source_verifier = Mock()

    build_base_image(options, builder=builder, platform=Platform.LINUX_AMD64, network="host",
                     source_verifier=source_verifier)

    source_verifier.assert_called_once()
    builder.build.assert_called_once()
    assert builder.build.call_args.args[0].image == "test-base:latest"
    assert builder.build.call_args.kwargs == {"network": "host", "platform": Platform.LINUX_AMD64}


def test_base_image_rejects_unreachable_revision_before_buildx(tmp_path: Path) -> None:
    pex = pex_fixture(tmp_path / "devcapsule.pex")
    options = BaseImageBuildOptions(pex, "test-base:latest", source_revision="a" * 40)
    builder = Mock()
    source_verifier = Mock(side_effect=CliError("source revision is not publicly reachable"))

    with pytest.raises(CliError, match="not publicly reachable"):
        build_base_image(options, builder=builder, platform=Platform.LINUX_AMD64, source_verifier=source_verifier)

    builder.build.assert_not_called()


def test_base_image_rejects_revision_that_disagrees_with_pex(tmp_path: Path) -> None:
    pex = pex_fixture(tmp_path / "devcapsule.pex")
    options = BaseImageBuildOptions(pex, source_revision="b" * 40)

    with pytest.raises(CliError, match="devcapsule-local.pex"):
        build_base_image_spec(options)


def test_base_image_requires_explicit_source_revision_by_default(tmp_path: Path) -> None:
    pex = pex_fixture(tmp_path / "devcapsule.pex")

    with pytest.raises(CliError, match="--source-revision is required"):
        build_base_image_spec(BaseImageBuildOptions(pex))


def test_base_image_requires_public_pex_revision_by_default(tmp_path: Path) -> None:
    pex = pex_fixture(tmp_path / "devcapsule.pex", revision="unknown", public=False)
    options = BaseImageBuildOptions(pex, source_revision="unknown")

    with pytest.raises(CliError, match="does not embed a full public GitHub revision"):
        build_base_image_spec(options)


def test_base_without_baseline_allows_explicit_local_source_escape_hatch(tmp_path: Path) -> None:
    pex = pex_fixture(
        tmp_path / "devcapsule.pex",
        revision="unknown",
        public=False,
        build_mnemonic="local-v026",
    )
    plan = build_base_image_spec(BaseImageBuildOptions(pex, allow_local_source=True, install_baseline=False)).build_plan()

    assert ("devcapsule.source.revision", "unknown") in plan.labels
    assert ("org.opencontainers.image.version", "local-v026") in plan.labels
    assert not any(stage.name == "webconsole" for stage in plan.stages)
    assert not any(key == "devcapsule.base.webconsole" for key, _ in plan.labels)


def test_console_base_rejects_missing_source_before_starting_the_builder(tmp_path: Path) -> None:
    pex = pex_fixture(tmp_path / "devcapsule.pex", revision="unknown", public=False)
    builder = Mock()
    with pytest.raises(CliError, match="--allow-local-source cannot supply the console source"):
        build_base_image(BaseImageBuildOptions(pex, allow_local_source=True), builder=builder,
                         platform=Platform.LINUX_AMD64)
    builder.build.assert_not_called()


def test_base_image_local_source_escape_hatch_skips_public_verification(tmp_path: Path) -> None:
    pex = pex_fixture(tmp_path / "devcapsule.pex")
    builder = Mock()
    source_verifier = Mock()

    build_base_image(
        BaseImageBuildOptions(pex, allow_local_source=True),
        builder=builder,
        platform=Platform.LINUX_AMD64,
        source_verifier=source_verifier,
    )

    source_verifier.assert_not_called()
    builder.build.assert_called_once()


def test_public_revision_verification_checks_exact_commit_url(monkeypatch: pytest.MonkeyPatch) -> None:
    info = BuildInfo(
        schema_version=1,
        version="0.1.0",
        source_repository="https://github.com/example/devcapsule",
        source_revision="a" * 40,
        source_url=f"https://github.com/example/devcapsule/commit/{'a' * 40}",
    )
    response = MagicMock()
    response.status = 200
    response.__enter__.return_value = response
    urlopen = Mock(return_value=response)
    monkeypatch.setattr("devcapsule.images.base.urllib.request.urlopen", urlopen)

    verify_public_github_revision(info)

    request = urlopen.call_args.args[0]
    assert request.full_url == info.source_url
    assert request.get_method() == "HEAD"


def test_public_revision_verification_rejects_missing_commit(monkeypatch: pytest.MonkeyPatch) -> None:
    info = BuildInfo(
        schema_version=1,
        version="0.1.0",
        source_repository="https://github.com/example/devcapsule",
        source_revision="b" * 40,
        source_url=f"https://github.com/example/devcapsule/commit/{'b' * 40}",
    )
    urlopen = Mock(
        side_effect=urllib.error.HTTPError(
            info.source_url, 404, "Not Found", hdrs=Message(), fp=None
        )
    )
    monkeypatch.setattr("devcapsule.images.base.urllib.request.urlopen", urlopen)

    with pytest.raises(CliError, match=r"not publicly reachable.*HTTP 404"):
        verify_public_github_revision(info)
