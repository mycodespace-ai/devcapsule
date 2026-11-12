from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

from devcapsule import cli, workflow_coordination as workflow_mail
from devcapsule.workflow_coordination import (
    Claim,
    WorkflowMailError,
    brief,
    check,
    claim,
    list_state,
    publish,
    send,
    take,
)

pytestmark = pytest.mark.legacy


def git(root: Path, *args: str, stdin: str | None = None) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, input=stdin, capture_output=True, text=True, check=True
    ).stdout


def clone(origin: Path, where: Path, name: str, branch: str) -> Path:
    """A checkout on ws-<name>/<branch> with an open-work directory for ``name``."""
    git(origin.parent, "clone", "--quiet", str(origin), str(where))
    git(where, "config", "user.name", name)
    git(where, "config", "user.email", f"{name}@example.invalid")
    # The bare origin's HEAD names a branch that never existed, so the clone
    # checks nothing out; start the workstream branch from main explicitly.
    git(where, "checkout", "--quiet", "main")
    git(where, "checkout", "--quiet", "-b", f"ws-{name}/{branch}")
    intake = where / "engineering-docs" / "wip" / f"2026-09-19-{name}" / "intake"
    intake.mkdir(parents=True)
    return where


@pytest.fixture
def repos(tmp_path: Path) -> tuple[Path, Path, Path]:
    origin = tmp_path / "origin.git"
    git(tmp_path, "init", "--quiet", "--bare", str(origin))
    seed = tmp_path / "seed"
    git(tmp_path, "clone", "--quiet", str(origin), str(seed))
    git(seed, "config", "user.name", "seed")
    git(seed, "config", "user.email", "seed@example.invalid")
    (seed / "README.md").write_text("# project\n", encoding="utf-8")
    git(seed, "add", "README.md")
    git(seed, "commit", "--quiet", "-m", "seed")
    git(seed, "push", "--quiet", "origin", "HEAD:main")
    # A branch whose last path component equals the coordination branch's
    # name must not be mistaken for it when the real branch does not exist.
    git(seed, "push", "--quiet", "origin", "HEAD:refs/heads/ws-gamma/coordination")
    sender = clone(origin, tmp_path / "sender", "alpha", "v1")
    recipient = clone(origin, tmp_path / "recipient", "beta", "v1")
    return origin, sender, recipient


def item(root: Path, name: str, text: str = "# Intake: hello\n") -> Path:
    """An item file written beside the checkout, not inside it, so sending
    leaves the sender's working tree clean."""
    outbox = root.parent / f"{root.name}-items"
    outbox.mkdir(exist_ok=True)
    path = outbox / name
    path.write_text(text, encoding="utf-8")
    return path


def test_send_creates_the_branch_and_check_sees_the_item(repos) -> None:
    origin, sender, recipient = repos

    commit = send(sender, "beta", item(sender, "2026-09-19-alpha-hello.md"))

    assert git(origin, "rev-parse", "refs/heads/coordination").strip() == commit
    tree = git(origin, "ls-tree", "-r", "--name-only", "coordination").split()
    assert tree == ["README.md", "mail/beta/2026-09-19-alpha-hello.md"]
    waiting = check(recipient, "beta")
    assert [entry.name for entry in waiting] == ["2026-09-19-alpha-hello.md"]
    assert check(recipient, "alpha") == []
    # The sender's own checkout is untouched: same branch, clean tree.
    assert git(sender, "symbolic-ref", "--short", "HEAD").strip() == "ws-alpha/v1"
    assert git(sender, "status", "--porcelain").strip() == ""


def test_take_copies_into_intake_stages_and_removes_from_branch(repos) -> None:
    origin, sender, recipient = repos
    send(sender, "beta", item(sender, "2026-09-19-alpha-one.md", "one\n"))
    send(sender, "beta", item(sender, "2026-09-19-alpha-two.md", "two\n"))

    written = take(recipient, "beta")

    intake = recipient / "engineering-docs/wip/2026-09-19-beta/intake"
    assert sorted(path.name for path in written) == [
        "2026-09-19-alpha-one.md",
        "2026-09-19-alpha-two.md",
    ]
    assert (intake / "2026-09-19-alpha-one.md").read_text(encoding="utf-8") == "one\n"
    staged = git(recipient, "diff", "--cached", "--name-only").split()
    assert len(staged) == 2 and all("intake/" in path for path in staged)
    assert git(origin, "ls-tree", "-r", "--name-only", "coordination").split() == ["README.md"]
    assert check(recipient, "beta") == []
    assert take(recipient, "beta") == []
    # History is append-only: the take is a commit on top of the sends, not a reset.
    assert len(git(origin, "rev-list", "coordination").split()) == 3


def test_send_is_idempotent_for_identical_content_and_refuses_rewrites(repos) -> None:
    _origin, sender, _recipient = repos
    path = item(sender, "2026-09-19-alpha-same.md", "same\n")
    first = send(sender, "beta", path)

    assert send(sender, "beta", path) == first
    path.write_text("changed\n", encoding="utf-8")
    with pytest.raises(WorkflowMailError, match="never rewrite"):
        send(sender, "beta", path)


def test_send_retries_after_losing_a_push_race(repos, monkeypatch) -> None:
    _origin, sender, recipient = repos
    send(recipient, "alpha", item(recipient, "2026-09-19-beta-first.md"))
    real_push = workflow_mail._push
    raced = {"done": False}

    def racing_push(git_, remote, branch, commit, expected):
        # Somebody else lands a commit between our fetch and our push, once.
        if not raced["done"]:
            raced["done"] = True
            send(recipient, "alpha", item(recipient, "2026-09-19-beta-second.md"))
        return real_push(git_, remote, branch, commit, expected)

    monkeypatch.setattr(workflow_mail, "_push", racing_push)

    send(sender, "beta", item(sender, "2026-09-19-alpha-late.md"))

    names = [entry.name for entry in check(sender, "alpha")]
    assert names == ["2026-09-19-beta-first.md", "2026-09-19-beta-second.md"]
    assert [entry.name for entry in check(sender, "beta")] == ["2026-09-19-alpha-late.md"]


def test_names_are_validated(repos) -> None:
    _origin, sender, _recipient = repos
    with pytest.raises(WorkflowMailError, match="not a valid recipient"):
        send(sender, "Beta/../x", item(sender, "2026-09-19-alpha-x.md"))
    with pytest.raises(WorkflowMailError, match="item name"):
        send(sender, "beta", item(sender, "notes.md"))
    with pytest.raises(WorkflowMailError, match="not a valid workstream name"):
        check(sender, "../beta")


def test_cli_infers_the_workstream_from_the_branch(repos, capsys) -> None:
    _origin, sender, recipient = repos
    sent = item(sender, "2026-09-19-alpha-cli.md")

    assert cli.main(["workflow", "mail", "send", "--project", str(sender), "beta", str(sent)]) == 0
    assert "delivered 2026-09-19-alpha-cli.md to beta" in capsys.readouterr().out
    assert cli.main(["workflow", "mail", "check", "--project", str(recipient)]) == 0
    assert "1 item(s) for beta" in capsys.readouterr().out
    assert cli.main(["workflow", "mail", "take", "--project", str(recipient)]) == 0
    assert "took 1 item(s)" in capsys.readouterr().out
    assert cli.main(["workflow", "mail", "check", "--project", str(recipient)]) == 0
    assert "no mail for beta" in capsys.readouterr().out


def status_file(root: Path, name: str, state: str, next_step: str) -> Path:
    path = root / "engineering-docs" / "wip" / f"2026-09-19-{name}" / "CURRENT-STATUS.md"
    path.write_text(
        f"# Workstream Current Status: {name}\n\nName: `{name}`\n\nState: {state}\n\n"
        f"Branch association: `ws-{name}/v1`\n\n## Planned Next Step\n\n{next_step}\n",
        encoding="utf-8",
    )
    return path


def test_publish_pushes_live_state_and_list_reads_it(repos) -> None:
    origin, sender, recipient = repos
    status_file(sender, "alpha", "active", "Ship the thing.")
    (sender / "engineering-docs/wip/2026-09-19-alpha/intake-dispositions.md").write_text(
        "| Item |\n", encoding="utf-8"
    )
    status_file(recipient, "beta", "paused 2026-09-19; waiting", "Resume after alpha ships.")

    first = publish(sender, "alpha")
    assert first is not None
    assert publish(sender, "alpha") is None  # nothing changed: no commit
    publish(recipient, "beta")

    tree = git(origin, "ls-tree", "-r", "--name-only", "coordination").split()
    assert "state/alpha/CURRENT-STATUS.md" in tree
    assert "state/alpha/intake-dispositions.md" in tree
    assert "state/beta/CURRENT-STATUS.md" in tree
    rows = list_state(recipient)
    assert [(row.name, row.state, row.branch) for row in rows] == [
        ("alpha", "active", "`ws-alpha/v1`"),
        ("beta", "paused 2026-09-19; waiting", "`ws-beta/v1`"),
    ]
    assert rows[0].next_step == "Ship the thing."
    # Publishing reads the working tree: an uncommitted edit is what goes live.
    status_file(sender, "alpha", "blocked; needs beta", "Wait.")
    publish(sender, "alpha")
    assert list_state(sender)[0].state == "blocked; needs beta"
    # The sender's checkout is untouched beyond its own files.
    assert git(sender, "symbolic-ref", "--short", "HEAD").strip() == "ws-alpha/v1"


def test_retire_removes_published_state_and_mail_survives(repos) -> None:
    origin, sender, recipient = repos
    status_file(sender, "alpha", "active", "x")
    publish(sender, "alpha")
    send(recipient, "alpha", item(recipient, "2026-09-19-beta-note.md"))

    assert publish(sender, "alpha", retire=True) is not None
    assert publish(sender, "alpha", retire=True) is None

    tree = git(origin, "ls-tree", "-r", "--name-only", "coordination").split()
    assert tree == ["README.md", "mail/alpha/2026-09-19-beta-note.md"]
    assert list_state(sender) == []


def test_publish_requires_a_status_file(repos) -> None:
    _origin, sender, _recipient = repos
    with pytest.raises(WorkflowMailError, match="nothing to publish"):
        publish(sender, "alpha")


def test_cli_publish_and_status(repos, capsys) -> None:
    _origin, sender, recipient = repos
    status_file(sender, "alpha", "active", "Do it.")

    assert cli.main(["workflow", "publish", "--project", str(sender)]) == 0
    assert "alpha: published to coordination" in capsys.readouterr().out
    assert cli.main(["workflow", "status", "--project", str(recipient)]) == 0
    out = capsys.readouterr().out
    assert "alpha  active" in out and "next: Do it." in out
    assert cli.main(["workflow", "publish", "--project", str(sender), "--retire"]) == 0
    assert "retired" in capsys.readouterr().out


def test_list_reads_headed_branch_association_and_joins_wrapped_paragraphs(repos) -> None:
    _origin, sender, _recipient = repos
    path = sender / "engineering-docs/wip/2026-09-19-alpha/CURRENT-STATUS.md"
    path.write_text(
        "# Status\n\nState: active\n\n## Branch Association\n\n`ws-alpha/v2`, forked\n"
        "from `main`.\n\n## Next Resumable Task\n\nFinish the first\nslice.\n\nThen rest.\n",
        encoding="utf-8",
    )
    publish(sender, "alpha")

    row = list_state(sender)[0]
    assert row.branch == "`ws-alpha/v2`, forked from `main`."
    assert row.next_step == "Finish the first slice."


def test_publish_stamps_the_definition_and_list_reports_the_facts(repos) -> None:
    origin, sender, recipient = repos
    (sender / "WORKFLOW.md").write_text("# definition v1\n", encoding="utf-8")
    git(sender, "add", "WORKFLOW.md")
    git(sender, "commit", "--quiet", "-m", "definition")
    git(sender, "push", "--quiet", "origin", "HEAD:refs/heads/main")
    git(sender, "push", "--quiet", "origin", "ws-alpha/v1")
    git(recipient, "pull", "--quiet", "--ff-only", "origin", "main")
    status_file(sender, "alpha", "active", "x")

    publish(sender, "alpha")

    stamped = (sender / "engineering-docs/wip/2026-09-19-alpha/CURRENT-STATUS.md").read_text(
        encoding="utf-8"
    )
    assert "\nDefinition read: WORKFLOW.md@" in stamped
    row = list_state(sender)[0]
    assert row.behind_main == 0 and row.definition_changed is False

    # main moves: the definition changes and two unrelated commits land.
    (recipient / "WORKFLOW.md").write_text("# definition v2\n", encoding="utf-8")
    git(recipient, "commit", "--quiet", "-am", "definition v2")
    (recipient / "other.txt").write_text("x\n", encoding="utf-8")
    git(recipient, "add", "other.txt")
    git(recipient, "commit", "--quiet", "-m", "unrelated")
    git(recipient, "push", "--quiet", "origin", "HEAD:refs/heads/main")

    row = list_state(sender)[0]
    assert row.behind_main == 2 and row.definition_changed is True
    # Rebasing and republishing clears both facts. The stamp is a working-tree
    # edit, so commit it first as a pair would at a checkpoint.
    git(sender, "add", "-A")
    git(sender, "commit", "--quiet", "-m", "checkpoint")
    git(sender, "fetch", "--quiet", "origin")
    git(sender, "rebase", "--quiet", "origin/main")
    git(sender, "push", "--quiet", "--force", "origin", "ws-alpha/v1")
    publish(sender, "alpha")
    row = list_state(sender)[0]
    assert row.behind_main == 0 and row.definition_changed is False
    # The author of a definition change is not told the definition changed:
    # its branch edits the file, main has not moved it since they diverged.
    (sender / "WORKFLOW.md").write_text("# definition v3, by alpha\n", encoding="utf-8")
    git(sender, "commit", "--quiet", "-am", "alpha edits the definition")
    git(sender, "push", "--quiet", "--force", "origin", "ws-alpha/v1")
    publish(sender, "alpha")
    assert list_state(sender)[0].definition_changed is False


def test_send_all_fans_out_to_every_published_workstream(repos) -> None:
    origin, sender, recipient = repos
    status_file(sender, "alpha", "active", "x")
    status_file(recipient, "beta", "active", "y")
    publish(sender, "alpha")
    publish(recipient, "beta")

    send(sender, "all", item(sender, "2026-09-21-alpha-notice.md", "hello all\n"))

    tree = git(origin, "ls-tree", "-r", "--name-only", "coordination").split()
    assert "mail/alpha/2026-09-21-alpha-notice.md" in tree
    assert "mail/beta/2026-09-21-alpha-notice.md" in tree
    assert len([entry for entry in check(recipient, "beta")]) == 1
    # A comma-separated list works the same way, and a repeat is a no-op.
    tip = send(sender, "beta,alpha", item(sender, "2026-09-21-alpha-notice.md", "hello all\n"))
    assert tip == git(origin, "rev-parse", "coordination").strip()


@pytest.mark.xfail(
    reason="Clock-dependent claim assertion; see 2026-09-22-workflow-claim-test-flakiness.md",
    strict=False,
    raises=AssertionError,
)
def test_claim_is_shown_live_expires_and_releases(repos) -> None:
    from datetime import datetime, timedelta, timezone

    _origin, sender, recipient = repos
    status_file(sender, "alpha", "active", "x")
    publish(sender, "alpha")

    assert claim(sender, "alpha", "the config fix") is not None
    assert claim(sender, "alpha", "the config fix") is None  # unchanged: no commit
    row = list_state(recipient)[0]
    assert row.claim is not None
    assert row.claim.who == "alpha" and row.claim.branch == "ws-alpha/v1"
    assert row.claim.slice == "the config fix" and not row.claim.expired()
    assert row.published is not None
    assert "claimed by alpha on ws-alpha/v1: the config fix (since" in workflow_mail.render_list([row])

    old = datetime.now(timezone.utc) - timedelta(hours=30)
    claim(sender, "alpha", "stale work", now=old)
    row = list_state(recipient)[0]
    assert row.claim is not None and row.claim.expired()
    assert "(EXPIRED)" in workflow_mail.render_list([row])

    assert claim(sender, "alpha", None, release=True) is not None
    assert claim(sender, "alpha", None, release=True) is None
    assert list_state(recipient)[0].claim is None
    with pytest.raises(WorkflowMailError, match="needs a slice"):
        claim(sender, "alpha", None)


def test_brief_prints_the_session_context(repos, capsys) -> None:
    _origin, sender, recipient = repos
    (sender / "WORKFLOW.md").write_text(
        "# W\n\n### Changes\n\n- **First rule.** x\n\n## Rest\n", encoding="utf-8"
    )
    git(sender, "add", "WORKFLOW.md")
    git(sender, "commit", "--quiet", "-m", "definition")
    git(sender, "push", "--quiet", "origin", "HEAD:refs/heads/main")
    git(sender, "push", "--quiet", "origin", "ws-alpha/v1")
    git(recipient, "pull", "--quiet", "--ff-only", "origin", "main")
    status_file(sender, "alpha", "active", "Ship it.")
    status_file(recipient, "beta", "active", "Review it.")
    publish(sender, "alpha")
    publish(recipient, "beta")
    claim(recipient, "beta", "reviewing alpha")
    send(recipient, "alpha", item(recipient, "2026-09-21-beta-hello.md"))

    text = brief(sender, "alpha")

    assert text.startswith("# alpha\nstate: active\nbranch: `ws-alpha/v1`\nnext: Ship it.\n")
    assert "- beta: beta on ws-beta/v1, reviewing alpha" in text
    assert "## Mail: 1 waiting" in text and "- 2026-09-21-beta-hello.md" in text
    assert "## Definition: nothing new since last read" in text
    assert "- suggested: nothing to synchronize" in text
    # No local workflow file yet: the brief says so instead of staying silent.
    assert "## Validation commands: no WORKFLOW-LOCAL.md" in text

    # The template's untouched placeholder is named as such, not printed as
    # if it were a command.
    (sender / "WORKFLOW-LOCAL.md").write_text(
        "# Local\n\n## Validation Commands\n\nRequired; write the commands here.\n"
        "A step that is not written here does not exist for the next agent.\n",
        encoding="utf-8",
    )
    text = brief(sender, "alpha")
    assert "## Validation commands: still the template's placeholder in WORKFLOW-LOCAL.md" in text

    # The local file's Validation Commands section is printed verbatim, and
    # only that section, so the session knows how to build and test first.
    (sender / "WORKFLOW-LOCAL.md").write_text(
        "# Local\n\n## Version Scheme\n\nPEP 440.\n\n## Validation Commands\n\n"
        "```text\ncd src\n.venv/bin/python -m nox -s build\n```\n\n## Exceptions\n\nNone.\n",
        encoding="utf-8",
    )
    text = brief(sender, "alpha")
    assert "## Validation commands, from WORKFLOW-LOCAL.md\n```text\ncd src\n.venv/bin/python -m nox -s build\n```\n" in text
    assert "PEP 440" not in text and "## Exceptions" not in text

    # main gains a rule the workstream has not read: the brief names it.
    (recipient / "WORKFLOW.md").write_text(
        "# W\n\n### Changes\n\n- **Second rule.** y\n- **First rule.** x\n\n## Rest\n",
        encoding="utf-8",
    )
    git(recipient, "commit", "--quiet", "-am", "second rule")
    git(recipient, "push", "--quiet", "origin", "HEAD:refs/heads/main")
    text = brief(sender, "alpha")
    assert "## Definition changes not yet read\n- Second rule.\n" in text
    assert "must synchronize" in text

    assert cli.main(["workflow", "brief", "--project", str(sender)]) == 0
    assert "# alpha" in capsys.readouterr().out
    assert cli.main(["workflow", "claim", "--project", str(sender), "writing the brief"]) == 0
    assert "claim recorded for 12 h" in capsys.readouterr().out
    assert cli.main(["workflow", "claim", "--project", str(sender), "--release"]) == 0
    assert "claim released" in capsys.readouterr().out


def test_stamp_lands_after_a_wrapped_state_paragraph(repos) -> None:
    _origin, sender, _recipient = repos
    # A stamp needs a definition to name; without WORKFLOW.md in the checkout
    # there is nothing to stamp and the file is left alone.
    (sender / "WORKFLOW.md").write_text("# definition\n", encoding="utf-8")
    git(sender, "add", "WORKFLOW.md")
    git(sender, "commit", "--quiet", "-m", "definition")
    path = sender / "engineering-docs/wip/2026-09-19-alpha/CURRENT-STATUS.md"
    path.write_text(
        "# Status\n\nState: active; a long state that\nwraps onto a second line.\n\n"
        "Branch association: `ws-alpha/v1`\n",
        encoding="utf-8",
    )
    publish(sender, "alpha")

    text = path.read_text(encoding="utf-8")
    assert "wraps onto a second line.\n\nDefinition read: " in text
    assert "State: active; a long state that\nwraps" in text


def test_publish_keeps_a_live_claim(repos) -> None:
    _origin, sender, _recipient = repos
    status_file(sender, "alpha", "active", "x")
    publish(sender, "alpha")
    claim(sender, "alpha", "still here")
    status_file(sender, "alpha", "active", "y")  # something changed, so publish commits

    publish(sender, "alpha")

    row = list_state(sender)[0]
    assert row.claim is not None and row.claim.slice == "still here"


def coordination_blobs(origin: Path) -> dict[str, str]:
    """Every path on the coordination branch with its blob ID: the unit of
    "unrelated files are untouched" is the blob, not the name."""
    entries = {}
    for line in git(origin, "ls-tree", "-r", "coordination").splitlines():
        meta, path = line.split("\t", 1)
        entries[path] = meta.split()[2]
    return entries


def assert_untouched(before: dict[str, str], after: dict[str, str], allowed) -> None:
    """Every pre-existing path the command had no business with keeps its blob."""
    for path, blob in before.items():
        if not allowed(path):
            assert after.get(path) == blob, f"{path} changed or vanished"


def test_commands_from_a_nested_directory_preserve_everyone_else(repos) -> None:
    """Regression for the 2026-09-22 coordination data loss: a send run from a
    subdirectory rebuilt the tree from a cwd-limited listing and dropped every
    other mailbox, state, and claim. Each nested command may touch only the
    paths it owns; everything else must be byte-identical afterwards, which
    the release-table review of 2026-09-22 asked for beyond the name check."""
    origin, sender, recipient = repos
    status_file(sender, "alpha", "active", "x")
    status_file(recipient, "beta", "active", "y")
    publish(sender, "alpha")
    publish(recipient, "beta")
    claim(recipient, "beta", "reviewing")
    send(recipient, "alpha", item(recipient, "2026-09-22-beta-first.md"))
    before = coordination_blobs(origin)
    assert len(before) == 5

    nested = sender / "devcapsule-src" / "deeper"
    nested.mkdir(parents=True)
    send(nested, "beta", item(sender, "2026-09-22-alpha-nested.md"))
    after_send = coordination_blobs(origin)
    assert_untouched(before, after_send, lambda path: path.startswith("mail/beta/"))
    assert "mail/beta/2026-09-22-alpha-nested.md" in after_send

    status_file(sender, "alpha", "active", "changed from nested")
    publish(nested, "alpha")
    after_publish = coordination_blobs(origin)
    assert_untouched(after_send, after_publish, lambda path: path.startswith("state/alpha/"))

    claim(nested, "alpha", "from nested")
    after_claim = coordination_blobs(origin)
    assert_untouched(after_publish, after_claim, lambda path: path == "state/alpha/claim")

    assert set(before) <= set(after_claim)
    assert list_state(nested)[0].state == "active"
    assert check(nested, "alpha")[0].name == "2026-09-22-beta-first.md"
    # Taking from a nested directory still writes into the repository's intake
    # and removes only the taken item from the branch.
    taken = take(nested, "alpha")
    assert taken == [sender / "engineering-docs/wip/2026-09-19-alpha/intake/2026-09-22-beta-first.md"]
    after_take = coordination_blobs(origin)
    assert_untouched(after_claim, after_take, lambda path: path.startswith("mail/alpha/"))
    assert "mail/alpha/2026-09-22-beta-first.md" not in after_take


def test_next_step_is_read_from_a_combined_heading(repos) -> None:
    _origin, sender, _recipient = repos
    path = sender / "engineering-docs/wip/2026-09-19-alpha/CURRENT-STATUS.md"
    path.write_text(
        "# S\n\nState: active\n\nBranch association: `ws-alpha/v1`\n\n"
        "## Last Task And Planned Next Step\n\nDo the thing.\n",
        encoding="utf-8",
    )
    publish(sender, "alpha")
    assert list_state(sender)[0].next_step == "Do the thing."
