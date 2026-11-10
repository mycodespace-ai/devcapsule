"""Embedded, inspectable source identity for a DevCapsule distribution."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from importlib.metadata import PackageNotFoundError, version as distribution_version
from importlib.resources import files
from importlib.resources.abc import Traversable
import json
from pathlib import Path
import re
import tomllib
from typing import Any, Mapping, Sequence
from zipfile import BadZipFile, ZipFile

__all__ = [
    "BuildInfo",
    "BuildInfoError",
    "build_info_json",
    "current_build_info",
    "is_built_distribution",
    "read_pex_build_info",
]


class BuildInfoError(ValueError):
    """A distribution's embedded build information is absent or malformed."""


@dataclass(frozen=True)
class BuildInfo:
    schema_version: int
    version: str
    source_repository: str
    source_revision: str
    source_url: str
    build_mnemonic: str = "unknown"

    @classmethod
    def from_mapping(cls, value: object) -> BuildInfo:
        if not isinstance(value, dict):
            raise BuildInfoError("build information must be a JSON object")
        schema_version = value.get("schema_version")
        if schema_version not in {1, 2}:
            raise BuildInfoError(f"unsupported build-information schema: {schema_version!r}")
        build_mnemonic = (
            "unknown" if schema_version == 1 else _string(value, "build_mnemonic")
        )
        if build_mnemonic != "unknown" and re.fullmatch(
            r"(?:local-)?v[0-9][0-9A-Za-z._-]*", build_mnemonic
        ) is None:
            raise BuildInfoError(
                "build information 'build_mnemonic' must be a release tag such as "
                "'v0.2.7', a local label such as 'v0.2.7-local' or "
                "'v0.2.7-local-linux-x86_64', or a v026-era label such as "
                "'v026' or 'local-v026'"
            )
        return cls(
            schema_version=schema_version,
            version=_string(value, "version"),
            source_repository=_string(value, "source_repository"),
            source_revision=_string(value, "source_revision"),
            source_url=_string(value, "source_url"),
            build_mnemonic=build_mnemonic,
        )

    @classmethod
    def from_json(cls, value: str) -> BuildInfo:
        try:
            document = json.loads(value)
        except json.JSONDecodeError as exc:
            raise BuildInfoError(f"build information is not valid JSON: {exc.msg}") from exc
        return cls.from_mapping(document)

    @property
    def has_public_revision(self) -> bool:
        if re.fullmatch(r"[0-9a-f]{40,64}", self.source_revision) is None:
            return False
        if re.fullmatch(r"https://github\.com/[^/]+/[^/]+", self.source_repository) is None:
            return False
        return self.source_url == f"{self.source_repository}/commit/{self.source_revision}"

    def to_mapping(self) -> dict[str, Any]:
        return asdict(self)


# In a source checkout the authored pyproject.toml sits beside the package;
# in any installed form it does not, and the installed metadata answers.
_SOURCE_PYPROJECT = Path(__file__).parents[1] / "pyproject.toml"


def is_built_distribution(
    *,
    record_paths: Sequence[Traversable | Path] | None = None,
) -> bool:
    """Whether this process runs from a ``scripts/build-pex.sh`` artifact rather than source.

    Only that script creates ``_build_info.json``, so the record's presence is
    the definition of a built artifact, in a PEX, a scie-wrapped PEX or an
    installed wheel of one alike; an editable or plain install of the source
    tree carries none. As in :func:`current_build_info`, a present-but-malformed
    record raises :class:`BuildInfoError` instead of masquerading as source.
    """

    return _embedded_build_info(record_paths) is not None


def current_build_info(
    *,
    record_paths: Sequence[Traversable | Path] | None = None,
    pyproject_path: Path | None = None,
    installed_version: str | None = None,
) -> BuildInfo:
    """Describe this running distribution: its stamped build, or its source form.

    Only ``scripts/build-pex.sh`` creates ``_build_info.json``, so the record's
    presence is the definition of a built artifact; a present-but-malformed
    record therefore stays an error rather than masquerading as source. In its
    absence this is a source-form run — nothing was built, so there is no build
    to describe — and the identity is derived: the version from the installed
    distribution metadata that ``pyproject.toml`` alone authors, and the
    ``v<version>-local`` mnemonic that marks an unbuilt source run.
    """

    embedded = _embedded_build_info(record_paths)
    if embedded is not None:
        return embedded
    return _source_form_build_info(
        pyproject_path=_SOURCE_PYPROJECT if pyproject_path is None else pyproject_path,
        installed_version=installed_version,
    )


def _embedded_build_info(
    record_paths: Sequence[Traversable | Path] | None = None,
) -> BuildInfo | None:
    """The stamped record of a built artifact, or ``None`` in a source-form run."""

    candidates: Sequence[Traversable | Path] = (
        record_paths
        if record_paths is not None
        else (
            files("devcapsule").joinpath("_build_info.json"),
            # Some editable installers expose the project root as the package's
            # resource location even though imports resolve to this source tree.
            # The sibling path preserves source/PEX command parity without
            # weakening the packaged-resource validation.
            Path(__file__).with_name("_build_info.json"),
        )
    )
    for candidate in candidates:
        try:
            text = candidate.read_text(encoding="utf-8")
        except OSError:
            continue
        return BuildInfo.from_json(text)
    return None


def _source_form_build_info(
    *,
    pyproject_path: Path,
    installed_version: str | None,
) -> BuildInfo:
    package_version = _authored_version(pyproject_path) or (
        installed_version if installed_version is not None else _installed_version()
    )
    return BuildInfo(
        schema_version=2,
        version=package_version,
        source_repository="unknown",
        source_revision="unknown",
        source_url="unknown",
        build_mnemonic=f"v{package_version}-local",
    )


def _authored_version(pyproject_path: Path) -> str | None:
    """The version pyproject.toml authors, when running from a source checkout.

    Preferred over installed metadata because an editable install freezes its
    metadata at install time: after a version bump it reports the old version
    until reinstalled, while the authored file is always current.
    """

    try:
        document = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return None
    project = document.get("project")
    if not isinstance(project, dict) or project.get("name") != "devcapsule":
        return None
    selected = project.get("version")
    return selected if isinstance(selected, str) and selected else None


def _installed_version() -> str:
    try:
        return distribution_version("devcapsule")
    except PackageNotFoundError as exc:
        raise BuildInfoError(
            "the devcapsule distribution is neither a source checkout nor "
            "installed, so no version metadata exists; install the package "
            "(for example 'pip install -e devcapsule-src') or run a built "
            "artifact"
        ) from exc


def read_pex_build_info(path: str | Path) -> BuildInfo:
    """Read metadata from a PEX without executing the selected artifact."""

    selected = Path(path)
    try:
        with ZipFile(selected) as archive:
            candidates = [name for name in archive.namelist() if name.endswith("/devcapsule/_build_info.json")]
            if len(candidates) != 1:
                raise BuildInfoError(
                    f"PEX must contain exactly one devcapsule/_build_info.json; found {len(candidates)}"
                )
            return BuildInfo.from_json(archive.read(candidates[0]).decode("utf-8"))
    except (OSError, BadZipFile, UnicodeDecodeError) as exc:
        raise BuildInfoError(f"cannot read build information from PEX {selected}: {exc}") from exc


def build_info_json(info: BuildInfo) -> str:
    return json.dumps(info.to_mapping(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _string(value: Mapping[str, Any], key: str) -> str:
    selected = value.get(key)
    if not isinstance(selected, str) or not selected or "\x00" in selected:
        raise BuildInfoError(f"build information {key!r} must be a non-empty string")
    return selected
