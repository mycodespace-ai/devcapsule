from __future__ import annotations

import gzip
import io
import json
import os
from pathlib import Path
import stat
import tarfile
import textwrap
import tomllib
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest

from devcapsule import cli, logs
from devcapsule.configuration.docker_arguments import arguments_path, update_environment
from devcapsule.configuration.file_formats import canonical_digest
from devcapsule.configuration.storage import find_checkout_record
from devcapsule.diagnostics import (
    DiagnosticsError,
    diagnose_project,
    inspect_container,
    select_session_directory,
    summarize_diagnosis,
)
from devcapsule.launch.session_logs import session_logs_root

pytestmark = pytest.mark.legacy


def _init_project(project: Path) -> dict[str, Any]:
    target = project / ".devcapsule"
    target.mkdir(parents=True, exist_ok=True)
    manifest_text = "\n".join(
        [
            "devcapsule-schema-version = 1",
            "",
            "[capabilities]",
            'need = ["python", "python-ide"]',
            "",
            "[project]",
            f'name = "{project.name}"',
            f'slug = "{project.name.lower()}"',
            'creator = "mailto:dev@example.test"',
            'mount = "/workspace/project"',
            "",
        ]
    )
    (target / "devcapsule.toml").write_text(manifest_text, encoding="utf-8")
    manifest = tomllib.loads(manifest_text)
    lock_text = "\n".join(
        [
            "devcapsule-lock-format-version = 1",
            'resolution-matrix-version = "dogfood-v1"',
            f'manifest-digest = "{canonical_digest(manifest)}"',
            'platform = "linux-amd64"',
            "",
            "[image]",
            'reference = "local/pycharm:dogfood"',
            "",
            "[components]",
            'interactive-surface = "pycharm"',
            "",
        ]
    )
    (target / "devcapsule.linux-amd64.lock").write_text(lock_text, encoding="utf-8")
    return manifest


def _write_fake_docker(bin_dir: Path, script_body: str) -> Path:
    bin_dir.mkdir(parents=True, exist_ok=True)
    docker_bin = bin_dir / "docker"
    docker_bin.write_text("#!/bin/sh\n" + script_body, encoding="utf-8")
    docker_bin.chmod(0o755)
    return docker_bin


def test_select_session_directory_handles_validation_active_and_crashed_sessions(
    tmp_path: Path,
) -> None:
    logs_root = tmp_path / "logs"
    logs_root.mkdir()

    for bad in ("../escape", "nested/id", ".dotstart", ""):
        with pytest.raises(DiagnosticsError):
            select_session_directory(logs_root, session_id=bad)

    with pytest.raises(DiagnosticsError, match="No session logs found"):
        select_session_directory(logs_root)

    s1 = logs_root / "20261027-100000-aaaa"
    s1.mkdir()
    (s1 / "session.json").write_text(
        json.dumps({"session": s1.name, "container": "dead-capsule", "started-at": "2026-10-27T10:00:00Z"}),
        encoding="utf-8",
    )
    s2 = logs_root / "20261027-110000-bbbb"
    s2.mkdir()
    (s2 / "session.json").write_text(
        json.dumps(
            {
                "session": s2.name,
                "container": "ended-capsule",
                "started-at": "2026-10-27T11:00:00Z",
                "ended-at": "2026-10-27T11:10:00Z",
                "exit-code": 0,
            }
        ),
        encoding="utf-8",
    )

    # s1 has no ended-at, yet its container is gone while s2 ended more recently -> pick s2.
    chosen, mode = select_session_directory(
        logs_root,
        is_container_running=lambda _name: False,
    )
    assert chosen == s2
    assert mode == "latest-ended"

    # If s1's container is actually still running concurrently, prefer s1 as active!
    chosen_live, mode_live = select_session_directory(
        logs_root,
        is_container_running=lambda name: name == "dead-capsule",
    )
    assert chosen_live == s1
    assert mode_live == "active"

    with pytest.raises(DiagnosticsError, match="Available sessions"):
        select_session_directory(logs_root, session_id="20261027-120000-missing")


def test_inspect_container_strips_env_values_and_handles_removed_or_hung_docker(
    tmp_path: Path,
) -> None:
    payload = [
        {
            "Id": "abc123def456",
            "Image": "sha256:1111",
            "State": {
                "Status": "running",
                "Running": True,
                "Paused": False,
                "Restarting": False,
                "OOMKilled": True,
                "Dead": False,
                "Pid": 4321,
                "ExitCode": 0,
                "Error": "",
                "StartedAt": "2026-10-27T12:00:00Z",
                "FinishedAt": "0001-01-01T00:00:00Z",
            },
            "HostConfig": {
                "Memory": 4294967296,
                "MemorySwap": 4294967296,
                "NanoCpus": 2000000000,
                "PidsLimit": 4096,
                "ShmSize": 67108864,
                "ReadonlyRootfs": True,
                "NetworkMode": "bridge",
            },
            "Config": {
                "Env": [
                    "OPENAI_API_KEY=sk-never-leak-this-secret-value",
                    "CUSTOM_INLINE=top-secret-inline",
                    "DISPLAY=:99",
                ]
            },
            "NetworkSettings": {
                "Ports": {
                    "6080/tcp": [{"HostIp": "127.0.0.1", "HostPort": "46080"}],
                    "6081/tcp": [{"HostIp": "127.0.0.1", "HostPort": "46081"}],
                }
            },
        }
    ]
    inspect_json = tmp_path / "inspect.json"
    inspect_json.write_text(json.dumps(payload), encoding="utf-8")

    bin_dir = tmp_path / "bin"
    _write_fake_docker(
        bin_dir,
        textwrap.dedent(
            f"""\
            if [ "$4" = "live-c" ]; then
              cat "{inspect_json}"
              exit 0
            fi
            if [ "$4" = "gone-c" ]; then
              echo "Error: No such container: gone-c" >&2
              exit 1
            fi
            sleep 2
            """
        ),
    )
    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ.get('PATH', '')}"}

    live = inspect_container("live-c", env=env, timeout=1.0)
    assert live["available"] is True
    assert live["oom_killed"] is True
    assert live["published_ports"]["6080/tcp"] == [{"host_ip": "127.0.0.1", "host_port": 46080}]
    assert live["environment_variable_names"] == ["CUSTOM_INLINE", "DISPLAY", "OPENAI_API_KEY"]
    serialized = json.dumps(live)
    assert "sk-never-leak-this-secret-value" not in serialized
    assert "top-secret-inline" not in serialized

    gone = inspect_container("gone-c", env=env, timeout=1.0)
    assert gone["available"] is False
    assert gone["container_removed"] is True

    hung = inspect_container("hung-c", env=env, timeout=0.15)
    assert hung["available"] is False
    assert hung["timed_out"] is True


def test_summarize_diagnosis_never_treats_http_200_or_socket_accept_as_healthy() -> None:
    degraded = summarize_diagnosis(
        session_manifest_doc={"session": "s1"},
        docker_inspect={"available": True, "running": True, "oom_killed": False},
        runtime_probe={
            "available": True,
            "cgroup": {"memory": {"events": {"oom_kill": 0}}},
            "processes": {
                "stopped": [{"pid": 20, "name": "Xvnc", "role": "xvnc"}],
                "zombies": [{"pid": 99, "name": "defunct", "role": "other"}],
            },
            "probes": {
                "rfb_unix": {"healthy": False, "accepted": True, "status": "greeting-timeout"},
                "display_http": {"healthy": True, "status": "ok"},
                "display_websocket_rfb": {"healthy": False, "status": "rfb-greeting-timeout"},
                "console_http": {"healthy": True, "status": "ok"},
            },
        },
        host_probes={
            "available": True,
            "probes": {
                "display_host_http": {"healthy": False, "port": 46080, "status": "connect-error"},
                "console_host_http": {"healthy": True, "status": "ok"},
            },
        },
    )
    assert degraded["state"] == "degraded"
    joined = "\n".join(degraded["issues"])
    assert "stopped (state T)" in joined
    assert "zombie" in joined
    assert "accepted connection without RFB greeting" in joined
    assert "websockify HTTP (/vnc.html) answered 200 while WebSocket-to-RFB bridge failed" in joined
    assert "host loopback port 46080 failed" in joined

    infra_exit = summarize_diagnosis(
        session_manifest_doc={"session": "s2", "ended-at": "2026-10-27T12:00:00Z", "exit-code": 70},
        docker_inspect={"available": False, "container_removed": True},
        runtime_probe={"available": False, "unavailable_reason": "container removed"},
        host_probes={"available": False, "unavailable_reason": "container removed"},
    )
    assert infra_exit["state"] == "post-mortem-issues"
    assert any("70" in item for item in infra_exit["issues"])

    ctrl_c_exit = summarize_diagnosis(
        session_manifest_doc={"session": "s3", "ended-at": "2026-10-27T12:00:00Z", "exit-code": 130},
        docker_inspect={"available": False, "container_removed": True},
        runtime_probe={"available": False, "unavailable_reason": "container removed"},
        host_probes={"available": False, "unavailable_reason": "container removed"},
    )
    assert ctrl_c_exit["state"] == "post-mortem"
    assert ctrl_c_exit["issues"] == []


def test_project_diagnose_export_redacts_logs_gz_excludes_ide_logs_by_default_and_refuses_symlinks(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    project = tmp_path / "sample-proj"
    manifest = _init_project(project)
    assert cli.main(["project", "--path", str(project), "checkout", "register", "default"]) == 0
    capsys.readouterr()
    record_path = find_checkout_record(manifest, project)
    assert record_path is not None
    update_environment(arguments_path(record_path), "CUSTOM_SAVED_SECRET", "saved_docker_secret_val_999")

    # Configure fake docker returning "No such container" so post-mortem path runs deterministically.
    bin_dir = tmp_path / "bin"
    _write_fake_docker(bin_dir, 'echo "Error: No such container: $4" >&2\nexit 1\n')

    jetbrains_logs = tmp_path / "ide-slots" / "jetbrains-log"
    jetbrains_logs.mkdir(parents=True)
    (jetbrains_logs / "idea.log").write_text(
        "2026-10-27 INFO open url http://127.0.0.1:6080/vnc.html?token=ide_url_token_1122334455667788\n",
        encoding="utf-8",
    )
    (jetbrains_logs / "symlink-idea.log").symlink_to("/etc/hosts")

    eclipse_meta = tmp_path / "ide-slots" / "eclipse" / ".metadata"
    (eclipse_meta / ".plugins").mkdir(parents=True)
    (eclipse_meta / ".log").write_text("!ENTRY eclipse log CUSTOM_SAVED_SECRET=saved_docker_secret_val_999\n", encoding="utf-8")
    (eclipse_meta / ".bak_0.log").write_text("!ENTRY rotated eclipse log\n", encoding="utf-8")
    (eclipse_meta / ".plugins" / "workspace-source-cache.txt").write_text(
        "UNRELATED_WORKSPACE_PLUGIN_STATE_MUST_NEVER_BE_EXPORTED\n",
        encoding="utf-8",
    )

    logs_dir = session_logs_root(project) / "20261027-123000-cafe"
    logs_dir.mkdir(parents=True)
    session_doc = {
        "schema-version": 1,
        "session": "../manifest-escape",
        "started-at": "2026-10-27T12:30:00Z",
        "ended-at": "2026-10-27T12:35:00Z",
        "exit-code": 0,
        "container": "devcapsule-sample-proj",
        "network-mode": "bridge",
        "display": {"transport": "contained", "host-port": 46080, "container-port": 6080},
        "console": {"enabled": True, "host-port": 46081, "container-port": 6081},
        "ide-logs": [
            {
                "slot": "pycharm/log",
                "family": "jetbrains",
                "host-path": str(jetbrains_logs),
                "container-path": "/home/devcapsule/.cache/JetBrains/PyCharm/log",
            },
            {
                "slot": "eclipse/workspace",
                "family": "eclipse",
                "host-path": str(eclipse_meta),
                "container-path": "/home/devcapsule/eclipse-workspace/.metadata",
            },
        ],
    }
    (logs_dir / "session.json").write_text(json.dumps(session_doc, indent=2), encoding="utf-8")
    (logs_dir / "devcapsule-novnc.log").write_text(
        "2026-10-27T12:30:01Z GET /vnc.html?token=deadbeefcafe1234567890abcdef1234\n"
        "2026-10-27T12:30:02Z redirect token%3Dencoded_secret_token_99887766\n"
        "2026-10-27T12:30:03Z Cookie: devcapsule-console-token=console_cookie_secret_554433\n"
        "2026-10-27T12:30:03Z debug cookie devcapsule-console-token=bare_cookie_secret_443322\n"
        "2026-10-27T12:30:03Z debug port cookie devcapsule-console-token-41273=port_cookie_secret_665544\n"
        "2026-10-27T12:30:04Z Authorization: Bearer bearer_secret_value_776655\n",
        encoding="utf-8",
    )
    with gzip.open(logs_dir / "devcapsule-launcher.log.1.gz", "wb") as gz_handle:
        gz_handle.write(
            (
                "2026-10-27T12:30:00Z docker run --env CUSTOM_SAVED_SECRET=saved_docker_secret_val_999\n"
                "2026-10-27T12:30:01Z OPENAI_API_KEY=sk-proj-secret-value-123456789\n"
            ).encode("utf-8")
        )
    (logs_dir / "devcapsule-corrupt.log.2.gz").write_bytes(b"\x1f\x8b\x08corrupt-not-valid-gzip")
    (logs_dir / "evil-symlink.log").symlink_to("/etc/hosts")

    # --include-ide-logs without --export must fail clearly.
    rc_bad = cli.main(["project", "--path", str(project), "diagnose", "--include-ide-logs"])
    assert rc_bad == 2
    assert "--include-ide-logs requires --export" in capsys.readouterr().err

    # Exporting through a symlink destination must be refused.
    symlink_export = tmp_path / "symlink-bundle.tar.gz"
    symlink_export.symlink_to(tmp_path / "target.tar.gz")
    with patch.dict(os.environ, {"PATH": f"{bin_dir}:{os.environ.get('PATH', '')}"}):
        rc_sym = cli.main(
            ["project", "--path", str(project), "diagnose", "--export", str(symlink_export)]
        )
    assert rc_sym == 2
    assert "symlink" in capsys.readouterr().err.lower()

    default_bundle = tmp_path / "default-export.tar.gz"
    with patch.dict(os.environ, {"PATH": f"{bin_dir}:{os.environ.get('PATH', '')}"}):
        rc_ok = cli.main(
            ["project", "--path", str(project), "diagnose", "--json", "--export", str(default_bundle)]
        )
    assert rc_ok == 0
    out_json = json.loads(capsys.readouterr().out)
    assert out_json["schema-version"] == 1
    assert out_json["session"]["id"] == logs_dir.name
    assert out_json["browser_evidence"]["collected"] is False
    assert out_json["browser_evidence"]["mode"] == "manual-devtools"
    assert out_json["ide_native_logs"]["included_in_export"] is False
    assert len(out_json["ide_native_logs"]["entries"]) == 2

    saved_snap = Path(out_json["saved_snapshot_path"])
    assert stat.S_IMODE(saved_snap.stat().st_mode) == 0o600
    assert stat.S_IMODE(default_bundle.stat().st_mode) == 0o600

    forbidden_secrets = (
        "deadbeefcafe1234567890abcdef1234",
        "encoded_secret_token_99887766",
        "console_cookie_secret_554433",
        "bare_cookie_secret_443322",
        "port_cookie_secret_665544",
        "bearer_secret_value_776655",
        "saved_docker_secret_val_999",
        "sk-proj-secret-value-123456789",
        "ide_url_token_1122334455667788",
    )

    with tarfile.open(default_bundle, "r:gz") as tar:
        names = tar.getnames()
        assert not any("/ide-logs/" in name for name in names)
        assert not any("evil-symlink" in name for name in names)
        for member in tar.getmembers():
            extracted = tar.extractfile(member)
            assert extracted is not None
            raw = extracted.read()
            text = (
                gzip.decompress(raw).decode("utf-8")
                if member.name.endswith(".gz")
                else raw.decode("utf-8")
            )
            for secret in forbidden_secrets:
                assert secret not in text, f"secret {secret!r} leaked in {member.name}"
            if member.name.endswith("/snapshot.json"):
                archived_snap = json.loads(text)
                skipped_reasons = {item["reason"] for item in archived_snap["export"]["skipped_files"]}
                assert "symlink refused" in skipped_reasons
                assert any("read failed" in reason for reason in skipped_reasons)

    # Now opt in with --include-ide-logs: JetBrains + Eclipse .log/.bak_0.log included (redacted),
    # Eclipse .plugins/ workspace files and symlinks STILL excluded!
    opt_in_bundle = tmp_path / "with-ide-logs.tar.gz"
    with patch.dict(os.environ, {"PATH": f"{bin_dir}:{os.environ.get('PATH', '')}"}):
        rc_ide = cli.main(
            [
                "project",
                "--path",
                str(project),
                "diagnose",
                "--export",
                str(opt_in_bundle),
                "--include-ide-logs",
            ]
        )
    assert rc_ide == 0
    human_out = capsys.readouterr().out
    assert "Verdict: post-mortem" in human_out
    assert "Export bundle:" in human_out

    with tarfile.open(opt_in_bundle, "r:gz") as tar:
        ide_members = [name for name in tar.getnames() if "/ide-logs/" in name]
        assert any(name.endswith("/idea.log") for name in ide_members)
        assert any(name.endswith("/.log") for name in ide_members)
        assert any(name.endswith("/.bak_0.log") for name in ide_members)
        assert not any("workspace-source-cache" in name for name in ide_members)
        assert not any("symlink-idea" in name for name in ide_members)
        for member in tar.getmembers():
            extracted = tar.extractfile(member)
            assert extracted is not None
            raw = extracted.read()
            text = (
                gzip.decompress(raw).decode("utf-8")
                if member.name.endswith(".gz")
                else raw.decode("utf-8")
            )
            for secret in forbidden_secrets:
                assert secret not in text, f"secret {secret!r} leaked in {member.name}"


def test_diagnose_project_in_capsule_mode_runs_in_process_and_guards_other_sessions(
    tmp_path: Path,
) -> None:
    capsule_logs = tmp_path / "var-log-devcapsule"
    capsule_logs.mkdir()
    (capsule_logs / "session.json").write_text(
        json.dumps({"session": "20261027-124000-live", "started-at": "2026-10-27T12:40:00Z"}),
        encoding="utf-8",
    )
    fake_context = SimpleNamespace(
        document={
            "project": {"creator": "mailto:dev@example.test", "slug": "capsule-proj"},
            "launcher-root": "/host/path/capsule-proj",
            "runtime-root": "/workspace/capsule-proj",
        },
        checkout_name="default",
        launcher_command=lambda args: f"devcapsule project --path /host/path/capsule-proj {' '.join(args)}",
    )
    fake_probe = {
        "schema_version": 1,
        "cgroup": {"available": False},
        "processes": {"available": True, "total_processes": 3, "components": {}, "novnc_workers": [], "zombies": [], "stopped": []},
        "sockets": {},
        "probes": {
            "rfb_unix": {"healthy": True, "status": "ok"},
            "display_http": {"healthy": True, "status": "ok"},
            "display_websocket_rfb": {"healthy": True, "status": "ok"},
            "console_http": {"healthy": True, "status": "ok"},
        },
    }

    with (
        patch("devcapsule.diagnostics.runtime_configuration.for_project", return_value=fake_context),
        patch("devcapsule.diagnostics.collect_runtime_probe", return_value=dict(fake_probe)),
    ):
        with pytest.raises(DiagnosticsError, match="inspect other sessions from the host"):
            diagnose_project(
                tmp_path,
                session_id="20261027-090000-older",
                environ={logs.DIRECTORY_ENV: str(capsule_logs)},
            )

        snap = diagnose_project(
            tmp_path,
            environ={logs.DIRECTORY_ENV: str(capsule_logs)},
        )
    assert snap["context"] == "in-capsule"
    assert snap["session"]["id"] == "20261027-124000-live"
    assert snap["summary"]["state"] == "healthy"


@pytest.mark.parametrize("text", [
    'TOKEN=bare-value',
    'APP_SECRET="quoted value with spaces"',
    "APP_PASSWORD='quoted value with spaces'",
    'path=websockify%3Ftoken%3Dprefix%2Fsecret-suffix',
])
def test_redaction_covers_full_credential_values(text: str) -> None:
    from devcapsule._redaction import redact_text

    result = redact_text(text)
    assert result.endswith("<redacted>")
    assert "value" not in result
    assert "secret-suffix" not in result


def test_structured_redaction_preserves_nonsecret_paths() -> None:
    from devcapsule._redaction import redact_json_value

    result = redact_json_value({
        "TOKEN": "secret", "Authorization": "Bearer secret", "Cookie": "a=secret",
        "DEVCAPSULE_TOKEN_FILE": "/run/token", "XAUTHORITY": "/tmp/xauth",
        "APP_SECRET": "secret", "normal": "helpful error", "token_gate_active": True,
    })
    assert result == {
        "TOKEN": "<redacted>", "Authorization": "<redacted>", "Cookie": "<redacted>",
        "DEVCAPSULE_TOKEN_FILE": "/run/token", "XAUTHORITY": "/tmp/xauth",
        "APP_SECRET": "<redacted>", "normal": "helpful error", "token_gate_active": True,
    }


@pytest.mark.parametrize("content", [b"[]", b"null", b"{", b"\xff"])
def test_invalid_manifest_is_reported(tmp_path: Path, content: bytes) -> None:
    from devcapsule.diagnostics import _read_session_manifest

    (tmp_path / "session.json").write_bytes(content)
    manifest, error = _read_session_manifest(tmp_path)
    assert manifest == {}
    assert error


def test_manifest_fifo_and_oversize_are_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from devcapsule import diagnostics

    manifest = tmp_path / "session.json"
    os.mkfifo(manifest)
    assert "not a regular file" in str(diagnostics._read_session_manifest(tmp_path)[1])
    manifest.unlink()
    manifest.write_text('{"large": "' + 'x' * 64 + '"}')
    monkeypatch.setattr(diagnostics, "MAX_SESSION_MANIFEST_BYTES", 32)
    assert diagnostics._read_session_manifest(tmp_path) == ({}, "session.json exceeds diagnostic byte limit")


def test_session_selection_checks_newest_container_before_older_live_session(tmp_path: Path) -> None:
    for name, container in (("20261027-100000-old", "live"), ("20261027-110000-new", "gone")):
        directory = tmp_path / name
        directory.mkdir()
        (directory / "session.json").write_text(json.dumps({"container": container}))
    chosen, mode = select_session_directory(tmp_path, is_container_running=lambda name: name == "live")
    assert chosen.name == "20261027-100000-old"
    assert mode == "active"


def test_ide_ancestor_symlink_and_entry_limit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from devcapsule import diagnostics

    outside = tmp_path / "outside"
    (outside / "logs").mkdir(parents=True)
    (outside / "logs" / "idea.log").write_text("private host content")
    link = tmp_path / "workspace"
    link.symlink_to(outside, target_is_directory=True)
    files, skipped = diagnostics._walk_ide_log_files(link / "logs", family="jetbrains")
    assert files == []
    assert skipped
    for index in range(5):
        (outside / "logs" / f"idea.log.{index}").write_text("log")
    monkeypatch.setattr(diagnostics, "MAX_IDE_LOG_ENTRIES", 3)
    files, skipped = diagnostics._walk_ide_log_files(outside / "logs", family="jetbrains")
    assert len(files) <= 3
    assert skipped[-1]["reason"] == "IDE log entry limit reached"


def test_export_read_refuses_parent_replacement_with_symlink(tmp_path: Path) -> None:
    from devcapsule import diagnostics

    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    (logs_dir / "idea.log").write_text("safe")
    files, _ = diagnostics._walk_ide_log_files(logs_dir, family="jetbrains")
    logs_dir.rename(tmp_path / "original")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "idea.log").write_text("private")
    logs_dir.symlink_to(outside, target_is_directory=True)
    with pytest.raises(OSError):
        diagnostics._sanitize_plain_bytes(files[0][0], max_bytes=1024, env_names=set())


def test_private_output_cleans_failure_and_refuses_parent_symlink(tmp_path: Path) -> None:
    from devcapsule import diagnostics

    destination = tmp_path / "snapshot.json"
    destination.write_bytes(b"old")
    with pytest.raises(OSError, match="disk full"):
        with diagnostics._private_output(destination) as handle:
            handle.write(b"partial")
            raise OSError("disk full")
    assert destination.read_bytes() == b"old"
    assert list(tmp_path.glob(".*.tmp")) == []
    diagnostics._atomic_write_private_bytes(destination, b"new")
    assert destination.read_bytes() == b"new"
    assert stat.S_IMODE(destination.stat().st_mode) == 0o600
    link = tmp_path / "link"
    link.symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(OSError):
        diagnostics._atomic_write_private_bytes(link / "snapshot.json", b"leak")
    assert destination.read_bytes() == b"new"


def test_gzip_export_caps_expansion_and_rejects_truncated_stream(tmp_path: Path) -> None:
    from devcapsule import diagnostics

    source = tmp_path / "component.log.1.gz"
    source.write_bytes(gzip.compress(b"TOKEN=secret\n" * 10000))
    payload, size, truncated = diagnostics._sanitize_gzip_bytes(source, max_uncompressed_bytes=128, env_names=set())
    plain = gzip.decompress(payload)
    assert truncated
    assert len(plain) == size < 512
    assert b"secret" not in plain
    source.write_bytes(gzip.compress(b"ordinary log")[:-4])
    with pytest.raises(EOFError):
        diagnostics._sanitize_gzip_bytes(source, max_uncompressed_bytes=128, env_names=set())


def test_json_export_scrubs_structured_credentials(tmp_path: Path) -> None:
    from devcapsule import diagnostics

    source = tmp_path / "session.json"
    source.write_text(json.dumps({"APP_API_KEY": "private-value", "normal": "visible"}))
    payload, truncated = diagnostics._sanitize_plain_bytes(source, max_bytes=1024, env_names=set())
    assert not truncated
    assert json.loads(payload) == {"APP_API_KEY": "<redacted>", "normal": "visible"}


def test_configured_environment_redaction_handles_quoted_values() -> None:
    from devcapsule._redaction import redact_text

    assert redact_text('CUSTOM="private value"', env_names={"CUSTOM"}) == 'CUSTOM=<redacted>'


def test_diagnose_filesystem_error_is_a_cli_diagnostic(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    project = tmp_path / "project"
    _init_project(project)
    with patch("devcapsule.diagnostics.diagnose_project", side_effect=PermissionError("export parent is unwritable")):
        result = cli.main(["project", "--path", str(project), "diagnose", "--export"])
    assert result == 2
    assert "Cannot capture or export diagnostics: export parent is unwritable" in capsys.readouterr().err


@pytest.mark.parametrize("slot", [".", "..", "../../"])
def test_archive_slot_cannot_traverse(slot: str) -> None:
    from devcapsule.diagnostics import _safe_slot_dir

    assert _safe_slot_dir(slot) not in {".", ".."}
    assert "/" not in _safe_slot_dir(slot)


def test_fallback_managed_path_preserves_links_for_refusal(tmp_path: Path) -> None:
    from devcapsule import diagnostics

    outside = tmp_path / "outside"
    outside.mkdir()
    link = tmp_path / "log-slot"
    link.symlink_to(outside, target_is_directory=True)
    declaration: Any = SimpleNamespace()
    with patch("devcapsule.diagnostics.managed_binding_path", return_value=link):
        target = diagnostics._managed_slot_path(tmp_path, declaration, os.environ)
    assert target == link
    assert diagnostics._walk_ide_log_files(target, family="jetbrains")[1][0]["reason"] == "symlink refused"
