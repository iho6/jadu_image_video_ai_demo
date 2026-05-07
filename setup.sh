#!/usr/bin/env bash
#
# Root ComfyUI environment setup and server start (inference services use 127.0.0.1:COMFY_PORT).
#
# Optional environment:
#   HF_TOKEN            — Hugging Face token; used by utils/download_models.py for gated models.
#   GITHUB_PAT          — If git LFS uses an HTTPS remote, ensure Git can authenticate (PAT / helper),
#                         same as a normal git lfs pull from this repo.
#   Setup profile        — This script installs only ComfyUI + Comfy-backed services + tests from
#                         requirements.comfy-services.txt (not direct Qwen diffusers runtime).
#   COMFY_PORT          — ComfyUI listen port (default 8188). Matches services/logic.py and inference CLIs.
#   COMFY_CACHE_ENABLE  — If set to 1, true, yes, y, or on, Comfy node cache is enabled; otherwise
#                         this script passes --cache-none (same as _launch_main_background in logic.py).
#
# Apt: if apt-get update fails because a deadsnakes Launchpad PPA is unreachable, this script may
# rename matching *.list files under /etc/apt/sources.list.d to *.list.disabled and retry once.
# Re-enable manually if you rely on that PPA.
#
# After this script runs, Comfy is in a tmux session; view logs with:
#   tmux attach -t jadu2026_comfy
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${REPO_ROOT}"

VENV_PATH="${REPO_ROOT}/.venv"
VENV_PYTHON="${VENV_PATH}/bin/python"
REQUIREMENTS_PY="${REPO_ROOT}/requirements.txt"
COMFY_APP_ROOT="${REPO_ROOT}/comfyui"
COMFY_BASE_DIR="${COMFY_APP_ROOT}"
COMFY_PORT_VAL="${COMFY_PORT:-8188}"
SESSION_NAME="jadu2026_comfy"
LOG_DIR="${REPO_ROOT}/logs"
COMFY_LOG="${LOG_DIR}/comfy_setup_startup.log"

elapsed_text() {
  local now elapsed
  now="$(date +%s)"
  elapsed=$((now - SCRIPT_START))
  printf "+%02d:%02d:%02d" $((elapsed / 3600)) $(((elapsed % 3600) / 60)) $((elapsed % 60))
}

meta_log() {
  echo "[setup] $(elapsed_text) $*"
}

SCRIPT_START="$(date +%s)"

# runner: empty when root, or "sudo" when privileges are needed for apt and mv.
apt_get_update_robust() {
  local runner="${1-}"
  local -a apt_opts=(
    -o Acquire::Retries=3
    -o Acquire::http::Timeout=15
    -o Acquire::https::Timeout=15
  )

  if DEBIAN_FRONTEND=noninteractive ${runner:+$runner }apt-get update "${apt_opts[@]}"; then
    return 0
  fi

  meta_log "apt-get update failed; checking for unreachable deadsnakes PPAs to disable..."
  local f disabled_any=0
  for f in /etc/apt/sources.list.d/*.list; do
    [[ -f "$f" ]] || continue
    if grep -E '^[[:space:]]*deb[[:space:]]+' "$f" 2>/dev/null | grep -Fq 'ppa.launchpadcontent.net/deadsnakes'; then
      local disabled="${f}.disabled"
      if [[ ! -e "$disabled" ]]; then
        meta_log "Disabling unreachable repo file: ${f}"
        ${runner:+$runner }mv -- "$f" "$disabled"
        disabled_any=1
      fi
    fi
  done

  if (( disabled_any )); then
    meta_log "Retrying apt-get update after disabling deadsnakes PPA source(s)..."
    DEBIAN_FRONTEND=noninteractive ${runner:+$runner }apt-get update "${apt_opts[@]}"
  else
    return 1
  fi
}

ensure_git_lfs() {
  if git lfs version >/dev/null 2>&1; then
    return 0
  fi

  meta_log "git-lfs not found; installing git-lfs via apt..."
  if ! command -v apt-get >/dev/null 2>&1; then
    echo "git-lfs not found and apt-get is unavailable. Install git-lfs and retry." >&2
    exit 1
  fi

  local runner
  if [[ "$(id -u)" == "0" ]]; then
    runner=""
  elif command -v sudo >/dev/null 2>&1; then
    runner="sudo"
  else
    echo "git-lfs not found and sudo is unavailable. Install git-lfs and retry." >&2
    exit 1
  fi

  apt_get_update_robust "${runner}"
  ${runner:+$runner }apt-get install -y git-lfs

  if ! git lfs version >/dev/null 2>&1; then
    echo "git-lfs install completed but git-lfs still not available. Open a new shell and retry." >&2
    exit 1
  fi
}

ensure_tmux() {
  if command -v tmux >/dev/null 2>&1; then
    return 0
  fi

  echo "tmux is required. Installing tmux via apt..." >&2
  if ! command -v apt-get >/dev/null 2>&1; then
    echo "apt-get is unavailable; install tmux and retry." >&2
    exit 1
  fi

  local runner
  if [[ "$(id -u)" == "0" ]]; then
    runner=""
  elif command -v sudo >/dev/null 2>&1; then
    runner="sudo"
  else
    echo "sudo is unavailable; install tmux and retry." >&2
    exit 1
  fi

  apt_get_update_robust "${runner}"
  ${runner:+$runner }apt-get install -y tmux

  if ! command -v tmux >/dev/null 2>&1; then
    echo "tmux install completed but tmux still not on PATH. Open a new shell and retry." >&2
    exit 1
  fi
}

port_in_use() {
  local port="$1"
  if command -v ss >/dev/null 2>&1; then
    ss -ltn "sport = :${port}" 2>/dev/null | awk 'NR>1 {found=1} END {exit found?0:1}'
    return $?
  fi
  (echo >/dev/tcp/127.0.0.1/"${port}") >/dev/null 2>&1
}

listener_pid_for_port() {
  local port="$1"
  if command -v ss >/dev/null 2>&1; then
    ss -ltnp "sport = :${port}" 2>/dev/null | awk '
      NR>1 {
        if (match($0, /pid=[0-9]+/)) {
          print substr($0, RSTART + 4, RLENGTH - 4)
          exit
        }
      }
    '
    return 0
  fi
  if command -v lsof >/dev/null 2>&1; then
    lsof -nP -iTCP:"${port}" -sTCP:LISTEN -Fp 2>/dev/null | awk '/^p[0-9]+/ {print substr($0,2); exit}'
    return 0
  fi
}

listener_info_for_port() {
  local port="$1"
  if command -v ss >/dev/null 2>&1; then
    ss -ltnp "sport = :${port}" 2>/dev/null || true
    return
  fi
  if command -v lsof >/dev/null 2>&1; then
    lsof -nP -iTCP:"${port}" -sTCP:LISTEN 2>/dev/null || true
    return
  fi
  echo "(listener details unavailable: install ss or lsof)"
}

comfy_http_ready() {
  local url="http://127.0.0.1:${COMFY_PORT_VAL}/system_stats"
  if command -v curl >/dev/null 2>&1; then
    curl -fsS --max-time 1 "${url}" >/dev/null 2>&1
    return $?
  fi
  python3 -c "import urllib.request; urllib.request.urlopen('${url}', timeout=1)" >/dev/null 2>&1
}

diagnose_comfy_start_failure() {
  echo "Comfy startup diagnostics for 127.0.0.1:${COMFY_PORT_VAL}:" >&2
  if port_in_use "${COMFY_PORT_VAL}"; then
    echo "- Port is occupied." >&2
    listener_info_for_port "${COMFY_PORT_VAL}" >&2
  else
    echo "- Port is not currently occupied." >&2
  fi
  if tmux has-session -t "${SESSION_NAME}" 2>/dev/null; then
    echo "- Recent tmux output (${SESSION_NAME}):" >&2
    tmux capture-pane -pt "${SESSION_NAME}" -S -60 2>/dev/null >&2 || true
  else
    echo "- tmux session '${SESSION_NAME}' is not running." >&2
  fi
  if [[ -f "${COMFY_LOG}" ]]; then
    echo "- Last 120 lines of ${COMFY_LOG}:" >&2
    tail -n 120 "${COMFY_LOG}" >&2 || true
  fi
  echo "Hints: stop conflicting listeners or set COMFY_PORT to a free port, then rerun setup." >&2
}

ensure_git_lfs
(
  cd "${REPO_ROOT}"
  git lfs install --local >/dev/null 2>&1 || true
  meta_log "Fetching Git LFS assets (git lfs pull)..."
  if ! git lfs pull; then
    echo >&2
    echo "ERROR: git lfs pull failed (auth may be required)." >&2
    echo "If using HTTPS, configure credentials (e.g. GITHUB_PAT / credential helper)." >&2
    echo >&2
    exit 2
  fi
)

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python3 not found. Install Python 3 and retry." >&2
  exit 1
fi

if [[ ! -x "${VENV_PYTHON}" ]]; then
  meta_log "Creating venv at: ${VENV_PATH}"
  python3 -m venv "${VENV_PATH}"
  meta_log "Venv creation completed"
fi

meta_log "Upgrading pip tooling in venv..."
"${VENV_PYTHON}" -m pip install --upgrade pip "setuptools<82" wheel
meta_log "Installing scoped Python requirements into venv..."
"${VENV_PYTHON}" -m pip install -r "${REQUIREMENTS_PY}"
meta_log "Python requirements installation completed"

meta_log "Running custom-node installer (placeholder-safe)..."
bash "${REPO_ROOT}/utils/install_custom_nodes.sh" "${COMFY_BASE_DIR}/custom_nodes"

meta_log "Downloading models (utils/download_models.py --img-edit --edit-angle)..."
"${VENV_PYTHON}" utils/download_models.py --img-edit --edit-angle

ensure_tmux

SKIP_COMFY_START=0
if port_in_use "${COMFY_PORT_VAL}"; then
  SKIP_COMFY_START=1
  meta_log "Port 127.0.0.1:${COMFY_PORT_VAL} already in use; skipping Comfy launch."
  listener_info_for_port "${COMFY_PORT_VAL}" || true
  if ! comfy_http_ready; then
    url="http://127.0.0.1:${COMFY_PORT_VAL}/system_stats"
    echo "Warning: listener on 127.0.0.1:${COMFY_PORT_VAL} did not respond as Comfy /system_stats (${url})." >&2
    if command -v curl >/dev/null 2>&1; then
      echo "--- Begin HTTP probe (${url}) ---" >&2
      curl -i --max-time 2 "${url}" 2>&1 | sed -n '1,40p' >&2 || true
      echo "--- End HTTP probe (${url}) ---" >&2
    fi
    echo "Continuing without launching a new Comfy process." >&2
  fi
fi

_cache_lower="$(echo "${COMFY_CACHE_ENABLE:-}" | tr '[:upper:]' '[:lower:]')"
CACHE_EXTRA=""
case "${_cache_lower}" in
  1 | true | yes | y | on) ;;
  *)
    CACHE_EXTRA="--cache-none"
    ;;
esac

_SH_COMFY_APP_ROOT="$(printf '%q' "${COMFY_APP_ROOT}")"
_SH_COMFY_BASE_DIR="$(printf '%q' "${COMFY_BASE_DIR}")"
_SH_PY="$(printf '%q' "${VENV_PYTHON}")"
COMFY_CMD="cd ${_SH_COMFY_APP_ROOT} && export PYTHONUTF8=1 PYTHONIOENCODING=utf-8 && exec ${_SH_PY} main.py --base-directory ${_SH_COMFY_BASE_DIR} --disable-metadata --listen 127.0.0.1 --port ${COMFY_PORT_VAL} ${CACHE_EXTRA}"

if (( ! SKIP_COMFY_START )); then
  mkdir -p "${LOG_DIR}"
  : > "${COMFY_LOG}"
  if tmux has-session -t "${SESSION_NAME}" 2>/dev/null; then
    meta_log "Replacing existing tmux session '${SESSION_NAME}'"
    tmux kill-session -t "${SESSION_NAME}"
  fi

  meta_log "Starting ComfyUI in tmux session '${SESSION_NAME}' (listen 127.0.0.1:${COMFY_PORT_VAL})"
  tmux new-session -d -s "${SESSION_NAME}" "${COMFY_CMD}"
  tmux pipe-pane -o -t "${SESSION_NAME}" "cat >> ${COMFY_LOG}"
  _expected_pane_pid="$(tmux display-message -p -t "${SESSION_NAME}" '#{pane_pid}' 2>/dev/null || true)"
  if [[ -z "${_expected_pane_pid}" ]]; then
    echo "Failed to inspect tmux pane pid for '${SESSION_NAME}'." >&2
    diagnose_comfy_start_failure
    exit 1
  fi

  # Strict readiness applies only when this run launches Comfy itself.
  meta_log "Waiting for Comfy process and HTTP readiness on 127.0.0.1:${COMFY_PORT_VAL}..."
  _ready_start="$(date +%s)"
  _ready_max=120
  while true; do
    if ! tmux has-session -t "${SESSION_NAME}" 2>/dev/null; then
      echo "Comfy tmux session '${SESSION_NAME}' exited before becoming ready." >&2
      diagnose_comfy_start_failure
      exit 1
    fi
    if ! kill -0 "${_expected_pane_pid}" 2>/dev/null; then
      echo "Comfy process (pid ${_expected_pane_pid}) exited before becoming ready." >&2
      diagnose_comfy_start_failure
      exit 1
    fi
    _listener_pid="$(listener_pid_for_port "${COMFY_PORT_VAL}" || true)"
    _port_ok=1
    if [[ -n "${_listener_pid}" ]]; then
      if [[ "${_listener_pid}" != "${_expected_pane_pid}" ]]; then
        _port_ok=0
      fi
    elif ! port_in_use "${COMFY_PORT_VAL}"; then
      _port_ok=0
    fi
    if (( _port_ok )) && comfy_http_ready; then
      break
    fi
    if (( $(date +%s) - _ready_start > _ready_max )); then
      echo "Timeout waiting for Comfy readiness on 127.0.0.1:${COMFY_PORT_VAL}" >&2
      diagnose_comfy_start_failure
      exit 1
    fi
    sleep 0.25
  done
else
  meta_log "Reusing existing listener on 127.0.0.1:${COMFY_PORT_VAL}; server start skipped."
fi

meta_log "Comfy ready."

echo
echo "Inference CLIs can use this host/port (same defaults as services/logic.py):"
echo "  export COMFY_PORT=${COMFY_PORT_VAL}"
echo "  export COMFY_URL=http://127.0.0.1:${COMFY_PORT_VAL}"
echo
echo "Attach to Comfy logs:"
echo "  tmux attach -t ${SESSION_NAME}"
echo
