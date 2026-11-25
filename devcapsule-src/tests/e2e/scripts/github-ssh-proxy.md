# E2E Scenario Script: GitHub SSH through the host proxy

This script presents the recorded interactive run `20261116T103152Z-af7fa02c`.
It is not a replay definition. The recording procedure and presentation producer
are indexed in the GitHub authentication workstream's status file.

## Goal

Use the host's existing GitHub SSH identity inside a fresh capsule without copying its private key or forwarding an SSH agent. See both successful Git access and the refusal when the proxy socket is unavailable.

## Stack And Capabilities

- **Editor:** VSCodium in a fresh DevCapsule on rootless Linux Docker.
- **Authentication:** The outside launcher owns the GitHub SSH proxy; host OpenSSH uses the host's identity.
- **Permission:** The launcher has explicit `ssh-proxy` authorization (named `github-ssh` when this scenario was recorded, with 0.3.1-rc3). Host trust and noninteractive GitHub authentication are already configured.
- **Recording:** The merged development PEX runs in both parent and child. The browser-automation component records the actual terminal.

## What It Illustrates

- Git over SSH can use the host identity while the private key stays on the host.
- The fresh child has zero SSH files and no SSH agent.
- A public repository's SSH URL still requires GitHub authentication.
- Removing the proxy socket from one command makes access fail; ordinary access still works afterward.
- Independent checks verify the checkout, runtime checksum, socket mount and cleanup.

## Steps

1. **Open a terminal in the fresh capsule.**
   - *User action:* Open VSCodium's terminal, trust the test-owned workspace and enlarge the terminal for readability.
   - *Expected observation:* A terminal opens in the new workspace. This is a disposable child capsule, with GitHub access granted by the outside launcher.

2. **Check the authentication boundary.**
   - *User action:* Count files in `~/.ssh`, inspect `SSH_AUTH_SOCK`, and check that `DEVCAPSULE_GITHUB_SOCKET` names a socket.
   - *Expected observation:* The capsule reports zero SSH files, no agent and a connected host GitHub proxy.

3. **Clone from GitHub over SSH.**
   - *User action:* Clone `git@github.com:mycodespace-ai/devcapsule.git`, then inspect the origin, latest commit and working tree.
   - *Expected observation:* The clone completes, the origin uses SSH, the recorded commit is `1942f39`, and the working tree is clean.

4. **Try the same access without the proxy.**
   - *User action:* Run a GitHub read with `DEVCAPSULE_GITHUB_SOCKET` pointing to an absent socket, for that command only.
   - *Expected observation:* Git reports that it cannot read the remote repository. The independently checked exit code is 128.

5. **Use the normal proxy again.**
   - *User action:* Display the previous exit code, then run `git ls-remote` without the socket override.
   - *Expected observation:* The failure code is 128. The normal read returns the GitHub HEAD and exits successfully; no credentials or configuration were repaired.

6. **Review the observed result.**
   - *User action:* Summarize the actual exit codes, SSH file count, origin and cloned commit in the terminal.
   - *Expected observation:* Clone and authenticated read passed without copied keys or an agent, while access without the proxy was refused. Independent checks also passed, and the test-owned capsule and workspace were removed after recording.
