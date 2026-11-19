"""HostAccess value contracts for the GitHub transport grant."""
from devcapsule.configuration.review import HostAccess


def test_github_access_is_denied_without_an_explicit_answer() -> None:
    """Default host access never exposes host GitHub authentication."""
    assert HostAccess().github_ssh is False


def test_a_recorded_denial_overrides_an_earlier_grant() -> None:
    """Overlaying a denial withdraws GitHub access without changing other host choices."""
    access = HostAccess(github_ssh=True, host_browser=True)
    result = access.overlay({'github-ssh': False})
    assert result.github_ssh is False
    assert result.host_browser is True


def test_a_run_once_answer_enables_github_access() -> None:
    """An explicit boolean grant becomes the launcher's effective GitHub access."""
    assert HostAccess().overlay({'github-ssh': True}).github_ssh is True


def test_host_ide_defaults_to_denied() -> None:
    """An unanswered host IDE node never starts a host editor."""
    assert HostAccess().host_ide is False


def test_host_ide_is_orthogonal_to_display_and_docker() -> None:
    """Host IDE authorization changes neither Docker access, host X11, networking nor sudo."""
    access = HostAccess(docker_daemon='host-socket', host_x11=True, network='host', development_sudo=True)
    result = access.overlay({'host-ide': True})
    assert result.host_ide is True
    assert result.docker_daemon == access.docker_daemon
    assert result.host_x11 == access.host_x11
    assert result.network == access.network
    assert result.development_sudo == access.development_sudo
