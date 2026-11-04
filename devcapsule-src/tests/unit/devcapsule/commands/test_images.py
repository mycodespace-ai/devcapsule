"""Unit tests of ``devcapsule/commands/images.py``: how ``images build`` maps its options onto the build.

The builder and the image inspection are fakes; nothing reaches Docker.
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from devcapsule import cli
from devcapsule.platforms import Platform


def test_images_build_base_maps_cli_options(tmp_path: Path, capsys) -> None:
    """A base build passes its options to the builder, with the platform this host creates projects for when none is named, and reports the image it built."""
    pex = tmp_path / "devcapsule.pex"
    pex.write_bytes(b"pex")
    inspected = SimpleNamespace(
        id="sha256:abc123",
        config=SimpleNamespace(
            labels={
                "devcapsule.base.recipe-version": "1",
                "devcapsule.pex.build-mnemonic": "v026",
                "devcapsule.pex.sha256": "a" * 64,
                "devcapsule.source.revision": "revision-1",
            }
        ),
    )

    with (
        patch("devcapsule.commands.images.build_base_image") as build,
        patch("devcapsule.commands.images.inspect_local_image", return_value=inspected),
    ):
        result = cli.main(
            [
                "images",
                "build",
                "--type",
                "base",
                "--tag",
                "devcapsule-base:debug-v019",
                "--from",
                "local-root:test",
                "--pex",
                str(pex),
                "--source-revision",
                "revision-1",
                "--network",
                "host",
            ]
        )

    assert result == 0
    options = build.call_args.args[0]
    assert options.pex == pex.resolve()
    assert options.image == "devcapsule-base:debug-v019"
    assert options.root_image == "local-root:test"
    assert options.source_revision == "revision-1"
    assert options.allow_local_source is False
    assert options.recipe == "ubuntu-24.04"
    assert build.call_args.kwargs == {"network": "host", "platform": Platform.LINUX_AMD64}
    output = capsys.readouterr().out
    assert "Image ID: sha256:abc123" in output
    assert "Runtime: supplied by the launcher" in output
    assert "Source verification: public GitHub commit reachable" in output
