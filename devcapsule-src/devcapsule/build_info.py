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
from typing import Any, Callable, Mapping, Sequence
from zipfile import BadZipFile, ZipFile

__all__ = [
    "BuildInfo",
    "BuildInfoError",
    "build_info_json",
    "build_info_text",
    "current_build_info",
    "distribution_build_info",
    "embedded_build_info",
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


def is_built_distribution() -> bool:
    """Whether this process runs from a ``scripts/build-pex.sh`` artifact rather than source.

    Only that script creates ``_build_info.json``, so the record's presence is
    the definition of a built artifact, in a PEX, a scie-wrapped PEX or an
    installed wheel of one alike; an editable or plain install of the source
    tree carries none. As in :func:`current_build_info`, a present-but-malformed
    record raises :class:`BuildInfoError` instead of masquerading as source.
    """

    return embedded_build_info(_package_locations()) is not None


def current_build_info() -> BuildInfo:
    """Describe this running distribution: its stamped build, or its source form.

    This names where the running distribution keeps its package, its authored
    ``pyproject.toml`` and its installed metadata; :func:`distribution_build_info`
    decides from them.
    """

    return distribution_build_info(
        package_locations=_package_locations(),
        pyproject_path=_SOURCE_PYPROJECT,
        installed_version=_installed_version,
    )


def _package_locations() -> tuple[Traversable | Path, ...]:
    return (
        files("devcapsule"),
        # Some editable installers expose the project root as the package's
        # resource location even though imports resolve to this source tree.
        # The module's own directory preserves source/PEX command parity
        # without weakening the packaged-resource validation.
        Path(__file__).parent,
    )


def distribution_build_info(
    *,
    package_locations: Sequence[Traversable | Path],
    pyproject_path: Path,
    installed_version: Callable[[], str],
) -> BuildInfo:
    """Describe the distribution these locations belong to: its stamped build, or its source form.

    Only ``scripts/build-pex.sh`` creates ``_build_info.json``, so the record's
    presence in the package is the definition of a built artifact; a
    present-but-malformed record therefore stays an error rather than
    masquerading as source. In its absence this is a source-form run — nothing
    was built, so there is no build to describe — and the identity is derived:
    the version from ``pyproject_path`` when that is the authored file of a
    source checkout, else from ``installed_version``, which is asked only then;
    and the ``v<version>-local`` mnemonic that marks an unbuilt source run.
    """

    embedded = embedded_build_info(package_locations)
    if embedded is not None:
        return embedded
    package_version = _authored_version(pyproject_path) or installed_version()
    return BuildInfo(
        schema_version=2,
        version=package_version,
        source_repository="unknown",
        source_revision="unknown",
        source_url="unknown",
        build_mnemonic=f"v{package_version}-local",
    )


def embedded_build_info(package_locations: Sequence[Traversable | Path]) -> BuildInfo | None:
    """The stamped ``_build_info.json`` of the first of ``package_locations`` that holds a readable one, or ``None``."""

    for location in package_locations:
        try:
            text = location.joinpath("_build_info.json").read_text(encoding="utf-8")
        except OSError:
            continue
        return BuildInfo.from_json(text)
    return None


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


def build_info_text(info: BuildInfo) -> str:
    """The lines ``devcapsule version`` shows a person: the build, then where its source is."""

    return "\n".join((
        f"DevCapsule {info.build_mnemonic} (package {info.version})",
        f"Source repository: {info.source_repository}",
        f"Source revision: {info.source_revision}",
        f"Source URL: {info.source_url}",
    ))


def _string(value: Mapping[str, Any], key: str) -> str:
    selected = value.get(key)
    if not isinstance(selected, str) or not selected or "\x00" in selected:
        raise BuildInfoError(f"build information {key!r} must be a non-empty string")
    return selected
