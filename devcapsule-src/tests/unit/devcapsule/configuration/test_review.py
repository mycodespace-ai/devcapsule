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
