"""Unit tests of ``devcapsule/images/base.py``: the base build's checks before it hands the plan to the builder.

The builder and the public-source verifier are fakes; the PEX is a fixture under ``tmp_path``.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

import pytest

from devcapsule.compat import CliError
from devcapsule.images.base import BaseImageBuildOptions, build_base_image
from devcapsule.platforms import Platform
from tests.test_base_image import pex_fixture


def test_base_image_build_forwards_host_network_to_buildx(tmp_path: Path) -> None:
    """A base build verifies its source and hands the builder the named network and the capsule platform."""
    pex = pex_fixture(tmp_path / "devcapsule.pex")
    options = BaseImageBuildOptions(pex, "test-base:latest", source_revision="a" * 40)
    builder = Mock()
    source_verifier = Mock()

    build_base_image(options, builder=builder, platform=Platform.LINUX_AMD64, network="host",
                     source_verifier=source_verifier)

    source_verifier.assert_called_once()
    builder.build.assert_called_once()
    assert builder.build.call_args.args[0].image == "test-base:latest"
    assert builder.build.call_args.kwargs == {"network": "host", "platform": Platform.LINUX_AMD64}


def test_base_image_rejects_unreachable_revision_before_buildx(tmp_path: Path) -> None:
    """A source revision the verifier cannot reach stops the build before the builder starts."""
    pex = pex_fixture(tmp_path / "devcapsule.pex")
    options = BaseImageBuildOptions(pex, "test-base:latest", source_revision="a" * 40)
    builder = Mock()
    source_verifier = Mock(side_effect=CliError("source revision is not publicly reachable"))

    with pytest.raises(CliError, match="not publicly reachable"):
        build_base_image(options, builder=builder, platform=Platform.LINUX_AMD64, source_verifier=source_verifier)

    builder.build.assert_not_called()


def test_console_base_rejects_missing_source_before_starting_the_builder(tmp_path: Path) -> None:
    """A web-console base without public source stops before the builder starts, even with local source allowed."""
    pex = pex_fixture(tmp_path / "devcapsule.pex", revision="unknown", public=False)
    builder = Mock()
    with pytest.raises(CliError, match="--allow-local-source cannot supply the console source"):
        build_base_image(BaseImageBuildOptions(pex, allow_local_source=True), builder=builder,
                         platform=Platform.LINUX_AMD64)
    builder.build.assert_not_called()


def test_base_image_local_source_escape_hatch_skips_public_verification(tmp_path: Path) -> None:
    """Allowing local source skips the public-source verification and still builds."""
    pex = pex_fixture(tmp_path / "devcapsule.pex")
    builder = Mock()
    source_verifier = Mock()

    build_base_image(
        BaseImageBuildOptions(pex, allow_local_source=True),
        builder=builder,
        platform=Platform.LINUX_AMD64,
        source_verifier=source_verifier,
    )

    source_verifier.assert_not_called()
    builder.build.assert_called_once()
