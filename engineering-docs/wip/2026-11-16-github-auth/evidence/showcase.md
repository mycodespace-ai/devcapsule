# GitHub SSH proxy: recorded fresh-capsule clone

## Purpose and acceptance

Show a user cloning a GitHub repository over SSH inside a fresh capsule. The
outside launcher uses the host identity. No SSH key or agent is supplied to the
child. Public GitHub repositories also require authentication on their SSH URL.
This scenario reads the canonical DevCapsule repository; it does not push.

Pass requires a real clone, the expected independently read commit, the unchanged
SSH origin, a clean working tree, no child SSH files or agent, and the canonical
broker socket mounted from the same host source as the parent. A second Git read
with an absent broker socket must fail. Keep the recording and independent
observations, and remove the fresh container, workspace and checkout state.
A video alone does not pass the test.

## Preconditions

Keep the outside launcher alive with `github-ssh` enabled. The host must already
trust GitHub and authenticate noninteractively. An unencrypted default SSH key
needs no host agent. The parent needs host Docker and host networking.

From `devcapsule-src`, use the development virtualenv and the exact PEX under test.
The historical recorded run uses SHA-256
`33c3c7bc7fe6ff6772eedee06424c95afcf4aebddca20ab99f9a31a7c103d35b`, built from
`d6fd93e0`. The merged artifact now has different bytes; set the expected hash
to the actual build being recorded for a new run. Do not rebuild between the launch and the evidence capture.

```sh
.venv/bin/python -m pip install 'playwright==1.63.0'
export DEVCAPSULE_EXPECTED_SHA256=33c3c7bc7fe6ff6772eedee06424c95afcf4aebddca20ab99f9a31a7c103d35b
```

## Start the recording controller

Save the following as a temporary Python script and run it with
`PYTHONPATH=. .venv/bin/python <script>`. It uses the normal PEX project-init and
project-run commands, a unique fresh project, the child browser component,
and the existing recorder. The script prints its evidence directory. The
interactive phase has a 30-minute deadline; initialization and launch also have
bounded deadlines. The context manager cleans up on stop or failure.

```python
import hashlib, json, os, platform
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from tests.e2e.ide_session import SURFACES, command
from tests.e2e.scenario_recorder import ScenarioSpec, serve_interactive_controller

pex = Path('dist/devcapsule-local.pex').resolve()
digest = hashlib.sha256(pex.read_bytes()).hexdigest()
assert digest == os.environ['DEVCAPSULE_EXPECTED_SHA256']
evidence = Path('tests/e2e/evidence/github-ssh-proxy') / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + digest[:8])
evidence.mkdir(parents=True)
run = {'pex':str(pex), 'sha256':digest, 'version':json.loads(command(str(pex), 'version', '--json').stdout),
       'host':platform.platform(), 'docker':json.loads(command('docker', 'info', '--format', '{{json .}}').stdout),
       'expected_head':command('git', 'ls-remote', 'git@github.com:mycodespace-ai/devcapsule.git', 'HEAD').stdout.split()[0]}
# Keep a minimal daemon record; omit unrelated local configuration.
run['docker'] = {k:run['docker'].get(k) for k in ('ServerVersion','OperatingSystem','Architecture','SecurityOptions','Name')}
(evidence / 'run.json').write_text(json.dumps(run, indent=2)+'\n')
surface = replace(next(s for s in SURFACES if s.name == 'codium'),
                  needs=('frontend-ide','node','browser-automation'), consents=(('github-ssh','true'),))
spec = ScenarioSpec('github-ssh-proxy', 'codium', 'GitHub access, host key stays outside',
                    'Clone over Git SSH from a fresh capsule using the outside launcher proxy.', {}, ())
print('EVIDENCE '+str(evidence),flush=True)
try:
 serve_interactive_controller(pex, spec, evidence, surface=surface, timeout=1800)
except BaseException as exc:
 (evidence/'failure.txt').write_text(repr(exc)+'\n')
 raise
```

## Act out the scenario

Use `tests.e2e.scenario_recorder ctl --evidence <printed-directory>` for each
interaction. Inspect screenshots to locate controls rather than assuming that an
unseen welcome screen has gone away. The controller records actual keyboard and
mouse actions; it saves the complete trace in `action-log.json`.

1. Open VSCodium's integrated terminal. Maximize the panel and increase the font
   so the commands and their output can be read in the recording.
2. Display the scenario title and check that `$HOME/.ssh` has no files, no
   `SSH_AUTH_SOCK` is set, and `$DEVCAPSULE_GITHUB_SOCKET` names a socket.
3. Run `git clone --depth 1 git@github.com:mycodespace-ai/devcapsule.git demo-repo`.
   Wait for the real checkout to appear, with a bounded deadline.
4. Show `git -C demo-repo remote get-url origin` and
   `git -C demo-repo log -1 --format='%h %s'`.
5. Run a read with `DEVCAPSULE_GITHUB_SOCKET=/tmp/absent-github-proxy.sock` and
   show its failure. Restore nothing: the override applies only to that command.
6. Independently inspect the child through Docker: verify the key/agent absence,
   canonical socket mount, runtime PEX checksum, origin, commit, and clean tree.
   Save the structured observations in `verification.json`. Compare the commit
   with the external `expected_head` saved before the launch. A repository update
   during the test is a failed precondition to investigate, not an automatic retry.
7. Capture a final screenshot, then send `{"cmd":"stop"}`. Require a successful
   WebM encoding, a nonempty movie, and `cleanup.json` reporting container removal.
   Verify the workspace and listed checkout records are also absent. Save this
   final assessment in `result.json`.

Example controller command, from `devcapsule-src`:

```sh
PYTHONPATH=. .venv/bin/python -m tests.e2e.scenario_recorder ctl \
  --evidence <printed-directory> \
  '{"cmd":"act","actions":[{"action":"press","text":"Control+Shift+p"}]}'
```

## Evidence

Keep `run.json`, `verification.json`, `result.json`, `action-log.json`, the WebM,
final screenshot and cleanup record together under `tests/e2e/evidence/github-ssh-proxy/`.
The launcher log can contain ephemeral console/desktop URLs; redact those before
sharing. Do not commit tokens, credentials, or raw logs to Git. Record failed
attempts and their causes; never overwrite them with a later successful attempt.

## Observed run

Run: `20261116T092248Z-33c3c7bc`, using the PEX identified above and rootless Docker.
The fresh child cloned canonical HEAD `1942f396dd11ffabb64784eb7279f283181e32dd`
over SSH, with no SSH files or agent. Its read-only proxy bind uses the same host
source as the parent. The independent missing-socket read failed with exit 128.
The externally observed origin, clean working tree, README and runtime checksum
passed. The base digest was
`sha256:d7047ced8556cd35964fcc058a1101cf2b5b202f7a5daa2fdd434dcda5ed82c9`.

One on-screen command initially tested that `.ssh` did not exist. The capsule
creates that directory empty, so this was the wrong predicate. The next command
counted its files and returned zero; the independent inspection also returned an
empty file list before and after cloning. The correction is retained in the action
trace and full recording. No second clone or container launch was used to hide it.

The result is **passed**. The recorder encoded 458 frames at 12 fps into a
38.17-second, 2,294,439-byte WebM. Its SHA-256 is
`d6ec02d7531fb0d961b5773059165a132fa6573d383efc07cb7e4e65af11f3eb`.
The full desktop recording and screenshots are retained beside it. Independent
cleanup checks found the container, workspace and checkout records absent.

Evidence directory, relative to this checkout:
`devcapsule-src/tests/e2e/evidence/github-ssh-proxy-pre-merge/` (copied from the
original dist evidence directory before the release merge rebuild).
`result.json` summarizes the checks and hashes the deliverables.
The final on-screen remote read overlaps the next typed command; the actual Git
outputs and independent verification remain valid. This is a recorded engineering
showcase, with the complete raw capture retained, rather than a polished tutorial.

For future runs, send each network command separately and wait for its observable
completion before typing the next. A successful controller action means that the
keystrokes were delivered; it does not mean the shell command has finished.
