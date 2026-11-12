from __future__ import annotations

from pathlib import Path

import pytest

from devcapsule import cli
from devcapsule.recursive_dogfood import (
    CONTAINER_NAME_ENV,
    ContainerInspection,
    Finding,
    Mount,
    PreflightError,
    PreflightReport,
    covering_mount,
    docker_socket_path,
    identify_current_container,
    parse_container_inspection,
    preflight_json,
    render_preflight,
    safe_child,
    validate_container_name,
)

pytestmark = pytest.mark.legacy


def inspection_mapping(
    *,
    identity: str = "a" * 64,
    name: str = "dogfood-current",
    upper_directory: str = "/docker/overlay/current/diff",
    mounts: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    return {
        "Id": identity,
        "Name": f"/{name}",
        "Image": "sha256:" + "b" * 64,
        "Config": {"Labels": {"devcapsule.source.revision": "c" * 40}},
        "HostConfig": {"NetworkMode": "host"},
        "GraphDriver": {"Data": {"UpperDir": upper_directory}},
        "Mounts": mounts
        or [
            {
                "Type": "bind",
                "Source": "/host/project",
                "Destination": "/workspace/project",
                "RW": True,
            }
        ],
    }


def test_malformed_container_identity_fails_closed() -> None:
    value = inspection_mapping(identity="not-a-container-id")

    with pytest.raises(PreflightError, match="malformed container identity"):
        parse_container_inspection(value)


def test_malformed_declared_container_name_fails_closed() -> None:
    with pytest.raises(PreflightError, match=CONTAINER_NAME_ENV):
        validate_container_name("../../host")


def test_daemon_container_mismatch_fails_closed() -> None:
    inspected = parse_container_inspection(inspection_mapping(name="different-container"))

    with pytest.raises(PreflightError, match="does not match"):
        identify_current_container(
            [inspected],
            expected_name="declared-container",
            self_upper_directory="/docker/overlay/current/diff",
        )


def test_overlay_fallback_identifies_v023_container_without_declared_name() -> None:
    current = parse_container_inspection(inspection_mapping())
    other = parse_container_inspection(
        inspection_mapping(
            identity="d" * 64,
            name="another-container",
            upper_directory="/docker/overlay/other/diff",
        )
    )

    assert (
        identify_current_container(
            [other, current],
            expected_name=None,
            self_upper_directory="/docker/overlay/current/diff",
        )
        == current
    )


def test_missing_explicit_docker_socket_fails_closed() -> None:
    with pytest.raises(PreflightError, match="DOCKER_HOST"):
        docker_socket_path(None)


def test_selected_but_missing_docker_socket_fails_closed(tmp_path: Path) -> None:
    from devcapsule import recursive_dogfood as module

    builder = module._ReportBuilder()
    selected = tmp_path / "missing-docker.sock"

    assert module._inspect_docker_socket(builder, {"DOCKER_HOST": f"unix://{selected}"}) is None
    assert builder.findings == [
        Finding("error", "docker-socket", "The selected Docker socket is missing or inaccessible.")
    ]


def test_ambiguous_mount_mapping_fails_closed() -> None:
    mounts = (
        Mount("/host/a", "/workspace", "bind", True),
        Mount("/host/b", "/workspace", "bind", True),
    )

    with pytest.raises(PreflightError, match="ambiguous"):
        covering_mount(Path("/workspace/project"), mounts, require_writable=True)


def test_read_only_workspace_mount_fails_closed() -> None:
    mounts = (Mount("/host/home", "/home/devcapsule", "bind", False),)

    with pytest.raises(PreflightError, match="read-only"):
        covering_mount(
            Path("/home/devcapsule/.local/share/devcapsule/e2e-workspaces"),
            mounts,
            require_writable=True,
        )


def test_recursive_workspace_rejects_path_escape(tmp_path: Path) -> None:
    home = tmp_path / "home"
    outside = tmp_path / "outside"
    home.mkdir()
    outside.mkdir()
    (home / "escape").symlink_to(outside, target_is_directory=True)

    with pytest.raises(PreflightError, match="escapes"):
        safe_child(home, Path("escape/workspace"))

    with pytest.raises(PreflightError, match="non-escaping"):
        safe_child(home, Path("../outside"))


def test_preflight_output_redacts_host_and_xauthority_paths() -> None:
    secret_source = "/host/private/runtime/pycharm-docker-xauth.secret"
    report = PreflightReport(
        findings=(Finding("pass", "display-authorization", "Authorization is present."),),
        facts={"display": "configured"},
        mounts=(Mount(secret_source, "/tmp/.docker.xauth", "bind", False),),
    )

    rendered = render_preflight(report)
    encoded = preflight_json(report)
    assert secret_source not in rendered
    assert secret_source not in encoded
    assert "/tmp/.docker.xauth" not in rendered
    assert "<display-authorization>" in rendered
    assert secret_source in render_preflight(report, show_host_paths=True)


def test_missing_display_is_an_explicit_preflight_error(tmp_path: Path, monkeypatch) -> None:
    from devcapsule import recursive_dogfood as module
    from devcapsule.container_runtime.contract import RuntimePlan

    checkout = tmp_path / "checkout"
    home = tmp_path / "home"
    checkout.mkdir()
    home.mkdir()
    plan_path = tmp_path / "runtime-plan.json"
    plan = RuntimePlan.from_mapping(
        {
            "version": 1,
            "project_path": str(checkout),
            "home": str(home),
            "identity": {"uid": 1000, "gid": 1000, "user": "developer"},
            "state_slots": [],
            "component": {"id": "pycharm", "adapter": "jetbrains", "configuration": {}},
        }
    )
    plan_path.write_text(plan.to_json(), encoding="utf-8")
    mounts = (
        Mount("/host/checkout", str(checkout), "bind", True),
        Mount("/host/home", str(home), "bind", True),
        Mount("/host/plan", str(plan_path), "bind", False),
        Mount("/host/x11", "/tmp/.X11-unix", "bind", False),
    )
    container = ContainerInspection(
        "a" * 64,
        "dogfood-current",
        "sha256:" + "b" * 64,
        None,
        "host",
        mounts,
        "/docker/overlay/current/diff",
    )
    builder = module._ReportBuilder()

    module._inspect_required_mounts(
        builder,
        checkout_root=checkout,
        runtime_plan_path=plan_path,
        runtime_plan=plan,
        container=container,
        env={"HOME": str(home)},
    )

    display = [item for item in builder.findings if item.check == "display"]
    assert display == [Finding("error", "display", "DISPLAY is not configured for successor IDE validation.")]


def recursive_project(root: Path) -> None:
    (root / ".devcapsule").mkdir(parents=True)
    (root / ".devcapsule" / "devcapsule.toml").write_text("", encoding="utf-8")
    (root / "devcapsule-src").mkdir()
    (root / "devcapsule-src" / "pyproject.toml").write_text(
        '[project]\nname = "devcapsule"\nversion = "0.0.0"\n',
        encoding="utf-8",
    )


def test_project_recursive_preflight_cli_returns_public_report_status(
    tmp_path: Path,
    capsys,
) -> None:
    recursive_project(tmp_path)

    result = cli.main(
        ["project", "--path", str(tmp_path), "recursive-e2e", "preflight", "--json"]
    )

    assert result == 1
    assert '"ready":false' in capsys.readouterr().out


def test_project_recursive_preflight_debug_mode_warns_before_inspection(
    tmp_path: Path,
    capsys,
) -> None:
    recursive_project(tmp_path)

    result = cli.main(
        [
            "project",
            "--path",
            str(tmp_path),
            "recursive-e2e",
            "preflight",
            "--show-host-paths",
        ]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert "do not share it unsanitized" in captured.err


def test_project_recursive_e2e_rejects_a_different_selected_project(
    tmp_path: Path,
    capsys,
) -> None:
    recursive_project(tmp_path)
    (tmp_path / "devcapsule-src" / "pyproject.toml").write_text(
        '[project]\nname = "different-project"\nversion = "0.0.0"\n',
        encoding="utf-8",
    )

    result = cli.main(
        ["project", "--path", str(tmp_path), "recursive-e2e", "preflight"]
    )

    assert result == 2
    assert "repository self-test" in capsys.readouterr().err


def test_contained_display_preflight_needs_no_host_x11(tmp_path: Path) -> None:
    from devcapsule import recursive_dogfood as module
    from devcapsule.container_runtime.contract import DisplayPlan, RuntimePlan

    checkout = tmp_path / "checkout"
    home = tmp_path / "home"
    checkout.mkdir()
    home.mkdir()
    plan_path = tmp_path / "runtime-plan.json"
    plan = RuntimePlan.from_mapping(
        {
            "version": 1,
            "project_path": str(checkout),
            "home": str(home),
            "identity": {"uid": 1000, "gid": 1000, "user": "developer"},
            "state_slots": [],
            "component": {"id": "pycharm", "adapter": "jetbrains", "configuration": {}},
        }
    ).with_display(DisplayPlan.contained("127.0.0.1", 40000, "/run/devcapsule-display-token"))
    plan_path.write_text(plan.to_json(), encoding="utf-8")
    # No X11 socket mount, no Xauthority mount: the capsule's X server is its own.
    mounts = (
        Mount("/host/checkout", str(checkout), "bind", True),
        Mount("/host/home", str(home), "bind", True),
        Mount("/host/plan", str(plan_path), "bind", False),
    )
    container = ContainerInspection(
        "a" * 64, "dogfood-current", "sha256:" + "b" * 64, None, "host", mounts, "/docker/overlay/current/diff"
    )
    builder = module._ReportBuilder()
    module._inspect_required_mounts(
        builder,
        checkout_root=checkout,
        runtime_plan_path=plan_path,
        runtime_plan=plan,
        container=container,
        env={"HOME": str(home), "DISPLAY": ":10", "XAUTHORITY": "/tmp/devcapsule-runtime-1000/display/Xauthority"},
    )
    by_check = {item.check: item for item in builder.findings}
    assert "x11-mount" not in by_check
    assert by_check["display"].status == "pass" and "own desktop" in by_check["display"].summary
    assert by_check["display-authorization"].status == "pass"
    assert not [item for item in builder.findings if item.status == "error"]
