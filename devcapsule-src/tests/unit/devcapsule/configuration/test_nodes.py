"""The node registry is built from values and gives every input one address."""
from typing import Any

import pytest

from devcapsule.configuration.nodes import (
    CARRIER_FAMILY_AUTHORIZE, CARRIER_FAMILY_BIND, CARRIER_FAMILY_SET,
    PROVIDER_HOST_DIRECTORY, PROVIDER_HOST_ENVIRONMENT, build_node_registry,
)
from devcapsule.configuration.file_formats import ProjectConfigurationError

def example_manifest() -> dict[str, Any]:
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


def example_lock() -> dict[str, Any]:
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



@pytest.mark.parametrize('name,family,required', [
    ('runtime.memory-limit', CARRIER_FAMILY_SET, False),
    ('home', CARRIER_FAMILY_BIND, False),
    ('pycharm/system', CARRIER_FAMILY_BIND, False),
    ('codex/openai-api-key', CARRIER_FAMILY_BIND, False),
    ('base-image', CARRIER_FAMILY_AUTHORIZE, True),
    ('docker-daemon', CARRIER_FAMILY_AUTHORIZE, False),
    ('ssh-proxy', CARRIER_FAMILY_AUTHORIZE, False),
])
def test_each_declaration_has_its_carrier(name: str, family: str, required: bool) -> None:
    """The registry maps each declared value, binding and authorization to its input family."""
    registry = build_node_registry(example_manifest(), example_lock())
    node = registry.node(name)
    assert node.family == family
    assert node.required is required


def test_registry_names_are_sorted() -> None:
    """The registry presents deterministic sorted names independent of declaration order."""
    registry = build_node_registry(example_manifest(), example_lock())
    names = registry.names()
    assert names == tuple(sorted(names))


def test_authorization_family_includes_the_optional_ssh_proxy_under_its_current_name_only() -> None:
    """The authorization family contains every default host boundary and the locked base; the retired
    name ``github-ssh`` is no node of its own."""
    registry = build_node_registry(example_manifest(), example_lock())
    nodes = registry.family(CARRIER_FAMILY_AUTHORIZE)
    assert {node.name for node in nodes} == {
        'base-image', 'docker-daemon', 'network', 'development-sudo', 'host-browser', 'host-x11', 'ssh-proxy',
    }


@pytest.mark.parametrize('name,providers', [('home', (PROVIDER_HOST_DIRECTORY,)),
                                         ('codex/openai-api-key', (PROVIDER_HOST_ENVIRONMENT,))])
def test_binding_declaration_exposes_its_allowed_providers(name: str, providers: tuple[str, ...]) -> None:
    """A directory binding and an environment secret accept their own providers only."""
    registry = build_node_registry(example_manifest(), example_lock())
    assert registry.node(name).providers == providers


def test_base_consent_cannot_be_justified_by_project_advice() -> None:
    """The base-image node requires an answer without project-authored justification."""
    registry = build_node_registry(example_manifest(), example_lock())
    assert registry.node('base-image').accepts_justification is False


def test_host_recommendation_carries_its_reason() -> None:
    """A project recommendation exposes its own justification on the host-access node."""
    registry = build_node_registry(example_manifest(), example_lock())
    node = registry.node('docker-daemon')
    assert node.accepts_justification is True
    assert node.description == 'Required for the full test suite.'


def test_unknown_node_lists_the_declared_vocabulary() -> None:
    """Unknown names are refused with the missing name and known vocabulary."""
    registry = build_node_registry(example_manifest(), example_lock())
    with pytest.raises(ProjectConfigurationError) as failure:
        registry.node('does-not-exist')
    assert "'does-not-exist'" in str(failure.value)
    assert 'runtime.memory-limit' in str(failure.value)


def test_wrong_carrier_family_names_the_right_spelling() -> None:
    """A directory cannot be answered as a scalar; the diagnostic names the proper carrier."""
    registry = build_node_registry(example_manifest(), example_lock())
    with pytest.raises(ProjectConfigurationError, match='answered with --bind, not --set'):
        registry.answerable('home', CARRIER_FAMILY_SET)


@pytest.mark.parametrize('name,binding,expected', [
    ('home', 'host-directory:/state/x:y', (PROVIDER_HOST_DIRECTORY, '/state/x:y')),
    ('codex/openai-api-key', 'host-environment:KEY', (PROVIDER_HOST_ENVIRONMENT, 'KEY')),
])
def test_bind_values_split_on_the_first_colon_only(name: str, binding: str, expected: tuple[str, str]) -> None:
    """Provider parsing retains colons inside a directory value and accepts environment names."""
    registry = build_node_registry(example_manifest(), example_lock())
    assert registry.split_bind_value(name, binding) == expected


@pytest.mark.parametrize('name,binding,message', [
    ('codex/openai-api-key', 'host-directory:/somewhere', 'host-environment:VALUE'),
    ('home', '/no/provider/prefix', 'host-directory:VALUE'),
])
def test_bind_value_rejects_wrong_or_missing_provider(name: str, binding: str, message: str) -> None:
    """A binding with a missing or incompatible provider is refused with the expected form."""
    registry = build_node_registry(example_manifest(), example_lock())
    with pytest.raises(ProjectConfigurationError, match=message):
        registry.split_bind_value(name, binding)


def test_a_name_declared_twice_fails_at_construction() -> None:
    """A scalar declaration cannot reuse the name of a component binding."""
    manifest = example_manifest()
    manifest['configuration']['values']['home'] = {'type': 'string', 'description': 'Collision.'}
    with pytest.raises(ProjectConfigurationError, match='declared twice'):
        build_node_registry(manifest, example_lock())
