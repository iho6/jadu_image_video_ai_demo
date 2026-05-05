#!/usr/bin/env bash
#
# Root ComfyUI environment setup and server start (inference services use 127.0.0.1:COMFY_PORT).
#
# Optional environment:
#   HF_TOKEN            — Hugging Face token; used by utils/download_models.py for gated models.
#   GITHUB_PAT          — If git LFS uses an HTTPS remote, ensure Git can authenticate (PAT / helper),
#                         same as a normal git lfs pull from this repo.
#   COMFY_PORT          — ComfyUI listen port (default 8188). Matches services/logic.py and inference CLIs.
#   COMFY_CACHE_ENABLE  — If set to 1, true, yes, y, or on, Comfy node cache is enabled; otherwise
#                         this script passes --cache-none (same as _launch_main_background in logic.py).
#
# After this script runs, Comfy is in a tmux session; view logs with:
#   tmux attach -t anime2026_comfy
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${REPO_ROOT}"

VENV_PATH="${REPO_ROOT}/.venv"
VENV_PYTHON="${VENV_PATH}/bin/python"
REQUIREMENTS_PY="${REPO_ROOT}/requirements.txt"
COMFY_PORT_VAL="${COMFY_PORT:-8188}"
SESSION_NAME="anime2026_comfy"

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

  ${runner:+$runner }apt-get update
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

  ${runner:+$runner }apt-get update
  ${runner:+$runner }apt-get install -y tmux

  if ! command -v tmux >/dev/null 2>&1; then
    echo "tmux install completed but tmux still not on PATH. Open a new shell and retry." >&2
    exit 1
  fi
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
meta_log "Installing PyTorch (cu121) from PyTorch index..."
"${VENV_PYTHON}" -m pip install torch torchvision torchaudio \
  --index-url https://download.pytorch.org/whl/cu121
meta_log "Installing Python requirements into venv..."
"${VENV_PYTHON}" -m pip install -r "${REQUIREMENTS_PY}"
meta_log "Python requirements installation completed"

meta_log "Running custom-node installer (placeholder-safe)..."
bash "${REPO_ROOT}/utils/install_custom_nodes.sh" "${REPO_ROOT}/comfyui/custom_nodes"

meta_log "Downloading models (utils/download_models.py --img-edit --edit-angle)..."
"${VENV_PYTHON}" utils/download_models.py --img-edit --edit-angle

ensure_tmux

if tmux has-session -t "${SESSION_NAME}" 2>/dev/null; then
  meta_log "Replacing existing tmux session '${SESSION_NAME}'"
  tmux kill-session -t "${SESSION_NAME}"
fi

_cache_lower="$(echo "${COMFY_CACHE_ENABLE:-}" | tr '[:upper:]' '[:lower:]')"
CACHE_EXTRA=""
case "${_cache_lower}" in
  1 | true | yes | y | on) ;;
  *)
    CACHE_EXTRA="--cache-none"
    ;;
esac

_SH_ROOT="$(printf '%q' "${REPO_ROOT}")"
_SH_PY="$(printf '%q' "${VENV_PYTHON}")"
COMFY_CMD="cd ${_SH_ROOT} && export PYTHONUTF8=1 PYTHONIOENCODING=utf-8 && exec ${_SH_PY} main.py --disable-metadata --listen 127.0.0.1 --port ${COMFY_PORT_VAL} ${CACHE_EXTRA}"

meta_log "Starting ComfyUI in tmux session '${SESSION_NAME}' (listen 127.0.0.1:${COMFY_PORT_VAL})"
tmux new-session -d -s "${SESSION_NAME}" "${COMFY_CMD}"

meta_log "Waiting for Comfy to accept connections on 127.0.0.1:${COMFY_PORT_VAL}..."
_ready_start="$(date +%s)"
_ready_max=120
while true; do
  if (echo >/dev/tcp/127.0.0.1/"${COMFY_PORT_VAL}") 2>/dev/null; then
    break
  fi
  if (( $(date +%s) - _ready_start > _ready_max )); then
    echo "Timeout waiting for Comfy on 127.0.0.1:${COMFY_PORT_VAL}" >&2
    echo "Check logs: tmux attach -t ${SESSION_NAME}" >&2
    exit 1
  fi
  sleep 0.25
done

meta_log "Comfy ready."

echo
echo "Inference CLIs can use this host/port (same defaults as services/logic.py):"
echo "  export COMFY_PORT=${COMFY_PORT_VAL}"
echo "  export COMFY_URL=http://127.0.0.1:${COMFY_PORT_VAL}"
echo
echo "Attach to Comfy logs:"
echo "  tmux attach -t ${SESSION_NAME}"
echo
