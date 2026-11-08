"""Unit tests of ``devcapsule/materialization.py``: launcher web console delivery and formation identity."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tarfile
from zipfile import ZipFile

import pytest

from devcapsule.compat import CliError
from devcapsule.images.build import ImageBuildSpec
from devcapsule.images.metadata import (
    CANONICAL_NAME_LABEL,
    IMAGE_KIND_LABEL,
    MANAGED_LABEL,
    MATERIALIZED_KIND,
    METADATA_VERSION,
    METADATA_VERSION_LABEL,
)
from devcapsule.materialization import (
    ArtifactSpec,
    ImageDetails,
    canonical_json,
    component_runtime_template,
    ensure_materialized_surface,
    formation_descriptor,
    formation_identity,
    sha256_file,
    surface_materialization_spec,
)
from devcapsule.webconsole_bundle import BUNDLE_RESOURCE_NAME, LAUNCHER_WEBCONSOLE_PATH, build_webconsole_bundle


def _surface_archive(path: Path) -> ArtifactSpec:
    tree = path.parent / "pycharm-tree" / "pycharm-2026.2"
    launcher = tree / "bin" / "pycharm.sh"
    launcher.parent.mkdir(parents=True)
    launcher.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    launcher.chmod(0o755)
    with tarfile.open(path, "w:gz") as archive:
        archive.add(tree, arcname="pycharm-2026.2")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return ArtifactSpec("2026.2", path.as_uri(), digest, variant="professional")


def _runtime_pex_with_console(path: Path, *, files_html: str) -> Path:
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
    artifact = ArtifactSpec("2026.2", "https://example.test/pycharm.tar.gz", "a" * 64)

    plan = surface_materialization_spec(
        base_reference="base:test",
        base_identity="sha256:base",
        image="devcapsule-local-pycharm:test",
        surface_root=surface,
        component_template=template,
        artifact=artifact,
        platform="linux-amd64",
        webconsole_root=webconsole,
    ).build_plan()

    assert any(
        copy.source == webconsole and copy.destination == LAUNCHER_WEBCONSOLE_PATH
        for copy in plan.directories
    )


def test_ensure_materialized_surface_unpacks_and_stages_the_launcher_webconsole(tmp_path: Path) -> None:
    """Materializing with a ``runtime_pex`` extracts its embedded ``devcapsule_webconsole`` bundle for ``/opt/devcapsule/webconsole``."""
    artifact = _surface_archive(tmp_path / "pycharm.tar.gz")
    pex = _runtime_pex_with_console(tmp_path / "devcapsule.pex", files_html="<title>Files v1</title>\n")
    built: dict[str, ImageDetails] = {}
    captured_html: list[str] = []

    def record_build(spec: ImageBuildSpec) -> None:
        plan = spec.build_plan()
        webconsole_copy = next(copy for copy in plan.directories if copy.destination == LAUNCHER_WEBCONSOLE_PATH)
        captured_html.append(
            (webconsole_copy.source / "devcapsule_webconsole" / "static" / "files.html").read_text(encoding="utf-8")
        )
        labels = dict(plan.labels)
        labels.update(
            {
                MANAGED_LABEL: "true",
                METADATA_VERSION_LABEL: METADATA_VERSION,
                IMAGE_KIND_LABEL: MATERIALIZED_KIND,
                CANONICAL_NAME_LABEL: plan.image,
            }
        )
        built[plan.image] = ImageDetails(
            reference=plan.image,
            identity="sha256:materialized",
            labels=labels,
            operating_system="linux",
            architecture="amd64",
            entrypoint=plan.entrypoint,
            command=plan.command,
        )

    image, created = ensure_materialized_surface(
        base_reference="base:test",
        base_identity="sha256:base",
        platform="linux-amd64",
        artifact=artifact,
        cache_root=tmp_path / "cache",
        inspect_image=lambda name: built.get(name),
        build=record_build,
        runtime_pex=pex,
    )

    assert created is True
    assert image in built
    assert captured_html == ["<title>Files v1</title>\n"]


def test_changing_bundled_webconsole_changes_pex_digest_and_formation_identity(tmp_path: Path) -> None:
    """Editing a web console file inside ``runtime_pex`` changes ``pex-sha256`` and the formation identity."""
    artifact = ArtifactSpec("2026.2", "https://example.test/pycharm.tar.gz", "a" * 64)
    first_pex = _runtime_pex_with_console(tmp_path / "first.pex", files_html="<title>v1</title>\n")
    second_pex = _runtime_pex_with_console(tmp_path / "second.pex", files_html="<title>v2</title>\n")

    first = formation_descriptor(
        platform="linux-amd64",
        base_identity="sha256:base",
        artifact=artifact,
        runtime_sha256=sha256_file(first_pex),
    )
    second = formation_descriptor(
        platform="linux-amd64",
        base_identity="sha256:base",
        artifact=artifact,
        runtime_sha256=sha256_file(second_pex),
    )

    assert first["runtime"]["pex-sha256"] != second["runtime"]["pex-sha256"]
    assert formation_identity(first) != formation_identity(second)


def test_ensure_materialized_surface_refuses_runtime_pex_without_webconsole_bundle(tmp_path: Path) -> None:
    """Materializing with a ``runtime_pex`` that lacks the web console bundle raises ``CliError``."""
    artifact = _surface_archive(tmp_path / "pycharm.tar.gz")
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
            artifact=artifact,
            cache_root=tmp_path / "cache",
            inspect_image=lambda _name: None,
            build=lambda _spec: None,
            runtime_pex=incomplete_pex,
        )
