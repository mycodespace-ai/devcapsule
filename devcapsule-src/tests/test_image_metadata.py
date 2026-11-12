from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import patch

from devcapsule.images.metadata import list_local_images, managed_labels
import pytest

pytestmark = pytest.mark.legacy


def fake_image(
    image_id: str,
    tags: tuple[str, ...],
    labels: dict[str, str],
    *,
    size: int = 1024,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=image_id,
        repo_tags=list(tags),
        config=SimpleNamespace(labels=labels),
        created=datetime(2026, 8, 1, tzinfo=UTC),
        size=size,
    )


def test_list_local_images_selects_managed_labels_and_groups_aliases() -> None:
    labels = dict(managed_labels("base", "devcapsule-base:debug-v019"))
    labels.update(
        {
            "devcapsule.base.recipe": "ubuntu-24.04",
            "devcapsule.base.recipe-version": "1",
            "devcapsule.base.recipe-status": "ready",
            "devcapsule.pex.sha256": "a" * 64,
            "devcapsule.source.revision": "abc123",
        }
    )
    managed = fake_image(
        "sha256:1234567890abcdef",
        ("devcapsule-base:debug-v019", "local/base:alias"),
        labels,
        size=1024**3,
    )
    unrelated = fake_image("sha256:fedcba", ("devcapsule-looking:latest",), {})

    with patch("devcapsule.images.metadata.docker.image.list", return_value=[managed, unrelated]):
        records = list_local_images()

    assert len(records) == 1
    assert records[0].kind == "base"
    assert records[0].canonical_name == "devcapsule-base:debug-v019"
    assert records[0].aliases == ("local/base:alias",)
    assert records[0].image_id == "1234567890ab"
    assert records[0].recipe == "ubuntu-24.04@1"
    assert records[0].size == "1.0 GiB"


def test_list_local_images_marks_wip_base_recipe() -> None:
    labels = dict(managed_labels("base", "devcapsule-base:cuda"))
    labels.update(
        {
            "devcapsule.base.recipe": "nvidia-cuda-devel",
            "devcapsule.base.recipe-version": "1",
            "devcapsule.base.recipe-status": "wip",
            "devcapsule.pex.sha256": "a" * 64,
            "devcapsule.source.revision": "abc123",
        }
    )

    with patch(
        "devcapsule.images.metadata.docker.image.list",
        return_value=[fake_image("sha256:cafe", ("devcapsule-base:cuda",), labels)],
    ):
        records = list_local_images()

    assert records[0].recipe == "nvidia-cuda-devel@1 [WIP]"


def test_list_local_images_keeps_unknown_and_invalid_metadata_visible() -> None:
    unknown = fake_image(
        "sha256:1111",
        ("unknown:latest",),
        {
            "devcapsule.image.managed": "true",
            "devcapsule.metadata.version": "99",
            "devcapsule.image.kind": "base",
        },
    )
    invalid = fake_image(
        "sha256:2222",
        ("invalid:latest",),
        {"devcapsule.image.managed": "true", "devcapsule.metadata.version": "1"},
    )

    with patch("devcapsule.images.metadata.docker.image.list", return_value=[unknown, invalid]):
        records = list_local_images()

    assert {record.kind for record in records} == {"unsupported-metadata", "invalid-metadata"}


def test_list_local_images_includes_legacy_only_when_requested() -> None:
    legacy = fake_image(
        "sha256:3333",
        ("mycodespace.ai/pycharm:debug-v018",),
        {"devcapsule.configuration": "pycharm"},
    )

    with patch("devcapsule.images.metadata.docker.image.list", return_value=[legacy]):
        assert list_local_images() == ()
        records = list_local_images(include_legacy=True)

    assert len(records) == 1
    assert records[0].kind == "legacy"
    assert records[0].component == "pycharm"
