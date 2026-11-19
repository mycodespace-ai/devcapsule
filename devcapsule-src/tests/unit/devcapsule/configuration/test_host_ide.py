"""The host IDE changes only the launch's surface, with pins from a supplied matrix."""
from copy import deepcopy
from pathlib import Path
import tomllib

import pytest

from devcapsule.components.catalog import COMPONENTS
from devcapsule.configuration.authorization import authorization_declarations
from devcapsule.configuration.file_formats import ProjectConfigurationError, canonical_digest
from devcapsule.configuration.host_ide import (
    apply_host_ide_surface, runtime_lock, split_surface_requested, validate_surface,
)
from devcapsule.configuration.model import Configuration
from devcapsule.configuration.storage import ResolvedProject
from devcapsule.environment_realization import omit_unavailable_optional
from devcapsule.platforms import Platform
from devcapsule.resolution_matrix import MATRICES, ResolutionMatrix, Capability, _BasePin, _ComponentPin, _VerifiedEdge


def matrix() -> ResolutionMatrix:
    return ResolutionMatrix(
        platform=Platform.LINUX_AMD64, matrix_version='test',
        bases=(_BasePin('base', 'family', {}, {'reference': 'test-base'}),),
        components={'xfce4-terminal': (_ComponentPin('xfce4-terminal', 'test', {'version': 'test', 'url': 'test-url'}),)},
        edges=(_VerifiedEdge('xfce4-terminal', 'test', 'family', 'test evidence'),), couplings=(),
        capability_table={'xfce4-terminal': Capability(('xfce4-terminal',), ide=True)},
        materialization={'xfce4-terminal': {'recipe': 'terminal-recipe', 'recipe-version': 'test'}},
    )


def test_runtime_substitution_preserves_inputs_and_other_components() -> None:
    """The launch substitutes a terminal pin and recipe without mutating the saved selection or base."""
    lock = {'platform': 'linux-amd64', 'base': {'reference': 'test-base'},
            'components': {'interactive-surface': 'vscode', 'vscode': {'version': 'selected'}, 'tool': {'version': 'chosen'}},
            'materialization': {'recipe': 'vscode-recipe'}}
    original = deepcopy(lock)
    result = runtime_lock(lock, matrix())
    assert lock == original
    assert result['base'] == lock['base']
    assert result['components'] == {'interactive-surface': 'xfce4-terminal', 'xfce4-terminal': {'version': 'test', 'url': 'test-url'},
                                    'tool': {'version': 'chosen'}}
    assert result['materialization'] == {'recipe': 'terminal-recipe', 'recipe-version': 'test'}


@pytest.mark.parametrize('surface', ['codium', 'pycharm', 'xfce4-terminal', None])
def test_other_surfaces_are_refused(surface: str | None) -> None:
    """The first slice refuses every resolved surface except VS Code, including VSCodium."""
    with pytest.raises(ProjectConfigurationError, match='supports vscode only'):
        validate_surface({'components': {'interactive-surface': surface}})


def test_other_base_families_are_refused() -> None:
    """A terminal pin cannot be applied to an unknown base family."""
    lock = {'platform': 'linux-amd64', 'base': {'reference': 'foreign-base'},
            'components': {'interactive-surface': 'vscode', 'vscode': {}}}
    with pytest.raises(ProjectConfigurationError, match='base family'):
        runtime_lock(lock, matrix())


def test_runtime_substitution_merges_unverified_combinations() -> None:
    """An experimental terminal note extends an existing unverified note instead of replacing it."""
    unverified_matrix = ResolutionMatrix(
        platform=Platform.LINUX_AMD64, matrix_version='test',
        bases=(_BasePin('base', 'family', {}, {'reference': 'test-base'}),),
        components={'xfce4-terminal': (_ComponentPin('xfce4-terminal', 'test', {'version': 'test', 'url': 'test-url'}),)},
        edges=(), couplings=(),
        capability_table={'xfce4-terminal': Capability(('xfce4-terminal',), ide=True)},
        materialization={'xfce4-terminal': {'recipe': 'terminal-recipe', 'recipe-version': 'test'}},
    )
    lock = {'platform': 'linux-amd64', 'base': {'reference': 'test-base'},
            'components': {'interactive-surface': 'vscode', 'vscode': {'version': 'selected'}},
            'materialization': {'recipe': 'vscode-recipe'},
            'unverified-combinations': 'custom-tool@1.0 on base'}
    result = runtime_lock(lock, unverified_matrix, allow_unverified=True)
    assert result['unverified-combinations'] == 'custom-tool@1.0 on base; xfce4-terminal test on base base'


def test_split_surface_flag_distinguishes_grant_from_denial() -> None:
    """An explicit false or none --authorize host-ide flag overrides a saved checkout grant to False."""
    manifest = {'project': {'name': 'demo'}}
    lock = {'components': {'interactive-surface': 'vscode'}}
    granted_checkout = {'authorization': {'host-ide': {'value': True}}}
    denied_checkout = {'authorization': {'host-ide': {'value': False}}}
    assert split_surface_requested(manifest, lock, granted_checkout, ()) is True
    assert split_surface_requested(manifest, lock, granted_checkout, (('host-ide', 'false'),)) is False
    assert split_surface_requested(manifest, lock, granted_checkout, (('host-ide', 'none'),)) is False
    assert split_surface_requested(manifest, lock, denied_checkout, (('host-ide', 'false'),)) is False
    assert split_surface_requested(manifest, lock, denied_checkout, (('host-ide', 'true'),)) is True
    assert split_surface_requested(manifest, lock, granted_checkout, (('host-ide', 'false'), ('host-ide', 'true'))) is True


def test_omitting_unavailable_optional_tool_preserves_host_ide_terminal() -> None:
    """Re-applying host-ide substitution after omitting an unavailable optional tool keeps xfce4-terminal."""
    manifest = {
        'devcapsule-schema-version': 2,
        'capabilities': {'required': ['python'], 'optional': ['claude-code-agent']},
        'project': {
            'name': 'demo',
            'slug': 'demo',
            'creator': 'mailto:test@example.test',
            'mount': '/workspace/demo',
        },
    }
    lock = tomllib.loads(MATRICES[Platform.LINUX_AMD64].resolve(['python', 'claude-code-agent', 'vscode-ide']).render_lock())
    declarations = authorization_declarations(manifest, lock)
    checkout = {
        'devcapsule-checkout-schema-version': 1,
        'project': {'creator': 'mailto:test@example.test', 'slug': 'demo'},
        'capabilities': {'selected': ['vscode-ide']},
        'authorization': {
            'base-image': {'reference': lock['base']['reference'], 'lock-digest': canonical_digest(lock)},
            'host-ide': {'value': True, 'recommendation-digest': declarations['host-ide'].recommendation_digest},
            'claude-code-download': {'value': True, 'recommendation-digest': declarations['claude-code-download'].recommendation_digest},
        },
    }
    resolution = Configuration(manifest, lock, checkout, {}).resolve().document()
    source_selected = ResolvedProject(
        root=Path('/tmp/demo'), manifest=manifest,
        lock_path=Path('/tmp/demo/.devcapsule/devcapsule.linux-amd64.lock'), lock=lock,
        checkout_path=Path('/tmp/demo/.devcapsule/checkout.toml'), checkout=checkout,
        resolution_path=Path('/tmp/demo/.devcapsule/resolution.toml'), resolution=resolution,
    )
    optional_url = COMPONENTS['claude-code'].locked_artifacts(
        source_selected.lock['components']['claude-code'], 'linux-amd64'
    )[0].url
    smaller = omit_unavailable_optional(source_selected, optional_url)
    assert smaller is not None
    assert set(source_selected.lock['components']) - set(smaller.lock['components']) == {'claude-code'}
    updated = apply_host_ide_surface(smaller, allow_unverified=False)
    assert updated.lock['components']['interactive-surface'] == 'xfce4-terminal'
    assert 'vscode' not in updated.lock['components']
    assert updated.resolution['runtime']['component'] == 'xfce4-terminal'
