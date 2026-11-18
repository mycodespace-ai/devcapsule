"""Check generated locks against the production configuration readers."""
from pathlib import Path

import pytest

from devcapsule.configuration.manifest import current_manifest
from devcapsule.configuration.nodes import build_node_registry
from devcapsule.configuration.storage import lock_for
from devcapsule.platforms import Platform
from devcapsule.resolution_matrix import MATRICES

pytestmark = pytest.mark.integration


def test_generated_lock_passes_the_real_loaders(tmp_path: Path) -> None:
    """A generated lock supplies the checkout, authorization and state nodes its components need."""
    project = tmp_path / "project"
    (project / ".devcapsule").mkdir(parents=True)
    need = ["python", "python-ide", "claude-code-agent", "codex-agent"]
    manifest = {
        "devcapsule-schema-version": 1,
        "capabilities": {"need": need},
        "project": {
            "name": "Example",
            "slug": "example",
            "creator": "https://github.com/example",
            "mount": "/workspace/example",
        },
    }
    (project / ".devcapsule" / "devcapsule.linux-amd64.lock").write_text(
        MATRICES[Platform.LINUX_AMD64].resolve(need).render_lock(), encoding="utf-8"
    )

    manifest = current_manifest(manifest, "manifest").document()
    lock_path, lock = lock_for(project, manifest)
    assert lock_path.name == "devcapsule.linux-amd64.lock"

    registry = build_node_registry(manifest, lock)
    assert registry.node("base-image").required is True
    assert registry.node("claude-code-download").family == "authorize"
    assert registry.node("codex/openai-api-key").providers == ("host-environment",)
    assert registry.node("pycharm/system").family == "bind"
