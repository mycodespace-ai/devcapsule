from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

import pytest

from devcapsule.compat import CliError
from devcapsule.components.claude_code import (
    CLAUDE_CODE_AUTHORIZATION,
    CLAUDE_CODE_TERMS_URL,
)
from devcapsule.environment_realization import realize_environment
from devcapsule.materialization import ImageDetails
from devcapsule.configuration.storage import (
    ResolvedProject,
)
from devcapsule.configuration.authorization import (
    authorization_declarations,
)
from devcapsule.configuration.file_formats import (
    canonical_digest,
)

pytestmark = pytest.mark.legacy


BASE_REFERENCE = f"docker.io/example/devcapsule-base@sha256:{'b' * 64}"
CANONICAL_IMAGE = "devcapsule-local-pycharm:0123456789abcdef0123"


def resolved_project(
    tmp_path: Path,
    *,
    authorized: bool = True,
    local_base: tuple[str, str] | None = None,
) -> ResolvedProject:
    lock = {
        "platform": "linux-amd64",
        "base": {"reference": BASE_REFERENCE, "identity": "sha256:base"},
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
    checkout = {}
    if authorized:
        reference = local_base[0] if local_base is not None else BASE_REFERENCE
        base_authorization = {
            "reference": reference,
            "lock-digest": canonical_digest(lock),
        }
        if local_base is not None:
            base_authorization["image-id"] = local_base[1]
        checkout = {
            "authorization": {
                "base-image": base_authorization,
            }
        }
    return ResolvedProject(
        root=tmp_path / "project",
        manifest={"project": {"creator": "example", "slug": "project"}},
        lock_path=tmp_path / "project" / ".devcapsule" / "devcapsule.linux-amd64.lock",
        lock=lock,
        checkout_path=tmp_path / "checkout.toml",
        checkout=checkout,
        resolution_path=tmp_path / "resolved.toml",
        resolution={"runtime": {"component": "pycharm"}},
    )


def base_image(reference: str = BASE_REFERENCE, identity: str = "sha256:base") -> ImageDetails:
    return ImageDetails(
        reference=reference,
        identity=identity,
        labels={
            "devcapsule.image.managed": "true",
            "devcapsule.metadata.version": "1",
            "devcapsule.image.kind": "base",
        },
        operating_system="linux",
        architecture="amd64",
    )


def completed_image() -> ImageDetails:
    return ImageDetails(
        reference=CANONICAL_IMAGE,
        identity="sha256:environment",
        labels={"devcapsule.materialization.identity": "f" * 64},
        operating_system="linux",
        architecture="amd64",
    )


def select_claude_code(selected: ResolvedProject, *, authorized: bool) -> None:
    components = selected.lock["components"]
    assert isinstance(components, dict)
    components["claude-code"] = {
        "version": "2.1.227",
        "delivery-policy": "local-materialization",
        "acquisition-authorization": CLAUDE_CODE_AUTHORIZATION,
        "terms-url": CLAUDE_CODE_TERMS_URL,
        "artifacts": {
            "linux-amd64": {
                "url": "https://downloads.claude.ai/example/claude",
                "sha256": "c" * 64,
            }
        },
    }
    authorization = selected.checkout["authorization"]
    assert isinstance(authorization, dict)
    base = authorization["base-image"]
    assert isinstance(base, dict)
    base["lock-digest"] = canonical_digest(selected.lock)
    if authorized:
        declaration = authorization_declarations(selected.manifest, selected.lock)[
            CLAUDE_CODE_AUTHORIZATION
        ]
        authorization[CLAUDE_CODE_AUTHORIZATION] = {
            "value": True,
            "recommendation-digest": declaration.recommendation_digest,
        }


@pytest.mark.parametrize("created", [False, True])
def test_realize_environment_reuses_or_builds_canonical_image(
    tmp_path: Path, created: bool
) -> None:
    selected = resolved_project(tmp_path)
    base = base_image()
    completed = completed_image()
    obtain = Mock(return_value=base)
    inspect = Mock()
    require = Mock(return_value=completed)
    build = Mock()
    materialize = Mock(return_value=(CANONICAL_IMAGE, created))

    realized = realize_environment(
        selected,
        root=tmp_path / "cache",
        obtain_image=obtain,
        inspect_image=inspect,
        require_image=require,
        build=build,
        materialize=materialize,
    )

    assert realized.image == completed
    assert realized.base == base
    assert realized.created is created
    assert realized.explicit_base_override is False
    obtain.assert_called_once_with(BASE_REFERENCE)
    require.assert_called_once_with(CANONICAL_IMAGE)
    assert materialize.call_args.kwargs["base_reference"] == BASE_REFERENCE
    assert materialize.call_args.kwargs["base_identity"] == "sha256:base"
    assert materialize.call_args.kwargs["platform"] == "linux-amd64"
    assert materialize.call_args.kwargs["cache_root"] == (tmp_path / "cache").resolve()
    assert materialize.call_args.kwargs["inspect_image"] is inspect
    assert materialize.call_args.kwargs["build"] is build


@pytest.mark.parametrize("local", [False, True])
def test_realization_reads_trust_but_preserves_a_local_override(tmp_path: Path, monkeypatch, local: bool) -> None:
    from devcapsule.configuration.storage import write_settings
    from devcapsule.configuration.trust import BASE_REPOSITORY, HomeTrust, channels_for
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    identity = "sha256:" + "c" * 64
    override = ("local/base:mine", identity) if local else None
    selected = resolved_project(tmp_path, authorized=True, local_base=override)
    select_claude_code(selected, authorized=False)
    selected.lock["base"]["reference"] = BASE_REPOSITORY + "@sha256:" + "b" * 64
    if not local:
        selected.checkout.clear()
    trust = HomeTrust()
    for channel in channels_for(selected.lock).values():
        trust = trust.with_channel(channel)
    write_settings({"trust": trust.document()})
    reference = override[0] if override else selected.lock["base"]["reference"]
    base = base_image(reference, identity if local else "sha256:base")
    obtain = Mock(return_value=base)
    materialize = Mock(return_value=(CANONICAL_IMAGE, False))
    result = realize_environment(selected, root=tmp_path / "cache", obtain_image=obtain,
                                 inspect_image=Mock(), require_image=Mock(return_value=completed_image()),
                                 build=Mock(), materialize=materialize)
    assert result.base_reference == reference and result.explicit_base_override is local
    obtain.assert_called_once_with(reference)
    assert materialize.call_args.kwargs["base_reference"] == reference
    # Neither a trusted base nor a trusted vendor may override a checkout denial.
    selected.checkout.setdefault("authorization", {})[CLAUDE_CODE_AUTHORIZATION] = {
        "value": False,
        "recommendation-digest": authorization_declarations(selected.manifest, selected.lock)[CLAUDE_CODE_AUTHORIZATION].recommendation_digest,
    }
    obtain.reset_mock()
    with pytest.raises(CliError, match="denied"):
        realize_environment(selected, obtain_image=obtain)
    obtain.assert_not_called()


def test_realize_environment_requires_exact_locked_base_authorization(tmp_path: Path) -> None:
    selected = resolved_project(tmp_path, authorized=False)
    obtain = Mock()
    materialize = Mock()

    with pytest.raises(CliError, match="config authorize base-image"):
        realize_environment(
            selected,
            obtain_image=obtain,
            materialize=materialize,
        )

    obtain.assert_not_called()
    materialize.assert_not_called()


def test_realize_environment_requires_explicit_claude_download_authorization(
    tmp_path: Path,
) -> None:
    selected = resolved_project(tmp_path)
    select_claude_code(selected, authorized=False)
    obtain = Mock()
    materialize = Mock()

    with pytest.raises(CliError, match="claude-code-download"):
        realize_environment(selected, obtain_image=obtain, materialize=materialize)

    obtain.assert_not_called()
    materialize.assert_not_called()


def test_realize_environment_allows_terms_bound_claude_download_authorization(
    tmp_path: Path,
) -> None:
    selected = resolved_project(tmp_path)
    select_claude_code(selected, authorized=True)
    materialize = Mock(return_value=(CANONICAL_IMAGE, True))

    realized = realize_environment(
        selected,
        obtain_image=Mock(return_value=base_image()),
        inspect_image=Mock(),
        require_image=Mock(return_value=completed_image()),
        build=Mock(),
        materialize=materialize,
    )

    assert realized.created is True
    artifacts = materialize.call_args.kwargs["ancillary_artifacts"]
    claude = next(item for item in artifacts if item.component_id == "claude-code")
    assert claude.artifact_format == "file"
    assert claude.destination == "/opt/claude/bin/claude"


def test_realize_environment_allows_explicit_managed_base_override(tmp_path: Path) -> None:
    selected = resolved_project(tmp_path, authorized=False)
    local_reference = "local/devcapsule-base:test"
    base = base_image(local_reference, "sha256:local-base")
    completed = completed_image()

    realized = realize_environment(
        selected,
        base_override=local_reference,
        root=tmp_path / "cache",
        obtain_image=Mock(return_value=base),
        inspect_image=Mock(),
        require_image=Mock(return_value=completed),
        build=Mock(),
        materialize=Mock(return_value=(CANONICAL_IMAGE, False)),
    )

    assert realized.base_reference == local_reference
    assert realized.base.identity == "sha256:local-base"
    assert realized.explicit_base_override is True


def test_realize_environment_uses_authorized_local_base_bound_to_image_id(
    tmp_path: Path,
) -> None:
    local_reference = "devcapsule-local-base:v022"
    local_identity = f"sha256:{'c' * 64}"
    selected = resolved_project(
        tmp_path,
        local_base=(local_reference, local_identity),
    )
    obtain = Mock(return_value=base_image(local_reference, local_identity))
    materialize = Mock(return_value=(CANONICAL_IMAGE, False))

    realized = realize_environment(
        selected,
        root=tmp_path / "cache",
        obtain_image=obtain,
        inspect_image=Mock(),
        require_image=Mock(return_value=completed_image()),
        build=Mock(),
        materialize=materialize,
    )

    assert realized.base_reference == local_reference
    assert realized.base.identity == local_identity
    assert realized.explicit_base_override is True
    obtain.assert_called_once_with(local_reference)
    assert materialize.call_args.kwargs["base_identity"] == local_identity


def test_realize_environment_rejects_retagged_authorized_local_base(tmp_path: Path) -> None:
    local_reference = "devcapsule-local-base:v022"
    authorized_identity = f"sha256:{'c' * 64}"
    selected = resolved_project(
        tmp_path,
        local_base=(local_reference, authorized_identity),
    )
    materialize = Mock()

    with pytest.raises(CliError, match="identity mismatch"):
        realize_environment(
            selected,
            obtain_image=Mock(
                return_value=base_image(local_reference, f"sha256:{'d' * 64}")
            ),
            materialize=materialize,
        )

    materialize.assert_not_called()


def test_realize_environment_rejects_manual_alternative_published_base(
    tmp_path: Path,
) -> None:
    alternative = f"docker.io/example/other-base@sha256:{'d' * 64}"
    selected = resolved_project(
        tmp_path,
        local_base=(alternative, f"sha256:{'c' * 64}"),
    )

    with pytest.raises(CliError, match="no longer the project's recommendation"):
        realize_environment(selected, obtain_image=Mock())


def test_realize_environment_propagates_canonical_conflict_without_launch(
    tmp_path: Path,
) -> None:
    selected = resolved_project(tmp_path)
    require = Mock()
    conflict = CliError("canonical image has conflicting metadata")

    with pytest.raises(CliError, match="conflicting metadata"):
        realize_environment(
            selected,
            root=tmp_path / "cache",
            obtain_image=Mock(return_value=base_image()),
            inspect_image=Mock(),
            require_image=require,
            build=Mock(),
            materialize=Mock(side_effect=conflict),
        )

    require.assert_not_called()
