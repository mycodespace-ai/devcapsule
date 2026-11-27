"""HostAccess value contracts for the ``ssh-proxy`` grant and its retired name ``github-ssh``."""
from typing import Any

import pytest

from devcapsule.configuration.file_formats import ProjectConfigurationError
from devcapsule.configuration.review import HostAccess


def test_the_ssh_proxy_is_denied_without_an_explicit_answer() -> None:
    """Default host access never exposes host SSH authentication."""
    assert HostAccess().ssh_proxy is False


def test_a_recorded_denial_overrides_an_earlier_grant() -> None:
    """Overlaying a denial withdraws the proxy without changing other host choices."""
    access = HostAccess(ssh_proxy="id_work", host_browser=True)
    result = access.overlay({'ssh-proxy': False})
    assert result.ssh_proxy is False
    assert result.host_browser is True


@pytest.mark.parametrize('grant', [True, 'default', 'id_work', '~/keys/deploy', '/keys/deploy'])
def test_a_run_once_answer_grants_the_proxy_with_the_key_it_names(grant: Any) -> None:
    """Every grant, by bool, by the default word, by key name or by key path, becomes the effective answer unchanged."""
    result = HostAccess().overlay({'ssh-proxy': grant})

    assert result.ssh_proxy == grant and type(result.ssh_proxy) is type(grant)


@pytest.mark.parametrize('answer', [True, False])
def test_an_answer_under_the_retired_name_is_the_ssh_proxys(answer: bool) -> None:
    """``github-ssh``, as a resolution written before the rename holds it, is read as ``ssh-proxy`` with the same value."""
    assert HostAccess(ssh_proxy=not answer).overlay({'github-ssh': answer}).ssh_proxy is answer


@pytest.mark.parametrize('answers', [{'github-ssh': True, 'ssh-proxy': 'id_work'}, {'ssh-proxy': 'id_work', 'github-ssh': True}])
def test_the_current_name_outranks_the_retired_one_in_the_same_answers(answers: dict[str, Any]) -> None:
    """With both names answered, in either order, the answer under ``ssh-proxy`` stands."""
    assert HostAccess().overlay(answers).ssh_proxy == 'id_work'


@pytest.mark.parametrize('name', ['ssh-proxy', 'github-ssh'])
@pytest.mark.parametrize('value', ['true', 'Default', 'keys/deploy', '', 1, None])
def test_an_answer_that_is_not_in_its_recorded_form_is_refused_under_the_name_it_was_given(name: str, value: Any) -> None:
    """A word that stands for a bool, a word in another letter case, a relative path, an empty string and a
    value of another type are no recorded answer; the refusal names the node as the document spelled it."""
    with pytest.raises(ProjectConfigurationError) as refused:
        HostAccess().overlay({name: value})

    assert str(refused.value) == (
        f"Host decision {name!r} must be false, true, 'default', a key name or a key path; found {value!r}."
    )


def test_an_unknown_host_decision_is_still_refused() -> None:
    """A name that is neither a host access nor a retired name of one is refused as before."""
    with pytest.raises(ProjectConfigurationError, match="Unknown legacy host decision 'ssh-agent'"):
        HostAccess().overlay({'ssh-agent': True})
