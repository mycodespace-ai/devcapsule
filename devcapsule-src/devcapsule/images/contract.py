"""What a base image promises, kept apart from who built it.

A base image is a prebuilt OCI image that every capsule image names in its
``FROM`` line. Its consumers, the formation built on it and the components
validated to run there, rely on a set of promises: an operating-system line
and its library ABI, the toolchains present and where they live, whether a
contained display is available, and what the runtime expects of the image.
Those promises are the base's *contract*, and the recipe in ``base_image``
is the contract's text. The release of the tool that happened to execute
the recipe is provenance, recorded and shown, never the base's identity.

Compatibility follows the ordinary API rule. A recipe may add services and
stay in its *family*; a consumer validated on an older recipe of the family
still runs on a newer one. Removing or replacing a service, changing the OS
line, or requiring a runtime vocabulary older launchers cannot execute opens
a new family, and nothing validated on the old family carries over. D-0007
already validates component versions per family; this module names the rule
the matrix applies.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

REPOSITORY = "https://github.com/mycodespace-ai/devcapsule"
# Where the recipe lives now, written into new images as a label, and where
# it lived for every image built before the move of 2026-09-26.
RECIPE_SOURCE_PATH = "devcapsule-src/devcapsule/images/base.py"
LEGACY_RECIPE_SOURCE_PATH = "devcapsule-src/devcapsule/base_image.py"

FAMILY_LABEL = "devcapsule.base.recipe"
RECIPE_VERSION_LABEL = "devcapsule.base.recipe-version"
SERVICES_LABEL = "devcapsule.base.services"
DISPLAY_LABEL = "devcapsule.base.display"
RUNTIME_LABEL = "devcapsule.base.runtime"
BUILDER_LABEL = "org.opencontainers.image.version"
SOURCE_REVISION_LABEL = "devcapsule.source.revision"
RECIPE_SOURCE_LABEL = "devcapsule.base.recipe-source"
WEBCONSOLE_LABEL = "devcapsule.base.webconsole"
# Recipe 10 installs the console and labels its root; recipe 11 gives it the
# process monitor its pages need. A base before 11 has no console the launcher
# should announce, label or not.
WEBCONSOLE_RECIPE = 11


@dataclass(frozen=True)
class WebConsoleAvailability:
    """Whether a base promises a working web console, and which base it is.

    ``available`` is read from the base's labels before the launch, so the
    launcher announces the console, binds its port and waits for it only
    when the base can answer. ``base`` is the identity ``family@recipe`` for
    the message when it cannot, or ``None`` for an image without recipe
    labels.
    """

    available: bool
    base: str | None


def web_console_availability(labels: Mapping[str, str]) -> WebConsoleAvailability:
    """Read the console's promise from a base image's labels.

    Available when the base labels the console's root and its recipe is
    ``WEBCONSOLE_RECIPE`` or later. A missing label, a recipe below it, or no
    recipe labels at all mean no console for callers that use this result.
    The low-level launcher defaults to available when no result is supplied.
    The runtime checks only that the console interpreter exists; it does not
    check the recipe or the package's dependencies.
    """

    family = labels.get(FAMILY_LABEL)
    version = labels.get(RECIPE_VERSION_LABEL)
    base = f"{family}@{version}" if family and version else None
    recipe = int(version) if version and version.isdigit() else None
    available = bool(labels.get(WEBCONSOLE_LABEL)) and recipe is not None and recipe >= WEBCONSOLE_RECIPE
    return WebConsoleAvailability(available=available, base=base)

CONTAINED_DISPLAY = "contained"
HOST_X11_ONLY_DISPLAY = "host-x11-only"
LAUNCHER_SUPPLIED_RUNTIME = "launcher-supplied"
EMBEDDED_RUNTIME = "embedded"


@dataclass(frozen=True)
class BaseContract:
    """The promises a base makes. It changes only when the recipe changes."""

    family: str
    """The incompatible-change line, e.g. ``ubuntu-24.04``; the recipe's name."""
    recipe: int
    """Compatible evolution within the family; the recipe's version."""
    services: frozenset[str]
    """Capabilities the base satisfies without a component: ``python``, ``docker-cli``, ..."""
    display: str
    """``contained`` when the base carries its own display stack, else ``host-x11-only``."""
    runtime: str
    """``launcher-supplied`` when the launcher brings the executable; ``embedded`` for older bases."""

    @property
    def identity(self) -> str:
        return f"{self.family}@{self.recipe}"

    def accepts(self, validated_on: BaseContract) -> bool:
        """May a consumer validated on ``validated_on`` run on this base?

        Same family and a recipe at least as new: the newer recipe only added.
        Any other family is an incompatible change by definition.
        """
        return self.family == validated_on.family and self.recipe >= validated_on.recipe

    def extends(self, older: BaseContract) -> bool:
        """The additive rule a maintainer must keep: within a family, a newer
        recipe offers every service the older one offered."""
        return (
            self.family == older.family
            and self.recipe > older.recipe
            and older.services <= self.services
        )

    def describe(self) -> str:
        services = ", ".join(sorted(self.services)) or "no declared services"
        return (
            f"{self.identity}: recipe {self.recipe} of the {self.family} family "
            f"(services: {services}; display {self.display}; runtime {self.runtime})"
        )


@dataclass(frozen=True)
class Provenance:
    """Who executed the recipe. Informational: it is never an identity."""

    builder: str
    """The release mnemonic of the executable that built the image, e.g. ``v0.2.12-rc5``."""
    source_revision: str | None = None
    recipe_path: str = LEGACY_RECIPE_SOURCE_PATH
    """Where the recipe lived in the builder's source; new images label it."""

    @property
    def recipe_url(self) -> str:
        """A permalink to the recipe as it was when this image was built.

        Release mnemonics are immutable tags in the repository, so the tag
        alone locates the text; a recorded revision is more exact when known.
        """
        ref = self.source_revision or self.builder
        return f"{REPOSITORY}/blob/{ref}/{self.recipe_path}"

    def describe(self) -> str:
        return f"built by {self.builder}; recipe source: {self.recipe_url}"


@dataclass(frozen=True)
class BaseImage:
    """One built artifact under a contract."""

    contract: BaseContract
    reference: str
    """A registry reference at an immutable digest, or a local image ID."""
    built: Provenance

    def describe(self) -> str:
        return f"Base {self.contract.describe()} at {self.reference}, {self.built.describe()}."

    @classmethod
    def from_labels(
        cls,
        reference: str,
        labels: Mapping[str, str],
        *,
        services: frozenset[str] = frozenset(),
    ) -> BaseImage:
        """Reconstruct the image from the labels its build wrote.

        Every base build labels its family, recipe version, display and
        runtime; recipe 10 and later also label their services. For older
        images the caller supplies the services it knows, typically from the
        matrix pin for the same reference.
        """
        family = labels.get(FAMILY_LABEL)
        version = labels.get(RECIPE_VERSION_LABEL)
        if not family or not version or not version.isdigit():
            raise ValueError(f"{reference} carries no DevCapsule base recipe labels")
        labelled = labels.get(SERVICES_LABEL)
        contract = BaseContract(
            family=family,
            recipe=int(version),
            services=frozenset(part for part in labelled.split(",") if part) if labelled else services,
            display=labels.get(DISPLAY_LABEL, HOST_X11_ONLY_DISPLAY),
            runtime=labels.get(RUNTIME_LABEL, EMBEDDED_RUNTIME),
        )
        return cls(
            contract=contract,
            reference=reference,
            built=Provenance(
                builder=labels.get(BUILDER_LABEL, "unknown"),
                source_revision=labels.get(SOURCE_REVISION_LABEL),
                recipe_path=labels.get(RECIPE_SOURCE_LABEL, LEGACY_RECIPE_SOURCE_PATH),
            ),
        )
