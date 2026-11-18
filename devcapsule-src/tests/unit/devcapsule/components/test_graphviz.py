"""Graphviz's artifact and runtime contract from explicit lock values."""
from __future__ import annotations

from typing import Any

import pytest

from devcapsule.compat import CliError
from devcapsule.components.graphviz import GraphvizComponent


def pin(platform: str = "linux-amd64") -> dict[str, Any]:
    """Construct a small reviewed-recipe lock without reading repository pins."""
    return {
        "version": "1.2.3", "platform": platform,
        "delivery-policy": "local-materialization", "build-recipe": "graphviz-autotools-v1",
        "artifacts": {
            "source": {"url": "https://example.test/graphviz.tar.gz", "sha256": "a" * 64},
            "libexample-dev": {"url": "https://example.test/libexample.deb", "sha256": "b" * 64},
        },
    }


@pytest.mark.parametrize("platform", ["linux-amd64", "linux-arm64"])
def test_artifacts_preserve_pins_and_keep_build_inputs_under_the_component(platform: str) -> None:
    """Source and build dependencies retain their URLs/hashes and stage only below /opt/graphviz."""
    metadata = pin(platform)
    declarations = GraphvizComponent().locked_artifacts(metadata, platform)
    assert {x.destination for x in declarations} == {
        "/opt/graphviz/.build/source.tar.gz", "/opt/graphviz/.build/libexample-dev.deb",
    }
    assert {(x.url, x.sha256) for x in declarations} == {
        (x["url"], x["sha256"]) for x in metadata["artifacts"].values()
    }
    assert all(x.artifact_format == "file" for x in declarations)
    assert [entry for x in declarations for entry in x.environment] == [("PATH", "/opt/graphviz/bin:${PATH}")]


@pytest.mark.parametrize("field,value", [
    ("version", "../unreviewed"), ("platform", "linux-arm64"),
    ("build-recipe", "unreviewed"), ("delivery-policy", "base-image"),
])
def test_an_unreviewed_recipe_or_wrong_platform_is_refused(field: str, value: str) -> None:
    """A lock cannot silently use another build recipe, release, delivery policy or architecture."""
    metadata = pin()
    metadata[field] = value
    with pytest.raises(CliError, match="reviewed source-build pin"):
        GraphvizComponent().locked_artifacts(metadata, "linux-amd64")


@pytest.mark.parametrize("artifacts", [
    {},
    {"source": {"url": "https://example.test/graphviz.tar.gz", "sha256": "a" * 64}},
    {"libexample-dev": {"url": "https://example.test/libexample.deb", "sha256": "b" * 64},
     "libother-dev": {"url": "https://example.test/libother.deb", "sha256": "c" * 64}},
])
def test_a_pin_without_source_or_without_build_dependencies_is_refused(artifacts: dict[str, Any]) -> None:
    """The source alone, or dependencies alone, cannot stand for the offline build's inputs."""
    metadata = pin()
    metadata["artifacts"] = artifacts
    with pytest.raises(CliError, match="source and offline build dependencies"):
        GraphvizComponent().locked_artifacts(metadata, "linux-amd64")


@pytest.mark.parametrize("name", ["../escape", "nested/input", "two words", ""])
def test_a_path_shaped_dependency_name_is_refused(name: str) -> None:
    """An artifact key becomes a staged file name, so it cannot carry a path or leave the staging directory."""
    metadata = pin()
    metadata["artifacts"][name] = {"url": "https://example.test/input.deb", "sha256": "c" * 64}
    with pytest.raises(CliError, match="Malformed Graphviz source or dependency artifact"):
        GraphvizComponent().locked_artifacts(metadata, "linux-amd64")


@pytest.mark.parametrize("item", [{}, {"url": "https://example.test/input.deb"}, {"url": "", "sha256": "c" * 64},
                                  {"url": "https://example.test/input.deb", "sha256": 7}, "input.deb"])
def test_a_dependency_without_its_url_and_hash_is_refused(item: Any) -> None:
    """Every staged input names where it comes from and the bytes it must have."""
    metadata = pin()
    metadata["artifacts"]["libexample-dev"] = item
    with pytest.raises(CliError, match="Malformed Graphviz source or dependency artifact"):
        GraphvizComponent().locked_artifacts(metadata, "linux-amd64")


def test_an_unsupported_capsule_platform_has_no_artifacts() -> None:
    """A lock for a platform outside the two Linux capsule architectures is refused, even when it is self-consistent."""
    with pytest.raises(CliError, match="reviewed source-build pin"):
        GraphvizComponent().locked_artifacts(pin("darwin-arm64"), "darwin-arm64")


@pytest.mark.parametrize("version,platform", [
    ("1.2.3'; touch /escaped; '", "linux-amd64"), ("1.2", "linux-amd64"), ("1.2.3", "darwin-arm64"),
])
def test_a_recipe_is_refused_for_a_version_or_platform_it_was_not_reviewed_for(version: str, platform: str) -> None:
    """The version enters the build's shell commands, so only an exact release on a Linux capsule platform gets a recipe."""
    with pytest.raises(CliError, match="Unsupported Graphviz source-build recipe"):
        GraphvizComponent().build_recipe(version, platform)


def test_the_build_exports_only_the_installation() -> None:
    """Build dependencies and package-manager changes have no exports outside /opt/graphviz."""
    recipe = GraphvizComponent().build_recipe("1.2.3", "linux-amd64")
    assert recipe.exports == ("/opt/graphviz",)


def test_the_runtime_is_additive_and_needs_no_credentials_or_state() -> None:
    """Graphviz is an ancillary component without secret inputs or component state slots."""
    definition = GraphvizComponent()
    template = definition.runtime_template()
    assert template.component.adapter == "ancillary"
    assert template.persistence.state_slots == ()
    assert definition.secret_inputs() == definition.state_environment() == ()
