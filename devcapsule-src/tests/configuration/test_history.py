"""Tests for the known-good configuration history (D-0008)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import stat

from devcapsule.configuration.history import (
    history_directory,
    record_known_good_configuration,
)
import pytest

pytestmark = pytest.mark.legacy


MANIFEST = {
    "project": {
        "creator": "https://github.com/example",
        "slug": "sample",
    }
}


def records(tmp_path: Path, checkout: str, resolved: str) -> tuple[Path, Path]:
    source = tmp_path / "config-tree"
    source.mkdir(exist_ok=True)
    checkout_path = source / "devcapsule.checkout.toml"
    resolved_path = source / "devcapsule.resolved.toml"
    checkout_path.write_text(checkout, encoding="utf-8")
    resolved_path.write_text(resolved, encoding="utf-8")
    return checkout_path, resolved_path


def env_for(tmp_path: Path) -> dict[str, str]:
    return {"HOME": str(tmp_path / "home"), "XDG_STATE_HOME": str(tmp_path / "state")}


def test_history_directory_is_outside_the_config_tree_and_url_encoded(
    tmp_path: Path,
) -> None:
    directory = history_directory(MANIFEST, env_for(tmp_path))

    assert directory == (
        tmp_path
        / "state"
        / "devcapsule"
        / "config-history"
        / "https%3A%2F%2Fgithub.com%2Fexample"
        / "sample"
    )


def test_first_success_records_one_private_generation(tmp_path: Path) -> None:
    env = env_for(tmp_path)
    checkout, resolved = records(tmp_path, 'a = "1"\n', 'r = "1"\n')

    created = record_known_good_configuration(
        MANIFEST, checkout, resolved, env, now=datetime(2026, 9, 1, tzinfo=timezone.utc)
    )

    assert created is not None
    assert created.name == "20260901T000000Z"
    assert (created / "devcapsule.checkout.toml").read_text(encoding="utf-8") == 'a = "1"\n'
    assert (created / "devcapsule.resolved.toml").read_text(encoding="utf-8") == 'r = "1"\n'
    metadata = (created / "snapshot.toml").read_text(encoding="utf-8")
    assert 'recorded-at = "20260901T000000Z"' in metadata
    assert "content-digest" in metadata
    for name in ("devcapsule.checkout.toml", "devcapsule.resolved.toml", "snapshot.toml"):
        assert stat.S_IMODE((created / name).stat().st_mode) == 0o600


def test_identical_content_never_creates_a_second_directory(tmp_path: Path) -> None:
    env = env_for(tmp_path)
    checkout, resolved = records(tmp_path, 'a = "1"\n', 'r = "1"\n')
    first = record_known_good_configuration(MANIFEST, checkout, resolved, env)

    assert first is not None
    assert record_known_good_configuration(MANIFEST, checkout, resolved, env) is None
    assert [entry.name for entry in first.parent.iterdir()] == [first.name]


def test_distinct_content_appends_and_dedup_covers_all_generations(
    tmp_path: Path,
) -> None:
    env = env_for(tmp_path)
    checkout, resolved = records(tmp_path, 'a = "1"\n', 'r = "1"\n')
    first = record_known_good_configuration(MANIFEST, checkout, resolved, env)
    assert first is not None

    checkout, resolved = records(tmp_path, 'a = "2"\n', 'r = "1"\n')
    second = record_known_good_configuration(MANIFEST, checkout, resolved, env)
    assert second is not None and second != first

    # Reverting to the first configuration finds its old generation: dedup
    # is against every recorded generation, not only the newest.
    checkout, resolved = records(tmp_path, 'a = "1"\n', 'r = "1"\n')
    assert record_known_good_configuration(MANIFEST, checkout, resolved, env) is None
    assert len(list(first.parent.iterdir())) == 2


def test_same_second_distinct_content_gets_a_counter(tmp_path: Path) -> None:
    env = env_for(tmp_path)
    moment = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
    checkout, resolved = records(tmp_path, 'a = "1"\n', 'r = "1"\n')
    first = record_known_good_configuration(MANIFEST, checkout, resolved, env, now=moment)
    checkout, resolved = records(tmp_path, 'a = "2"\n', 'r = "1"\n')
    second = record_known_good_configuration(MANIFEST, checkout, resolved, env, now=moment)

    assert first is not None and second is not None
    assert first.name == "20260901T120000Z"
    assert second.name == "20260901T120000Z-2"


def test_hand_edited_history_is_recomputed_not_trusted(tmp_path: Path) -> None:
    env = env_for(tmp_path)
    checkout, resolved = records(tmp_path, 'a = "1"\n', 'r = "1"\n')
    first = record_known_good_configuration(MANIFEST, checkout, resolved, env)
    assert first is not None
    # A user edited a recorded generation; its content no longer matches the
    # running configuration, so the running configuration records anew.
    (first / "devcapsule.checkout.toml").write_text('a = "edited"\n', encoding="utf-8")

    assert record_known_good_configuration(MANIFEST, checkout, resolved, env) is not None
