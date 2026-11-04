#!/usr/bin/env bash
set -euo pipefail

IDE_HOME="${IDE_HOME:-${PYCHARM_HOME:-/opt/pycharm}}"
case "$(uname -m)" in
  aarch64 | arm64) SKIKO_ARCH=arm64 ;;
  *) SKIKO_ARCH=x64 ;;
esac
SKIKO_LIB="$IDE_HOME/lib/skiko-awt-runtime-all/libskiko-linux-$SKIKO_ARCH.so"
FAILURES=0

pass() {
  printf 'ok: %s\n' "$1"
}

fail() {
  printf 'FAIL: %s\n' "$1" >&2
  FAILURES=$((FAILURES + 1))
}

warn() {
  printf 'warn: %s\n' "$1" >&2
}

check_dir_writable() {
  local path="$1"

  if [ -d "$path" ] && [ -w "$path" ]; then
    pass "$path exists and is writable"
  else
    fail "$path is missing or not writable"
  fi
}

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

printf 'DevCapsule runtime check\n'
printf '  IDE_HOME=%s\n' "$IDE_HOME"
printf '  DISPLAY=%s\n' "${DISPLAY:-}"
printf '  XDG_RUNTIME_DIR=%s\n' "${XDG_RUNTIME_DIR:-}"
printf '  LIBGL_ALWAYS_SOFTWARE=%s\n' "$LIBGL_ALWAYS_SOFTWARE"
printf '  MESA_LOADER_DRIVER_OVERRIDE=%s\n' "$MESA_LOADER_DRIVER_OVERRIDE"
printf '  LIBGL_DRI3_DISABLE=%s\n' "$LIBGL_DRI3_DISABLE"

if [ -f "$SKIKO_LIB" ]; then
  pass "Skiko native library exists: $SKIKO_LIB"
  LDD_OUTPUT="$(ldd "$SKIKO_LIB" 2>&1 || true)"
  if printf '%s\n' "$LDD_OUTPUT" | grep -qi 'not found'; then
    printf '%s\n' "$LDD_OUTPUT" | grep -i 'not found' >&2 || true
    fail "Skiko native library has unresolved dependencies"
  else
    pass "Skiko native library has no unresolved ldd dependencies"
  fi
  if printf '%s\n' "$LDD_OUTPUT" | grep -q 'libGL.so.1 =>'; then
    pass "libGL.so.1 resolves for Skiko"
  else
    fail "libGL.so.1 was not found in Skiko ldd output"
  fi
else
  fail "Skiko native library is missing: $SKIKO_LIB"
fi

if [ -n "${XDG_RUNTIME_DIR:-}" ] && [ -d "$XDG_RUNTIME_DIR" ] && [ -w "$XDG_RUNTIME_DIR" ]; then
  pass "XDG_RUNTIME_DIR exists and is writable"
else
  fail "XDG_RUNTIME_DIR is missing or not writable"
fi

check_dir_writable "${IDE_GLOBAL_SETTINGS_PATH:-/ide-global-settings}"
check_dir_writable "${IDE_CONFIG_PATH:-/ide-config}"
check_dir_writable "${IDE_PROJECT_STATE_PATH:-/ide-project-state}"
check_dir_writable /ide-plugins
check_dir_writable "${HOME:-/ide-global-settings/home}"

if command -v glxinfo >/dev/null 2>&1 && [ -n "${DISPLAY:-}" ]; then
  GLX_OUTPUT="$(glxinfo -B 2>&1 || true)"
  if printf '%s\n' "$GLX_OUTPUT" | grep -Eqi 'Failed to query drm device|failed to create dri3 screen|failed to load driver: iris'; then
    printf '%s\n' "$GLX_OUTPUT" | grep -Ei 'Failed to query drm device|failed to create dri3 screen|failed to load driver: iris' >&2 || true
    fail "GLX still attempted the noisy hardware DRI path"
  elif printf '%s\n' "$GLX_OUTPUT" | grep -q 'OpenGL renderer string:'; then
    printf '%s\n' "$GLX_OUTPUT" | grep 'OpenGL renderer string:' | head -n 1
    pass "GLX context check completed without drm/dri3/iris warnings"
  else
    printf '%s\n' "$GLX_OUTPUT" >&2
    fail "GLX check did not report an OpenGL renderer"
  fi
else
  warn "Skipping GLX check; glxinfo or DISPLAY is unavailable"
fi

if command -v sudo >/dev/null 2>&1; then
  pass "sudo command is installed"
  if [ "${ENABLE_SUDO:-0}" = "1" ] && [ "$(id -u)" -ne 0 ]; then
    if sudo -n true >/dev/null 2>&1; then
      pass "passwordless sudo is enabled for this runtime user"
    else
      fail "ENABLE_SUDO=1, but passwordless sudo failed for this runtime user"
    fi
  fi
else
  fail "sudo command is missing"
fi

if [ "$FAILURES" -gt 0 ]; then
  exit 1
fi

printf 'runtime checks passed\n'
