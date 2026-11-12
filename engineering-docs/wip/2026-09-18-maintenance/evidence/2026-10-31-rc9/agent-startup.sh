set -eux
useradd -o -u 1000 -m -d /home/rc9 rc9
cp -r /artifacts/agent-smoke/home/. /home/rc9/
chown -R rc9:rc9 /home/rc9
mkdir -p /opt/rc9/codex /opt/rc9/bin
cat > /opt/rc9/codex/package.json <<'JSON'
{"private":true,"dependencies":{"@openai/codex":"file:/artifacts/codex-0.166.0.tar.gz","@openai/codex-linux-x64":"file:/artifacts/codex-linux-0.166.0-linux-x64.tar.gz"}}
JSON
npm install --prefix /opt/rc9/codex --offline --ignore-scripts --no-audit --no-fund --no-update-notifier
cp /artifacts/claude-2.1.314.bin /opt/rc9/bin/claude
chmod 755 /opt/rc9/bin/claude
tar -xzf /artifacts/antigravity-1.4.12.tar.gz -C /opt/rc9/bin antigravity
sha256sum /home/rc9/.codex/config.toml /home/rc9/.claude/settings.json /home/rc9/.gemini/antigravity-cli/settings.json > /tmp/seeds.before
runuser -u rc9 -- /opt/rc9/codex/node_modules/.bin/codex --version
runuser -u rc9 -- /opt/rc9/codex/node_modules/.bin/codex features list
runuser -u rc9 -- /opt/rc9/codex/node_modules/.bin/codex exec --help >/tmp/codex-help
runuser -u rc9 -- /opt/rc9/bin/claude --version
set +e
runuser -u rc9 -- /opt/rc9/bin/claude --help >/tmp/claude-help
help_result=$?
set -e
printf 'Claude help exit: %s\n' "$help_result"
if [ "$help_result" -ne 0 ]; then cat /tmp/claude-help; fi
set +e
runuser -u rc9 -- timeout --kill-after=10 45 /opt/rc9/bin/claude -p 'Reply with READY only.' --output-format json --debug-file /tmp/claude-debug.log > /tmp/claude-result.json
result=$?
set -e
printf 'Claude unauthenticated probe exit: %s\n' "$result"
cat /tmp/claude-result.json
python3 - <<'PY'
from pathlib import Path
for line in Path('/tmp/claude-debug.log').read_text().splitlines():
 if 'bypassPermissions' in line: print(line)
PY
runuser -u rc9 -- /opt/rc9/bin/antigravity --version
runuser -u rc9 -- /opt/rc9/bin/antigravity --help >/tmp/antigravity-help
runuser -u rc9 -- /opt/rc9/bin/antigravity changelog >/tmp/antigravity-changelog
sha256sum /home/rc9/.codex/config.toml /home/rc9/.claude/settings.json /home/rc9/.gemini/antigravity-cli/settings.json > /tmp/seeds.after
diff -u /tmp/seeds.before /tmp/seeds.after
printf 'AGENT_STARTUP_AND_SEEDS_PASSED\n'
