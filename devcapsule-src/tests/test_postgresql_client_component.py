from __future__ import annotations

import pytest

from devcapsule.compat import CliError
from devcapsule.components.catalog import COMPONENTS, selected_component_definitions
from devcapsule.components.postgresql_client import DEFINITION, runtime_template

pytestmark = pytest.mark.legacy


def lock_metadata(**overrides: object) -> dict[str, object]:
    metadata: dict[str, object] = {
        "version": "16",
        "delivery-policy": "base-image",
        "license": "PostgreSQL",
    }
    metadata.update(overrides)
    return metadata


def test_component_is_registered_in_the_catalog() -> None:
    assert COMPONENTS["postgresql-client"] is DEFINITION
    assert DEFINITION.capability == "postgresql-client"


def test_base_image_delivery_contributes_no_materialized_artifact() -> None:
    assert DEFINITION.locked_artifacts(lock_metadata(), "linux-amd64") == ()


def test_component_declares_no_state_or_secret_inputs() -> None:
    assert DEFINITION.state_environment() == ()
    assert DEFINITION.secret_inputs() == ()


def test_runtime_template_is_an_ancillary_component_without_state_slots() -> None:
    template = runtime_template()

    assert template.component.id == "postgresql-client"
    assert template.persistence.state_slots == ()


def test_local_materialization_delivery_is_rejected() -> None:
    with pytest.raises(CliError, match="delivery-policy must be 'base-image'"):
        DEFINITION.locked_artifacts(
            lock_metadata(**{"delivery-policy": "local-materialization"}), "linux-amd64"
        )


def test_wrong_license_is_rejected() -> None:
    with pytest.raises(CliError, match="license must be 'PostgreSQL'"):
        DEFINITION.locked_artifacts(lock_metadata(license="Proprietary"), "linux-amd64")


def test_missing_version_is_rejected() -> None:
    metadata = lock_metadata()
    del metadata["version"]

    with pytest.raises(CliError, match="version must be a non-empty string"):
        DEFINITION.locked_artifacts(metadata, "linux-amd64")


def test_declaring_artifacts_is_rejected() -> None:
    metadata = lock_metadata(artifacts={"linux-amd64": {"url": "https://example.invalid/psql"}})

    with pytest.raises(CliError, match="provided by the pinned base"):
        DEFINITION.locked_artifacts(metadata, "linux-amd64")


def test_lock_selecting_the_component_resolves_through_the_catalog() -> None:
    lock = {
        "components": {
            "interactive-surface": "pycharm",
            "pycharm": {"version": "2026.2.0.1"},
            "postgresql-client": lock_metadata(),
        }
    }

    interactive, ancillary = selected_component_definitions(lock)

    assert interactive.id == "pycharm"
    assert [component.id for component in ancillary] == ["postgresql-client"]
