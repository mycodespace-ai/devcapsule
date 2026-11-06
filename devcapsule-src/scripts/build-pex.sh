#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  scripts/build-pex.sh [options]

Options:
  --output PATH             Output archive. Defaults by source policy.
  --source-revision SHA     Assert and embed this full source commit.
  --source-repository URL   Public HTTPS GitHub repository URL.
  --release-mnemonic TAG   Mark an official release build with its exact Git tag.
  --allow-unpublished-revision
                            Embed clean HEAD without checking that GitHub advertises it.
  --allow-local-source      Permit dirty inputs and disclose unknown revision.

Output policy:
  strict public source     dist/devcapsule.pex
  clean unpublished HEAD  dist/devcapsule.pex
  --allow-local-source     dist/devcapsule-local.pex

Build a directly executable DevCapsule PEX scie from the local package and the
pinned runtime dependency lock file. The scie eagerly embeds portable CPython,
so the resulting artifact needs neither host Python nor a first-run download.

Environment:
  PYTHON                 Python executable used for the build. Default: python
  DEVCAPSULE_SCIE_PLATFORM
                         Native target platform. Default: linux-x86_64
  DEVCAPSULE_SCIE_PYTHON_VERSION
                         Embedded CPython version. Default: 3.12.14
  DEVCAPSULE_SCIE_PBS_RELEASE
                         Python Build Standalone release. Default: 20260814
  DOCKER4IDES_RUNTIME_PEX_ROOT
                         Runtime extraction/cache root embedded in the archive.
                         Default: /tmp/devcapsule-pex-root
  DEVCAPSULE_SOURCE_REVISION
                         Default value for --source-revision.
  DEVCAPSULE_SOURCE_REPOSITORY
                         Default value for --source-repository.
USAGE
}

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd "${script_dir}/.." && pwd)"
output="${project_dir}/dist/devcapsule.pex"
output_explicit=0
source_revision="${DEVCAPSULE_SOURCE_REVISION:-}"
source_repository="${DEVCAPSULE_SOURCE_REPOSITORY:-}"
release_mnemonic=""
allow_local_source=0
allow_unpublished_revision=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --output)
      if [[ $# -lt 2 ]]; then
        echo "scripts/build-pex.sh: --output requires a path" >&2
        exit 2
      fi
      output="$2"
      output_explicit=1
      shift 2
      ;;
    --source-revision)
      if [[ $# -lt 2 ]]; then
        echo "scripts/build-pex.sh: --source-revision requires a value" >&2
        exit 2
      fi
      source_revision="$2"
      shift 2
      ;;
    --source-repository)
      if [[ $# -lt 2 ]]; then
        echo "scripts/build-pex.sh: --source-repository requires a value" >&2
        exit 2
      fi
      source_repository="${2%.git}"
      shift 2
      ;;
    --release-mnemonic)
      if [[ $# -lt 2 ]]; then
        echo "scripts/build-pex.sh: --release-mnemonic requires a value" >&2
        exit 2
      fi
      release_mnemonic="$2"
      shift 2
      ;;
    --allow-local-source)
      allow_local_source=1
      shift
      ;;
    --allow-unpublished-revision)
      allow_unpublished_revision=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "scripts/build-pex.sh: unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

python_bin="${PYTHON:-python}"
scie_platform="${DEVCAPSULE_SCIE_PLATFORM:-linux-x86_64}"
scie_python_version="${DEVCAPSULE_SCIE_PYTHON_VERSION:-3.12.14}"
scie_pbs_release="${DEVCAPSULE_SCIE_PBS_RELEASE:-20260814}"
runtime_pex_root="${DOCKER4IDES_RUNTIME_PEX_ROOT:-/tmp/devcapsule-pex-root}"

if [[ ${allow_local_source} -eq 1 && ${output_explicit} -eq 0 ]]; then
  output="${project_dir}/dist/devcapsule-local.pex"
fi
if [[ "${output}" != /* ]]; then
  output="${project_dir}/${output}"
fi

if ! "${python_bin}" -c "import pex" >/dev/null 2>&1; then
  cat >&2 <<EOF
scripts/build-pex.sh: PEX is not installed for ${python_bin}.

Set up contributor dependencies first, or point PYTHON at that environment:
  python -m pip install -r devcapsule-src/dev-requirements.txt
  python -m pip install -e ./devcapsule-src --no-deps
  PYTHON=/path/to/venv/bin/python devcapsule-src/scripts/build-pex.sh
EOF
  exit 1
fi

"${python_bin}" "${project_dir}/scripts/bump-version.py" --check
project_version="$("${python_bin}" -c 'import sys, tomllib; print(tomllib.load(open(sys.argv[1], "rb"))["project"]["version"])' "${project_dir}/pyproject.toml")"
# The release identity is derived from the package version, not configured
# separately. A contributor binary carries the target platform so distinct
# unofficial artifacts stay distinguishable; the official mnemonic is exactly
# the release tag, asserted below.
build_mnemonic="v${project_version}-local-${scie_platform}"

mkdir -p "$(dirname "${output}")"

repo_root="$(git -C "${project_dir}" rev-parse --show-toplevel 2>/dev/null || true)"
head_revision=""
source_inputs_dirty=1
if [[ -n "${repo_root}" ]]; then
  head_revision="$(git -C "${repo_root}" rev-parse HEAD 2>/dev/null || true)"
  if [[ -z "$(git -C "${repo_root}" status --porcelain -- \
    devcapsule-src/devcapsule \
    devcapsule-src/pyproject.toml \
    devcapsule-src/requirements.txt \
    devcapsule-src/scripts/bump-version.py \
    devcapsule-src/scripts/build-pex.sh)" ]]; then
    source_inputs_dirty=0
  fi
fi

if [[ ${allow_local_source} -eq 1 && ${allow_unpublished_revision} -eq 1 ]]; then
  echo "scripts/build-pex.sh: --allow-local-source cannot be combined with --allow-unpublished-revision" >&2
  exit 2
elif [[ ${allow_local_source} -eq 1 && -n "${source_revision}" ]]; then
  echo "scripts/build-pex.sh: --allow-local-source cannot be combined with --source-revision" >&2
  exit 2
elif [[ ${allow_local_source} -eq 1 ]]; then
  source_revision="unknown"
elif [[ -z "${source_revision}" ]]; then
  if [[ ${source_inputs_dirty} -eq 0 && -n "${head_revision}" ]]; then
    source_revision="${head_revision}"
  else
    source_revision="unknown"
  fi
elif [[ ${source_inputs_dirty} -ne 0 ]]; then
  echo "scripts/build-pex.sh: cannot assert a source revision with modified PEX inputs" >&2
  exit 1
elif [[ "${source_revision}" != "${head_revision}" ]]; then
  echo "scripts/build-pex.sh: source revision does not match checkout HEAD ${head_revision}" >&2
  exit 1
fi

if [[ -n "${release_mnemonic}" ]]; then
  if [[ ${allow_local_source} -eq 1 || ${allow_unpublished_revision} -eq 1 ]]; then
    echo "scripts/build-pex.sh: --release-mnemonic cannot mark a local or unpublished build" >&2
    exit 2
  fi
  if [[ ! "${release_mnemonic}" =~ ^v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(-rc(0|[1-9][0-9]*))?$ ]]; then
    echo "scripts/build-pex.sh: release mnemonic must be vMAJOR.MINOR.PATCH[-rcN]" >&2
    exit 2
  fi
  project_version="${release_mnemonic#v}"
  project_version="${project_version/-rc/rc}"
  tagged_revision="$(git -C "${repo_root}" rev-list -n 1 "refs/tags/${release_mnemonic}" 2>/dev/null || true)"
  if [[ -z "${repo_root}" || "${tagged_revision}" != "${head_revision}" ]]; then
    echo "scripts/build-pex.sh: release mnemonic ${release_mnemonic} must be an exact tag for checkout HEAD" >&2
    exit 1
  fi
  build_mnemonic="${release_mnemonic}"
fi

if [[ -z "${source_repository}" && -n "${repo_root}" ]]; then
  remote="$(git -C "${repo_root}" remote get-url origin 2>/dev/null || true)"
  case "${remote}" in
    git@github.com:*) source_repository="https://github.com/${remote#git@github.com:}" ;;
    ssh://git@github.com/*) source_repository="https://github.com/${remote#ssh://git@github.com/}" ;;
    https://github.com/*) source_repository="${remote}" ;;
  esac
  source_repository="${source_repository%.git}"
fi
source_repository="${source_repository:-unknown}"
source_repository="${source_repository%/}"
source_url="unknown"
if [[ "${source_revision}" != "unknown" && "${source_repository}" != "unknown" ]]; then
  source_url="${source_repository}/commit/${source_revision}"
fi

if [[ ${allow_local_source} -eq 0 ]]; then
  if [[ ${source_inputs_dirty} -ne 0 ]]; then
    echo "scripts/build-pex.sh: public-revision builds require clean PEX inputs" >&2
    exit 1
  fi
  if [[ ! "${source_revision}" =~ ^[0-9a-f]{40,64}$ ]]; then
    echo "scripts/build-pex.sh: public-revision builds require a full hexadecimal commit" >&2
    exit 1
  fi
  if [[ ! "${source_repository}" =~ ^https://github\.com/[^/]+/[^/]+$ ]]; then
    echo "scripts/build-pex.sh: public-revision builds require a public HTTPS GitHub repository" >&2
    exit 1
  fi
  if [[ ${allow_unpublished_revision} -eq 0 ]] && \
    ! git ls-remote "${source_repository}.git" 2>/dev/null | cut -f1 | grep -Fx "${source_revision}" >/dev/null; then
    echo "scripts/build-pex.sh: source revision is not advertised by the public GitHub repository" >&2
    exit 1
  fi
fi

build_root="$(mktemp -d "${TMPDIR:-/tmp}/devcapsule-pex-build.XXXXXXXX")"
trap 'rm -rf "${build_root}"' EXIT
cp "${project_dir}/pyproject.toml" "${project_dir}/README.md" "${build_root}/"
cp -a "${project_dir}/devcapsule" "${build_root}/devcapsule"
# The tag is the release version authority. Change only the disposable build
# tree; the tagged source remains clean and needs no version-bump commit.
"${python_bin}" - "${build_root}/pyproject.toml" "${project_version}" <<'PY'
from pathlib import Path
import re
import sys
path = Path(sys.argv[1])
text, count = re.subn(r'^version = "[^"]+"$', f'version = "{sys.argv[2]}"',
                      path.read_text(), count=1, flags=re.MULTILINE)
if count != 1:
    raise SystemExit("Cannot stamp the package version")
path.write_text(text)
PY
"${python_bin}" - \
  "${build_root}/devcapsule/_build_info.json" \
  "${project_version}" \
  "${source_repository}" \
  "${source_revision}" \
  "${source_url}" \
  "${build_mnemonic}" <<'PY'
import json
from pathlib import Path
import sys

path, version, repository, revision, url, build_mnemonic = sys.argv[1:]
value = {
    "schema_version": 2,
    "version": version,
    "build_mnemonic": build_mnemonic,
    "source_repository": repository,
    "source_revision": revision,
    "source_url": url,
}
Path(path).write_text(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
PY

# The authored compatibility advisories travel inside the launcher as its last
# fallback, read when the published feed cannot be fetched and nothing is
# cached. No vendor is asked at build time.
policy_path="${project_dir}/../component-status/policy-v1.json"
if [[ ! -f "${policy_path}" ]]; then
  echo "scripts/build-pex.sh: ${policy_path} is missing; the compatibility feed cannot be embedded" >&2
  exit 1
fi
PYTHONPATH="${build_root}" "${python_bin}" -m devcapsule.component_status_publisher \
  --policy "${policy_path}" \
  --output "${build_root}/component-status" \
  --revision "${source_revision}" \
  --without-probes > /dev/null
cp "${build_root}/component-status/compatibility-v1.json" "${build_root}/devcapsule/_compatibility-v1.json"

rm -rf "${project_dir}/build" "${project_dir}/devcapsule.egg-info"
scie_build_output="${build_root}/devcapsule-scie"
"${python_bin}" -m pex \
  -r "${project_dir}/requirements.txt" \
  "${build_root}" \
  -c devcapsule \
  --runtime-pex-root "${runtime_pex_root}" \
  --scie eager \
  --scie-only \
  --scie-platform "${scie_platform}" \
  --scie-python-version "${scie_python_version}" \
  --scie-pbs-release "${scie_pbs_release}" \
  --scie-pbs-stripped \
  -o "${scie_build_output}"
install -m 0755 "${scie_build_output}" "${output}"

echo "${output}"
echo "Build mnemonic: ${build_mnemonic}"
echo "Self-contained runtime: CPython ${scie_python_version} (${scie_platform}, PBS ${scie_pbs_release})"
echo "Source revision: ${source_revision}"
echo "Source URL: ${source_url}"
