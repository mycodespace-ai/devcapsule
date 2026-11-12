"""PyCharm image-build spec and python-on-whales backend orchestration."""

from __future__ import annotations

import contextlib
import tempfile
from dataclasses import dataclass
from pathlib import Path

from devcapsule.compat import CliError
from devcapsule.images.build import (
    AptPackagesComponent,
    BaseImageComponent,
    BuildComponent,
    BuildxImageBuilder,
    DirectoryComponent,
    EntrypointComponent,
    EnvComponent,
    ExecComponent,
    FileComponent,
    ImageBuildSpec,
    LabelComponent,
    normalize_pycharm_source,
    resource_to_tempdir,
)
from devcapsule.images.tooling import NODE_CURRENT_BIN, node_tooling_component
from devcapsule.platforms import Platform

DEFAULT_BASE_IMAGE = "ubuntu:24.04"
DEFAULT_IMAGE = "pycharm-isolated:latest"

BASE_APT_PACKAGES = (
    "ca-certificates",
    "curl",
    "wget",
    "xz-utils",
    "git",
    "openssh-client",
    "gnupg2",
    "xauth",
    "build-essential",
    "make",
    "cmake",
    "pkg-config",
    "gcc",
    "g++",
    "gdb",
    "lldb",
    "python3",
    "python-is-python3",
    "python3-pip",
    "python3-venv",
    "python3-dev",
    "netcat-openbsd",
    "dnsutils",
    "iproute2",
    "iputils-ping",
    "traceroute",
    "procps",
    "psmisc",
    "lsof",
    "strace",
    "tcpdump",
    "socat",
    "telnet",
    "whois",
    "file",
    "jq",
    "ripgrep",
    "fd-find",
    "fzf",
    "shellcheck",
    "tree",
    "less",
    "nano",
    "sudo",
    "libpq5",
    "libpq-dev",
    # Redistributable under the PostgreSQL License, so the published base can
    # carry it and projects declare the postgresql-client component instead of
    # acquiring a client per developer.
    "postgresql-client",
    "tini",
    "docker.io",
    "docker-buildx",
    "docker-compose-v2",
    "gosu",
    "libx11-6",
    "libxext6",
    "libxrender1",
    "libxtst6",
    "libxi6",
    "libxrandr2",
    "libxss1",
    "libxkbfile1",
    "libgtk-3-0",
    "libnss3",
    "libnspr4",
    "libasound2t64",
    "libfontconfig1",
    "libfreetype6",
    "libdbus-1-3",
    "xdg-utils",
    "fonts-dejavu",
    "fonts-liberation",
    "libgl1",
    "libglx-mesa0",
    "libgl1-mesa-dri",
    "mesa-utils",
    "vim",
)

DEFAULT_ENV = (
    ("PATH", f"{NODE_CURRENT_BIN}:${{PATH}}"),
    ("PROJECT_PATH", "/workspace/project"),
    ("IDE_GLOBAL_SETTINGS_PATH", "/ide-global-settings"),
    ("IDE_PROJECT_STATE_PATH", "/ide-project-state"),
    ("HOME", "/ide-global-settings/home"),
    ("XDG_CONFIG_HOME", "/ide-global-settings/home/.config"),
    ("XDG_CACHE_HOME", "/ide-project-state/home/.cache"),
    ("XDG_DATA_HOME", "/ide-global-settings/home/.local/share"),
    ("QT_X11_NO_MITSHM", "1"),
    ("_JAVA_AWT_WM_NONREPARENTING", "1"),
    ("LIBGL_ALWAYS_SOFTWARE", "1"),
    ("MESA_LOADER_DRIVER_OVERRIDE", "llvmpipe"),
    ("LIBGL_DRI3_DISABLE", "1"),
)


@dataclass(frozen=True)
class PycharmImageBuildOptions:
    pycharm: Path
    image: str = DEFAULT_IMAGE
    base_image: str = DEFAULT_BASE_IMAGE
    network: str = "default"
    extra_apt_packages: tuple[str, ...] = ()


def parse_pycharm_build_options(
    *,
    pycharm: Path,
    image: str,
    base_image: str,
    network: str,
    extra_apt_packages: tuple[str, ...],
) -> PycharmImageBuildOptions:
    resolved_source = pycharm.expanduser().resolve()
    if not resolved_source.exists():
        raise CliError(f"PyCharm source path does not exist: {resolved_source}")
    return PycharmImageBuildOptions(
        pycharm=resolved_source,
        image=image,
        base_image=base_image,
        network=network,
        extra_apt_packages=extra_apt_packages,
    )


def build_pycharm_image(options: PycharmImageBuildOptions, builder: BuildxImageBuilder | None = None) -> int:
    builder = builder or BuildxImageBuilder()
    with contextlib.ExitStack() as stack:
        assets_dir = Path(stack.enter_context(resource_to_tempdir("devcapsule.assets.pycharm")))
        build_root = Path(stack.enter_context(tempfile.TemporaryDirectory(prefix="devcapsule-pycharm-build-")))
        pycharm_root = normalize_pycharm_source(options.pycharm, build_root)
        spec = build_pycharm_image_spec(options, pycharm_root=pycharm_root, assets_root=assets_dir)
        builder.build(spec, platform=Platform.current(), network=options.network)
    return 0


def build_pycharm_image_spec(
    options: PycharmImageBuildOptions,
    *,
    pycharm_root: Path,
    assets_root: Path,
) -> ImageBuildSpec:
    components: list[BuildComponent] = [
        BaseImageComponent(options.base_image),
        AptPackagesComponent(BASE_APT_PACKAGES + tuple(options.extra_apt_packages)),
        DirectoryComponent(source=pycharm_root, destination="/opt/pycharm"),
        FileComponent(source=assets_root / "entrypoint.sh", destination="/usr/local/bin/entrypoint.sh", permissions=0o755),
        FileComponent(
            source=assets_root / "bootstrap-project.sh",
            destination="/usr/local/bin/docker4ide-bootstrap-project",
            permissions=0o755,
        ),
        FileComponent(
            source=assets_root / "check-runtime-deps.sh",
            destination="/usr/local/bin/docker4ide-check-runtime-deps",
            permissions=0o755,
        ),
        FileComponent(
            source=assets_root / "image-assets" / "vibe-coding-process.md",
            destination="/usr/local/share/docker4ide/vibe-coding-process.md",
            permissions=0o644,
        ),
        ExecComponent(
            args=(
                "sh",
                "-euxc",
                "chmod +x /opt/pycharm/bin/pycharm.sh "
                "&& ln -s /opt/pycharm/bin/pycharm.sh /usr/local/bin/pycharm "
                "&& printf '%%ide-sudo ALL=(ALL) NOPASSWD:ALL\\n' > /etc/sudoers.d/ide-sudo "
                "&& chmod 0440 /etc/sudoers.d/ide-sudo "
                "&& mkdir -p /ide-config /var/lib/docker /usr/local/share/docker4ide",
            ),
        ),
        node_tooling_component(),
        EnvComponent(DEFAULT_ENV),
        LabelComponent((("devcapsule.configuration", "pycharm"), ("devcapsule.builder", "python-on-whales"))),
        EntrypointComponent(("/usr/bin/tini", "--", "/usr/local/bin/entrypoint.sh")),
    ]
    return ImageBuildSpec(image=options.image, base_image=options.base_image, components=tuple(components))
