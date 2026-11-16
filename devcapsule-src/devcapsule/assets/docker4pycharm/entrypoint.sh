#!/usr/bin/env bash
set -euo pipefail

: "${PROJECT_PATH:=/workspace/project}"
: "${IDE_GLOBAL_SETTINGS_PATH:=/ide-global-settings}"
: "${IDE_CONFIG_PATH:=$IDE_GLOBAL_SETTINGS_PATH/config}"
: "${IDE_PROJECT_STATE_PATH:=/ide-project-state}"
: "${HOME:=$IDE_GLOBAL_SETTINGS_PATH/home}"
: "${ENABLE_DIND:=0}"
: "${ENABLE_SUDO:=0}"
: "${IDE_UID:=}"
: "${IDE_GID:=}"
: "${IDE_USER:=ideuser}"

export XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-$IDE_PROJECT_STATE_PATH/home/.cache}"
export XDG_DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"

RUN_AS_IDE_USER=()
if [ "$(id -u)" -eq 0 ] && [ -n "$IDE_UID" ] && [ -n "$IDE_GID" ] && { [ "$IDE_UID" != "0" ] || [ "$IDE_GID" != "0" ]; }; then
  if [ "$ENABLE_SUDO" = "1" ] && getent passwd "$IDE_USER" >/dev/null 2>&1; then
    RUN_AS_IDE_USER=(gosu "$IDE_USER")
  else
    RUN_AS_IDE_USER=(gosu "$IDE_UID:$IDE_GID")
  fi
fi

as_ide_user() {
  if [ "${#RUN_AS_IDE_USER[@]}" -gt 0 ]; then
    "${RUN_AS_IDE_USER[@]}" "$@"
  else
    "$@"
  fi
}

install_ide_file() {
  local src="$1"
  local dst="$2"
  local mode="$3"

  if [ "$(id -u)" -eq 0 ] && [ -n "$IDE_UID" ] && [ -n "$IDE_GID" ] && { [ "$IDE_UID" != "0" ] || [ "$IDE_GID" != "0" ]; }; then
    install -o "$IDE_UID" -g "$IDE_GID" -m "$mode" "$src" "$dst"
  else
    install -m "$mode" "$src" "$dst"
  fi
}

as_ide_user mkdir -p \
  "$IDE_GLOBAL_SETTINGS_PATH" \
  "$IDE_CONFIG_PATH" \
  "$IDE_PROJECT_STATE_PATH" \
  "$IDE_PROJECT_STATE_PATH/system" \
  "$IDE_PROJECT_STATE_PATH/log" \
  "$HOME" \
  "$HOME/.ssh" \
  "$XDG_CONFIG_HOME" \
  "$XDG_CACHE_HOME" \
  "$XDG_DATA_HOME" \
  /ide-plugins
as_ide_user chmod 700 "$HOME/.ssh" 2>/dev/null || true

export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/tmp/runtime-${IDE_UID:-$(id -u)}}"
as_ide_user mkdir -p "$XDG_RUNTIME_DIR"
as_ide_user chmod 700 "$XDG_RUNTIME_DIR" 2>/dev/null || true
export NO_AT_BRIDGE="${NO_AT_BRIDGE:-1}"
if [ -z "${LIBGL_ALWAYS_SOFTWARE+x}" ]; then
  export LIBGL_ALWAYS_SOFTWARE=1
else
  export LIBGL_ALWAYS_SOFTWARE
fi
if [ -z "${MESA_LOADER_DRIVER_OVERRIDE+x}" ]; then
  export MESA_LOADER_DRIVER_OVERRIDE=llvmpipe
else
  export MESA_LOADER_DRIVER_OVERRIDE
fi
if [ -z "${LIBGL_DRI3_DISABLE+x}" ]; then
  export LIBGL_DRI3_DISABLE=1
else
  export LIBGL_DRI3_DISABLE
fi

IDEA_PROPERTIES=/tmp/pycharm-docker.idea.properties
cat > "$IDEA_PROPERTIES" <<EOF_PROPS
idea.config.path=$IDE_CONFIG_PATH
idea.system.path=$IDE_PROJECT_STATE_PATH/system
idea.plugins.path=/ide-plugins
idea.log.path=$IDE_PROJECT_STATE_PATH/log
EOF_PROPS
export PYCHARM_PROPERTIES="$IDEA_PROPERTIES"

start_dind() {
  if [ "$(id -u)" -ne 0 ]; then
    echo "Docker-in-Docker was enabled, but the entrypoint is not running as root." >&2
    echo "Start the container through run-pycharm-container.sh or disable it with --no-docker." >&2
    exit 1
  fi
  if ! command -v dockerd >/dev/null 2>&1; then
    echo "Docker-in-Docker was enabled, but dockerd is not installed in this image." >&2
    echo "Rebuild the image with the updated docker4pycharm/Dockerfile." >&2
    exit 1
  fi

  mkdir -p /run/docker /var/lib/docker
  rm -f /run/docker/docker.pid /var/run/docker.sock

  DOCKERD_LOG=$IDE_PROJECT_STATE_PATH/log/dockerd.log
  DOCKER_SOCKET_GROUP="${IDE_GID:-0}"
  dockerd \
    --host=unix:///var/run/docker.sock \
    --group="$DOCKER_SOCKET_GROUP" \
    --data-root=/var/lib/docker \
    --exec-root=/run/docker \
    --pidfile=/run/docker/docker.pid \
    --bridge=none \
    --iptables=false \
    --ip-forward=false \
    --ip-masq=false \
    >"$DOCKERD_LOG" 2>&1 &
  export DOCKER_HOST=unix:///var/run/docker.sock

  for _ in $(seq 1 60); do
    if docker info >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done

  echo "Docker-in-Docker daemon failed to become ready. Last dockerd log lines:" >&2
  tail -n 80 "$DOCKERD_LOG" >&2 || true
  exit 1
}

if [ "$ENABLE_DIND" = "1" ]; then
  start_dind
fi

# Keep GitHub SSH first-use state inside the isolated IDE home, not in the host home.
if [ ! -f "$HOME/.ssh/config" ]; then
  SSH_CONFIG_TMP=/tmp/pycharm-docker-ssh-config
  cat > "$SSH_CONFIG_TMP" <<'EOF_SSH'
Host github.com
  StrictHostKeyChecking accept-new
  UserKnownHostsFile ~/.ssh/known_hosts
EOF_SSH
  install_ide_file "$SSH_CONFIG_TMP" "$HOME/.ssh/config" 600
  rm -f "$SSH_CONFIG_TMP"
fi

# Optional Git identity. The wrapper passes only explicit values or host global
# user.name/user.email values, then Git stores them in the isolated IDE home.
if command -v git >/dev/null 2>&1; then
  if [ -n "${GIT_USER_NAME:-}" ]; then
    as_ide_user git config --global user.name "$GIT_USER_NAME"
  fi
  if [ -n "${GIT_USER_EMAIL:-}" ]; then
    as_ide_user git config --global user.email "$GIT_USER_EMAIL"
  fi
fi

# Optional HTTPS Git credential path. The wrapper mounts the token as a file
# rather than exposing it as a long-lived Docker environment variable.
GIT_TOKEN_FILE="${GIT_TOKEN_FILE:-${GITHUB_TOKEN_FILE:-}}"
GIT_TOKEN_USERNAME="${GIT_TOKEN_USERNAME:-${GITHUB_USER:-x-access-token}}"
GIT_TOKEN_HOSTS="${GIT_TOKEN_HOSTS:-github.com}"
if [ -n "$GIT_TOKEN_FILE" ] && [ -r "$GIT_TOKEN_FILE" ]; then
  ASKPASS=/tmp/git-askpass-token.sh
  ASKPASS_TMP=/tmp/git-askpass-token.sh.tmp
  cat > "$ASKPASS_TMP" <<'EOF_ASKPASS'
#!/usr/bin/env sh
prompt="$1"
allowed=0
prompt_host=""

prompt_url="$(printf '%s\n' "$prompt" | sed -n "s/.*'\([^']*:\/\/[^']*\)'.*/\1/p")"
if [ -n "$prompt_url" ]; then
  prompt_host="${prompt_url#*://}"
  prompt_host="${prompt_host%%/*}"
  prompt_host="${prompt_host#*@}"
  prompt_host="${prompt_host%%:*}"
fi

if [ -z "${GIT_TOKEN_HOSTS:-}" ]; then
  allowed=1
else
  hosts="$(printf '%s\n' "$GIT_TOKEN_HOSTS" | tr ',[:space:]' ' ')"
  for host in $hosts; do
    if [ "$prompt_host" = "$host" ]; then
      allowed=1
      break
    fi
  done
fi

if [ "$allowed" -ne 1 ]; then
  printf '\n'
  exit 0
fi

case "$1" in
  *Username*|*username*) printf '%s\n' "${GIT_TOKEN_USERNAME:-x-access-token}" ;;
  *Password*|*password*) cat "${GIT_TOKEN_FILE}" ;;
  *) printf '\n' ;;
esac
EOF_ASKPASS
  install_ide_file "$ASKPASS_TMP" "$ASKPASS" 700
  rm -f "$ASKPASS_TMP"
  export GIT_ASKPASS="$ASKPASS"
  export GIT_TERMINAL_PROMPT=0
fi

if [ "$#" -eq 0 ]; then
  set -- /opt/pycharm/bin/pycharm.sh "$PROJECT_PATH"
fi

if [ "${#RUN_AS_IDE_USER[@]}" -gt 0 ]; then
  exec "${RUN_AS_IDE_USER[@]}" "$@"
fi

exec "$@"
