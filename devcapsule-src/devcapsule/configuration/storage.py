"""Configuration file discovery, checkout ownership and atomic persistence."""

from __future__ import annotations
import re
import tempfile
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import quote
from devcapsule.platforms import Platform, UnsupportedPlatformError, XdgHomes

from .capabilities import RequirementDeparture
from .authorization import locked_base_reference
from .file_formats import ConfigurationFileKind, ProjectConfigurationError, canonical_digest, legacy_lock, validate_file_format, table, selected_version_lock, render_toml
from .manifest import current_manifest
from .nodes import build_node_registry


CHECKOUT_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


@dataclass(frozen=True)
class RegisteredCheckout:
    project_creator: str
    project_slug: str
    checkout_name: str
    checkout_path: Path
    record_path: Path
    status: str


@dataclass(frozen=True)
class ResolvedProject:
    root: Path
    manifest: dict[str, Any]
    lock_path: Path
    lock: dict[str, Any]
    checkout_path: Path
    checkout: dict[str, Any]
    resolution_path: Path
    resolution: dict[str, Any]
    # The named departures from the project's contract this launch runs
    # with (``RequirementDeparture``); empty for an ordinary launch.
    departures: tuple[RequirementDeparture, ...] = ()


def discover_project(path: Path) -> Path:
    candidate = path.expanduser().resolve()
    if candidate.is_file():
        candidate = candidate.parent
    for directory in (candidate, *candidate.parents):
        if (directory / ".devcapsule" / "devcapsule.toml").is_file():
            return directory
    raise ProjectConfigurationError(
        f"No .devcapsule/devcapsule.toml found from {candidate}; run 'devcapsule project init'."
    )


def load_toml(path: Path) -> dict[str, Any]:
    try:
        with path.open("rb") as stream:
            value = tomllib.load(stream)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ProjectConfigurationError(f"Cannot read {path}: {exc}") from exc
    return value


def load_checkout(path: Path, manifest: Mapping[str, Any], root: Path) -> dict[str, Any]:
    recover_activation(path)
    document = load_toml(path)
    validate_file_format(document, ConfigurationFileKind.checkout, path)
    recorded = table(document, "checkout").get("path")
    if not isinstance(recorded, str) or not recorded or Path(recorded).expanduser().resolve() != root:
        raise ProjectConfigurationError(f"{path} does not match observed checkout {root}.")
    identity = table(document, "project")
    if any(identity.get(key) != manifest["project"][key] for key in ("creator", "slug")):
        raise ProjectConfigurationError(f"{path} does not match the project's creator and slug.")
    return document


def load_resolution(path: Path) -> dict[str, Any]:
    document = load_toml(path)
    validate_file_format(document, ConfigurationFileKind.resolution, path)
    return document


def config_root(env: Mapping[str, str] | None = None) -> Path:
    return XdgHomes.from_environment(env).config


def settings_path(env: Mapping[str, str] | None = None) -> Path:
    """This home's settings file, the one a write goes to."""
    return config_root(env) / "settings.toml"


def settings_source(env: Mapping[str, str] | None = None) -> Path:
    """The settings file a read takes.

    Inside a capsule the launcher's settings arrive as a read-only mount. A
    capsule that has no settings of its own and names no home reads that
    mount, so that what it trusts and defaults to is what launched it; once
    it writes its own, or names a home, that home is the whole truth, as it
    is for a launcher the capsule runs.
    """
    from devcapsule.runtime_configuration import mounted_settings_path
    own = settings_path(env)
    if own.exists():
        return own
    mounted = mounted_settings_path(env)
    return mounted if mounted is not None and mounted.exists() else own


def launcher_release() -> str:
    from importlib.metadata import version
    return re.split(r"rc|\.dev|\+", version("devcapsule"), maxsplit=1)[0]


def launcher_meets_minimum(required: object) -> bool:
    """Compare three release integers; the file must name a complete release."""
    pattern = r"([0-9]+)\.([0-9]+)\.([0-9]+)"
    minimum = re.fullmatch(pattern, required) if isinstance(required, str) else None
    if minimum is None:
        raise ValueError("minimum-devcapsule must be a release version string (X.Y.Z)")
    own = re.fullmatch(pattern, launcher_release())
    if own is None:
        raise ValueError("the launcher must have a release version (X.Y.Z)")
    return tuple(map(int, own.groups())) >= tuple(map(int, minimum.groups()))


def validate_settings(document: Mapping[str, Any], path: Path) -> None:
    """Check reader admission before the schema or the settings themselves."""
    from .home import HomeDefaults
    from .trust import HomeTrust
    required = document.get("minimum-devcapsule")
    try:
        admitted = launcher_meets_minimum(required)
    except ValueError as exc:
        raise ProjectConfigurationError(f"{path}: {exc}") from exc
    from importlib.metadata import version
    own = version("devcapsule")
    if not admitted:
        raise ProjectConfigurationError(
            f"DevCapsule home {path.parent} requires DevCapsule {required}; this launcher is {own}. "
            "Get the release at https://github.com/ccozianu/devcapsule/releases."
        )
    schema = document.get("devcapsule-settings-schema-version")
    if type(schema) is not int or schema != 1:
        raise ProjectConfigurationError(f"{path}: unsupported schema version {schema!r}; this launcher reads 1.")
    try:
        HomeDefaults.read(document)
        HomeTrust.read(document)
    except ProjectConfigurationError as exc:
        raise ProjectConfigurationError(f"{path}: {exc}") from exc


def load_settings(env: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Read the single settings document; a missing home is empty."""
    path = settings_source(env)
    if not path.exists():
        return {}
    document = load_toml(path)
    validate_settings(document, path)
    return document


def load_trust(env: Mapping[str, str] | None = None) -> dict[str, Any]:
    return dict(table(load_settings(env), "trust"))


def write_settings(document: Mapping[str, Any], env: Mapping[str, str] | None = None) -> Path:
    """Merge changed tables, retain headers, and replace only changed content.

    Atomic replacement prevents partial reads. Concurrent updates of the same
    table use the last writer's value; this is not a transaction across launchers.
    """
    path = settings_path(env)
    before = load_settings(env)
    after = {**before, **document}
    after.setdefault("devcapsule-settings-schema-version", 1)
    after.setdefault("minimum-devcapsule", launcher_release())
    validate_settings(after, path)
    # A no-op keeps comments, spelling, permissions and timestamps intact.
    if all(before.get(key, {}) == after.get(key, {}) for key in set(before) | set(after)):
        return path
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    atomic_write(path, render_toml(after))
    return path


def checkout_directory(manifest: Mapping[str, Any], env: Mapping[str, str] | None = None) -> Path:
    project = manifest["project"]
    creator = quote(str(project["creator"]), safe="")
    slug = quote(str(project["slug"]), safe="")
    return config_root(env) / "projects" / creator / slug


def checkout_record_paths(
    manifest: Mapping[str, Any],
    project_root: Path,
    env: Mapping[str, str] | None = None,
) -> tuple[Path, Path]:
    """Select the default or named checkout record matching one canonical path."""

    directory = checkout_directory(manifest, env)
    default_input = directory / "devcapsule.checkout.toml"
    matched = find_checkout_record(manifest, project_root, env)
    if matched is not None:
        return matched, resolved_record_path(matched)
    if not default_input.exists():
        return default_input, resolved_record_path(default_input)
    raise ProjectConfigurationError(
        f"Project identity is already registered for another checkout in {directory}; "
        "run 'devcapsule project --path PATH checkout register NAME'."
    )


def find_checkout_record(
    manifest: Mapping[str, Any],
    project_root: Path,
    env: Mapping[str, str] | None = None,
) -> Path | None:
    directory = checkout_directory(manifest, env)
    default_input = directory / "devcapsule.checkout.toml"
    candidates = (default_input, *sorted((directory / "checkouts").glob("*.checkout.toml")))
    expected = project_root.expanduser().resolve()
    for candidate in candidates:
        if not candidate.is_file():
            continue
        try:
            value = load_toml(candidate)
        except ProjectConfigurationError:
            continue
        metadata = value.get("checkout", {})
        if not isinstance(metadata, dict):
            raise ProjectConfigurationError(f"{candidate}: checkout must be a table.")
        recorded = metadata.get("path")
        if recorded and Path(str(recorded)).expanduser().resolve() == expected:
            return candidate
    return None


def named_checkout_record_paths(
    manifest: Mapping[str, Any],
    name: str,
    env: Mapping[str, str] | None = None,
) -> tuple[Path, Path]:
    if not CHECKOUT_NAME_PATTERN.fullmatch(name):
        raise ProjectConfigurationError(
            "Checkout name must start with an alphanumeric character and contain only letters, digits, '.', '_', or '-'."
        )
    input_path = checkout_directory(manifest, env) / "checkouts" / f"{name}.checkout.toml"
    return input_path, resolved_record_path(input_path)


def checkout_name_for(manifest: Mapping[str, Any], input_path: Path, env: Mapping[str, str] | None = None) -> str:
    """The checkout's name from where its record lives.

    The unnamed record in the project's configuration directory is ``default``.
    For a record under its ``checkouts/`` directory, strip ``.checkout.toml``
    from the filename. A ``devcapsule.checkout.toml`` there is a named
    checkout called ``devcapsule``. The record stores no name key.
    """
    named = input_path.parent == checkout_directory(manifest, env) / "checkouts"
    return checkout_record_name(input_path, named=named)


def checkout_record_name(input_path: Path, *, named: bool = False) -> str:
    """Return the display name of a default or named checkout record.

    Callers identify records in the named-checkout directory explicitly:
    ``devcapsule.checkout.toml`` is also a valid named record there.
    """
    if not named and input_path.name == "devcapsule.checkout.toml":
        return "default"
    if input_path.name.endswith(".checkout.toml"):
        return input_path.name.removesuffix(".checkout.toml")
    raise ValueError(f"not a DevCapsule checkout record path: {input_path}")


def resolved_record_path(input_path: Path) -> Path:
    if input_path.name == "devcapsule.checkout.toml":
        return input_path.with_name("devcapsule.resolved.toml")
    if input_path.name.endswith(".checkout.toml"):
        return input_path.with_name(f"{input_path.name.removesuffix('.checkout.toml')}.resolved.toml")
    raise ValueError(f"not a DevCapsule checkout record path: {input_path}")


def registered_checkouts(env: Mapping[str, str] | None = None) -> tuple[RegisteredCheckout, ...]:
    """Enumerate valid developer-owned checkout records without scanning source trees."""

    projects_root = config_root(env) / "projects"
    records: list[RegisteredCheckout] = []
    if not projects_root.is_dir():
        return ()
    candidates = sorted(projects_root.rglob("*.checkout.toml"))
    for candidate in candidates:
        try:
            value = load_toml(candidate)
        except ProjectConfigurationError:
            continue
        if value.get("devcapsule-checkout-schema-version") != 1:
            continue
        project = value.get("project")
        checkout = value.get("checkout")
        if not isinstance(project, dict) or not isinstance(checkout, dict):
            continue
        creator = project.get("creator")
        slug = project.get("slug")
        raw_path = checkout.get("path")
        if not creator or not slug or not raw_path:
            continue
        source = Path(str(raw_path)).expanduser()
        name = checkout_name_for(value, candidate, env)
        if not source.exists():
            status = "missing"
        elif not (source / ".devcapsule" / "devcapsule.toml").is_file():
            status = "uninitialized"
        else:
            status = "ready"
        records.append(
            RegisteredCheckout(
                project_creator=str(creator),
                project_slug=str(slug),
                checkout_name=name,
                checkout_path=source,
                record_path=candidate,
                status=status,
            )
        )
    return tuple(
        sorted(
            records,
            key=lambda record: (
                record.project_creator,
                record.project_slug,
                record.checkout_name,
                str(record.checkout_path),
            ),
        )
    )


def atomic_write(path: Path, content: str, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # The staging file is private from creation, not merely after the bytes
    # have been written. A failed write/replace keeps the previous checkpoint.
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                     prefix=f".{path.name}.", delete=False) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(content)
            stream.flush()
            temporary.chmod(mode)
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)


def require_settled(root: Path) -> None:
    if (root / ".devcapsule" / ".capability-transaction.toml").exists():
        raise ProjectConfigurationError("Interrupted configuration edit; run 'devcapsule project config capabilities --recover'. No candidate is admitted until recovery.")


def manifest_for(project: Path) -> tuple[Path, dict[str, Any]]:
    """The project root and its manifest as this launcher reads it: schema 2, a schema-1 file upgraded in memory."""
    root = discover_project(project)
    require_settled(root)
    path = root / ".devcapsule" / "devcapsule.toml"
    return root, current_manifest(load_toml(path), path).document()


def manifest_source_digest(root: Path) -> str | None:
    """The digest of the manifest file as written, which checkpoints before scoped digests recorded.

    None when the file holds a TOML value the digest does not support; the
    freshness check then compares derived meaning instead.
    """
    try:
        return canonical_digest(load_toml(root / ".devcapsule" / "devcapsule.toml"))
    except ProjectConfigurationError:
        return None


def platform_lock_path(root: Path, platform: Platform) -> Path:
    """The path of the project's lock for ``platform``."""
    return root / ".devcapsule" / f"devcapsule.{platform}.lock"


def project_platform(root: Path) -> Platform:
    """The capsule platform this host runs the project at ``root`` as.

    The first platform this host runs that the project has a lock for, so
    Apple Silicon runs a project locked for linux-arm64 natively and one
    locked only for linux-amd64 under emulation; for a project with no such
    lock, the platform this host creates projects for. Reads only.
    """
    try:
        for platform in Platform.runnable():
            if platform_lock_path(root, platform).is_file():
                return platform
        return Platform.current()
    except UnsupportedPlatformError as exc:
        raise ProjectConfigurationError(str(exc)) from exc


def locked_platforms(root: Path) -> tuple[Platform, ...]:
    """Every platform the project at ``root`` has a lock for, on any host."""
    return tuple(platform for platform in Platform if platform_lock_path(root, platform).is_file())


def recommendation_lock_for(root: Path, manifest: Mapping[str, Any]) -> tuple[Path, dict[str, Any]]:
    """Load the committed lock of the platform this host runs the project as.

    The lock is the project-side record of one resolution: the version set and
    property defaults selected for one platform. It is a record, not a
    permission gate: loading it must never refuse ordinary work because some
    other project input changed. Drift between the manifest and a checkout's
    generated resolution belongs to the resolution layer
    (``fresh_resolved_project``), whose source digests name exactly what
    drifted and whose remedy — ``devcapsule project run`` — actually
    reconciles it. See "The Lock Is A Record, Not A Mandate" in
    ``engineering-docs/design-notes/devcapsule/v1-user-experience.md``.

    Committed locks may carry a ``manifest-digest`` of the whole manifest.
    This function once compared it and refused every dependent command after
    any manifest edit, fatally and with a remedy that could not help. The
    field is deliberately not read: a lock derives from the capability set and
    the platform, so no other manifest field may affect its validity (the
    scoped-digest principle), and R-COMPAT-001 forbids demanding user action
    to keep existing committed locks working.
    """

    platform = project_platform(root)
    path = platform_lock_path(root, platform)
    if not path.is_file():
        raise ProjectConfigurationError(
            f"Missing {path}: this project carries no platform lock for {platform}. "
            "The platform lock is authored on the project side and committed with the project; "
            "'devcapsule project init' adds it."
        )
    value = load_toml(path)
    validate_file_format(value, ConfigurationFileKind.lock, path)
    if "base" in value:
        locked_base_reference(value, source=str(path))
    # Every public consumer gets the same unambiguous vocabulary.
    from .capabilities import CapabilityPolicy
    policy = CapabilityPolicy.read(manifest)
    if legacy_lock(value) and not policy.optional and not policy.minimums:
        build_node_registry(manifest, value)
    return path, value


def composition_for(root: Path, manifest: Mapping[str, Any]) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    """The checkout's persistent software selection, before execution filtering.

    Return the project platform's shared lock path, the composed selection (the
    explicit version set, or the shared lock with personal pins laid over it)
    and the loaded checkout record, empty when the checkout is unregistered.
    A version set for another platform raises ProjectConfigurationError.
    """
    from .capability_selection import compose_lock
    record = find_checkout_record(manifest, root)
    checkout = load_checkout(record, manifest, root) if record is not None else {}
    selected = selected_version_lock(checkout)
    if selected is not None:
        platform = project_platform(root)
        if selected.get("platform") != str(platform):
            raise ProjectConfigurationError("Local version set is for another platform; follow the project explicitly.")
        path, shared = platform_lock_path(root, platform), selected
    else:
        path, shared = recommendation_lock_for(root, manifest)
    return path, compose_lock(manifest, shared, checkout), checkout


def selection_for(root: Path, manifest: Mapping[str, Any]) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    """The checkout's persistent selection and its effective lock for this host.

    Return the shared lock path, the composed selection from ``composition_for``
    and its execution projection. The projection must name a base this
    launcher knows and an IDE, or ProjectConfigurationError is raised with
    the command that chooses one. Optional omissions are printed as warnings.
    """
    from .capability_selection import effective_lock
    path, composed, checkout = composition_for(root, manifest)
    value = effective_lock(manifest, composed, checkout)
    if "base" in value:
        locked_base_reference(value)
    if not value.get("components", {}).get("interactive-surface"):
        raise ProjectConfigurationError(
            "Choose your IDE for this checkout: devcapsule project config ide IDE "
            "(python-ide, frontend-ide, vscode-ide, java-ide, eclipse-ide or dotnet-ide)."
        )
    build_node_registry(manifest, value)
    return path, composed, value


def lock_for(root: Path, manifest: Mapping[str, Any]) -> tuple[Path, dict[str, Any]]:
    """Effective software selection, independently of current host decisions."""
    path, _, value = selection_for(root, manifest)
    return path, value


_ACTIVATION_JOURNAL_SUFFIX = ".activation.toml"


def interrupted_activation(input_path: Path) -> bool:
    """Whether this checkout has an activation journal awaiting recovery."""
    return input_path.with_suffix(_ACTIVATION_JOURNAL_SUFFIX).exists()


def recover_activation(input_path: Path) -> None:
    """Finish or undo an interrupted two-file activation under serialized access.

    Checkout replacement is the commit point. No old authorization snapshot is
    used after the transaction: a later edit that differs from both endpoints
    causes refusal, never resurrection of a historical permission.
    """
    journal = input_path.with_suffix(_ACTIVATION_JOURNAL_SUFFIX)
    if not journal.exists():
        return
    transaction = load_toml(journal)
    current = input_path.read_text()
    if current == transaction["after-checkout"]:
        resolution = transaction["after-resolution"]
    elif current == transaction["before-checkout"]:
        resolution = transaction["before-resolution"]
    else:
        raise ProjectConfigurationError(f"Interrupted activation conflicts with a later edit; inspect {journal}. No choices were replaced.")
    atomic_write(resolved_record_path(input_path), resolution)
    journal.unlink()


def activate_configuration(input_path: Path, checkout: Mapping[str, Any], resolution: Mapping[str, Any]) -> None:
    """Publish a prepared choice and its derived plan recoverably."""
    recover_activation(input_path)
    output = resolved_record_path(input_path)
    journal = input_path.with_suffix(_ACTIVATION_JOURNAL_SUFFIX)
    transaction = {
        "before-checkout": input_path.read_text(),
        "before-resolution": output.read_text() if output.exists() else "",
        "after-checkout": render_toml(checkout),
        "after-resolution": render_toml(resolution),
    }
    atomic_write(journal, render_toml(transaction))
    try:
        atomic_write(output, transaction["after-resolution"])
        atomic_write(input_path, transaction["after-checkout"])
    except OSError:
        recover_activation(input_path)
        raise
    journal.unlink()
