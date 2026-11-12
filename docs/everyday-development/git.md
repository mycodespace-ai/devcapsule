---
description: Committing, pushing and pulling from inside the capsule, and how credentials reach Git without your host keys entering the capsule.
weight: 2
updated: 2026-10-30
---
# Git

`git` and `openssh-client` are preinstalled in every capsule, and your project
working tree (including `.git`) is mounted read-write at `/workspace/<slug>`.
Commits, branches, stashes, and rebases you or a coding agent create inside the
capsule are immediately present in the same repository on your computer.

## What is deliberately not imported

By default, `devcapsule project run` does not mount:

- your host `~/.gitconfig` or `~/.config/git`,
- your host `~/.ssh` private keys or `SSH_AUTH_SOCK` agent socket, or
- your host `~/.netrc`, keyring, or Git credential helper state.

The launcher can pass your host's global author name and email as
`GIT_USER_NAME` and `GIT_USER_EMAIL`. These are not credentials, and they do
not replace Git's `user.name` and `user.email` settings inside the capsule.

## Setting your Git author identity

Your checkout's `/home/devcapsule` directory persists across container
replacements. Set `user.name` and `user.email` once inside the capsule terminal
so commits created in the IDE or by agents carry your identity:

```bash
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

That writes `/home/devcapsule/.gitconfig` in this checkout's persistent `home`
slot without touching your host configuration or any other project. You can
also set repository-local `git config user.name` / `user.email` when a project
uses a separate work email.

## Pushing, pulling, and fetching from remotes

Choose the remote authentication workflow that fits how much access you want
inside the capsule:

### 1. Push and pull from a host terminal

Because `/workspace/<slug>` is a live bind mount of your host checkout, the
capsule never needs remote credentials at all for ordinary feature work:

1. Create branches, edit, run tests, and commit inside the capsule.
2. Inspect `git status` and `git log -p` from a terminal on your host.
3. Run `git fetch`, `git pull`, and `git push` on your host using your existing
   SSH keys, hardware security key, or OS credential manager.

This avoids giving the capsule remote credentials. Review commits before
pushing: processes inside the capsule can change the working tree and local
Git history.

### 2. Forward your host SSH agent for a session

When you want `git push` and `git pull` over SSH inside the capsule without
copying private key files into the container, run this from your host terminal.
First check that `SSH_AUTH_SOCK` names a live agent socket:

```bash
devcapsule project run -- \
  --mount "type=bind,src=$SSH_AUTH_SOCK,dst=/run/host-ssh-agent.sock" \
  --env SSH_AUTH_SOCK=/run/host-ssh-agent.sock
```

Keep two details in mind:

- **Pass `$SSH_AUTH_SOCK` on `project run --` rather than saving it with
  `docker-args set`:** host SSH agent socket paths often change across logins or
  reboots, and a stale path prevents the next container from starting.
- **Understand what agent forwarding allows:** private keys never leave your
  host agent, and `/home/devcapsule/.ssh` (`0700`) persists `known_hosts` across
  launches, but any process inside that running capsule can ask the forwarded
  agent to sign challenges while the session is open. Load only the key you
  need or require per-use confirmation (`ssh-add -c`) on your host.

### 3. Use a repository-scoped credential per checkout

If a workflow inside the capsule must push or call forge APIs unattended, create
a **fine-grained HTTPS personal access token** or **single-repository SSH deploy
key** scoped strictly to that repository and store it inside the checkout's
persistent `/home/devcapsule` (for example under `/home/devcapsule/.ssh/`,
which DevCapsule creates with mode `0700`). Avoid placing broad personal tokens
that grant access to unrelated repositories inside a capsule.

## Crediting an agent in a commit

Keep your own Git author identity. If your project credits agent contributions,
put a co-author trailer after a blank line at the end of the commit message:

```text
Explain the change

Co-authored-by: Agent Name <agent@example.invalid>
```

Replace the example name and address with the attribution your project uses.
