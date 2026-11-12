"""Delivery and isolation contracts for the browser and IntelliJ components."""
from pathlib import Path
import stat
import tomllib
import zipfile

import pytest

from devcapsule.compat import CliError
from devcapsule.components.browser_artifacts import extract_zip
from devcapsule.components.intellij import DEFINITION as IDEA
from devcapsule.components.pycharm import DEFINITION as PYCHARM
from devcapsule.components.playwright import DEFINITION as PLAYWRIGHT
from devcapsule.components.playwright_pin import PIN
from devcapsule.materialization import parse_locked_environment, _ancillary_contributions
from devcapsule.platforms import Platform
from devcapsule.resolution_matrix import MATRICES

pytestmark = pytest.mark.legacy


def test_intellij_selects_its_own_surface_and_browser() -> None:
    lock = tomllib.loads(MATRICES[Platform.LINUX_AMD64].resolve(["java-ide", "java", "browser-automation"]).render_lock())
    environment = parse_locked_environment(lock)
    assert lock["components"]["interactive-surface"] == "intellij"
    assert environment is not None
    assert IDEA.runtime_template().component.configuration["launcher"] == "bin/idea.sh"
    assert IDEA.runtime_template().component.configuration["properties_environment_variable"] == "IDEA_PROPERTIES"
    assert PYCHARM.runtime_template().component.configuration["launcher"] == "bin/pycharm.sh"
    assert IDEA.runtime_template().component.id != PYCHARM.runtime_template().component.id
    assert IDEA.runtime_template().logical_slot_name("config") == "intellij/config"
    assert PYCHARM.runtime_template().logical_slot_name("config") == "pycharm/config"
    # Names match the adapter contract; namespace is the owning component id.
    assert IDEA.runtime_template().persistence.state_slots == PYCHARM.runtime_template().persistence.state_slots


def test_browser_contribution_installs_only_verified_wheels_offline(tmp_path: Path) -> None:
    artifacts = PLAYWRIGHT.locked_artifacts(PIN, "linux-amd64")
    assert len(artifacts) == 7
    assert all(len(item.sha256) == 64 for item in artifacts)
    contributions = _ancillary_contributions(tuple((tmp_path / str(i), item) for i, item in enumerate(artifacts)), ())
    assert contributions[0].exports == ("/opt/playwright",)
    text = repr(contributions)
    assert "--no-index --no-deps" in text
    assert "python3 -m venv" in text
    assert "/opt/playwright/browsers/chromium-1243" in text
    assert PLAYWRIGHT.secret_inputs() == ()
    assert PLAYWRIGHT.runtime_template().persistence.state_slots == ()


@pytest.mark.parametrize("entry,mode", [("../outside", 0), ("/absolute", 0), ("a\\b", 0), ("link", stat.S_IFLNK | 0o777)])
def test_browser_zip_rejects_paths_and_links_before_extracting(tmp_path: Path, entry: str, mode: int) -> None:
    archive = tmp_path / "browser.zip"
    with zipfile.ZipFile(archive, "w") as output:
        info = zipfile.ZipInfo(entry)
        info.external_attr = mode << 16
        output.writestr(info, "bad")
    with pytest.raises(CliError, match="Unsafe"):
        extract_zip(archive, tmp_path / "extracted")
    assert not (tmp_path / "extracted").exists()


def test_browser_zip_preserves_executable_without_special_mode_bits(tmp_path: Path) -> None:
    archive = tmp_path / "browser.zip"
    with zipfile.ZipFile(archive, "w") as output:
        info = zipfile.ZipInfo("chrome/chrome")
        info.external_attr = (stat.S_IFREG | 0o6755) << 16
        output.writestr(info, "binary")
    root = extract_zip(archive, tmp_path / "extracted")
    assert (root / "chrome/chrome").stat().st_mode & 0o7777 == 0o755
