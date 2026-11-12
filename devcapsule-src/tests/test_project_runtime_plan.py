from __future__ import annotations

import hashlib
import json
from pathlib import Path

from devcapsule.container_runtime.contract import (
    ComponentRuntimeTemplate,
    RuntimePlan,
)
from devcapsule.materialization import (
    ArtifactSpec,
    LockedEnvironment,
    canonical_json,
    component_runtime_template,
    formation_descriptor,
    parse_locked_environment,
)
from devcapsule.configuration.storage import (
    ResolvedProject,
)
from devcapsule.project_runtime_plan import project_runtime_plan
from devcapsule_runtime.contract import RuntimePlan as LegacyRuntimePlan
import pytest

pytestmark = pytest.mark.legacy


def selected_project(tmp_path: Path) -> tuple[ResolvedProject, LockedEnvironment]:
    lock = {
        "platform": "linux-amd64",
        "base": {
            "reference": f"docker.io/example/base@sha256:{'b' * 64}",
            "identity": "sha256:base",
        },
        "components": {
            "interactive-surface": "pycharm",
            "pycharm": {
                "version": "2026.2.0.1",
                "variant": "professional",
                "delivery-policy": "local-materialization",
                "url": "https://example.test/pycharm.tar.gz",
                "sha256": "a" * 64,
            },
        },
        "materialization": {
            "recipe": "jetbrains-local-materialization",
            "recipe-version": "1",
        },
    }
    host_state = tmp_path / "sensitive-host-state"
    selected = ResolvedProject(
        root=tmp_path / "private-checkout",
        manifest={"project": {"mount": "/workspace/project"}},
        lock_path=tmp_path / "private-checkout" / ".devcapsule" / "lock",
        lock=lock,
        checkout_path=tmp_path / "private-config" / "checkout.toml",
        checkout={
            "authorization": {"network": {"value": "host", "secret-marker": "do-not-copy"}},
            "configuration": {
                "bindings": {"host-directory": {"pycharm/config": str(host_state)}}
            },
        },
        resolution_path=tmp_path / "private-config" / "resolved.toml",
        resolution={
            "runtime": {"component": "pycharm", "project-mount": "/workspace/project"},
            "state": {"bindings": {"pycharm/config": str(host_state)}},
            "authorization": {"network": "host"},
        },
    )
    return selected, parse_locked_environment(lock)


def test_project_runtime_plan_contains_only_in_container_contract(tmp_path: Path) -> None:
    selected, locked = selected_project(tmp_path)
    plan = project_runtime_plan(
        selected,
        locked,
        uid=1234,
        gid=2345,
        user="developer",
    )

    assert plan.version == 1
    assert plan.project_path == "/workspace/project"
    assert plan.home == "/home/devcapsule"
    assert plan.identity.uid == 1234
    assert plan.identity.gid == 2345
    assert plan.identity.user == "developer"
    assert plan.component.id == "pycharm"
    assert plan.component.adapter == "jetbrains"
    assert plan.slots_by_name() == {
        "pycharm/config": "/ide-config",
        "pycharm/plugins": "/ide-plugins",
        "pycharm/system": "/ide-project-state/system",
        "pycharm/log": "/ide-project-state/log",
        "pycharm/cache": "/home/devcapsule/.cache",
    }

    encoded = plan.to_json()
    assert RuntimePlan.from_json(encoded) == plan
    assert str(tmp_path) not in encoded
    assert "sensitive-host-state" not in encoded
    assert "do-not-copy" not in encoded
    assert "authorization" not in encoded
    assert "host-directory" not in encoded


def test_runtime_plan_and_formation_use_the_same_component_template(tmp_path: Path) -> None:
    selected, locked = selected_project(tmp_path)
    plan = project_runtime_plan(
        selected,
        locked,
        uid=1000,
        gid=1000,
        user="developer",
    )
    template_mapping = component_runtime_template()
    template = ComponentRuntimeTemplate.from_mapping(template_mapping)
    artifact = ArtifactSpec(
        version="2026.2.0.1",
        variant="professional",
        url="https://example.test/pycharm.tar.gz",
        sha256="a" * 64,
    )
    descriptor = formation_descriptor(
        platform="linux-amd64",
        base_identity="sha256:base",
        artifact=artifact,
    )
    expected_digest = hashlib.sha256(canonical_json(template_mapping).encode()).hexdigest()

    assert plan.component == template.component
    assert descriptor["runtime"]["component-template-sha256"] == expected_digest
    assert json.loads(plan.to_json())["component"] == {
        "id": template.component.id,
        "adapter": template.component.adapter,
        "configuration": dict(template.component.configuration),
        "environment": dict(template.component.environment),
    }


def test_runtime_plan_round_trips_named_host_integration_without_host_source(
    tmp_path: Path,
) -> None:
    selected, locked = selected_project(tmp_path)
    plan = project_runtime_plan(
        selected,
        locked,
        uid=1000,
        gid=1000,
        user="developer",
    ).with_host_integration("browser-open")

    encoded = plan.to_json()

    assert RuntimePlan.from_json(encoded) == plan
    assert json.loads(encoded)["host_integrations"] == ["browser-open"]
    assert "host-open.sock" not in encoded


def test_project_runtime_plan_includes_locked_codex_component(tmp_path: Path) -> None:
    selected, locked = selected_project(tmp_path)
    selected.lock["components"]["codex"] = {
        "version": "0.145.0",
        "delivery-policy": "local-materialization",
        "npm-package": "@openai/codex",
        "url": "https://example.test/codex-0.145.0.tgz",
        "sha256": "b" * 64,
        "artifacts": {
            "linux-amd64": {
                "npm-package": "@openai/codex-linux-x64",
                "url": "https://example.test/codex-0.145.0-linux-x64.tgz",
                "sha256": "c" * 64,
            }
        },
    }
    plan = project_runtime_plan(selected, locked, uid=1000, gid=1000, user="developer")

    assert "codex/home" not in plan.slots_by_name()
    assert plan.ancillary_components[0].id == "codex"
    assert plan.component_environment() == {
        "CODEX_HOME": "/home/devcapsule/.codex",
        "JAVA_TOOL_OPTIONS": "-Dide.browser.jcef.sandbox.enable=false",
    }
    encoded = plan.to_json()
    legacy = LegacyRuntimePlan.from_json(encoded)
    assert "codex/home" not in legacy.slots_by_name()
    assert "OPENAI_API_KEY" not in encoded
    assert "auth.json" not in encoded
