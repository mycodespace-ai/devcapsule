"""The host IDE changes only the launch's surface, with pins from a supplied matrix."""
from copy import deepcopy
from pathlib import Path
import tomllib

import pytest

from devcapsule.configuration.file_formats import ProjectConfigurationError
from devcapsule.configuration.host_ide import (
    apply_host_ide_surface, runtime_lock, split_surface_requested, validate_surface,
)
from devcapsule.configuration.storage import ResolvedProject
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


@pytest.mark.parametrize(('checkout', 'flags', 'expected'), [
    ({'authorization': {'host-ide': {'value': True}}}, (), True),
    ({'authorization': {'host-ide': {'value': True}}}, (('host-ide', 'false'),), False),
    ({'authorization': {'host-ide': {'value': True}}}, (('host-ide', 'none'),), False),
    ({'authorization': {'host-ide': {'value': False}}}, (('host-ide', 'false'),), False),
    ({'authorization': {'host-ide': {'value': False}}}, (('host-ide', 'true'),), True),
    ({'authorization': {'host-ide': {'value': True}}}, (('host-ide', 'false'), ('host-ide', 'true')), True),
])
def test_split_surface_flag_distinguishes_grant_from_denial(
    checkout: dict, flags: tuple[tuple[str, str], ...], expected: bool,
) -> None:
    """An explicit --authorize host-ide override takes precedence over the checkout decision."""
    manifest = {'project': {'name': 'demo'}}
    lock = {'components': {'interactive-surface': 'vscode'}}
    assert split_surface_requested(manifest, lock, checkout, flags) is expected


def test_apply_host_ide_surface_updates_resolved_component_without_mutating_source() -> None:
    """Applying split surface swaps only vscode for xfce4-terminal in both lock and resolution without home I/O."""
    lock = tomllib.loads(MATRICES[Platform.LINUX_AMD64].resolve(['python', 'vscode-ide']).render_lock())
    selected = ResolvedProject(
        root=Path('/tmp/demo'),
        manifest={'project': {'name': 'demo'}},
        lock_path=Path('/tmp/demo/.devcapsule/devcapsule.linux-amd64.lock'),
        lock=lock,
        checkout_path=Path('/tmp/demo/.devcapsule/checkout.toml'),
        checkout={'capabilities': {'selected': ['vscode-ide']}},
        resolution_path=Path('/tmp/demo/.devcapsule/resolution.toml'),
        resolution={'runtime': {'component': 'vscode', 'project-mount': '/workspace/demo'}},
    )
    updated = apply_host_ide_surface(selected)
    assert selected.lock['components']['interactive-surface'] == 'vscode'
    assert selected.resolution['runtime']['component'] == 'vscode'
    assert updated.lock['components']['interactive-surface'] == 'xfce4-terminal'
    assert 'vscode' not in updated.lock['components']
    assert 'xfce4-terminal' in updated.lock['components']
    assert updated.resolution['runtime']['component'] == 'xfce4-terminal'
