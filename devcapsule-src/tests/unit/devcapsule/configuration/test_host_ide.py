"""The host IDE changes only the launch's surface, with pins from a supplied matrix."""
from copy import deepcopy

import pytest

from devcapsule.configuration.host_ide import runtime_lock, validate_surface
from devcapsule.configuration.file_formats import ProjectConfigurationError
from devcapsule.platforms import Platform
from devcapsule.resolution_matrix import ResolutionMatrix, Capability, _BasePin, _ComponentPin, _VerifiedEdge


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
