# Review brief for the Codex + gpt-6.2-astra pair: PR75.1 on the `ssh-proxy` authorization

The Claude Code + Fable 5.2 pair opened
[PR #75](https://github.com/mycodespace-ai/devcapsule/pull/75), "Rename the
GitHub SSH authorization to ssh-proxy and let it select the host key", from
`ws-github-auth/ssh-proxy-fix` into `release-0.3.1`. It changes a feature that
PR #47 delivered on 2026-11-16 and that the Antigravity pair reviewed then
(PR #44). No review of PR #75 exists yet. Your job is one improvement pull
request against that branch.

The hosted checks of PR #75 passed on its head `595c3f04`: `ci-gate`,
`Python 3.12` and `Website verification`.

## Your checkout

You are in the git worktree at `/home/devcapsule/worktrees/github-auth-review`,
on the branch `ws-github-auth/ssh-proxy-fix-review`, branched from
`ws-github-auth/ssh-proxy-fix`. Work only there. Do not touch the main
checkout at `/workspace/301e4208ef81-ChatGPT_Codex`.

Read first, in this order:

1. `AGENTS.md`, `WORKFLOW.md`, `WORKFLOW-LOCAL.md`.
2. `engineering-docs/wip/2026-11-16-github-auth/CURRENT-STATUS.md`, the
   section *SSH proxy key selection, 2026-11-25*. It holds the owner's rulings
   and the implementor's choices. The rulings are the contract. The choices are
   yours to question.
3. `devcapsule-src/devcapsule/ssh_identity.py`. Its module docstring states
   the values of `ssh-proxy`.
4. The body of PR #75: `gh pr view 75`.

## GitHub CLI

In every shell you run, first execute:

    . /opt/xtras/miniconda3/etc/profile.d/conda.sh && conda activate gh

Then `gh` is logged in to github.com as the owner's account against
`mycodespace-ai/devcapsule`. Do not edit `.bashrc` or any shell profile. Push
only to `git@github.com:mycodespace-ai/devcapsule.git`.

## Validation environment

Your worktree's `devcapsule-src/.venv` exists, and the `website` submodule is
initialized. Run unit tests and mypy from `devcapsule-src`.

`WORKFLOW-LOCAL.md` gives the review partner a scratch directory under
`/opt/devcapsule-gate`. This capsule has no such directory and `/opt` is not
writable. Use pytest's default directory under `/tmp`. The implementor's gate
ran there with room to spare. If `/tmp` fills, stop and say so.

This PR touches:

- `devcapsule-src/devcapsule/`: `ssh_identity.py` (new), `github_transport.py`,
  `github_proxy.py`, `commands/github_ssh.py`, `commands/project.py`,
  `commands/_launch_review.py`, `launch/pycharm/_launcher.py`.
- `devcapsule-src/devcapsule/configuration/`: `authorization.py`, `review.py`,
  `resolution.py`, `listing.py`, `operations.py`, `console_channel.py`.
- `devcapsule-webconsole/`: `devcapsule_webconsole/configuration.py`,
  `CONFIGURATION-CHANNEL.md`.
- Tests: `tests/unit/devcapsule/test_ssh_identity.py` (new),
  `tests/integration/test_ssh_proxy_cli.py` (new),
  `tests/unit/devcapsule/test_github_proxy.py`,
  `tests/unit/devcapsule/test_github_transport.py`,
  `tests/unit/devcapsule/configuration/test_authorization.py`,
  `test_review.py`, `test_nodes.py`, `test_console_channel.py`,
  `tests/unit/devcapsule/commands/test_launch_review.py`,
  `tests/integration/test_github_proxy.py`.
- User documentation: `docs/everyday-development/git.md`,
  `docs/containment/the-boundary.md`, `docs/reference/configuration-nodes.md`.

The gate type-checks `tests/` too. Run `nox -s build` before your final push
and report its result. Run `nox -s integration` too: the hosted gate does not
run the integration tests, and two files of this PR are integration tests.

Do not build images. Do not launch a capsule. Do not connect to GitHub over
SSH. Do not read, copy or use a key of this machine's `~/.ssh`; a test makes
its own home under `tmp_path`. You may run `ssh -G`, which opens no
connection, with `-F` pointing at a file you write. Nobody runs the recorded
end-to-end scenario in this loop; the owner tests a locally built executable.

## The task

Review the diff of PR 75 against its base:

    gh pr diff 75

Read `ssh_identity.py` first, then `github_transport.py` and `github_proxy.py`,
then `configuration/authorization.py` and `configuration/review.py`, then the
command layer.

The owner's rulings, which you do not change:

- The authorization is `ssh-proxy`. `github-ssh` is its retired name.
- `default` is the one private key named `id_*` in `~/.ssh`. The launcher
  looks for it when the user runs DevCapsule, not when the answer is
  recorded. A launch that fails and says what changed in `~/.ssh` is correct.
- A value without `/` is a file in `~/.ssh`. A value with `/` is a path.
- `true` lets host OpenSSH choose, as 0.3.1-rc3 did. `false` denies.
- The old name and its old values keep working. Each place that meets the old
  name tells the user to change it, because the name will be removed.
- The proxy carries GitHub only in 0.3.1.

Improve the PR on your branch, focused on these things, in this order:

1. Correctness of the new and modified lines. Questions to answer with a test
   or a command:
   - Can `normalize_selection` accept a value that names another file than it
     spells? Think of what OpenSSH does to the argument of `-i`: tokens,
     variables, a leading `~`, a leading `-`, a trailing newline. Think of
     what TOML does to the value in the checkout record and in the resolution.
   - Is the reading of `default` right for every content of `~/.ssh`:
     symbolic links, directories, `id_*` public keys and certificates, an
     unreadable or absent directory, a home that is not the passwd home
     OpenSSH itself uses?
   - `GitHubRequest.ssh_command` claims this: with `-oIdentitiesOnly=yes -i
     KEY`, OpenSSH offers the key first, offers neither the agent's other
     keys nor the default key files, and still offers an `IdentityFile` that
     the host's own configuration gives GitHub. Is each part true? Can a host
     configuration undo `IdentitiesOnly` or add an agent or a certificate?
     Does an option given on the command line before `-i` win over the file?
     The user documentation repeats the claim; a false sentence there is a
     defect.
   - `github_ssh_bridge` refuses a key that is not a file before the capsule
     starts. What happens when the key disappears after the check? Is the
     order of the refusals right? Is it certain that no key is looked for
     inside a capsule?
   - `ssh-proxy` is the first authorization whose grant is not one fixed
     value. Follow a string grant through `normalize_authorization_value`,
     `authorization_deny_value`, `_authorization_choices`,
     `review_authorizations`, the listing rows, `HostAccess.overlay`, the
     resolution written and read back, the interactive questions of a launch,
     `--save`, and `config authorize --all-recommended`. Does any place still
     assume "the grant or the denial"? Does any comparison treat a string as
     a denial or as a bool?
   - The retired name: `_current_records` with both names, with an entry
     that is no table, with another digest. `CheckoutRecord.authorize` and
     `_forget_authorization` remove the old entry: can either remove an
     answer the user did not name? Is there a command that takes an
     authorization name and does not read the old one? What happens with
     `--authorize github-ssh true --authorize ssh-proxy id_work` on one
     command line? Is the notice printed once for one use?
   - The console channel takes `authorize ssh-proxy KEY` from inside a
     capsule and keeps it for the host's confirmation. A capsule can so ask
     for any key path of the host. Is what the host shows before the
     confirmation enough for the user to see which key was asked?
   - PR #75 states that 0.3.1-rc3 refuses a checkout that records `ssh-proxy`,
     and that a later removal of `github-ssh` makes a checkout that records it
     refused. Check both against the code at tag `v0.3.1-rc3` and this tree.
2. Clarity of the new and modified lines. The standard is "obviously no
   deficiencies". The owner reviews Python only, and reads comments.
3. Test coverage of the new and modified lines. Add tests where a branch is
   not exercised. Every test must fail if the line it covers is broken. Do
   not pad.
4. Every new or changed test against *Unit Tests* in `WORKFLOW-LOCAL.md`:
   it lives in the mirror and names its unit; it establishes its own
   precondition, calls one public operation and asserts a promised
   postcondition; its docstring states the contract. For each, name what
   would make it fail for a reason that is not a bug. A finding here is a
   finding; "confined to tests" does not dismiss it. Under rule 7 of that
   section, verify the rules on the changed tests yourself.
5. The changed code and its tests against *Host Inputs* in
   `WORKFLOW-LOCAL.md`, rules 1 to 6: name every read of the host outside
   an entry layer, every parameter default that reads it, every parameter
   that only a test passes, every constructor that does more than store,
   every decision taken inside an entry layer, and every patch in a new or
   changed test. `github_ssh_bridge` read the host before this PR; say
   whether the PR made that better, worse or the same.
6. The three documentation pages against the behaviour you verified.

Stay inside the PR's scope: the name of the authorization, the key its value
selects, and the reading of the retired name. Do not open the proxy to other
hosts. Do not rename the capsule-side `github-ssh` command, the socket
variable, the socket path, or the `github_*` modules: images built with rc3
hold them. Do not change the grammar of another authorization. Do not widen
the contract; if you believe a ruling is wrong, say why in the PR body and
keep your change minimal.

## What you must not do

- Do not edit `CURRENT-STATUS.md` files, `intake-dispositions.md`, the
  `evidence/` directory, or run `devcapsule workflow publish`.
- Do not commit the `website` submodule pointer, `.idea/` files,
  `*.egg-info`, `.nox/`, `dist/` or `__pycache__`.
- Do not merge anything. Do not push to `main`, to `release-0.3.1` or to any
  branch other than your review branch.
- Do not rebase or force-push. Do not build images or run capsules.

## Deliverable

1. Commits on `ws-github-auth/ssh-proxy-fix-review`, each message naming the
   component and the evidence, ending with your co-author line as
   *Commit Authorship* in `WORKFLOW-LOCAL.md` writes it: the model name your
   session reports, then `Codex`, then `<noreply@openai.com>`. Keep the
   human's Git author identity.
2. Push the branch and open one pull request with
   `gh pr create --base ws-github-auth/ssh-proxy-fix --head ws-github-auth/ssh-proxy-fix-review`.
   Title: "Correctness, clarity and coverage review of #75 (PR75.1)".
   The body lists each finding as: what was wrong or unclear, where, what
   you changed, how the test proves it. Separate "changed" from
   "considered and left alone, because". List the proposals you did not
   implement. State the gate result with counts and what was skipped. If
   you find nothing to change, say so in the PR body and open the PR with
   the added tests only, or, if there are none, say that in your final
   report instead of opening an empty PR.
3. Print the PR URL as the last line of your output, or "NO PR" if you
   opened none.

Write the PR body and your report at about 80% ASD-STE100: one fact per
sentence, about twenty words, active voice. Every claim about behavior
must be backed by a test or a command you ran.

If you cannot proceed, because of a blocker like network or credentials,
stop and say exactly what blocked you. Do not work around a blocker.
