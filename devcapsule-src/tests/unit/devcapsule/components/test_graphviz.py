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


@pytest.mark.parametrize("artifacts", [{}, {"source": {}}, {"source": {}, "../escape": {}}])
def test_missing_or_path_shaped_build_dependencies_are_refused(artifacts: dict[str, Any]) -> None:
    """Source/dependencies must be present and artifact keys cannot escape the staging directory."""
    metadata = pin()
    metadata["artifacts"] = artifacts
    with pytest.raises(CliError):
        GraphvizComponent().locked_artifacts(metadata, "linux-amd64")


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
