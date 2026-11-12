"""The notifications store: the contract's validation, the merged listing, and where the store lives."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import stat

import pytest

from devcapsule import notifications
from devcapsule.notifications import (
    ListingError,
    Notification,
    NotificationError,
    NotificationStore,
    listing_document,
    notification_from_mapping,
    store_for,
    store_in_environment,
)

pytestmark = pytest.mark.legacy

DOCUMENT = {
    "format": 1, "id": "20261009t120000-abc123", "kind": "gate", "title": "Gate failed on main",
    "summary": "Two unit cases; see the **log**.", "link": "/records/engineering-docs/README.md",
    "posted-by": "ci", "posted-at": "2026-10-09T12:00:00+00:00", "read-at": None,
}


def write(directory: Path, name: str, document: object) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


@pytest.fixture
def store(tmp_path: Path) -> NotificationStore:
    return NotificationStore(tmp_path / "state" / "notifications", tmp_path / "state" / "decisions")


def test_a_valid_document_round_trips() -> None:
    notification = notification_from_mapping(DOCUMENT)
    assert notification == Notification("20261009t120000-abc123", "gate", "Gate failed on main", "ci",
                                        "2026-10-09T12:00:00+00:00", "Two unit cases; see the **log**.",
                                        "/records/engineering-docs/README.md")
    assert notification.unread
    assert notification.to_mapping() == DOCUMENT


@pytest.mark.parametrize("change, message", [
    ({"format": "1"}, "format must be 1"),
    ({"format": True}, "format must be 1"),
    ({"id": "Bad Id"}, "id must be lowercase"),
    ({"id": "-leading"}, "id must be lowercase"),
    ({"kind": "decision"}, "kind 'decision' is reserved"),
    ({"kind": "x" * 33}, "kind must be lowercase"),
    ({"title": " "}, "title must be a non-empty string"),
    ({"posted-by": None}, "posted-by must be a non-empty string"),
    ({"posted-at": "2026-10-09"}, "posted-at must be an ISO 8601 timestamp"),
    ({"posted-at": "noon"}, "posted-at must be an ISO 8601 timestamp"),
    ({"read-at": 5}, "read-at must be a string"),
    ({"link": "records/x.md"}, "link must be a console path"),
    ({"link": "/records/a b.md"}, "link must be a console path"),
    ({"link": "/" + "x" * 1000}, "link must be a console path"),
    ({"summary": "\udc80"}, "summary must contain valid Unicode text"),
])
def test_malformed_documents_are_refused_with_the_field_named(change: dict[str, object], message: str) -> None:
    with pytest.raises(NotificationError, match=re.escape(message)):
        notification_from_mapping({**DOCUMENT, **change})


def test_not_an_object_is_refused() -> None:
    with pytest.raises(NotificationError, match="must be a JSON object"):
        notification_from_mapping(["not", "an", "object"])


def test_post_writes_a_validated_document_with_a_fresh_sortable_id(store: NotificationStore) -> None:
    first = store.post(kind="gate", title="First", posted_by="ci", now="2026-10-09T12:00:00+00:00")
    second = store.post(kind="gate", title="Second", posted_by="ci", summary="s", link="/records/x.md",
                        now="2026-10-09T12:00:01+02:00")
    assert first.id.startswith("20261009t120000-") and second.id.startswith("20261009t100001-")
    assert first.id != second.id and notifications.ID_PATTERN.fullmatch(second.id)
    written = json.loads(store.path(second.id).read_text(encoding="utf-8"))
    assert written == second.to_mapping() and written["read-at"] is None
    assert stat.S_IMODE(store.path(second.id).stat().st_mode) == 0o600
    with pytest.raises(NotificationError, match="kind 'decision' is reserved"):
        store.post(kind="decision", title="No", posted_by="ci")
    assert sorted(p.name for p in store.directory.iterdir()) == sorted([f"{first.id}.json", f"{second.id}.json"])


def test_listing_is_newest_first_and_merges_unanswered_decisions(store: NotificationStore) -> None:
    old = store.post(kind="gate", title="Old", posted_by="ci", now="2026-10-08T12:00:00+00:00")
    new = store.post(kind="note", title="New", posted_by="me", now="2026-10-10T12:00:00+00:00")
    write(store.decisions, "intake-pass.json", {"format": 1, "id": "intake-pass", "title": "Intake pass",
                                                "asked-by": "project-management", "asked-at": "2026-10-09T12:00:00+00:00",
                                                "items": []})
    write(store.decisions, "answered.json", {"format": 1, "id": "answered", "title": "Answered", "items": []})
    write(store.decisions, "answered.answer.json", {"format": 1, "id": "answered", "answered-at": "2026-10-09T13:00:00+00:00", "answers": {}})
    entries = store.list()
    assert [entry.id for entry in entries] == [new.id, "intake-pass", old.id]
    decision = entries[1]
    assert isinstance(decision, Notification)
    assert decision == Notification("intake-pass", "decision", "Intake pass", "project-management",
                                    "2026-10-09T12:00:00+00:00", link="/decisions/intake-pass")
    assert decision.unread
    document = listing_document(store)
    assert document["unread"] == 3 and [entry["id"] for entry in document["notifications"]] == [new.id, "intake-pass", old.id]
    store.mark_read(old.id, now="2026-10-10T13:00:00+00:00")
    unread = listing_document(store, unread_only=True)
    assert unread["unread"] == 2 and [entry["id"] for entry in unread["notifications"]] == [new.id, "intake-pass"]


def test_a_decision_without_a_title_or_timestamp_is_listed_from_its_file(store: NotificationStore) -> None:
    path = write(store.decisions, "bare.json", {"format": 1, "id": "bare", "items": []})
    os.utime(path, (1_760_000_000, 1_760_000_000))
    (entry,) = store.list()
    assert isinstance(entry, Notification)
    assert entry.title == "bare" and entry.posted_by == "an agent" and entry.posted_at == "2025-10-09T08:53:20+00:00"
    assert entry.link == "/decisions/bare"


def test_malformed_files_are_listed_as_errors_not_hidden(store: NotificationStore) -> None:
    good = store.post(kind="gate", title="Good", posted_by="ci", now="2026-10-09T12:00:00+00:00")
    write(store.directory, "broken.json", {"format": 1, "id": "other", "kind": "gate", "title": "x",
                                           "posted-by": "ci", "posted-at": "2026-10-09T12:00:00+00:00"})
    (store.directory / "garbage.json").write_text("{", encoding="utf-8")
    (store.directory / "Ignored.json").write_text("{}", encoding="utf-8")  # not an id: never listed
    (store.directory / "huge.json").write_bytes(b"[" + b" " * notifications.MAXIMUM_DOCUMENT_BYTES + b"]")
    (store.decisions.mkdir(parents=True, exist_ok=True))
    (store.decisions / "bad-decision.json").write_text("[]", encoding="utf-8")
    entries = store.list()
    errors = {entry.id: entry for entry in entries if isinstance(entry, ListingError)}
    assert [entry.id for entry in entries if isinstance(entry, Notification)] == [good.id]
    assert set(errors) == {"broken", "garbage", "huge", "bad-decision"}
    assert "carries id 'other'" in errors["broken"].error
    assert "not a JSON document" in errors["garbage"].error
    assert "larger than" in errors["huge"].error
    assert errors["bad-decision"].kind == "decision" and "must be a JSON object" in errors["bad-decision"].error
    assert json.loads(json.dumps(listing_document(store)))["notifications"][1]["error"]


def test_symbolic_links_and_special_files_are_refused(store: NotificationStore, tmp_path: Path) -> None:
    target = tmp_path / "elsewhere.json"
    target.write_text(json.dumps(DOCUMENT), encoding="utf-8")
    store.directory.mkdir(parents=True)
    (store.directory / "linked.json").symlink_to(target)
    os.mkfifo(store.directory / "pipe.json")
    errors = {entry.id: entry.error for entry in store.list() if isinstance(entry, ListingError)}
    assert set(errors) == {"linked", "pipe"}
    assert "cannot read linked.json" in errors["linked"]
    assert "must be a regular file" in errors["pipe"]


def test_read_marks_once_and_dismiss_removes(store: NotificationStore) -> None:
    posted = store.post(kind="gate", title="Gate", posted_by="ci", now="2026-10-09T12:00:00+00:00")
    read = store.mark_read(posted.id, now="2026-10-09T12:30:00+00:00")
    assert read.read_at == "2026-10-09T12:30:00+00:00" and not read.unread
    again = store.mark_read(posted.id, now="2026-10-09T13:00:00+00:00")
    assert again.read_at == "2026-10-09T12:30:00+00:00"
    assert json.loads(store.path(posted.id).read_text(encoding="utf-8"))["read-at"] == "2026-10-09T12:30:00+00:00"
    store.dismiss(posted.id)
    assert not store.path(posted.id).exists()
    with pytest.raises(NotificationError, match=f"no notification '{posted.id}'"):
        store.read(posted.id)


def test_decisions_are_neither_read_nor_dismissed_here(store: NotificationStore) -> None:
    write(store.decisions, "intake-pass.json", {"format": 1, "id": "intake-pass", "title": "Intake pass", "items": []})
    with pytest.raises(NotificationError, match="'intake-pass' is a decision: answer it in the web console"):
        store.mark_read("intake-pass")
    with pytest.raises(NotificationError, match="is a decision"):
        store.dismiss("intake-pass")
    assert (store.decisions / "intake-pass.json").exists()
    with pytest.raises(NotificationError, match="the id must be lowercase"):
        store.dismiss("../escape")


def test_store_in_environment_follows_xdg_state_and_the_overrides(tmp_path: Path) -> None:
    home = tmp_path / "home"
    by_home = store_in_environment({"HOME": str(home)})
    assert by_home.directory == home / ".local" / "state" / "devcapsule" / "notifications"
    assert by_home.decisions == home / ".local" / "state" / "devcapsule" / "decisions"
    by_state = store_in_environment({"HOME": str(home), "XDG_STATE_HOME": str(tmp_path / "xdg")})
    assert by_state.directory == tmp_path / "xdg" / "devcapsule" / "notifications"
    named = store_in_environment({"HOME": str(home), "DEVCAPSULE_NOTIFICATIONS": str(tmp_path / "n"),
                                  "DEVCAPSULE_CONSOLE_DECISIONS": str(tmp_path / "d")})
    assert named == NotificationStore(tmp_path / "n", tmp_path / "d")
    assert store_in_environment({"HOME": str(home), "DEVCAPSULE_NOTIFICATIONS": str(tmp_path / "s" / "n")}).decisions \
        == tmp_path / "s" / "decisions"


def test_inside_a_capsule_the_environment_wins_over_the_selected_path(tmp_path: Path) -> None:
    env = {"HOME": str(tmp_path / "home"), "DEVCAPSULE_CONTAINER_NAME": "capsule-1"}
    inside = store_for(tmp_path / "some" / "project", env)
    assert inside.directory == tmp_path / "home" / ".local" / "state" / "devcapsule" / "notifications"


def test_environment_store_posts_and_lists_with_a_linked_home(tmp_path: Path) -> None:
    home = tmp_path / "real-home"
    home.mkdir()
    linked_home = tmp_path / "home-link"
    linked_home.symlink_to(home, target_is_directory=True)
    store = store_in_environment({"HOME": str(linked_home)})

    posted = store.post(kind="note", title="Linked home", posted_by="agent")

    state = home / ".local" / "state" / "devcapsule"
    assert json.loads((state / "notifications" / f"{posted.id}.json").read_text()) == posted.to_mapping()
    assert store.decisions == state / "decisions"
    assert store.list() == [posted]


def test_environment_store_posts_and_lists_with_an_override_through_a_linked_parent(tmp_path: Path) -> None:
    parent = tmp_path / "real-state"
    parent.mkdir()
    linked_parent = tmp_path / "state-link"
    linked_parent.symlink_to(parent, target_is_directory=True)
    store = store_in_environment({"DEVCAPSULE_NOTIFICATIONS": str(linked_parent / "notifications")})

    posted = store.post(kind="note", title="Linked override", posted_by="agent")

    assert json.loads((parent / "notifications" / f"{posted.id}.json").read_text()) == posted.to_mapping()
    assert store.decisions == parent / "decisions"
    assert store.list() == [posted]


@pytest.mark.parametrize("link", ["//other.example/path", "/\\other.example/path", "/records/\u00a0x", "/records/\x7fx"])
def test_links_must_stay_on_the_console_origin(link: str) -> None:
    with pytest.raises(NotificationError, match="link must be a console path"):
        notification_from_mapping({**DOCUMENT, "link": link})


@pytest.mark.parametrize("change, field", [
    ({"format": 1.0}, "format"), ({"id": "a" * 101}, "id"),
    ({"kind": "-gate"}, "kind"), ({"title": 3}, "title"),
    ({"read-at": "yesterday"}, "read-at"), ({"posted-at": None}, "posted-at"),
])
def test_remaining_field_refusals(change: dict[str, object], field: str) -> None:
    with pytest.raises(NotificationError, match=field):
        notification_from_mapping({**DOCUMENT, **change})


def test_optional_fields_and_grammar_boundaries() -> None:
    document = {key: value for key, value in DOCUMENT.items() if key not in {"summary", "link", "read-at"}}
    document.update(id="a" * 100, kind="b" * 32)
    entry = notification_from_mapping(document)
    assert entry.summary == entry.link == entry.read_at == ""
    assert entry.id == "a" * 100 and entry.kind == "b" * 32


@pytest.mark.parametrize("operation", ["post", "mark_read"])
def test_writes_enforce_the_encoded_size_and_preserve_previous_state(store: NotificationStore, operation: str) -> None:
    if operation == "post":
        with pytest.raises(NotificationError, match="larger than 65536 bytes"):
            store.post(kind="note", title="Large", posted_by="agent", summary="\u00e9" * 32768)
        assert not store.directory.exists()
    else:
        entry = notification_from_mapping(DOCUMENT)
        compact = json.dumps(entry.to_mapping(), ensure_ascii=False, separators=(",", ":")) + "\n"
        document = {**DOCUMENT, "summary": "x" * (notifications.MAXIMUM_DOCUMENT_BYTES - len(compact.encode()) + len(entry.summary))}
        path = write(store.directory, f"{entry.id}.json", document)
        path.write_text(json.dumps(document, separators=(",", ":")) + "\n", encoding="utf-8")
        before = path.read_bytes()
        assert len(before) == notifications.MAXIMUM_DOCUMENT_BYTES
        assert store.read(entry.id).unread
        with pytest.raises(NotificationError, match="larger than 65536 bytes"):
            store.mark_read(entry.id)
        assert path.read_bytes() == before


@pytest.mark.parametrize("operation", ["post", "mark_read"])
def test_write_timestamp_refusals_name_the_field(store: NotificationStore, operation: str) -> None:
    if operation == "post":
        with pytest.raises(NotificationError, match="posted-at"):
            store.post(kind="note", title="T", posted_by="agent", now="bad")
        assert not store.directory.exists()
    else:
        entry = store.post(kind="note", title="T", posted_by="agent")
        before = store.path(entry.id).read_bytes()
        with pytest.raises(NotificationError, match="read-at"):
            store.mark_read(entry.id, now="bad")
        assert store.path(entry.id).read_bytes() == before


def test_decisions_use_their_own_size_limit(store: NotificationStore) -> None:
    write(store.decisions, "large.json", {"format": 1, "id": "large", "title": "Large", "context": "x" * 65536})
    (entry,) = store.list()
    assert isinstance(entry, Notification) and entry.title == "Large"
    (store.decisions / "large.json").write_bytes(b" " * (1024 * 1024 + 1))
    (error,) = store.list()
    assert isinstance(error, ListingError) and "1048576 bytes" in error.error


@pytest.mark.parametrize("change, field", [
    ({"format": True}, "format"), ({"id": "other"}, "id"),
    ({"title": "\ud800"}, "title"), ({"asked-by": []}, "asked-by"),
    ({"asked-at": "noon"}, "asked-at"),
])
def test_bad_decision_metadata_is_an_error(store: NotificationStore, change: dict[str, object], field: str) -> None:
    write(store.decisions, "question.json", {"format": 1, "id": "question", **change})
    (entry,) = store.list()
    assert isinstance(entry, ListingError) and entry.kind == "decision" and field in entry.error


@pytest.mark.parametrize("answer", ["symlink", "fifo", "directory", "json", "timestamp", "id", "format", "answers", "array"])
def test_invalid_answers_do_not_hide_decisions(store: NotificationStore, answer: str, tmp_path: Path) -> None:
    write(store.decisions, "question.json", {"format": 1, "id": "question"})
    path = store.decisions / "question.answer.json"
    document: dict[str, object] = {"format": 1, "id": "question", "answered-at": "2026-10-09T12:00:00+00:00", "answers": {}}
    if answer == "symlink":
        target = write(tmp_path, "answer.json", document)
        path.symlink_to(target)
    elif answer == "fifo":
        os.mkfifo(path)
    elif answer == "directory":
        path.mkdir()
    elif answer == "json":
        path.write_text("{", encoding="utf-8")
    elif answer == "array":
        write(store.decisions, path.name, [])
    else:
        changes: dict[str, dict[str, object]] = {
            "timestamp": {"answered-at": "noon"}, "id": {"id": "other"},
            "format": {"format": True}, "answers": {"answers": []},
        }
        document.update(changes[answer])
        write(store.decisions, path.name, document)
    (entry,) = store.list()
    assert isinstance(entry, ListingError) and entry.id == "question" and entry.kind == "decision"
    assert path.name in entry.error


@pytest.mark.parametrize("operation", ["list", "read", "mark_read", "dismiss", "post"])
@pytest.mark.parametrize("parent", [False, True])
def test_store_directory_links_cannot_reach_another_checkout(
    store: NotificationStore, tmp_path: Path, operation: str, parent: bool,
) -> None:
    victim = NotificationStore(tmp_path / "victim" / "notifications", tmp_path / "victim" / "decisions")
    path = write(victim.directory, f"{DOCUMENT['id']}.json", DOCUMENT)
    before = path.read_bytes()
    if parent:
        store.directory.parent.symlink_to(victim.directory.parent, target_is_directory=True)
    else:
        store.directory.parent.mkdir()
        store.directory.symlink_to(victim.directory, target_is_directory=True)
    with pytest.raises(NotificationError):
        if operation == "post":
            store.post(kind="note", title="No", posted_by="agent")
        elif operation == "list":
            store.list()
        else:
            getattr(store, operation)(DOCUMENT["id"])
    assert path.read_bytes() == before
    assert list(victim.directory.iterdir()) == [path]


def test_atomic_write_stays_in_the_opened_directory_when_it_is_replaced(
    store: NotificationStore, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    entry = store.post(kind="note", title="Original", posted_by="agent")
    other = tmp_path / "other"
    target = write(other, f"{entry.id}.json", {"untouched": True})
    previous = target.read_bytes()
    moved = store.directory.with_name("moved")
    real_replace = os.replace

    def swap(source: str, destination: str, *, src_dir_fd: int, dst_dir_fd: int) -> None:
        assert src_dir_fd == dst_dir_fd
        assert store.path(entry.id).read_bytes() != (store.directory / source).read_bytes()
        store.directory.rename(moved)
        store.directory.symlink_to(other, target_is_directory=True)
        real_replace(source, destination, src_dir_fd=src_dir_fd, dst_dir_fd=dst_dir_fd)

    monkeypatch.setattr(notifications.os, "replace", swap)
    read = store.mark_read(entry.id)
    assert json.loads((moved / target.name).read_bytes())["read-at"] == read.read_at
    assert target.read_bytes() == previous
    assert sorted(p.name for p in moved.iterdir()) == [target.name]


def test_failed_atomic_replace_preserves_document_and_removes_temporary(
    store: NotificationStore, monkeypatch: pytest.MonkeyPatch,
) -> None:
    entry = store.post(kind="note", title="Original", posted_by="agent")
    path = store.path(entry.id)
    before = path.read_bytes()

    def fail(*args: object, **kwargs: object) -> None:
        raise PermissionError("replace denied")

    monkeypatch.setattr(notifications.os, "replace", fail)
    with pytest.raises(NotificationError, match="replace denied"):
        store.mark_read(entry.id)
    assert path.read_bytes() == before and list(store.directory.iterdir()) == [path]


@pytest.mark.parametrize("invalid", ["../escape", "-leading", "A", "a" * 101, "", "a/b"])
@pytest.mark.parametrize("operation", ["read", "mark_read", "dismiss"])
def test_every_id_operation_refuses_invalid_ids(store: NotificationStore, invalid: str, operation: str) -> None:
    with pytest.raises(NotificationError, match="the id must"):
        getattr(store, operation)(invalid)
    assert not store.directory.exists()


def test_read_refuses_a_mismatched_document_id(store: NotificationStore) -> None:
    write(store.directory, "wrong.json", DOCUMENT)
    with pytest.raises(NotificationError, match="file name is the id"):
        store.read("wrong")


@pytest.mark.parametrize("raw", [b"\xff", b"[" * 16000 + b"]" * 16000], ids=["utf8", "deep-json"])
def test_undecodable_documents_become_listing_errors(store: NotificationStore, raw: bytes) -> None:
    store.directory.mkdir(parents=True)
    (store.directory / "broken.json").write_bytes(raw)
    (entry,) = store.list()
    assert isinstance(entry, ListingError) and "not a JSON document" in entry.error
    assert listing_document(store, unread_only=True)["notifications"] == [entry.to_mapping()]


def test_ordering_compares_instants_and_treats_naive_times_as_utc(store: NotificationStore) -> None:
    for key, stamp in [("first", "2026-10-09T12:00:00+02:00"), ("second", "2026-10-09T11:00:00")]:
        write(store.directory, f"{key}.json", {**DOCUMENT, "id": key, "posted-at": stamp})
    assert [entry.id for entry in store.list()] == ["second", "first"]


def test_environment_decisions_override_without_notifications_override(tmp_path: Path) -> None:
    store = store_in_environment({"HOME": str(tmp_path), "DEVCAPSULE_CONSOLE_DECISIONS": str(tmp_path / "questions")})
    assert store.decisions == tmp_path / "questions"
    assert store.directory == tmp_path / ".local/state/devcapsule/notifications"


@pytest.mark.parametrize("source", ["notifications", "decisions"])
def test_files_removed_after_scan_are_omitted(store: NotificationStore, source: str, monkeypatch: pytest.MonkeyPatch) -> None:
    directory = store.directory if source == "notifications" else store.decisions
    path = write(directory, "gone.json", {**DOCUMENT, "id": "gone"})
    scan = NotificationStore._document_stems

    def remove_after_scan(self: NotificationStore, directory: Path) -> list[str]:
        stems = scan(self, directory)
        if directory == path.parent:
            path.unlink()
        return stems

    monkeypatch.setattr(NotificationStore, "_document_stems", remove_after_scan)
    assert store.list() == []


def test_file_removed_during_scan_is_omitted(store: NotificationStore, monkeypatch: pytest.MonkeyPatch) -> None:
    path = write(store.directory, "gone.json", DOCUMENT)
    original_stat = os.stat

    def vanish(name: object, *args: object, **kwargs: object) -> os.stat_result:
        if name == "gone.json":
            path.unlink()
            raise FileNotFoundError(name)
        return original_stat(name, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(notifications.os, "stat", vanish)
    assert store.list() == []


def test_decision_timestamp_comes_from_the_file_that_was_read(store: NotificationStore, monkeypatch: pytest.MonkeyPatch) -> None:
    path = write(store.decisions, "question.json", {"format": 1, "id": "question"})
    os.utime(path, (1_760_000_000, 1_760_000_000))
    original = notifications._read_document

    def remove_after_read(path: Path, *, maximum: int = notifications.MAXIMUM_DOCUMENT_BYTES) -> tuple[object, float]:
        result = original(path, maximum=maximum)
        path.unlink()
        return result

    monkeypatch.setattr(notifications, "_read_document", remove_after_read)
    (entry,) = store.list()
    assert isinstance(entry, Notification) and entry.posted_at == "2025-10-09T08:53:20+00:00"


def test_scan_ignores_non_documents_and_sorts_equal_timestamps(store: NotificationStore) -> None:
    for name in ("z", "a"):
        write(store.directory, f"{name}.json", {**DOCUMENT, "id": name})
    (store.directory / "folder.json").mkdir()
    (store.directory / "ignored.answer.json").write_text("{}", encoding="utf-8")
    (store.directory / "ignored.txt").write_text("{}", encoding="utf-8")
    assert [entry.id for entry in store.list()] == ["a", "z"]


def test_reader_requests_only_the_bound_plus_one(store: NotificationStore, monkeypatch: pytest.MonkeyPatch) -> None:
    from typing import BinaryIO, cast

    path = write(store.directory, f"{DOCUMENT['id']}.json", DOCUMENT)
    original = os.fdopen
    requested: list[int] = []

    def bounded_open(descriptor: int, mode: str) -> BinaryIO:
        stream = original(descriptor, mode)
        read = stream.read

        def bounded_read(size: int = -1) -> bytes:
            requested.append(size)
            assert size == notifications.MAXIMUM_DOCUMENT_BYTES + 1
            return cast(bytes, read(size))

        monkeypatch.setattr(stream, "read", bounded_read)
        return cast(BinaryIO, stream)

    monkeypatch.setattr(notifications.os, "fdopen", bounded_open)
    assert store.read(path.stem).id == DOCUMENT["id"]
    assert requested == [notifications.MAXIMUM_DOCUMENT_BYTES + 1]


def test_planted_temporary_link_is_not_opened_or_removed(store: NotificationStore, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    entry = store.post(kind="note", title="Original", posted_by="agent")
    target = tmp_path / "record"
    target.write_text("untouched", encoding="utf-8")
    monkeypatch.setattr(notifications.secrets, "token_hex", lambda size: "fixed")
    planted = store.directory / f".{entry.id}.json.fixed.tmp"
    planted.symlink_to(target)
    before = store.path(entry.id).read_bytes()
    with pytest.raises(NotificationError, match="cannot write"):
        store.mark_read(entry.id)
    assert planted.is_symlink() and target.read_text() == "untouched"
    assert store.path(entry.id).read_bytes() == before


@pytest.mark.parametrize("failure", [FileNotFoundError, PermissionError])
def test_dismiss_handles_a_removed_file_and_reports_other_errors(
    store: NotificationStore, monkeypatch: pytest.MonkeyPatch, failure: type[OSError],
) -> None:
    entry = store.post(kind="note", title="Original", posted_by="agent")
    original = os.unlink

    def unlink(name: str, *, dir_fd: int) -> None:
        if failure is FileNotFoundError:
            original(name, dir_fd=dir_fd)
        raise failure("gone or denied")

    monkeypatch.setattr(notifications.os, "unlink", unlink)
    if failure is FileNotFoundError:
        store.dismiss(entry.id)
        assert not store.path(entry.id).exists()
    else:
        with pytest.raises(NotificationError, match="cannot dismiss.*gone or denied"):
            store.dismiss(entry.id)
        assert store.read(entry.id) == entry


def test_host_directory_override_does_not_require_a_project(tmp_path: Path) -> None:
    env = {"DEVCAPSULE_NOTIFICATIONS": str(tmp_path / "notifications"),
           "DEVCAPSULE_CONSOLE_DECISIONS": str(tmp_path / "questions")}
    assert store_for(tmp_path / "not-a-project", env) == NotificationStore(tmp_path / "notifications", tmp_path / "questions")
