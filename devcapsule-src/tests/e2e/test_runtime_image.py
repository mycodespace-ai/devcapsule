from __future__ import annotations

import json
import hashlib
import io
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import tarfile
import textwrap
import time
import tomllib
import uuid

import pytest

from devcapsule.images.base import BaseImageBuildOptions, build_base_image_spec, file_sha256
from devcapsule.components.pycharm import runtime_template as pycharm_runtime_template
from devcapsule.container_runtime.contract import DisplayPlan, Identity, RuntimePlan
from devcapsule.images.build import render_build_context
from devcapsule.materialization import ArtifactSpec, ImageDetails, ensure_materialized_surface

pytestmark = pytest.mark.legacy

DEFAULT_BASE_IMAGE = str(tomllib.loads(
    (Path(__file__).resolve().parents[3] / ".devcapsule/devcapsule.linux-amd64.lock").read_text()
)["base"]["reference"])


# Image builds here install apt packages (the display stack), so the suite
# accepts the same network choice as the nox base build (`--build-network`).
BUILD_NETWORK_ARGS = (
    ["--network", os.environ["DEVCAPSULE_E2E_BUILD_NETWORK"]]
    if os.environ.get("DEVCAPSULE_E2E_BUILD_NETWORK")
    else []
)


def command(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    """Run a command, and when it fails, fail with its output in the message.

    ``subprocess.run(check=True)`` raises without the captured streams, so a
    failing ``docker build`` used to leave nothing to diagnose (the rc2
    release run of 2026-09-24). The output stays captured for the callers
    that read it; only the failure path changes.
    """
    completed = subprocess.run(args, check=False, text=True, capture_output=True)
    if check and completed.returncode != 0:
        raise AssertionError(
            f"{' '.join(args)!r} exited {completed.returncode}\n"
            f"--- stdout ---\n{completed.stdout[-4000:]}\n--- stderr ---\n{completed.stderr[-4000:]}"
        )
    return completed


def create_jetbrains_fixture(path: Path) -> bytes:
    # The fixture "IDE" reports its own parentage and display so the supervised
    # run can assert the process tree, then exits, which ends the session.
    # With FIXTURE_HOLD set it instead checks the contained display and stays
    # up so the run can be probed from outside before it is stopped.
    launcher = textwrap.dedent(
        """\
        #!/bin/sh
        echo "pycharm-fixture pid=$$ ppid=$PPID DISPLAY=${DISPLAY-unset} XAUTHORITY=${XAUTHORITY-unset}"
        if [ -n "${FIXTURE_HOLD-}" ]; then
          test -S "/tmp/.X11-unix/X${DISPLAY#:}" || exit 5
          test -r "$XAUTHORITY" || exit 6
          echo fixture-ready
          exec sleep 300
        fi
        """
    ).encode()
    with tarfile.open(path, "w:gz") as archive:
        info = tarfile.TarInfo("pycharm-fixture/bin/pycharm.sh")
        info.mode = 0o755
        info.size = len(launcher)
        archive.addfile(info, io.BytesIO(launcher))
    return path.read_bytes()


# Runs inside the capsule (docker exec) and reports the facts the design note's
# regression test names: TCP listeners, the X socket, the token gate, and the
# display processes' parentage and identity.
DISPLAY_PROBE = textwrap.dedent(
    """
    import base64, json, os, re, socket, stat, sys
    token = sys.argv[1]
    listeners = set()
    for table in ("/proc/net/tcp", "/proc/net/tcp6"):
        try:
            rows = open(table).read().splitlines()[1:]
        except OSError:
            continue
        for row in rows:
            parts = row.split()
            if parts[3] == "0A":
                listeners.add(int(parts[1].rsplit(":", 1)[1], 16))

    def ws(path):
        s = socket.create_connection(("127.0.0.1", 6080), timeout=5)
        key = base64.b64encode(os.urandom(16)).decode()
        s.sendall((f"GET {path} HTTP/1.1\\r\\nHost: 127.0.0.1:6080\\r\\nUpgrade: websocket\\r\\n"
                   f"Connection: Upgrade\\r\\nSec-WebSocket-Key: {key}\\r\\nSec-WebSocket-Version: 13\\r\\n"
                   "Sec-WebSocket-Protocol: binary\\r\\n\\r\\n").encode())
        data = b""
        while b"\\r\\n\\r\\n" not in data:
            chunk = s.recv(4096)
            if not chunk:
                return ["closed", data.decode(errors="replace")[:80]]
            data += chunk
        head, rest = data.split(b"\\r\\n\\r\\n", 1)
        while len(rest) < 14:
            chunk = s.recv(4096)
            if not chunk:
                break
            rest += chunk
        s.close()
        return [head.split(b"\\r\\n")[0].decode(), rest[2:14].decode(errors="replace")]

    processes = {}
    for entry in os.listdir("/proc"):
        if not entry.isdigit():
            continue
        try:
            argv = open(f"/proc/{entry}/cmdline", "rb").read().split(b"\\0")
            status = open(f"/proc/{entry}/status").read()
        except OSError:
            continue
        names = [os.path.basename(a.decode(errors="replace")) for a in argv if a]
        for wanted in ("Xvnc", "openbox", "tint2", "websockify"):
            if wanted in names[:2]:
                fields = dict(line.split(":\\t", 1) for line in status.splitlines() if ":\\t" in line)
                processes[wanted] = {"ppid": int(fields["PPid"]), "uid": int(fields["Uid"].split()[0])}
    def x_root_properties(display_number, xauthority, names):
        # A minimal X11 client: enough of the core protocol to read root-window
        # properties, so the test needs no X tools in the image.
        import struct
        cookie = open(xauthority, "rb").read()
        def field(buf, off):
            n = struct.unpack(">H", buf[off:off + 2])[0]
            return buf[off + 2:off + 2 + n], off + 2 + n
        off = 2
        _, off = field(cookie, off); _, off = field(cookie, off)
        proto, off = field(cookie, off); data, off = field(cookie, off)
        pad = lambda b: b + b"\\0" * ((4 - len(b) % 4) % 4)
        s = socket.socket(socket.AF_UNIX); s.settimeout(5); s.connect(f"/tmp/.X11-unix/X{display_number}")
        def recv_exact(n):
            out = b""
            while len(out) < n:
                chunk = s.recv(n - len(out))
                if not chunk:
                    raise RuntimeError("X connection closed")
                out += chunk
            return out
        s.sendall(struct.pack("<BxHHHHxx", 0x6C, 11, 0, len(proto), len(data)) + pad(proto) + pad(data))
        head = recv_exact(8)
        if head[0] != 1:
            raise RuntimeError("X setup refused: %r" % recv_exact(struct.unpack("<H", head[6:8])[0] * 4))
        body = recv_exact(struct.unpack("<H", head[6:8])[0] * 4)
        vendor_len = struct.unpack("<H", body[16:18])[0]
        nformats = body[21]
        root = struct.unpack("<I", body[32 + len(pad(b"x" * vendor_len)) + 8 * nformats:][:4])[0]
        def intern(name):
            s.sendall(struct.pack("<BBHHxx", 16, 0, 2 + len(pad(name)) // 4, len(name)) + pad(name))
            reply = recv_exact(32)
            return struct.unpack("<I", reply[8:12])[0]
        def get_property(atom):
            s.sendall(struct.pack("<BBHIIIII", 20, 0, 6, root, atom, 0, 0, 256))
            reply = recv_exact(32)
            fmt = reply[1]
            length = struct.unpack("<I", reply[4:8])[0] * 4
            value_count = struct.unpack("<I", reply[16:20])[0]
            payload = recv_exact(length)
            if fmt == 8:
                return payload[:value_count].decode(errors="replace")
            if fmt == 32:
                return list(struct.unpack("<%dI" % value_count, payload[:4 * value_count]))
            return None
        result = {name: get_property(intern(name.encode())) for name in names}
        s.close()
        return result

    import http.client
    connection = http.client.HTTPConnection("127.0.0.1", 6080, timeout=5)
    connection.request("GET", "/vnc.html")
    vnc_html = connection.getresponse().status
    display_number = sorted(os.listdir("/tmp/.X11-unix"))[0][1:]

    def window_manager_facts():
        # Openbox publishes its root properties once initialized, and the
        # runtime deliberately has no readiness gate for it (X clients cope
        # with a window manager appearing later), so wait for the announcement
        # rather than race it: a slow CI runner lost that race.
        import time
        deadline = time.monotonic() + 30
        while True:
            facts = x_root_properties(
                display_number,
                "/tmp/devcapsule-runtime-1000/display/Xauthority",
                ["_OB_CONFIG_FILE", "_NET_NUMBER_OF_DESKTOPS", "_NET_SUPPORTING_WM_CHECK"],
            )
            if facts["_NET_SUPPORTING_WM_CHECK"] and facts["_OB_CONFIG_FILE"]:
                return facts
            if time.monotonic() > deadline:
                facts["timed_out"] = True
                return facts
            time.sleep(0.25)

    print(json.dumps({
        "window_manager": window_manager_facts(),
        "listeners": sorted(listeners),
        "x_socket": [stat.S_ISSOCK(os.stat(f"/tmp/.X11-unix/{n}").st_mode) for n in sorted(os.listdir("/tmp/.X11-unix"))],
        "abstract_x_sockets": sorted(set(re.findall(r"@/tmp/\\.X11-unix/X\\d+", open("/proc/net/unix").read()))),
        "valid": ws(f"/websockify?token={token}"),
        "bad": ws("/websockify?token=nope"),
        "missing": ws("/websockify"),
        "vnc_html": vnc_html,
        "processes": processes,
    }))
    """
)


@pytest.mark.e2e
def test_pex_runtime_help_inside_disposable_image(tmp_path: Path, built_pex: Path) -> None:
    docker = shutil.which("docker")
    assert docker is not None, "Docker CLI is required for the explicit E2E suite"
    command(docker, "version")

    base_image = os.environ.get("DEVCAPSULE_E2E_BASE_IMAGE", DEFAULT_BASE_IMAGE)
    inspected_base = command(docker, "image", "inspect", base_image, check=False)
    assert inspected_base.returncode == 0, (
        f"E2E base image {base_image!r} is not available locally; pull it explicitly "
        "or set DEVCAPSULE_E2E_BASE_IMAGE"
    )

    if expected_base := os.environ.get("DEVCAPSULE_E2E_BUILT_BASE"):
        assert json.loads(inspected_base.stdout)[0]["Id"] == expected_base

    identifier = uuid.uuid4().hex
    image = f"devcapsule-runtime-e2e:{identifier}"
    materialized_image: str | None = None
    built_supervised_image: str | None = None
    built_display_image: str | None = None
    spec = build_base_image_spec(
        BaseImageBuildOptions(
            pex=built_pex,
            image=image,
            root_image=base_image,
            allow_local_source=True,
            install_baseline=False,
        )
    )
    render_build_context(spec.build_plan(), tmp_path)

    try:
        command(
            docker,
            "build",
            "--pull=false",
            *BUILD_NETWORK_ARGS,
            "--tag",
            image,
            str(tmp_path),
        )
        inspection = json.loads(command(docker, "image", "inspect", image).stdout)[0]
        assert inspection["Config"]["Labels"]["devcapsule.image.kind"] == "base"
        assert inspection["Config"]["Labels"]["devcapsule.base.runtime"] == "launcher-supplied"
        assert inspection["Config"]["Labels"]["devcapsule.base.display"] == "contained"

        python = command(docker, "run", "--rm", "--entrypoint", "python3.12", image, "--version")
        assert python.stdout.startswith("Python 3.12")
        archive = tmp_path / "pycharm-fixture.tar.gz"
        payload = create_jetbrains_fixture(archive)
        artifact = ArtifactSpec("fixture-1", archive.as_uri(), hashlib.sha256(payload).hexdigest())
        cache = tmp_path / "materialization-cache"
        build_count = 0

        def inspect_image(candidate: str) -> ImageDetails | None:
            inspected = command(docker, "image", "inspect", candidate, check=False)
            if inspected.returncode != 0:
                return None
            value = json.loads(inspected.stdout)[0]
            return ImageDetails(
                reference=candidate,
                identity=value["Id"],
                labels=value["Config"].get("Labels") or {},
                operating_system=value["Os"],
                architecture=value["Architecture"],
            )

        def build_materialized(materialization_spec) -> None:
            nonlocal build_count
            build_count += 1
            context = tmp_path / f"materialization-context-{build_count}"
            context.mkdir()
            rendered = render_build_context(materialization_spec.build_plan(), context)
            command(docker, "build", "--pull=false", *rendered.build_context_arguments(),
                    "--tag", materialization_spec.image, str(context))

        materialized_image, created = ensure_materialized_surface(
            base_reference=image,
            base_identity=inspection["Id"],
            platform=f"{inspection['Os']}-{inspection['Architecture']}",
            artifact=artifact,
            cache_root=cache,
            inspect_image=inspect_image,
            build=build_materialized,
            runtime_pex=built_pex,
        )
        assert created is True
        assert build_count == 1
        in_image_digest = command(
            docker,
            "run",
            "--rm",
            "--entrypoint",
            "sha256sum",
            materialized_image,
            "/opt/devcapsule/bin/devcapsule.pex",
        ).stdout.split()[0]
        assert in_image_digest == file_sha256(built_pex)

        completed = command(docker, "run", "--rm", "--network", "none", materialized_image, "--help", check=False)
        assert completed.returncode == 0, completed.stderr
        assert "usage: devcapsule runtime RUNTIME_PLAN.json" in completed.stdout

        command(
            docker,
            "run",
            "--rm",
            "--entrypoint",
            "test",
            materialized_image,
            "-x",
            "/opt/jetbrains/pycharm/bin/pycharm.sh",
        )
        command(
            docker,
            "run",
            "--rm",
            "--entrypoint",
            "test",
            materialized_image,
            "-r",
            "/etc/devcapsule/component-runtime-template.json",
        )
        command(
            docker,
            "run",
            "--rm",
            "--entrypoint",
            "test",
            materialized_image,
            "!",
            "-e",
            "/etc/devcapsule/runtime-plan.json",
        )

        archive.unlink()
        reused_image, created = ensure_materialized_surface(
            base_reference=image,
            base_identity=inspection["Id"],
            platform=f"{inspection['Os']}-{inspection['Architecture']}",
            artifact=artifact,
            cache_root=cache,
            inspect_image=inspect_image,
            build=build_materialized,
            runtime_pex=built_pex,
        )
        assert reused_image == materialized_image
        assert created is False
        assert build_count == 1

        # --- Supervised sessions against the materialized image ---
        # The runtime plan is baked into a derived image rather than
        # bind-mounted: the suite may run inside a capsule against the host
        # Docker daemon, where a local temporary path cannot be mounted.
        plan = RuntimePlan.for_component(
            pycharm_runtime_template(),
            project_path="/workspace/project",
            home="/home/devcapsule",
            identity=Identity(1000, 1000),
        )
        supervised_context = tmp_path / "supervised-context"
        supervised_context.mkdir()
        (supervised_context / "runtime-plan.json").write_text(
            plan.to_json() + "\n", encoding="utf-8"
        )
        (supervised_context / "Dockerfile").write_text(
            f"FROM {materialized_image}\n"
            "COPY runtime-plan.json /etc/devcapsule/runtime-plan.json\n"
            "RUN mkdir -p /workspace/project && chown 1000:1000 /workspace/project\n",
            encoding="utf-8",
        )
        supervised_image = f"devcapsule-supervised-e2e:{identifier}"
        command(docker, "build", "--pull=false", "--tag", supervised_image, str(supervised_context))
        built_supervised_image = supervised_image
        run_prefix = (docker, "run", "--rm", supervised_image)

        # Interactive shape: the supervisor is PID 1, the IDE is its child,
        # and the IDE exiting ends the session with its exit code.
        interactive = command(*run_prefix, check=False)
        assert interactive.returncode == 0, interactive.stderr
        parentage = re.search(r"pycharm-fixture pid=(\d+) ppid=(\d+) DISPLAY=unset", interactive.stdout)
        assert parentage is not None, interactive.stdout
        assert parentage.group(1) != "1"
        assert parentage.group(2) == "1"

        # Headless mode: the job takes the same distinguished slot, runs in
        # the project, sees the supervisor as PID 1, finds no zombies after an
        # orphan died (PID 1 reaped it), and its exit code is the session's.
        job = """
set -eu
test "$$" -ne 1
test "$PPID" -eq 1
tr '\\0' ' ' </proc/1/cmdline | grep -q ' runtime /etc/devcapsule/runtime-plan.json'
test "$(pwd)" = /workspace/project
( sleep 0.2 & )
sleep 0.7
for stat in /proc/[0-9]*/stat; do
  state=$(cut -d" " -f3 "$stat" 2>/dev/null) || continue
  if [ "$state" = Z ]; then exit 21; fi
done
exit 9
"""
        headless = command(
            *run_prefix,
            "/etc/devcapsule/runtime-plan.json",
            "--",
            "sh",
            "-c",
            job,
            check=False,
        )
        assert headless.returncode == 9, (headless.stdout, headless.stderr)

        # Explicit session end: `docker stop` reaches the supervisor as
        # SIGTERM, the child is terminated within the grace period, and the
        # session exit code reports the forwarded signal honestly (128+15).
        started = command(
            docker,
            "run",
            "--detach",
            supervised_image,
            "/etc/devcapsule/runtime-plan.json",
            "--",
            "sh",
            "-c",
            "echo supervisor-e2e-ready; exec sleep 300",
        )
        container_id = started.stdout.strip()
        try:
            deadline = time.monotonic() + 30
            while "supervisor-e2e-ready" not in command(docker, "logs", container_id).stdout:
                assert time.monotonic() < deadline, "headless job never became ready"
                time.sleep(0.2)
            command(docker, "stop", container_id)
            stopped = command(docker, "wait", container_id)
            assert stopped.stdout.strip() == str(128 + signal.SIGTERM)
            logs = command(docker, "logs", container_id)
            assert "session end requested (SIGTERM)" in logs.stderr
        finally:
            command(docker, "rm", "--force", container_id, check=False)

        # --- Contained display: the regression test for the X11 credential bug ---
        # The plan selects the contained transport; the token file is baked in
        # beside it for the same bind-mount reason as the plan itself.
        token = "e2e" + uuid.uuid4().hex
        display_plan = plan.with_display(
            DisplayPlan.contained("0.0.0.0", 6080, "/etc/devcapsule/display-token")
        )
        display_context = tmp_path / "display-context"
        display_context.mkdir()
        (display_context / "runtime-plan.json").write_text(display_plan.to_json() + "\n", encoding="utf-8")
        (display_context / "display-token").write_text(token + "\n", encoding="utf-8")
        (display_context / "Dockerfile").write_text(
            f"FROM {supervised_image}\n"
            "COPY runtime-plan.json /etc/devcapsule/runtime-plan.json\n"
            "COPY display-token /etc/devcapsule/display-token\n"
            "RUN chown 1000:1000 /etc/devcapsule/display-token && chmod 0600 /etc/devcapsule/display-token\n",
            encoding="utf-8",
        )
        display_image = f"devcapsule-display-e2e:{identifier}"
        command(docker, "build", "--pull=false", "--tag", display_image, str(display_context))
        built_display_image = display_image
        # No host X socket, no host credential, no DISPLAY: the capsule brings
        # its own. FIXTURE_HOLD keeps the "IDE" up while the run is probed.
        started = command(docker, "run", "--detach", "--env", "FIXTURE_HOLD=1", display_image)
        container_id = started.stdout.strip()
        try:
            deadline = time.monotonic() + 60
            while "fixture-ready" not in command(docker, "logs", container_id).stdout:
                assert time.monotonic() < deadline, command(docker, "logs", container_id)
                assert command(docker, "inspect", "-f", "{{.State.Running}}", container_id).stdout.strip() == "true", command(docker, "logs", container_id)
                time.sleep(0.2)
            display_logs = command(docker, "logs", container_id).stdout
            assert re.search(
                r"pycharm-fixture pid=\d+ ppid=1 DISPLAY=:\d+ XAUTHORITY=/tmp/devcapsule-runtime-1000/display/Xauthority",
                display_logs,
            ), display_logs
            probe = command(docker, "exec", container_id, "python3", "-c", DISPLAY_PROBE, token)
            facts = json.loads(probe.stdout)
            # The only listener is the token-gated bridge; Xvnc has no TCP port.
            assert facts["listeners"] == [6080], facts
            assert facts["x_socket"] == [True], facts  # exactly one X socket, ours
            # No abstract X socket of ours: under host networking it would be
            # visible to (and collide with) the host; ours is filesystem-only.
            display_number = re.search(r"DISPLAY=:(\d+)", display_logs).group(1)  # type: ignore[union-attr]
            assert f"@/tmp/.X11-unix/X{display_number}" not in facts["abstract_x_sockets"], facts
            assert facts["valid"] == ["HTTP/1.1 101 Switching Protocols", "RFB 003.008\n"], facts
            assert facts["bad"] == ["closed", ""], facts
            assert facts["missing"] == ["closed", ""], facts
            assert facts["vnc_html"] == 200
            # Display processes are the supervisor's direct children and run
            # as the capsule user, never as root.
            for name in ("Xvnc", "openbox", "tint2", "websockify"):
                assert facts["processes"][name] == {"ppid": 1, "uid": 1000}, facts
            # Openbox runs DevCapsule's configuration, not the distribution
            # default: it announces the file it loaded and a single desktop.
            window_manager = facts["window_manager"]
            assert window_manager["_OB_CONFIG_FILE"] == "/tmp/devcapsule-runtime-1000/display/openbox-rc.xml", facts
            assert window_manager["_NET_NUMBER_OF_DESKTOPS"] == [1], facts
            assert window_manager["_NET_SUPPORTING_WM_CHECK"], facts
            command(docker, "stop", container_id)
            stopped = command(docker, "wait", container_id)
            assert stopped.stdout.strip() == str(128 + signal.SIGTERM)
            assert "session end requested (SIGTERM)" in command(docker, "logs", container_id).stderr
        finally:
            command(docker, "rm", "--force", container_id, check=False)
    finally:
        if built_display_image is not None:
            command(docker, "image", "rm", "--force", built_display_image, check=False)
        if built_supervised_image is not None:
            command(docker, "image", "rm", "--force", built_supervised_image, check=False)
        if materialized_image is not None:
            command(docker, "image", "rm", "--force", materialized_image, check=False)
        command(docker, "image", "rm", "--force", image, check=False)
