from __future__ import annotations

import inspect
import tomllib

import pytest

from devcapsule.components import ComponentDefinition
from devcapsule.compat import CliError
from devcapsule.components.codex import (
    CODEX_CONFIG_SEED,
    CODEX_PACKAGE,
    DEFINITION,
    CodexComponent,
    codex_bin,
    codex_installation,
    runtime_template,
)
from devcapsule.components.pycharm import PyCharmComponent
from devcapsule.container_runtime.contract import Identity, RuntimePlan
from devcapsule.configuration.bindings import (
    component_secret_inputs,
    configuration_binding_declarations,
)

pytestmark = pytest.mark.legacy


def locked_components() -> dict[str, object]:
    return {
        "components": {
            "interactive-surface": "pycharm",
            "pycharm": {},
            "codex": {
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
            },
        }
    }


def test_built_in_components_explicitly_implement_abstract_contract() -> None:
    assert inspect.isabstract(ComponentDefinition)
    assert issubclass(CodexComponent, ComponentDefinition)
    assert issubclass(PyCharmComponent, ComponentDefinition)
    assert isinstance(DEFINITION, ComponentDefinition)

    incomplete_component = type("IncompleteComponent", (ComponentDefinition,), {})
    assert inspect.isabstract(incomplete_component)
    with pytest.raises(TypeError, match="abstract"):
        incomplete_component()


def test_codex_implements_component_contract_and_declares_the_npm_packages() -> None:
    definition: ComponentDefinition = DEFINITION
    meta, platform = definition.locked_artifacts(
        locked_components()["components"]["codex"],  # type: ignore[index]
        "linux-amd64",
    )

    assert definition.id == "codex"
    assert definition.capability == "codex-agent"
    # Both tarballs install into one versioned npm project under /opt; the
    # meta package brings the launcher npm links into node_modules/.bin,
    # which is what the image PATH gains.
    assert codex_installation("0.145.0") == "/opt/codex/0.145.0"
    assert codex_bin("0.145.0") == "/opt/codex/0.145.0/node_modules/.bin"
    for declaration in (meta, platform):
        assert declaration.version == "0.145.0"
        assert declaration.artifact_format == "npm-package"
        assert declaration.destination == "/opt/codex/0.145.0"
        assert declaration.archive_member is None
        assert declaration.permissions == 0o644
    assert meta.npm_package == CODEX_PACKAGE == "@openai/codex"
    assert meta.url == "https://example.test/codex-0.145.0.tgz"
    assert meta.sha256 == "b" * 64
    assert meta.environment == (("PATH", "/opt/codex/0.145.0/node_modules/.bin:${PATH}"),)
    assert platform.npm_package == "@openai/codex-linux-x64"
    assert platform.url == "https://example.test/codex-0.145.0-linux-x64.tgz"
    assert platform.sha256 == "c" * 64
    assert platform.environment == ()


def test_codex_seeds_a_yolo_configuration_into_a_fresh_home_slot() -> None:
    (seed,) = DEFINITION.state_seeds()

    assert seed.slot == "home"
    assert seed.relative_path == "config.toml"
    assert seed.content == CODEX_CONFIG_SEED
    # Owner ruling 2026-09-05: the capsule is the sandbox. The seed is a
    # complete, valid TOML document whose keys are all top-level, so the
    # tables codex appends later cannot capture them.
    parsed = tomllib.loads(seed.content)
    assert parsed == {
        "approval_policy": "never",
        "sandbox_mode": "danger-full-access",
        "use_legacy_landlock": True,
    }
    first_key_line = next(
        line for line in seed.content.splitlines() if line and not line.startswith("#")
    )
    assert first_key_line.startswith("approval_policy")
    assert "[" not in seed.content.replace("[table]", "")


def test_codex_lock_metadata_must_name_the_meta_package_and_platform_alias() -> None:
    metadata = dict(locked_components()["components"]["codex"])  # type: ignore[index, arg-type]
    metadata["npm-package"] = "@openai/codex-fork"
    with pytest.raises(CliError, match="components.codex.npm-package must be '@openai/codex'"):
        DEFINITION.locked_artifacts(metadata, "linux-amd64")

    metadata = dict(locked_components()["components"]["codex"])  # type: ignore[index, arg-type]
    metadata["artifacts"] = {"linux-amd64": {"url": "https://example.test/x.tgz", "sha256": "c" * 64}}
    with pytest.raises(CliError, match="artifacts.linux-amd64.npm-package"):
        DEFINITION.locked_artifacts(metadata, "linux-amd64")

    with pytest.raises(CliError, match="no artifact for 'linux-arm64'"):
        DEFINITION.locked_artifacts(
            locked_components()["components"]["codex"],  # type: ignore[index]
            "linux-arm64",
        )


def test_codex_component_derives_environment_from_credential_state() -> None:
    template = runtime_template()
    slot = template.persistence.state_slots[0]
    assert template.component.environment == {"CODEX_HOME": "/home/devcapsule/.codex"}
    assert DEFINITION.state_environment()[0].state_slot == "home"
    assert slot.name == "home"
    assert slot.sensitivity == "credentials"
    assert slot.home_overlay is True
    assert slot.permissions == "0700"


def test_runtime_plan_combines_ancillary_state_and_environment() -> None:
    from devcapsule.components.pycharm import runtime_template as pycharm_template

    plan = RuntimePlan.for_component(
        pycharm_template(),
        project_path="/workspace/project",
        home="/home/devcapsule",
        identity=Identity(1000, 1000),
        ancillary_templates=(runtime_template(),),
    )
    assert plan.slots_by_name()["codex/home"] == "/home/devcapsule/.codex"
    assert plan.component_environment() == {
        "CODEX_HOME": "/home/devcapsule/.codex",
        "JAVA_TOOL_OPTIONS": "-Dide.browser.jcef.sandbox.enable=false",
    }
    assert RuntimePlan.from_json(plan.to_json()) == plan


def test_catalog_exposes_codex_state_and_optional_secret_metadata() -> None:
    lock = locked_components()
    codex_home = configuration_binding_declarations(lock)["codex/home"]
    secret = component_secret_inputs(lock)["codex/openai-api-key"]

    assert codex_home.container_path == "/home/devcapsule/.codex"
    assert codex_home.sensitivity == "credentials"
    assert secret.environment_variable == "OPENAI_API_KEY"
    assert secret.required is False
    assert secret.exposure == "container-environment"
