"""The session log framework: names, levels, the lifecycle record, the tee."""

from __future__ import annotations

from collections.abc import Buffer
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import gzip
import io
import logging
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Iterator

import pytest

from devcapsule import logs

pytestmark = pytest.mark.legacy


@pytest.fixture(autouse=True)
def clean_logging() -> Iterator[None]:
    """Each test configures from a bare root logger and leaves none of its handlers behind."""
    yield
    logs.reset()


def test_log_files_follow_one_recognizable_pattern(tmp_path: Path) -> None:
    assert logs.log_path(tmp_path, "launcher") == tmp_path / "devcapsule-launcher.log"
    assert logs.log_path(tmp_path, "window-manager").name == "devcapsule-window-manager.log"
    for bad in ("", "a/b", " spaced"):
        with pytest.raises(ValueError, match="plain words"):
            logs.log_path(tmp_path, bad)


def test_the_baseline_is_warning_and_the_override_names_a_level() -> None:
    assert logs.level_from_environment({}) == logging.WARNING
    assert logs.level_from_environment({logs.LEVEL_ENV: "debug"}) == logging.DEBUG
    assert logs.level_from_environment({logs.LEVEL_ENV: " Info "}) == logging.INFO
    with pytest.raises(logs.LogLevelError, match="DEBUG, INFO, WARNING, ERROR, not 'loud'"):
        logs.level_from_environment({logs.LEVEL_ENV: "loud"})


def test_configure_writes_warnings_to_the_file_with_utc_timestamps_and_drops_info(tmp_path: Path) -> None:
    path = logs.configure("launcher", tmp_path, environ={})
    assert path == tmp_path / "devcapsule-launcher.log"
    logger = logging.getLogger("devcapsule.launcher")
    logger.info("not kept")
    logger.warning("kept: %s", "detail")
    logging.getLogger("devcapsule").warning("root of the package")
    text = path.read_text(encoding="utf-8")
    assert "not kept" not in text
    lines = text.splitlines()
    assert len(lines) == 2
    assert lines[0].endswith(f"WARNING devcapsule.launcher[{os.getpid()}]: kept: detail")
    assert lines[0][:21].endswith("Z ") and lines[0][4] == "-" and lines[0][10] == "T"


def test_lifecycle_events_are_recorded_at_info_whatever_the_baseline(tmp_path: Path) -> None:
    path = logs.configure("supervisor", tmp_path, environ={})
    events = logs.events_logger("supervisor")
    events.info("child %r started", "xvnc")
    logging.getLogger("devcapsule.supervisor").info("ordinary info stays out")
    assert path is not None
    text = path.read_text(encoding="utf-8")
    assert "INFO devcapsule.supervisor.events" in text and "child 'xvnc' started" in text
    assert "ordinary info" not in text


def test_the_override_lowers_the_baseline_for_ordinary_loggers(tmp_path: Path) -> None:
    path = logs.configure("launcher", tmp_path, environ={logs.LEVEL_ENV: "DEBUG"})
    logging.getLogger("devcapsule.launcher").debug("now kept")
    assert path is not None and "DEBUG devcapsule.launcher" in path.read_text(encoding="utf-8")


def test_configure_prints_warnings_to_the_console_in_the_component_form(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    logs.configure("supervisor", None, environ={})
    logging.getLogger("devcapsule.supervisor").warning("session end requested")
    logs.events_logger("supervisor").info("child started")
    err = capsys.readouterr().err
    assert err == "devcapsule supervisor: session end requested\n"


def test_configure_is_repeatable_and_reports_a_bad_override_and_an_unwritable_directory(tmp_path: Path) -> None:
    reports: list[str] = []
    first = logs.configure("launcher", tmp_path, environ={}, console=reports.append)
    second = logs.configure("launcher", tmp_path, environ={logs.LEVEL_ENV: "loud"}, console=reports.append)
    assert first == second
    installed = [h for h in logging.getLogger().handlers if getattr(h, "_devcapsule_installed", False)]
    assert len(installed) == 2  # one console, one file; never accumulated
    assert reports == ["devcapsule launcher: DEVCAPSULE_LOG_LEVEL must be one of DEBUG, INFO, WARNING, ERROR, not 'loud'; logging at WARNING"]
    blocked = tmp_path / "file-not-directory"
    blocked.write_text("", encoding="utf-8")
    assert logs.configure("launcher", blocked / "logs", environ={}, console=reports.append) is None
    assert reports[-1].startswith("devcapsule launcher: cannot write") and reports[-1].endswith("logging to the console only")


def test_session_ids_sort_by_start_time() -> None:
    earlier = logs.new_session_id(1_700_000_000)
    later = logs.new_session_id(1_700_000_001)
    assert earlier.startswith("20231114-221320-") and len(earlier) == len("20231114-221320-abcd")
    assert earlier < later


def test_prune_removes_the_oldest_sessions_until_the_budget_fits_and_spares_the_current(tmp_path: Path) -> None:
    manifest = '{"format": 1, "ended-at": "2026-01-05T00:00:00Z"}'
    for name, size in (("20260101-000000-aaaa", 30), ("20260102-000000-bbbb", 30), ("20260103-000000-cccc", 30), ("20260104-000000-dddd", 5)):
        (tmp_path / name).mkdir()
        (tmp_path / name / "devcapsule-x.log").write_bytes(b"x" * size)
        (tmp_path / name / "session.json").write_text(manifest, encoding="utf-8")
    (tmp_path / "not-a-dir").write_text("", encoding="utf-8")
    session = 30 + len(manifest)
    assert logs.directory_size(tmp_path / "20260101-000000-aaaa") == session
    # Three full sessions and a small one; removing the oldest is enough.
    assert logs.prune_sessions(tmp_path, budget_bytes=2 * session + (5 + len(manifest)) + 10, current="20260104-000000-dddd") == ["20260101-000000-aaaa"]
    assert logs.prune_sessions(tmp_path, budget_bytes=0, current="20260101-000000-aaaa") == ["20260102-000000-bbbb", "20260103-000000-cccc", "20260104-000000-dddd"]
    assert sorted(entry.name for entry in tmp_path.iterdir()) == ["not-a-dir"]
    assert logs.prune_sessions(tmp_path / "absent", budget_bytes=1, current="x") == []
    with pytest.raises(ValueError):
        logs.prune_sessions(tmp_path, budget_bytes=-1, current="x")


def test_the_budget_knob_parses_sizes_and_has_a_floor() -> None:
    assert logs.parse_size("256M") == 256 * 1024 ** 2
    assert logs.parse_size(" 1g ") == 1024 ** 3
    assert logs.parse_size("512KiB") == 512 * 1024
    assert logs.parse_size("4096") == 4096
    assert logs.format_size(256 * 1024 ** 2) == "256 MiB" and logs.format_size(1024 ** 3) == "1 GiB" and logs.format_size(1500) == "1500 bytes"
    assert logs.budget_from_environment({}) == 256 * 1024 ** 2
    assert logs.budget_from_environment({logs.BUDGET_ENV: "64M"}) == 64 * 1024 ** 2
    with pytest.raises(logs.LogBudgetError, match="DEVCAPSULE_LOG_BUDGET: 'much' is not a size; use a number with K, M or G"):
        logs.budget_from_environment({logs.BUDGET_ENV: "much"})
    with pytest.raises(logs.LogBudgetError, match="at least 16 MiB"):
        logs.budget_from_environment({logs.BUDGET_ENV: "8M"})
    # One thirty-second of the budget per segment, between 1 and 10 MiB.
    assert logs.segment_bytes_for(256 * 1024 ** 2) == 8 * 1024 ** 2
    assert logs.segment_bytes_for(16 * 1024 ** 2) == 1024 ** 2
    assert logs.segment_bytes_for(10 * 1024 ** 3) == 10 * 1024 ** 2


@pytest.mark.parametrize("text", ["", " ", "-1M", "1.5G", "1T", "1iB", "9" * 5000])
def test_invalid_sizes_raise_the_recoverable_budget_error(text: str) -> None:
    with pytest.raises(logs.LogBudgetError):
        logs.parse_size(text)


@pytest.mark.parametrize("size", [0, 1, 1023, 1024, 1025, 16 * 1024 ** 2, 1024 ** 3, 3 * 1024 ** 3])
def test_formatted_sizes_are_exact(size: int) -> None:
    # Byte counts and binary units must not round when shown in diagnostics.
    text = logs.format_size(size)
    if text.endswith(" bytes"):
        assert text == f"{size} bytes"
    else:
        assert logs.parse_size(text) == size


def run_tee(tmp_path: Path, payload: bytes, **options: object) -> tuple[bytes, Path]:
    passthrough = io.BytesIO()
    path = tmp_path / "devcapsule-child.log"
    tee = logs.Tee(io.BytesIO(payload), path, passthrough, clock=lambda: 0.0, **options)  # type: ignore[arg-type]
    tee.start()
    tee.join(5.0)
    return passthrough.getvalue(), path


def test_tee_stamps_every_line_into_the_file_and_copies_nothing_to_the_console(tmp_path: Path) -> None:
    # The file is the record (C10, 2026-10-22): a healthy launch no longer
    # looks unhealthy under the display stack's ERROR-labelled chatter.
    passthrough, path = run_tee(tmp_path, b"first line\nsecond\nno newline at the end")
    assert passthrough == b""
    assert path.read_bytes() == (
        b"1970-01-01T00:00:00Z first line\n1970-01-01T00:00:00Z second\n1970-01-01T00:00:00Z no newline at the end"
    )


def test_tee_degrades_to_a_plain_copy_when_the_file_cannot_be_opened(tmp_path: Path) -> None:
    reports: list[str] = []
    passthrough = io.BytesIO()
    tee = logs.Tee(io.BytesIO(b"still seen\n"), tmp_path / "missing" / "devcapsule-x.log", passthrough, console=reports.append)
    tee.start()
    tee.join(5.0)
    assert passthrough.getvalue() == b"still seen\n"
    assert len(reports) == 1 and "devcapsule-x.log goes to the console only" in reports[0]


def test_tee_follows_a_real_child_process(tmp_path: Path) -> None:
    process = subprocess.Popen(
        [sys.executable, "-c", "import sys; print('out'); print('err', file=sys.stderr)"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    assert process.stdout is not None
    passthrough = io.BytesIO()
    path = tmp_path / "devcapsule-job.log"
    tee = logs.Tee(process.stdout, path, passthrough).start()
    assert process.wait(timeout=10) == 0
    tee.join(5.0)
    assert passthrough.getvalue() == b""
    text = path.read_text(encoding="utf-8")
    assert sorted(line.split("Z ")[1] for line in text.splitlines()) == ["err", "out"]


def test_reconfigure_closes_old_file_and_keeps_unrelated_handlers(tmp_path: Path) -> None:
    unrelated = logging.NullHandler()
    root = logging.getLogger()
    root.addHandler(unrelated)
    try:
        first = logs.configure("launcher", tmp_path / "first", environ={logs.LEVEL_ENV: "DEBUG"})
        old = next(h for h in root.handlers if isinstance(h, logs._SessionFileHandler))
        logging.getLogger("devcapsule.launcher").debug("first session")
        second = logs.configure("launcher", tmp_path / "second", environ={logs.LEVEL_ENV: "ERROR"})
        assert old._file is None and unrelated in root.handlers
        logger = logging.getLogger("devcapsule.launcher")
        logger.debug("discarded debug")
        logger.warning("discarded warning")
        logs.events_logger("launcher").info("second session")
        assert first is not None and second is not None
        assert "second session" not in first.read_text()
        assert "first session" not in second.read_text()
        assert "discarded" not in second.read_text()
        assert second.read_text().count("second session") == 1
        logs.configure("launcher", None, environ={})
        logs.events_logger("launcher").info("console only")
        assert "console only" not in second.read_text()
    finally:
        root.removeHandler(unrelated)


@pytest.mark.parametrize("close_fails", [False, True])
def test_tee_write_failure_reports_once_and_keeps_forwarding(tmp_path: Path, monkeypatch, close_fails: bool) -> None:
    class FullDisk(io.BytesIO):
        def write(self, data: Buffer, /) -> int:
            raise OSError("disk full")

        def close(self) -> None:
            super().close()
            if close_fails:
                raise OSError("close failed too")

    real = open(tmp_path / "log", "ab")  # the segmented file reads its size from the descriptor
    file = FullDisk()
    file.fileno = real.fileno  # type: ignore[method-assign]
    monkeypatch.setattr("builtins.open", lambda *args, **kwargs: file)
    passthrough = io.BytesIO()
    reports: list[str] = []
    tee = logs.Tee(io.BytesIO(), tmp_path / "log", passthrough, console=reports.append)
    # Run synchronously so a broken write path fails this test directly.
    tee._forward(b"first\n")
    tee._forward(b"second\n")
    assert passthrough.getvalue() == b"first\nsecond\n"
    assert file.closed and len(reports) == 1 and "disk full" in reports[0]
    real.close()


def test_tee_write_failure_mid_chunk_and_mid_line_copies_only_unwritten_bytes(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "log"
    passthrough = io.BytesIO()
    reports: list[str] = []
    tee = logs.Tee(io.BytesIO(), path, passthrough, clock=lambda: 0.0, console=reports.append)
    assert tee._file is not None
    real_write = tee._file.write
    writes = 0

    def fail_on_third(data: bytes) -> None:
        nonlocal writes
        writes += 1
        if writes >= 3:
            raise OSError("disk full")
        real_write(data)

    monkeypatch.setattr(tee._file, "write", fail_on_third)
    tee._forward(b"split ")
    tee._forward(b"first\nsecond\nthird\n")
    tee._forward(b"fourth\n")
    assert path.read_bytes() == b"1970-01-01T00:00:00Z split first\n"
    assert passthrough.getvalue() == b"second\nthird\nfourth\n"
    assert tee._file is None and len(reports) == 1 and "disk full" in reports[0]


def test_tee_ownership_failure_closes_file_and_keeps_console(tmp_path: Path, monkeypatch) -> None:
    file = io.BytesIO()
    monkeypatch.setattr("builtins.open", lambda *args, **kwargs: file)

    def fail(path, owner):
        raise PermissionError("chown denied")

    monkeypatch.setattr(logs, "own", fail)
    reports: list[str] = []
    passthrough, _ = run_tee(tmp_path, b"still seen\n", owner=(1234, 5678), console=reports.append)
    assert file.closed and passthrough == b"still seen\n"
    assert len(reports) == 1 and "chown denied" in reports[0]


def test_tee_bounds_reads_without_repeating_timestamps_within_a_line(tmp_path: Path) -> None:
    payload = b"x" * (2 * logs._TEE_READ_BYTES) + b"\nlast\rbyte\n"

    class BoundedSource(io.BytesIO):
        def read1(self, size: int | None = -1) -> bytes:
            assert size is not None and 0 < size <= logs._TEE_READ_BYTES
            return super().read1(size)

    path = tmp_path / "log"
    passthrough = io.BytesIO()
    tee = logs.Tee(BoundedSource(payload), path, passthrough, clock=lambda: 0.0).start()
    tee.join(5)
    assert passthrough.getvalue() == b""
    assert path.read_bytes() == b"1970-01-01T00:00:00Z " + payload.replace(b"\nlast", b"\n1970-01-01T00:00:00Z last")


def test_prune_never_takes_a_session_that_is_still_running_unless_it_is_abandoned(tmp_path: Path) -> None:
    import json
    import time

    now = datetime(2026, 1, 10, 12, tzinfo=timezone.utc).timestamp()
    running = tmp_path / "20260110-100000-aaaa"  # two hours old, no end recorded
    abandoned = tmp_path / "20260101-100000-bbbb"  # nine days old, no end recorded
    ended = tmp_path / "20260110-110000-cccc"
    for directory in (running, abandoned, ended):
        directory.mkdir()
        (directory / "devcapsule-x.log").write_bytes(b"x" * 10)
    (ended / "session.json").write_text(json.dumps({"format": 1, "ended-at": "2026-01-10T11:30:00Z"}), encoding="utf-8")
    (running / "session.json").write_text(json.dumps({"format": 1}), encoding="utf-8")
    assert not logs.session_ended(running, now=now)
    assert logs.session_ended(abandoned, now=now) and logs.session_ended(ended, now=now)
    assert logs.session_ended(tmp_path / "not-a-session", now=now)
    assert logs.prune_sessions(tmp_path, budget_bytes=0, current="20260110-120000-dddd", now=now) == [abandoned.name, ended.name]
    assert sorted(entry.name for entry in tmp_path.iterdir()) == [running.name]


@pytest.mark.parametrize("tz", ["UTC0", "EST5EDT,M3.2.0,M11.1.0", "JST-9"])
def test_abandonment_uses_utc_even_during_daylight_saving(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, tz: str,
) -> None:
    directory = tmp_path / "20260701-120000-aaaa"
    boundary = datetime(2026, 7, 8, 12, tzinfo=timezone.utc).timestamp()
    try:
        with monkeypatch.context() as context:
            context.setenv("TZ", tz)
            time.tzset()
            assert not logs.session_ended(directory, now=boundary - 1)
            assert not logs.session_ended(directory, now=boundary)
            assert logs.session_ended(directory, now=boundary + 1)
    finally:
        time.tzset()


@pytest.mark.parametrize("manifest", [None, b"{", b"\xff", b"[]", b'{"ended-at": null}'])
def test_unreadable_manifest_requires_abandonment_before_pruning(tmp_path: Path, manifest: bytes | None) -> None:
    directory = tmp_path / "20260701-120000-aaaa"
    directory.mkdir()
    (directory / "devcapsule-job.log").write_bytes(b"output")
    if manifest is not None:
        (directory / logs.SESSION_MANIFEST).write_bytes(manifest)
    boundary = datetime(2026, 7, 8, 12, tzinfo=timezone.utc).timestamp()
    assert logs.prune_sessions(tmp_path, budget_bytes=0, current="other", now=boundary) == []
    assert directory.exists()
    assert logs.prune_sessions(tmp_path, budget_bytes=0, current="other", now=boundary + 1) == [directory.name]


def test_inaccessible_manifest_does_not_make_a_young_session_prunable(tmp_path: Path) -> None:
    directory = tmp_path / "20260701-120000-aaaa"
    directory.mkdir()
    # Reading a directory as the manifest raises OSError even when run as root.
    (directory / logs.SESSION_MANIFEST).mkdir()
    (directory / "devcapsule-job.log").write_bytes(b"output")
    now = datetime(2026, 7, 1, 13, tzinfo=timezone.utc).timestamp()
    assert logs.prune_sessions(tmp_path, budget_bytes=0, current="other", now=now) == []


def segments(path: Path) -> dict[str, bytes]:
    """The rotated segments beside ``path``, decompressed, by suffix."""
    import gzip

    return {entry.name[len(path.name):]: gzip.decompress(entry.read_bytes()) for entry in sorted(path.parent.glob(path.name + ".*.gz"))}


def test_a_segmented_file_rotates_at_the_exact_size_and_keeps_the_count(tmp_path: Path) -> None:
    path = tmp_path / "devcapsule-x.log"
    file = logs.SegmentedFile(path, segment_bytes=100, rotations=2)
    for label in (b"a", b"b", b"c", b"d"):
        file.write(label * 60)
        assert file.size <= 100 and path.stat().st_size == file.size
    file.close()
    assert path.read_bytes() == b"d" * 60
    assert segments(path) == {".1.gz": b"c" * 60, ".2.gz": b"b" * 60}  # the oldest, a, is gone
    reopened = logs.SegmentedFile(path, segment_bytes=100, rotations=2)
    assert reopened.size == 60  # the live file's size is read back, so the bound holds across reopening
    reopened.write(b"e" * 50)  # 110 > 100: rotates first
    reopened.close()
    assert path.read_bytes() == b"e" * 50 and segments(path) == {".1.gz": b"d" * 60, ".2.gz": b"c" * 60}
    with pytest.raises(ValueError):
        logs.SegmentedFile(path, segment_bytes=0, rotations=1)


def test_a_single_write_larger_than_the_segment_goes_into_a_fresh_file_alone(tmp_path: Path) -> None:
    path = tmp_path / "devcapsule-x.log"
    file = logs.SegmentedFile(path, segment_bytes=100, rotations=1)
    file.write(b"short\n")
    file.write(b"L" * 150)
    assert file.size == 150 and segments(path) == {".1.gz": b"short\n"}
    file.write(b"next\n")  # rotates again: the oversize write is sealed on its own
    file.close()
    assert path.read_bytes() == b"next\n" and segments(path) == {".1.gz": b"L" * 150}


def test_a_segmented_file_gives_every_file_it_creates_to_the_owner(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(logs.os, "geteuid", lambda: 0)
    owned: list[Path] = []
    monkeypatch.setattr(logs.os, "chown", lambda path, uid, gid: owned.append(Path(path)) if (uid, gid) == (1234, 5678) else None)
    path = tmp_path / "devcapsule-x.log"
    file = logs.SegmentedFile(path, segment_bytes=10, rotations=1, owner=(1234, 5678))
    file.write(b"x" * 8)
    file.write(b"y" * 8)
    file.close()
    assert owned == [path, path.with_name("devcapsule-x.log.1.gz.tmp"), path]


def test_empty_rotation_preserves_history_and_exact_fill_waits_for_more_data(tmp_path: Path) -> None:
    path = tmp_path / "log"
    file = logs.SegmentedFile(path, segment_bytes=4, rotations=1)
    file.write(b"1234")
    assert file.size == 4 and segments(path) == {}
    file.write(b"")
    assert segments(path) == {}
    file.rotate()
    file.rotate()  # an empty live file must not evict the previous output
    assert path.read_bytes() == b"" and file.size == 0
    assert segments(path) == {".1.gz": b"1234"}
    file.write(b"oversize")
    file.close()
    reopened = logs.SegmentedFile(path, segment_bytes=4, rotations=1)
    assert reopened.size == len(b"oversize")
    reopened.write(b"")
    assert path.read_bytes() == b"oversize"
    reopened.write(b"next")
    reopened.close()
    assert path.read_bytes() == b"next" and segments(path) == {".1.gz": b"oversize"}
    with pytest.raises(ValueError, match="closed"):
        reopened.rotate()


@pytest.mark.parametrize("rotations", [3, 4])
def test_rotation_ages_archives_across_a_gap(tmp_path: Path, rotations: int) -> None:
    path = tmp_path / "log"
    file = logs.SegmentedFile(path, segment_bytes=4, rotations=rotations)
    file.segment_path(1).write_bytes(gzip.compress(b"recent"))
    file.segment_path(3).write_bytes(gzip.compress(b"oldest"))
    file.write(b"live")
    file.write(b"next")
    file.close()
    expected = {".1.gz": b"live", ".2.gz": b"recent"}
    if rotations == 4:
        expected[".4.gz"] = b"oldest"
    assert segments(path) == expected


def test_compression_failure_preserves_history_and_cleans_owned_staging(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "log"
    owned: list[Path] = []
    monkeypatch.setattr(logs, "own", lambda path, owner: owned.append(path))
    file = logs.SegmentedFile(path, segment_bytes=4, rotations=2, owner=(1234, 5678))
    file.segment_path(1).write_bytes(gzip.compress(b"recent"))
    file.segment_path(2).write_bytes(gzip.compress(b"oldest"))
    staging = path.with_name("log.1.gz.tmp")
    staging.write_bytes(b"left by an interrupted compression")

    def fail(source, target):
        assert staging in owned  # ownership precedes writing the payload
        target.write(source.read(2))
        raise OSError("compression failed")

    monkeypatch.setattr(logs.shutil, "copyfileobj", fail)
    file.write(b"live")
    with pytest.raises(OSError, match="compression failed"):
        file.write(b"next")
    file.close()
    assert not staging.exists()
    assert path.read_bytes() == b"live"
    assert segments(path) == {".1.gz": b"recent", ".2.gz": b"oldest"}


@pytest.mark.parametrize("step", ["shift", "publish", "unlink", "reopen"])
def test_rotation_failure_keeps_the_live_payload_recoverable(tmp_path: Path, monkeypatch, step: str) -> None:
    path = tmp_path / "log"
    file = logs.SegmentedFile(path, segment_bytes=4, rotations=3)
    for index, payload in enumerate((b"recent", b"older", b"oldest"), 1):
        file.segment_path(index).write_bytes(gzip.compress(payload))
    file.write(b"live")
    real_replace, real_unlink = os.replace, os.unlink

    def replace(source, destination):
        if (step == "shift" and source == file.segment_path(1)) or (step == "publish" and str(source).endswith(".tmp")):
            raise OSError(step)
        real_replace(source, destination)

    def unlink(name, **kwargs):
        if step == "unlink" and name == path:
            raise OSError(step)
        real_unlink(name, **kwargs)

    def reopen():
        raise OSError("reopen")

    monkeypatch.setattr(logs.os, "replace", replace)
    monkeypatch.setattr(logs.os, "unlink", unlink)
    if step == "reopen":
        monkeypatch.setattr(file, "_open", reopen)
    with pytest.raises(OSError, match=step):
        file.write(b"next")
    file.close()
    assert not path.with_name("log.1.gz.tmp").exists()
    assert (path.read_bytes() if path.exists() else None) == (None if step == "reopen" else b"live")
    expected = {".3.gz": b"older"}  # the oldest has already expired
    if step == "shift":
        expected[".1.gz"] = b"recent"
    else:
        expected[".2.gz"] = b"recent"
        if step in ("unlink", "reopen"):
            expected[".1.gz"] = b"live"
    assert segments(path) == expected


@pytest.mark.parametrize("stalls", [False, True])
def test_short_writes_are_completed_or_reported_with_the_actual_size(tmp_path: Path, stalls: bool) -> None:
    class ShortFile(io.BytesIO):
        def write(self, data: Buffer, /) -> int:
            if stalls and self.tell() >= 3:
                return 0
            return super().write(memoryview(data)[:3])

    file = logs.SegmentedFile(tmp_path / "log", segment_bytes=10, rotations=1)
    file.close()
    target = ShortFile()
    file._file = target
    if stalls:
        with pytest.raises(OSError, match="no progress"):
            file.write(b"1234567")
    else:
        file.write(b"1234567")
    assert target.getvalue() == (b"123" if stalls else b"1234567")
    assert file.size == len(target.getvalue())
    file.close()


def test_handler_serializes_threaded_records_through_rotation(tmp_path: Path) -> None:
    path = tmp_path / "log"
    handler = logs._SessionFileHandler(path, segment_bytes=32, rotations=50, owner=None, report=pytest.fail)
    handler.setFormatter(logging.Formatter("%(message)s"))

    def emit(index: int) -> None:
        handler.handle(logging.LogRecord("test", logging.INFO, "", 0, f"record {index:03d}", (), None))

    try:
        with ThreadPoolExecutor(max_workers=4) as workers:
            list(workers.map(emit, range(100)))
    finally:
        handler.close()
    rotated = segments(path)
    payloads = [*rotated.values(), path.read_bytes()]
    assert all(len(payload) <= 32 for payload in payloads)
    assert sorted(b"".join(payloads).splitlines()) == [f"record {index:03d}".encode() for index in range(100)]


def test_tee_line_split_across_reads_can_continue_in_the_next_segment(tmp_path: Path) -> None:
    path = tmp_path / "log"
    passthrough = io.BytesIO()
    tee = logs.Tee(io.BytesIO(), path, passthrough, segment_bytes=32, rotations=1, clock=lambda: 0.0)
    tee._forward(b"a" * 10)
    tee._forward(b"continued\n")
    tee.start()
    tee.join(5)
    assert passthrough.getvalue() == b""
    assert segments(path) == {".1.gz": b"1970-01-01T00:00:00Z " + b"a" * 10}
    assert path.read_bytes() == b"continued\n"


def test_the_handler_rotates_its_own_file_at_the_segment(tmp_path: Path) -> None:
    path = logs.configure("supervisor", tmp_path, environ={}, segment_bytes=160, rotations=2)
    assert path is not None
    for index in range(6):
        logs.events_logger("supervisor").info("record %d padded to a fixed width ........", index)
    assert path.stat().st_size <= 160 and b"record 5" in path.read_bytes()
    rotated = segments(path)
    assert set(rotated) == {".1.gz", ".2.gz"}
    assert all(0 < len(data) <= 160 and b"record " in data for data in rotated.values())
    assert b"record 4" in rotated[".1.gz"] or b"record 5" not in rotated[".1.gz"]


def test_a_handler_write_failure_reports_once_and_keeps_the_console(tmp_path: Path, monkeypatch, capsys) -> None:
    reports: list[str] = []
    logs.configure("supervisor", tmp_path, environ={}, console=reports.append)
    handler = next(h for h in logging.getLogger().handlers if isinstance(h, logs._SessionFileHandler))
    assert handler._file is not None

    def fail(data: bytes) -> None:
        raise OSError("bind mount unavailable")

    monkeypatch.setattr(handler._file, "write", fail)
    logger = logging.getLogger("devcapsule.supervisor")
    logger.warning("first warning")
    logger.warning("second warning")
    assert handler._file is None
    assert len(reports) == 1 and "bind mount unavailable" in reports[0]
    assert capsys.readouterr().err == "devcapsule supervisor: first warning\ndevcapsule supervisor: second warning\n"


def test_tee_rotates_a_real_child_output_at_the_segment(tmp_path: Path) -> None:
    import subprocess

    process = subprocess.Popen(
        [sys.executable, "-c", "import sys\nfor i in range(4000): print(f'line {i:05d} ' + 'x' * 60)"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    assert process.stdout is not None
    passthrough = io.BytesIO()
    path = tmp_path / "devcapsule-job.log"
    tee = logs.Tee(process.stdout, path, passthrough, segment_bytes=100_000, rotations=3, clock=lambda: 0.0).start()
    assert process.wait(timeout=20) == 0
    tee.join(10.0)
    payload = b"".join(f"line {index:05d} ".encode("ascii") + b"x" * 60 + b"\n" for index in range(4000))
    assert passthrough.getvalue() == b""
    assert path.stat().st_size <= 100_000
    rotated = segments(path)
    assert set(rotated) == {".1.gz", ".2.gz", ".3.gz"} and all(len(data) <= 100_000 for data in rotated.values())
    kept = b"".join(rotated[key] for key in (".3.gz", ".2.gz", ".1.gz")) + path.read_bytes()
    stamped = b"".join(b"1970-01-01T00:00:00Z " + line for line in payload.splitlines(keepends=True))
    # Pipe reads can split a line just before rotation. The retained output
    # is an exact byte suffix, even if its first line began in a dropped file.
    assert stamped.endswith(kept)
