"""Unit tests of ``devcapsule/materialization.py``: artifact acquisition, lock parsing, formation descriptors, and image materialization."""

from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import tarfile
from zipfile import ZipFile

import pytest

from devcapsule.compat import CliError
from devcapsule.components import LockedArtifactDeclaration
from devcapsule.images.build import ExecStep, ImageBuildSpec
from devcapsule.materialization import (
    ENTRYPOINT_CONTRACT,
    RUNTIME_PLAN_PATH,
    UNPACKED_DIRECTORY,
    UNPACKED_MARKER,
    ArtifactSpec,
    ImageDetails,
    acquire_artifact,
    canonical_image_name,
    canonical_json,
    component_runtime_template,
    descriptor_differences,
    ensure_materialized_surface,
    formation_descriptor,
    formation_identity,
    npm_install_step,
    parse_locked_environment,
    sha256_file,
    surface_materialization_spec,
    validate_base_image,
    verify_materialized_image,
)
from devcapsule.webconsole_bundle import BUNDLE_RESOURCE_NAME, LAUNCHER_WEBCONSOLE_PATH, build_webconsole_bundle


def fixture_archive(path: Path) -> bytes:
    content = b"#!/bin/sh\n"
    with tarfile.open(path, "w:gz") as archive:
        info = tarfile.TarInfo("pycharm-test/bin/pycharm.sh")
        info.mode = 0o755
        info.size = len(content)
        archive.addfile(info, io.BytesIO(content))
    return path.read_bytes()


def member_archive(path: Path, member: str) -> bytes:
    content = b"tool-binary-fixture"
    with tarfile.open(path, "w:gz") as archive:
        info = tarfile.TarInfo(member)
        info.mode = 0o755
        info.size = len(content)
        archive.addfile(info, io.BytesIO(content))
    return path.read_bytes()


def codium_fixture_archive(path: Path) -> bytes:
    with tarfile.open(path, "w:gz") as archive:
        for member, content in (
            ("./codium", b"electron-binary-fixture"),
            ("./bin/codium", b"#!/bin/sh\n"),
            ("./chrome-sandbox", b"sandbox-helper-fixture"),
            ("./product.json", b"{}\n"),
        ):
            info = tarfile.TarInfo(member)
            info.mode = 0o755
            info.size = len(content)
            archive.addfile(info, io.BytesIO(content))
    return path.read_bytes()


def artifact(path: Path, digest: str = "a" * 64) -> ArtifactSpec:
    return ArtifactSpec("2099.1.0", path.as_uri(), digest, "professional")


def codium_artifact(path: Path, digest: str = "b" * 64) -> ArtifactSpec:
    return ArtifactSpec("1.99.0", path.as_uri(), digest, None)


def image_details(reference: str, labels: dict[str, str], identity: str = "sha256:image") -> ImageDetails:
    return ImageDetails(reference, identity, labels, "linux", "amd64")


def expected_labels(base_identity: str, spec: ArtifactSpec) -> tuple[str, dict[str, str]]:
    descriptor = formation_descriptor(platform="linux-amd64", base_identity=base_identity, artifact=spec)
    canonical = canonical_image_name(descriptor)
    labels = {
        "devcapsule.image.managed": "true",
        "devcapsule.metadata.version": "1",
        "devcapsule.image.kind": "materialized",
        "devcapsule.image.canonical-name": canonical,
        "devcapsule.materialization.descriptor": canonical_json(descriptor),
        "devcapsule.materialization.identity": formation_identity(descriptor),
        "devcapsule.materialization.recipe-version": "1",
        "devcapsule.materialization.base-identity": base_identity,
        "devcapsule.component.id": "pycharm",
        "devcapsule.component.version": spec.version,
        "devcapsule.component.sha256": spec.sha256,
    }
    return canonical, labels


def codex_npm_declarations(tmp_path: Path) -> tuple[LockedArtifactDeclaration, LockedArtifactDeclaration]:
    meta_source = tmp_path / "codex-1.0.0.tgz"
    meta_source.write_bytes(b"meta-package-tarball")
    platform_source = tmp_path / "codex-1.0.0-linux-x64.tgz"
    platform_source.write_bytes(b"platform-package-tarball")
    return (
        LockedArtifactDeclaration(
            component_id="codex",
            version="1.0.0",
            url=meta_source.as_uri(),
            sha256=hashlib.sha256(meta_source.read_bytes()).hexdigest(),
            destination="/opt/codex/1.0.0",
            artifact_format="npm-package",
            npm_package="@openai/codex",
            permissions=0o644,
            environment=(("PATH", "/opt/codex/1.0.0/node_modules/.bin:${PATH}"),),
        ),
        LockedArtifactDeclaration(
            component_id="codex",
            version="1.0.0",
            url=platform_source.as_uri(),
            sha256=hashlib.sha256(platform_source.read_bytes()).hexdigest(),
            destination="/opt/codex/1.0.0",
            artifact_format="npm-package",
            npm_package="@openai/codex-linux-x64",
            permissions=0o644,
        ),
    )


def test_acquire_artifact_verifies_digest_and_reuses_cached_copy(tmp_path: Path) -> None:
    """``acquire_artifact`` downloads on cache miss, verifies SHA-256, and reuses the cached file on repeat calls."""
    source = tmp_path / "source.tar.gz"
    payload = fixture_archive(source)
    spec = artifact(source, hashlib.sha256(payload).hexdigest())

    first = acquire_artifact(spec, tmp_path / "cache")
    second = acquire_artifact(spec, tmp_path / "cache")

    assert first.downloaded is True
    assert second.downloaded is False
    assert second.path == first.path
    assert (tmp_path / "cache" / "locks" / "artifacts" / f"{spec.sha256}.lock").is_file()


def test_acquire_artifact_rejects_digest_mismatch(tmp_path: Path) -> None:
    """``acquire_artifact`` raises ``CliError`` when the downloaded payload's SHA-256 differs from ``spec.sha256``."""
    source = tmp_path / "source.tar.gz"
    fixture_archive(source)
    spec = artifact(source, "0" * 64)

    with pytest.raises(CliError, match="digest mismatch"):
        acquire_artifact(spec, tmp_path / "cache")


def test_formation_descriptor_is_canonical_and_excludes_checkout_data(tmp_path: Path) -> None:
    """``formation_descriptor`` serializes deterministically and excludes checkout paths, home paths, and UIDs."""
    spec = artifact(tmp_path / "unused.tar.gz")

    descriptor = formation_descriptor(platform="linux-amd64", base_identity="sha256:base", artifact=spec)

    assert descriptor["schema"] == {"name": "devcapsule-formation", "version": 1}
    assert descriptor["base"] == {"identity": "sha256:base"}
    assert descriptor["components"][0]["artifact"]["sha256"] == "a" * 64
    encoded = canonical_json(descriptor)
    assert json.loads(encoded) == descriptor
    assert "/workspace" not in encoded
    assert "/home/devcapsule" not in encoded
    assert "uid" not in encoded
    assert len(formation_identity(descriptor)) == 64


def test_component_runtime_template_declares_persistence_slots() -> None:
    """``component_runtime_template`` places durable ``config``, cache ``system``, and home-overlay ``cache`` under ``persistence``."""
    template = component_runtime_template()
    persistence = template["component"]["persistence"]
    slots = {slot["name"]: slot for slot in persistence["state_slots"]}

    assert persistence["home"] == "required"
    assert persistence["xdg"] == "home-relative"
    assert "state_slots" not in template
    assert slots["config"]["kind"] == "durable"
    assert slots["system"]["kind"] == "cache"
    assert slots["cache"]["home_overlay"] is True


def test_codium_formation_descriptor_omits_variant_and_names_vscode_recipe(tmp_path: Path) -> None:
    """For ``codium``, ``formation_descriptor`` omits ``variant`` and records ``vscode-local-materialization`` at ``/opt/codium``."""
    descriptor = formation_descriptor(
        platform="linux-amd64",
        base_identity="sha256:base",
        artifact=codium_artifact(tmp_path / "unused.tar.gz"),
        recipe_id="vscode-local-materialization",
        component_id="codium",
    )

    assert descriptor["components"][0]["id"] == "codium"
    assert "variant" not in descriptor["components"][0]
    assert descriptor["recipe"]["id"] == "vscode-local-materialization"
    assert descriptor["recipe"]["parameters"] == {"installation-path": "/opt/codium"}


def test_codium_materialization_builds_image_without_setuid_sandbox(tmp_path: Path) -> None:
    """Recipe-2 ``codium`` materialization copies ``/opt/codium`` without ``chmod 4755`` and stamps ``codium`` labels."""
    source = tmp_path / "codium.tar.gz"
    payload = codium_fixture_archive(source)
    spec = codium_artifact(source, hashlib.sha256(payload).hexdigest())
    built: dict[str, ImageDetails] = {}

    def build(build_spec: ImageBuildSpec) -> None:
        plan = build_spec.build_plan()
        assert any(copy.destination == "/opt/codium" for stage in plan.stages for copy in stage.plan.directories)
        assert not any("chmod" in step.args and "4755" in step.args for step in plan.exec_steps)
        labels = dict(plan.labels)
        assert labels["devcapsule.component.id"] == "codium"
        assert labels["devcapsule.component.vscode.version"] == "1.99.0"
        assert labels["devcapsule.materialization.recipe-version"] == "2"
        assert "devcapsule.component.variant" not in labels
        built[plan.image] = image_details(plan.image, labels)

    image, created = ensure_materialized_surface(
        base_reference="base:debug",
        base_identity="sha256:base",
        platform="linux-amd64",
        artifact=spec,
        cache_root=tmp_path / "cache",
        inspect_image=built.get,
        build=build,
        recipe_id="vscode-local-materialization",
        recipe_version="2",
        component_id="codium",
    )

    assert created is True
    assert image.startswith("devcapsule-local-codium:")


def test_codium_materialization_rejects_archive_missing_codium_layout(tmp_path: Path) -> None:
    """``ensure_materialized_surface`` refuses a ``codium`` archive that lacks the expected VSCodium layout."""
    source = tmp_path / "codium.tar.gz"
    payload = fixture_archive(source)
    spec = codium_artifact(source, hashlib.sha256(payload).hexdigest())

    with pytest.raises(CliError, match="does not contain codium"):
        ensure_materialized_surface(
            base_reference="base:debug",
            base_identity="sha256:base",
            platform="linux-amd64",
            artifact=spec,
            cache_root=tmp_path / "cache",
            inspect_image=lambda _reference: None,
            build=lambda _spec: None,
            recipe_id="vscode-local-materialization",
            component_id="codium",
        )


def test_parse_locked_environment_reads_codium_lock_without_variant() -> None:
    """``parse_locked_environment`` accepts a recipe-2 ``codium`` lock with no ``variant``."""
    locked = parse_locked_environment(
        {
            "platform": "linux-amd64",
            "base": {"reference": "docker.io/example/base@sha256:abc"},
            "components": {
                "interactive-surface": "codium",
                "codium": {
                    "version": "1.99.0",
                    "delivery-policy": "local-materialization",
                    "url": "https://example.invalid/codium.tar.gz",
                    "sha256": "b" * 64,
                },
            },
            "materialization": {
                "recipe": "vscode-local-materialization",
                "recipe-version": "2",
            },
        }
    )

    assert locked.component_id == "codium"
    assert locked.artifact.variant is None
    assert locked.recipe_id == "vscode-local-materialization"


def test_parse_locked_environment_rejects_jetbrains_recipe_for_codium() -> None:
    """``parse_locked_environment`` refuses a ``codium`` lock paired with ``jetbrains-local-materialization``."""
    with pytest.raises(CliError, match="vscode-local-materialization"):
        parse_locked_environment(
            {
                "platform": "linux-amd64",
                "base": {"reference": "docker.io/example/base@sha256:abc"},
                "components": {
                    "interactive-surface": "codium",
                    "codium": {
                        "version": "1.99.0",
                        "delivery-policy": "local-materialization",
                        "url": "https://example.invalid/codium.tar.gz",
                        "sha256": "b" * 64,
                    },
                },
                "materialization": {
                    "recipe": "jetbrains-local-materialization",
                    "recipe-version": "1",
                },
            }
        )


def test_parse_locked_environment_rejects_obsolete_codium_recipe_version() -> None:
    """``parse_locked_environment`` refuses a recipe-1 ``codium`` lock and names ``'vscode-local-materialization'@2``."""
    with pytest.raises(CliError, match="'vscode-local-materialization'@2"):
        parse_locked_environment(
            {
                "platform": "linux-amd64",
                "base": {"reference": "docker.io/example/base@sha256:abc"},
                "components": {
                    "interactive-surface": "codium",
                    "codium": {
                        "version": "1.99.0",
                        "delivery-policy": "local-materialization",
                        "url": "https://example.invalid/codium.tar.gz",
                        "sha256": "b" * 64,
                    },
                },
                "materialization": {
                    "recipe": "vscode-local-materialization",
                    "recipe-version": "1",
                },
            }
        )


def test_materialization_reuses_verified_canonical_image_without_rebuilding(tmp_path: Path) -> None:
    """When the canonical image already carries matching formation labels, ``ensure_materialized_surface`` reuses it."""
    spec = artifact(tmp_path / "missing.tar.gz")
    canonical, labels = expected_labels("sha256:base", spec)
    builds: list[object] = []

    image, created = ensure_materialized_surface(
        base_reference="base:debug",
        base_identity="sha256:base",
        platform="linux-amd64",
        artifact=spec,
        cache_root=tmp_path / "cache",
        inspect_image=lambda reference: image_details(reference, labels) if reference == canonical else None,
        build=builds.append,
    )

    assert image == canonical
    assert created is False
    assert builds == []


def test_materialization_rejects_canonical_tag_with_conflicting_labels(tmp_path: Path) -> None:
    """``ensure_materialized_surface`` raises ``CliError`` when an existing canonical image has mismatched metadata."""
    spec = artifact(tmp_path / "missing.tar.gz")
    canonical, labels = expected_labels("sha256:base", spec)
    labels["devcapsule.component.sha256"] = "b" * 64

    with pytest.raises(CliError, match="conflicting or malformed metadata"):
        ensure_materialized_surface(
            base_reference="base:debug",
            base_identity="sha256:base",
            platform="linux-amd64",
            artifact=spec,
            cache_root=tmp_path / "cache",
            inspect_image=lambda reference: image_details(reference, labels) if reference == canonical else None,
            build=lambda _spec: None,
        )


def test_materialization_builds_from_verified_archive_and_rechecks_built_image(tmp_path: Path) -> None:
    """On cache miss, ``ensure_materialized_surface`` unpacks the verified archive, builds the image, and verifies labels."""
    source = tmp_path / "pycharm.tar.gz"
    payload = fixture_archive(source)
    spec = artifact(source, hashlib.sha256(payload).hexdigest())
    built: dict[str, ImageDetails] = {}

    def build(build_spec: ImageBuildSpec) -> None:
        plan = build_spec.build_plan()
        built[plan.image] = image_details(plan.image, dict(plan.labels))
        assert plan.base_image == "base:debug"
        assert any(copy.destination == "/opt/jetbrains/pycharm" for stage in plan.stages for copy in stage.plan.directories)
        assert any(copy.destination == "/etc/devcapsule/component-runtime-template.json" for copy in plan.files)
        assert not any(copy.destination == "/etc/devcapsule/runtime-plan.json" for copy in plan.files)

    image, created = ensure_materialized_surface(
        base_reference="base:debug",
        base_identity="sha256:base",
        platform="linux-amd64",
        artifact=spec,
        cache_root=tmp_path / "cache",
        inspect_image=built.get,
        build=build,
    )

    assert created is True
    assert image in built
    assert (tmp_path / "cache" / "locks" / "materializations").is_dir()


def test_materialization_extracts_locked_tar_gz_member(tmp_path: Path) -> None:
    """A ``tar-gz-member`` ancillary artifact is extracted on the host and copied executable into its stage."""
    pycharm_source = tmp_path / "pycharm.tar.gz"
    pycharm_spec = artifact(pycharm_source, hashlib.sha256(fixture_archive(pycharm_source)).hexdigest())
    member = "antigravity"
    tool_source = tmp_path / "antigravity.tar.gz"
    tool_payload = member_archive(tool_source, member)
    tool = LockedArtifactDeclaration(
        component_id="antigravity-cli",
        version="1.0.0",
        url=tool_source.as_uri(),
        sha256=hashlib.sha256(tool_payload).hexdigest(),
        archive_member=member,
        destination="/opt/antigravity-cli/bin/antigravity",
    )
    built: dict[str, ImageDetails] = {}

    def build(build_spec: ImageBuildSpec) -> None:
        plan = build_spec.build_plan()
        copied = next(
            copy for stage in plan.stages for copy in stage.plan.files
            if copy.destination == "/opt/antigravity-cli/bin/antigravity"
        )
        assert copied.source.read_bytes() == b"tool-binary-fixture"
        assert copied.permissions == 0o755
        assert not any("tar" in step.args for step in plan.exec_steps)
        built[plan.image] = image_details(plan.image, dict(plan.labels))

    image, created = ensure_materialized_surface(
        base_reference="base:debug",
        base_identity="sha256:base",
        platform="linux-amd64",
        artifact=pycharm_spec,
        ancillary_artifacts=(tool,),
        cache_root=tmp_path / "cache",
        inspect_image=built.get,
        build=build,
    )

    assert created is True
    descriptor = json.loads(built[image].labels["devcapsule.materialization.descriptor"])
    assert descriptor["components"][1]["id"] == "antigravity-cli"
    assert descriptor["components"][1]["artifact"]["sha256"] == tool.sha256
    assert descriptor["components"][1]["installation"] == {
        "archive-member": member,
        "destination": "/opt/antigravity-cli/bin/antigravity",
        "format": "tar-gz-member",
    }


def test_materialization_installs_npm_packages_offline_with_generated_manifest(tmp_path: Path) -> None:
    """``npm-package`` artifacts copy tarballs plus ``package.json`` and run one offline ``npm install`` step."""
    pycharm_source = tmp_path / "pycharm.tar.gz"
    pycharm_spec = artifact(pycharm_source, hashlib.sha256(fixture_archive(pycharm_source)).hexdigest())
    meta, platform = codex_npm_declarations(tmp_path)
    built: dict[str, ImageDetails] = {}

    def build(build_spec: ImageBuildSpec) -> None:
        plan = build_spec.build_plan()
        copies = {copy.destination: copy for stage in plan.stages for copy in stage.plan.files}
        assert copies["/opt/codex/1.0.0/codex-1.0.0.tgz"].source.read_bytes() == b"meta-package-tarball"
        assert copies["/opt/codex/1.0.0/codex-1.0.0-linux-x64.tgz"].source.read_bytes() == b"platform-package-tarball"
        assert copies["/opt/codex/1.0.0/codex-1.0.0.tgz"].permissions == 0o644
        manifest = json.loads(copies["/opt/codex/1.0.0/package.json"].source.read_text())
        assert manifest == {
            "name": "devcapsule-codex",
            "version": "0.0.0",
            "private": True,
            "dependencies": {
                "@openai/codex": "file:./codex-1.0.0.tgz",
                "@openai/codex-linux-x64": "file:./codex-1.0.0-linux-x64.tgz",
            },
        }
        assert next(stage.plan for stage in plan.stages if stage.name == "codex").exec_steps == (
            ExecStep(npm_install_step("/opt/codex/1.0.0")),
        )
        assert npm_install_step("/opt/codex/1.0.0") == (
            "sh",
            "-c",
            "npm_config_cache=/tmp/devcapsule-npm-cache npm --prefix '/opt/codex/1.0.0' "
            "install --offline --ignore-scripts --no-audit --no-fund --no-update-notifier "
            "--loglevel=error --logs-max=0 && rm -rf /tmp/devcapsule-npm-cache",
        )
        assert ("PATH", "/opt/codex/1.0.0/node_modules/.bin:${PATH}") in plan.env
        built[plan.image] = image_details(plan.image, dict(plan.labels))

    image, created = ensure_materialized_surface(
        base_reference="base:debug",
        base_identity="sha256:base",
        platform="linux-amd64",
        artifact=pycharm_spec,
        ancillary_artifacts=(meta, platform),
        cache_root=tmp_path / "cache",
        inspect_image=built.get,
        build=build,
    )

    assert created is True
    descriptor = json.loads(built[image].labels["devcapsule.materialization.descriptor"])
    assert [item["id"] for item in descriptor["components"]] == ["pycharm", "codex", "codex"]
    assert descriptor["components"][1]["installation"] == {
        "destination": "/opt/codex/1.0.0",
        "format": "npm-package",
        "npm-package": "@openai/codex",
    }
    assert descriptor["components"][2]["installation"] == {
        "destination": "/opt/codex/1.0.0",
        "format": "npm-package",
        "npm-package": "@openai/codex-linux-x64",
    }


def _lock_with_codex(**codex_overrides: object) -> dict[str, object]:
    return {
        "platform": "linux-amd64",
        "base": {"reference": "base@sha256:manifest"},
        "components": {
            "interactive-surface": "pycharm",
            "pycharm": {
                "version": "2099.1.0",
                "variant": "professional",
                "delivery-policy": "local-materialization",
                "url": "https://example.test/pycharm.tar.gz",
                "sha256": "a" * 64,
            },
            "codex": {
                "version": "1.0.0",
                "delivery-policy": "local-materialization",
                "npm-package": "@openai/codex",
                "url": "https://example.test/codex-1.0.0.tgz",
                "sha256": "b" * 64,
                "artifacts": {
                    "linux-amd64": {
                        "npm-package": "@openai/codex-linux-x64",
                        "url": "https://example.test/codex-1.0.0-linux-x64.tgz",
                        "sha256": "c" * 64,
                    }
                },
                **codex_overrides,
            },
        },
        "materialization": {"recipe": "jetbrains-local-materialization", "recipe-version": "1"},
    }


def test_parse_locked_environment_reads_npm_package_ancillary_artifacts() -> None:
    """``parse_locked_environment`` collects both meta and platform ``npm-package`` declarations for ``codex``."""
    locked = parse_locked_environment(_lock_with_codex())

    assert [item.npm_package for item in locked.ancillary_artifacts] == [
        "@openai/codex",
        "@openai/codex-linux-x64",
    ]


def test_parse_locked_environment_rejects_npm_url_without_tarball_filename() -> None:
    """``parse_locked_environment`` raises ``CliError`` when an ``npm-package`` URL does not end in a tarball name."""
    with pytest.raises(CliError, match="must end in a tarball file name"):
        parse_locked_environment(_lock_with_codex(url="https://example.test/codex/"))


def test_materialization_refuses_npm_directory_shared_by_two_components(tmp_path: Path) -> None:
    """``ensure_materialized_surface`` refuses two different components targeting the same npm prefix directory."""
    pycharm_source = tmp_path / "pycharm.tar.gz"
    pycharm_spec = artifact(pycharm_source, hashlib.sha256(fixture_archive(pycharm_source)).hexdigest())
    meta, platform = codex_npm_declarations(tmp_path)
    other_source = tmp_path / "other-1.tgz"
    other_source.write_bytes(b"other-package-tarball")
    other = LockedArtifactDeclaration(
        component_id="other-agent",
        version="1",
        url=other_source.as_uri(),
        sha256=hashlib.sha256(other_source.read_bytes()).hexdigest(),
        destination="/opt/codex/1.0.0",
        artifact_format="npm-package",
        npm_package="@example/other",
    )

    with pytest.raises(CliError, match="claimed by several components: codex, other-agent"):
        ensure_materialized_surface(
            base_reference="base:debug",
            base_identity="sha256:base",
            platform="linux-amd64",
            artifact=pycharm_spec,
            ancillary_artifacts=(meta, platform, other),
            cache_root=tmp_path / "cache",
            inspect_image=lambda _reference: None,
            build=lambda _spec: None,
        )


def test_materialization_refuses_duplicate_npm_package_in_one_component(tmp_path: Path) -> None:
    """``ensure_materialized_surface`` refuses a component declaring the same ``npm_package`` twice."""
    pycharm_source = tmp_path / "pycharm.tar.gz"
    pycharm_spec = artifact(pycharm_source, hashlib.sha256(fixture_archive(pycharm_source)).hexdigest())
    meta, _platform = codex_npm_declarations(tmp_path)
    dup_source = tmp_path / "codex-again.tgz"
    dup_source.write_bytes(b"duplicate-package-tarball")
    duplicate = LockedArtifactDeclaration(
        component_id="codex",
        version="1.0.0",
        url=dup_source.as_uri(),
        sha256=hashlib.sha256(dup_source.read_bytes()).hexdigest(),
        destination="/opt/codex/1.0.0",
        artifact_format="npm-package",
        npm_package="@openai/codex",
    )

    with pytest.raises(CliError, match="declares npm package '@openai/codex' twice"):
        ensure_materialized_surface(
            base_reference="base:debug",
            base_identity="sha256:base",
            platform="linux-amd64",
            artifact=pycharm_spec,
            ancillary_artifacts=(meta, duplicate),
            cache_root=tmp_path / "cache",
            inspect_image=lambda _reference: None,
            build=lambda _spec: None,
        )


def test_materialization_installs_locked_raw_executable_and_image_environment(tmp_path: Path) -> None:
    """A ``file`` ancillary artifact is copied ``0o755`` to ``destination`` and its environment entries join the image."""
    pycharm_source = tmp_path / "pycharm.tar.gz"
    pycharm_spec = artifact(pycharm_source, hashlib.sha256(fixture_archive(pycharm_source)).hexdigest())
    claude_source = tmp_path / "claude"
    claude_source.write_bytes(b"claude-code-binary-fixture")
    claude = LockedArtifactDeclaration(
        component_id="claude-code",
        version="2.0.0",
        url=claude_source.as_uri(),
        sha256=hashlib.sha256(claude_source.read_bytes()).hexdigest(),
        destination="/opt/claude/bin/claude",
        artifact_format="file",
        environment=(
            ("PATH", "/opt/claude/bin:${PATH}"),
            ("DISABLE_UPDATES", "1"),
        ),
    )
    built: dict[str, ImageDetails] = {}

    def build(build_spec: ImageBuildSpec) -> None:
        plan = build_spec.build_plan()
        copied = next(
            item for stage in plan.stages for item in stage.plan.files if item.destination == "/opt/claude/bin/claude"
        )
        assert copied.source.read_bytes() == b"claude-code-binary-fixture"
        assert copied.permissions == 0o755
        assert ("PATH", "/opt/claude/bin:${PATH}") in plan.env
        assert ("DISABLE_UPDATES", "1") in plan.env
        built[plan.image] = image_details(plan.image, dict(plan.labels))

    image, created = ensure_materialized_surface(
        base_reference="base:debug",
        base_identity="sha256:base",
        platform="linux-amd64",
        artifact=pycharm_spec,
        ancillary_artifacts=(claude,),
        cache_root=tmp_path / "cache",
        inspect_image=built.get,
        build=build,
    )

    assert created is True
    descriptor = json.loads(built[image].labels["devcapsule.materialization.descriptor"])
    assert descriptor["components"][1]["installation"] == {
        "destination": "/opt/claude/bin/claude",
        "format": "file",
    }


def test_surface_materialization_spec_stamps_complete_formation_labels(tmp_path: Path) -> None:
    """``surface_materialization_spec`` produces labels that satisfy ``verify_materialized_image``."""
    pycharm = tmp_path / "pycharm"
    pycharm.mkdir()
    template = tmp_path / "component-template.json"
    template.write_text(canonical_json(component_runtime_template()), encoding="utf-8")
    spec = artifact(tmp_path / "pycharm.tar.gz")
    descriptor = formation_descriptor(platform="linux-amd64", base_identity="sha256:base", artifact=spec)
    image = canonical_image_name(descriptor)

    plan = surface_materialization_spec(
        base_reference="base:debug",
        base_identity="sha256:base",
        image=image,
        surface_root=pycharm,
        component_template=template,
        artifact=spec,
        platform="linux-amd64",
    ).build_plan()
    labels = dict(plan.labels)

    assert labels["devcapsule.image.kind"] == "materialized"
    assert labels["devcapsule.image.canonical-name"] == image
    assert labels["devcapsule.materialization.descriptor"] == canonical_json(descriptor)
    assert labels["devcapsule.materialization.identity"] == formation_identity(descriptor)
    assert labels["devcapsule.materialization.base-identity"] == "sha256:base"
    assert labels["devcapsule.component.version"] == "2099.1.0"
    verify_materialized_image(image_details(image, labels), descriptor=descriptor, canonical_name=image)


def test_parse_locked_environment_reads_jetbrains_surface_and_base_identity() -> None:
    """``parse_locked_environment`` extracts the JetBrains surface spec, recipe, and optional ``base.identity``."""
    locked = parse_locked_environment(
        {
            "platform": "linux-amd64",
            "base": {"reference": "base@sha256:manifest", "identity": "sha256:base"},
            "components": {
                "interactive-surface": "pycharm",
                "pycharm": {
                    "version": "2099.1.0",
                    "variant": "professional",
                    "delivery-policy": "local-materialization",
                    "url": "https://example.test/pycharm.tar.gz",
                    "sha256": "a" * 64,
                },
            },
            "materialization": {"recipe": "jetbrains-local-materialization", "recipe-version": "1"},
        }
    )

    assert locked.component_id == "pycharm"
    assert locked.artifact.version == "2099.1.0"
    assert locked.base_identity == "sha256:base"


def test_validate_base_image_accepts_matching_managed_base() -> None:
    """``validate_base_image`` succeeds when managed base labels, platform, and ``expected_identity`` match."""
    details = image_details(
        "base@sha256:manifest",
        {
            "devcapsule.image.managed": "true",
            "devcapsule.metadata.version": "1",
            "devcapsule.image.kind": "base",
        },
        identity="sha256:base",
    )

    validate_base_image(details, platform="linux-amd64", expected_identity="sha256:base")


def test_validate_base_image_rejects_identity_mismatch() -> None:
    """``validate_base_image`` raises ``CliError`` when ``details.identity`` differs from ``expected_identity``."""
    details = image_details(
        "base:debug",
        {
            "devcapsule.image.managed": "true",
            "devcapsule.metadata.version": "1",
            "devcapsule.image.kind": "base",
        },
        identity="sha256:other",
    )

    with pytest.raises(CliError, match="identity mismatch"):
        validate_base_image(details, platform="linux-amd64", expected_identity="sha256:expected")


def test_materialization_chains_ancillary_path_prefixes_in_declaration_order(tmp_path: Path) -> None:
    """Multiple ancillary ``PATH`` prefixes merge in declaration order before ``${PATH}``."""
    pycharm_source = tmp_path / "pycharm.tar.gz"
    pycharm_spec = artifact(pycharm_source, hashlib.sha256(fixture_archive(pycharm_source)).hexdigest())
    first_bin = tmp_path / "claude"
    first_bin.write_bytes(b"claude")
    second_bin = tmp_path / "antigravity"
    second_bin.write_bytes(b"antigravity")
    ancillary = (
        LockedArtifactDeclaration(
            component_id="claude-code",
            version="1",
            url=first_bin.as_uri(),
            sha256=hashlib.sha256(first_bin.read_bytes()).hexdigest(),
            destination="/opt/claude/bin/claude",
            artifact_format="file",
            environment=(("PATH", "/opt/claude/bin:${PATH}"),),
        ),
        LockedArtifactDeclaration(
            component_id="antigravity-cli",
            version="1",
            url=second_bin.as_uri(),
            sha256=hashlib.sha256(second_bin.read_bytes()).hexdigest(),
            destination="/opt/antigravity-cli/bin/antigravity",
            artifact_format="file",
            environment=(("PATH", "/opt/antigravity-cli/bin:${PATH}"),),
        ),
    )
    built: dict[str, ImageDetails] = {}

    def build(build_spec: ImageBuildSpec) -> None:
        plan = build_spec.build_plan()
        assert ("PATH", "/opt/claude/bin:/opt/antigravity-cli/bin:${PATH}") in plan.env
        built[plan.image] = image_details(plan.image, dict(plan.labels))

    _image, created = ensure_materialized_surface(
        base_reference="base:debug",
        base_identity="sha256:base",
        platform="linux-amd64",
        artifact=pycharm_spec,
        ancillary_artifacts=ancillary,
        cache_root=tmp_path / "cache",
        inspect_image=built.get,
        build=build,
    )

    assert created is True


def test_materialization_refuses_conflicting_non_path_ancillary_environment(tmp_path: Path) -> None:
    """``ensure_materialized_surface`` raises ``CliError`` when two ancillary components disagree on one env variable."""
    pycharm_source = tmp_path / "pycharm.tar.gz"
    pycharm_spec = artifact(pycharm_source, hashlib.sha256(fixture_archive(pycharm_source)).hexdigest())
    first_bin = tmp_path / "claude"
    first_bin.write_bytes(b"claude")
    second_bin = tmp_path / "other"
    second_bin.write_bytes(b"other")
    ancillary = (
        LockedArtifactDeclaration(
            component_id="claude-code",
            version="1",
            url=first_bin.as_uri(),
            sha256=hashlib.sha256(first_bin.read_bytes()).hexdigest(),
            destination="/opt/claude/bin/claude",
            artifact_format="file",
            environment=(("DISABLE_UPDATES", "1"),),
        ),
        LockedArtifactDeclaration(
            component_id="other",
            version="1",
            url=second_bin.as_uri(),
            sha256=hashlib.sha256(second_bin.read_bytes()).hexdigest(),
            destination="/opt/other/bin/other",
            artifact_format="file",
            environment=(("DISABLE_UPDATES", "0"),),
        ),
    )

    with pytest.raises(CliError, match="conflicting values for environment DISABLE_UPDATES"):
        ensure_materialized_surface(
            base_reference="base:debug",
            base_identity="sha256:base",
            platform="linux-amd64",
            artifact=pycharm_spec,
            ancillary_artifacts=ancillary,
            cache_root=tmp_path / "cache",
            inspect_image=lambda _reference: None,
            build=lambda _spec: None,
        )


def test_materialization_recipe_enforces_boot_contract(tmp_path: Path) -> None:
    """``ensure_materialized_surface`` sets ``ENTRYPOINT_CONTRACT`` and ``RUNTIME_PLAN_PATH`` on the built image."""
    source = tmp_path / "pycharm.tar.gz"
    spec = artifact(source, hashlib.sha256(fixture_archive(source)).hexdigest())
    built: dict[str, ImageDetails] = {}

    def build(build_spec: ImageBuildSpec) -> None:
        plan = build_spec.build_plan()
        assert plan.entrypoint == ENTRYPOINT_CONTRACT
        assert plan.command == (RUNTIME_PLAN_PATH,)
        built[plan.image] = ImageDetails(
            plan.image,
            "sha256:image",
            dict(plan.labels),
            "linux",
            "amd64",
            entrypoint=plan.entrypoint,
            command=plan.command,
        )

    image, created = ensure_materialized_surface(
        base_reference="base:debug",
        base_identity="sha256:base",
        platform="linux-amd64",
        artifact=spec,
        cache_root=tmp_path / "cache",
        inspect_image=built.get,
        build=build,
    )

    assert created is True
    assert built[image].entrypoint == ENTRYPOINT_CONTRACT


def test_existing_image_with_stale_boot_config_is_repaired_in_place(tmp_path: Path) -> None:
    """An existing canonical image with drifted entrypoint is repaired in place by a configuration-only layer."""
    spec = artifact(tmp_path / "missing.tar.gz")
    canonical, labels = expected_labels("sha256:base", spec)
    stale = ImageDetails(
        canonical,
        "sha256:stale",
        labels,
        "linux",
        "amd64",
        entrypoint=("/usr/bin/tini", "--") + ENTRYPOINT_CONTRACT,
        command=(RUNTIME_PLAN_PATH,),
    )
    state = {"current": stale}
    repairs: list[object] = []
    messages: list[str] = []

    def build(build_spec: ImageBuildSpec) -> None:
        plan = build_spec.build_plan()
        repairs.append(build_spec)
        assert plan.base_image == canonical
        assert plan.directories == () and plan.files == () and plan.labels == ()
        assert plan.entrypoint == ENTRYPOINT_CONTRACT
        assert plan.command == (RUNTIME_PLAN_PATH,)
        state["current"] = ImageDetails(
            canonical,
            "sha256:repaired",
            labels,
            "linux",
            "amd64",
            entrypoint=plan.entrypoint,
            command=plan.command,
        )

    image, created = ensure_materialized_surface(
        base_reference="base:debug",
        base_identity="sha256:base",
        platform="linux-amd64",
        artifact=spec,
        cache_root=tmp_path / "cache",
        inspect_image=lambda reference: state["current"] if reference == canonical else None,
        build=build,
        report=messages.append,
    )

    assert image == canonical
    assert created is False
    assert len(repairs) == 1
    assert any("Enforcing the recorded boot contract" in message for message in messages)


def test_verify_materialized_image_rejects_boot_config_contradicting_descriptor(tmp_path: Path) -> None:
    """``verify_materialized_image`` raises ``CliError`` when the image's entrypoint differs from ``descriptor``."""
    spec = artifact(tmp_path / "missing.tar.gz")
    canonical, labels = expected_labels("sha256:base", spec)
    descriptor = formation_descriptor(platform="linux-amd64", base_identity="sha256:base", artifact=spec)
    lying = ImageDetails(
        canonical,
        "sha256:image",
        labels,
        "linux",
        "amd64",
        entrypoint=("/usr/bin/tini", "--") + ENTRYPOINT_CONTRACT,
        command=(RUNTIME_PLAN_PATH,),
    )

    with pytest.raises(CliError, match="boots differently"):
        verify_materialized_image(lying, descriptor=descriptor, canonical_name=canonical)


def test_materialization_explains_difference_from_nearest_prior_formation(tmp_path: Path) -> None:
    """Before building, ``ensure_materialized_surface`` reports leaf differences and total size of prior formations."""
    source = tmp_path / "pycharm.tar.gz"
    spec = artifact(source, hashlib.sha256(fixture_archive(source)).hexdigest())
    _prior_canonical, prior_labels = expected_labels("sha256:otherbase", spec)
    prior = ImageDetails(
        "devcapsule-local-pycharm:oldtag",
        "sha256:prior",
        prior_labels,
        "linux",
        "amd64",
        size_bytes=7_000_000_000,
    )
    built: dict[str, ImageDetails] = {}
    messages: list[str] = []

    def build(build_spec: ImageBuildSpec) -> None:
        assert any("differs from devcapsule-local-pycharm:oldtag in base.identity" in m for m in messages)
        plan = build_spec.build_plan()
        built[plan.image] = ImageDetails(
            plan.image, "sha256:image", dict(plan.labels), "linux", "amd64",
            entrypoint=plan.entrypoint, command=plan.command,
        )

    ensure_materialized_surface(
        base_reference="base:debug",
        base_identity="sha256:base",
        platform="linux-amd64",
        artifact=spec,
        cache_root=tmp_path / "cache",
        inspect_image=built.get,
        build=build,
        report=messages.append,
        list_formations=lambda: (prior,),
    )

    assert any("Prior pycharm formation images remain (7.0 GB total)" in m for m in messages)


def test_materialization_explains_first_formation_on_host(tmp_path: Path) -> None:
    """With no prior formations on the host, ``ensure_materialized_surface`` announces the first formation before build."""
    source = tmp_path / "pycharm.tar.gz"
    spec = artifact(source, hashlib.sha256(fixture_archive(source)).hexdigest())
    built: dict[str, ImageDetails] = {}
    messages: list[str] = []

    def build(build_spec: ImageBuildSpec) -> None:
        assert any("first pycharm formation on this host" in m for m in messages)
        plan = build_spec.build_plan()
        built[plan.image] = ImageDetails(
            plan.image, "sha256:image", dict(plan.labels), "linux", "amd64",
            entrypoint=plan.entrypoint, command=plan.command,
        )

    ensure_materialized_surface(
        base_reference="base:debug",
        base_identity="sha256:base",
        platform="linux-amd64",
        artifact=spec,
        cache_root=tmp_path / "cache",
        inspect_image=built.get,
        build=build,
        report=messages.append,
        list_formations=lambda: (),
    )

    assert any("first pycharm formation on this host" in m for m in messages)


def test_descriptor_differences_reports_changed_leaf_paths() -> None:
    """``descriptor_differences`` returns dotted paths of leaves that differ between two nested mappings."""
    expected = {"base": {"identity": "a"}, "runtime": {"entrypoint": ["x"], "command": ["c"]}}
    actual = {"base": {"identity": "b"}, "runtime": {"entrypoint": ["y"], "command": ["c"]}}

    assert descriptor_differences(expected, actual) == ("base.identity", "runtime.entrypoint")


def test_materialization_reuses_unpacked_archive_tree_across_formations(tmp_path: Path) -> None:
    """Two formations of the same verified archive read the same digest-keyed unpacked directory under the cache."""
    source = tmp_path / "pycharm.tar.gz"
    digest = hashlib.sha256(fixture_archive(source)).hexdigest()
    spec = artifact(source, digest)
    built: dict[str, ImageDetails] = {}
    surface_roots: list[Path] = []

    def build(build_spec: ImageBuildSpec) -> None:
        plan = build_spec.build_plan()
        built[plan.image] = image_details(plan.image, dict(plan.labels))
        surface_roots.extend(
            copy.source for stage in plan.stages for copy in stage.plan.directories
            if copy.destination == "/opt/jetbrains/pycharm"
        )

    ensure_materialized_surface(
        base_reference="base:debug", base_identity="sha256:one", platform="linux-amd64",
        artifact=spec, cache_root=tmp_path / "cache", inspect_image=built.get, build=build,
    )
    ensure_materialized_surface(
        base_reference="base:debug", base_identity="sha256:two", platform="linux-amd64",
        artifact=spec, cache_root=tmp_path / "cache", inspect_image=built.get, build=build,
    )

    tree = tmp_path / "cache" / UNPACKED_DIRECTORY / digest
    assert len(surface_roots) == 2 and surface_roots[0] == surface_roots[1]
    assert surface_roots[0].is_relative_to(tree) and (surface_roots[0] / "bin" / "pycharm.sh").is_file()
    marker = json.loads((tree / UNPACKED_MARKER).read_text())
    assert marker["sha256"] == digest and surface_roots[0] == tree / marker["root"]
    assert not list(tree.parent.glob("*.partial-*"))


def test_materialization_redoes_unpacked_tree_missing_completion_marker(tmp_path: Path) -> None:
    """An unpacked cache directory lacking ``UNPACKED_MARKER`` is discarded and unpacked cleanly."""
    source = tmp_path / "pycharm.tar.gz"
    digest = hashlib.sha256(fixture_archive(source)).hexdigest()
    spec = artifact(source, digest)
    tree = tmp_path / "cache" / UNPACKED_DIRECTORY / digest
    tree.mkdir(parents=True)
    (tree / "leftover").write_text("partial", encoding="utf-8")
    built: dict[str, ImageDetails] = {}

    def build(build_spec: ImageBuildSpec) -> None:
        plan = build_spec.build_plan()
        built[plan.image] = image_details(plan.image, dict(plan.labels))

    ensure_materialized_surface(
        base_reference="base:debug", base_identity="sha256:one", platform="linux-amd64",
        artifact=spec, cache_root=tmp_path / "cache", inspect_image=built.get, build=build,
    )

    assert not (tree / "leftover").exists()
    assert (tree / UNPACKED_MARKER).is_file()


def runtime_pex_with_console(path: Path, *, files_html: str) -> Path:
    pkg = path.parent / f"pkg-{path.stem}" / "devcapsule_webconsole"
    (pkg / "static").mkdir(parents=True)
    (pkg / "__init__.py").write_text('__version__ = "0.1.0"\n', encoding="utf-8")
    (pkg / "static" / "files.html").write_text(files_html, encoding="utf-8")
    bundle = build_webconsole_bundle(pkg, path.parent / f"{path.stem}-{BUNDLE_RESOURCE_NAME}")
    revision = "b" * 40
    with ZipFile(path, "w") as archive:
        archive.writestr(
            ".deps/devcapsule-0.3.1-py3-none-any.whl/devcapsule/_build_info.json",
            json.dumps(
                {
                    "schema_version": 2,
                    "version": "0.3.1",
                    "build_mnemonic": "v0.3.1-rc2",
                    "source_repository": "https://github.com/example/devcapsule",
                    "source_revision": revision,
                    "source_url": f"https://github.com/example/devcapsule/commit/{revision}",
                }
            ),
        )
        archive.writestr(
            f".deps/devcapsule-0.3.1-py3-none-any.whl/devcapsule/{BUNDLE_RESOURCE_NAME}",
            bundle.read_bytes(),
        )
    return path


def test_surface_materialization_spec_copies_webconsole_root_when_supplied(tmp_path: Path) -> None:
    """When ``webconsole_root`` is supplied, ``surface_materialization_spec`` copies it to ``/opt/devcapsule/webconsole``."""
    surface = tmp_path / "surface"
    surface.mkdir()
    webconsole = tmp_path / "webconsole"
    (webconsole / "devcapsule_webconsole").mkdir(parents=True)
    (webconsole / "devcapsule_webconsole" / "__init__.py").write_text("", encoding="utf-8")
    template = tmp_path / "template.json"
    template.write_text(canonical_json(component_runtime_template("pycharm")), encoding="utf-8")
    spec = ArtifactSpec("2026.2", "https://example.test/pycharm.tar.gz", "a" * 64)

    plan = surface_materialization_spec(
        base_reference="base:test",
        base_identity="sha256:base",
        image="devcapsule-local-pycharm:test",
        surface_root=surface,
        component_template=template,
        artifact=spec,
        platform="linux-amd64",
        webconsole_root=webconsole,
    ).build_plan()

    assert any(
        copy.source == webconsole and copy.destination == LAUNCHER_WEBCONSOLE_PATH
        for copy in plan.directories
    )


def test_ensure_materialized_surface_unpacks_and_stages_the_launcher_webconsole(tmp_path: Path) -> None:
    """Materializing with a ``runtime_pex`` extracts its embedded ``devcapsule_webconsole`` bundle for ``/opt/devcapsule/webconsole``."""
    source = tmp_path / "pycharm.tar.gz"
    spec = artifact(source, hashlib.sha256(fixture_archive(source)).hexdigest())
    pex = runtime_pex_with_console(tmp_path / "devcapsule.pex", files_html="<title>Files v1</title>\n")
    built: dict[str, ImageDetails] = {}
    captured_html: list[str] = []

    def record_build(build_spec: ImageBuildSpec) -> None:
        plan = build_spec.build_plan()
        webconsole_copy = next(copy for copy in plan.directories if copy.destination == LAUNCHER_WEBCONSOLE_PATH)
        captured_html.append(
            (webconsole_copy.source / "devcapsule_webconsole" / "static" / "files.html").read_text(encoding="utf-8")
        )
        built[plan.image] = ImageDetails(
            reference=plan.image,
            identity="sha256:materialized",
            labels=dict(plan.labels),
            operating_system="linux",
            architecture="amd64",
            entrypoint=plan.entrypoint,
            command=plan.command,
        )

    image, created = ensure_materialized_surface(
        base_reference="base:test",
        base_identity="sha256:base",
        platform="linux-amd64",
        artifact=spec,
        cache_root=tmp_path / "cache",
        inspect_image=built.get,
        build=record_build,
        runtime_pex=pex,
    )

    assert created is True
    assert image in built
    assert captured_html == ["<title>Files v1</title>\n"]


def test_changing_bundled_webconsole_changes_pex_digest_and_formation_identity(tmp_path: Path) -> None:
    """Editing a web console file inside ``runtime_pex`` changes ``pex-sha256`` and the formation identity."""
    spec = ArtifactSpec("2026.2", "https://example.test/pycharm.tar.gz", "a" * 64)
    first_pex = runtime_pex_with_console(tmp_path / "first.pex", files_html="<title>v1</title>\n")
    second_pex = runtime_pex_with_console(tmp_path / "second.pex", files_html="<title>v2</title>\n")

    first = formation_descriptor(
        platform="linux-amd64",
        base_identity="sha256:base",
        artifact=spec,
        runtime_sha256=sha256_file(first_pex),
    )
    second = formation_descriptor(
        platform="linux-amd64",
        base_identity="sha256:base",
        artifact=spec,
        runtime_sha256=sha256_file(second_pex),
    )

    assert first["runtime"]["pex-sha256"] != second["runtime"]["pex-sha256"]
    assert formation_identity(first) != formation_identity(second)


def test_ensure_materialized_surface_refuses_runtime_pex_without_webconsole_bundle(tmp_path: Path) -> None:
    """Materializing with a ``runtime_pex`` that lacks the web console bundle raises ``CliError``."""
    source = tmp_path / "pycharm.tar.gz"
    spec = artifact(source, hashlib.sha256(fixture_archive(source)).hexdigest())
    incomplete_pex = tmp_path / "incomplete.pex"
    with ZipFile(incomplete_pex, "w") as archive:
        archive.writestr(
            ".deps/devcapsule-0.3.1-py3-none-any.whl/devcapsule/_build_info.json",
            json.dumps(
                {
                    "schema_version": 2,
                    "version": "0.3.1",
                    "build_mnemonic": "v0.3.1-rc2",
                    "source_repository": "unknown",
                    "source_revision": "unknown",
                    "source_url": "unknown",
                }
            ),
        )

    with pytest.raises(CliError, match="Cannot unpack the launcher web console"):
        ensure_materialized_surface(
            base_reference="base:test",
            base_identity="sha256:base",
            platform="linux-amd64",
            artifact=spec,
            cache_root=tmp_path / "cache",
            inspect_image=lambda _name: None,
            build=lambda _spec: None,
            runtime_pex=incomplete_pex,
        )
