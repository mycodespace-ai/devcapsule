"""Focused tests for the configuration-node registry."""

from __future__ import annotations

import pytest

from devcapsule.configuration.nodes import (
    CARRIER_FAMILY_AUTHORIZE,
    CARRIER_FAMILY_BIND,
    CARRIER_FAMILY_SET,
    PROVIDER_HOST_DIRECTORY,
    PROVIDER_HOST_ENVIRONMENT,
    build_node_registry,
)
from devcapsule.configuration.file_formats import (
    ProjectConfigurationError,
)

pytestmark = pytest.mark.legacy


def example_manifest() -> dict:
    return {
        "devcapsule-schema-version": 1,
        "capabilities": {"need": ["python", "python-ide", "codex-agent"]},
        "project": {
            "name": "Example",
            "slug": "example",
            "creator": "https://github.com/example",
            "mount": "/workspace/example",
        },
        "configuration": {
            "values": {
                "runtime.memory-limit": {
                    "type": "memory-size",
                    "runtime-effect": "docker.memory-limit",
                    "description": "Hard memory limit for the project container.",
                }
            }
        },
        "host": {
            "docker": {
                "mode": {
                    "recommended": {
                        "value": "host-socket",
                        "justification": "Required for the full test suite.",
                    }
                }
            }
        },
    }


def example_lock() -> dict:
    return {
        "devcapsule-lock-format-version": 1,
        "platform": "linux-amd64",
        "base": {
            "reference": "docker.io/mycodespaceai/devcapsule-base@sha256:" + "6" * 64,
        },
        "components": {
            "interactive-surface": "pycharm",
            "pycharm": {
                "version": "2026.2.0.1",
                "variant": "professional",
                "delivery-policy": "local-materialization",
                "url": "https://example.test/pycharm.tar.gz",
                "sha256": "a" * 64,
            },
            "codex": {
                "version": "0.145.0",
                "delivery-policy": "local-materialization",
            },
        },
    }


def test_registry_assigns_each_declaration_kind_to_its_family() -> None:
    registry = build_node_registry(example_manifest(), example_lock())

    value = registry.node("runtime.memory-limit")
    assert value.family == CARRIER_FAMILY_SET
    assert value.required is False

    home = registry.node("home")
    assert home.family == CARRIER_FAMILY_BIND
    assert home.providers == (PROVIDER_HOST_DIRECTORY,)

    slot = registry.node("pycharm/system")
    assert slot.family == CARRIER_FAMILY_BIND

    secret = registry.node("codex/openai-api-key")
    assert secret.family == CARRIER_FAMILY_BIND
    assert secret.providers == (PROVIDER_HOST_ENVIRONMENT,)
    assert secret.required is False

    base = registry.node("base-image")
    assert base.family == CARRIER_FAMILY_AUTHORIZE
    assert base.required is True
    assert base.accepts_justification is False

    docker = registry.node("docker-daemon")
    assert docker.family == CARRIER_FAMILY_AUTHORIZE
    assert docker.required is False
    assert docker.accepts_justification is True
    assert docker.description == "Required for the full test suite."


def test_registry_names_are_sorted_and_family_filtered() -> None:
    registry = build_node_registry(example_manifest(), example_lock())
    names = registry.names()
    assert names == tuple(sorted(names))
    authorize = registry.family(CARRIER_FAMILY_AUTHORIZE)
    # docker-daemon comes from the manifest recommendation; network,
    # development-sudo, host-browser and host-x11 exist as
    # home-capability defaults, network since 2026-10-22.
    assert {node.name for node in authorize} == {
        "base-image",
        "docker-daemon",
        "network",
        "development-sudo",
        "host-browser",
        "host-x11",
    }


def test_unknown_node_lists_the_declared_vocabulary() -> None:
    registry = build_node_registry(example_manifest(), example_lock())
    with pytest.raises(ProjectConfigurationError) as failure:
        registry.node("does-not-exist")
    assert "'does-not-exist'" in str(failure.value)
    assert "runtime.memory-limit" in str(failure.value)


def test_wrong_carrier_family_names_the_right_spelling() -> None:
    registry = build_node_registry(example_manifest(), example_lock())
    with pytest.raises(ProjectConfigurationError, match="answered with --bind, not --set"):
        registry.answerable("home", CARRIER_FAMILY_SET)


def test_bind_values_split_on_the_first_colon_only() -> None:
    registry = build_node_registry(example_manifest(), example_lock())
    provider, value = registry.split_bind_value("home", "host-directory:/state/x:y")
    assert provider == PROVIDER_HOST_DIRECTORY
    assert value == "/state/x:y"

    provider, value = registry.split_bind_value(
        "codex/openai-api-key", "host-environment:OPENAI_API_KEY"
    )
    assert provider == PROVIDER_HOST_ENVIRONMENT
    assert value == "OPENAI_API_KEY"


def test_bind_value_rejects_wrong_or_missing_provider() -> None:
    registry = build_node_registry(example_manifest(), example_lock())
    with pytest.raises(ProjectConfigurationError, match="host-environment:VALUE"):
        registry.split_bind_value("codex/openai-api-key", "host-directory:/somewhere")
    with pytest.raises(ProjectConfigurationError, match="host-directory:VALUE"):
        registry.split_bind_value("home", "/no/provider/prefix")


def test_a_name_declared_twice_fails_at_construction() -> None:
    manifest = example_manifest()
    # A project-declared value colliding with the component slot name 'home'.
    manifest["configuration"]["values"]["home"] = {
        "type": "string",
        "description": "Colliding declaration.",
    }
    with pytest.raises(ProjectConfigurationError, match="declared twice"):
        build_node_registry(manifest, example_lock())
