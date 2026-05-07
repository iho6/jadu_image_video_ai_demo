---
name: Comfy startup cu124 alignment
overview: "Align the Comfy startup playbook with the repo’s actual CUDA target: **cu124** (CUDA 12.4 wheels) per `requirements.txt`, not cu128. Keep logging and venv reset steps; fix drift risk by pinning torch/vision/audio for cu124."
todos:
  - id: verify-requirements-cu124
    content: Confirm requirements.txt keeps cu124 index; add pinned torch/torchvision/torchaudio +cu124 to stop pip drifting to CUDA 13
    status: pending
  - id: setup-requirements-txt
    content: Point setup.sh REQUIREMENTS_PY at requirements.txt so every run uses cu124 stack
    status: pending
  - id: keep-comfy-logging
    content: Retain logs/comfy_setup_startup.log pipe-pane + tail-on-failure + port HTTP probe in setup.sh
    status: pending
isProject: false
---

# Comfy startup: align with **cu124** (current `requirements.txt`)

## Correction from earlier chat

The repo’s [`requirements.txt`](requirements.txt) is **not** on cu128. It currently has:

```text
--extra-index-url https://download.pytorch.org/whl/cu124
torch>=2.5.0
```

So any playbook that assumed **cu128** was wrong for this tree. Your environment should be described as **CUDA 12.4 PyTorch wheels (cu124)** unless you intentionally change the index.

## Why Comfy still failed in history (unchanged logic)

- **Unpinned `torch>=2.5.0`** plus `-r comfyui/requirements.txt` (bare `torch`) lets pip resolve **newer torch + CUDA 13** wheels from PyPI, which then **break** on hosts whose driver only supports up to **12.x** (or causes `libcudart`/NCCL symbol mismatches).
- **Silent tmux exit**: without `logs/comfy_setup_startup.log` + `pipe-pane`, failures looked like “port not ready” with no traceback.

## Plan to fix / stay fixed on **cu124**

### 1) Keep startup diagnostics in [`setup.sh`](setup.sh)

- `LOG_DIR` / `COMFY_LOG` under `logs/`
- `tmux pipe-pane` into `comfy_setup_startup.log`
- `diagnose_comfy_start_failure`: tail last ~120 lines of log
- Port-in-use branch: HTTP probe to `http://127.0.0.1:${COMFY_PORT}/system_stats` when `curl` exists

### 2) Lock PyTorch to **cu124** in [`requirements.txt`](requirements.txt)

- Keep `--extra-index-url https://download.pytorch.org/whl/cu124`
- Replace loose `torch>=2.5.0` with **pinned** lines, e.g.:

  - `torch==<version>+cu124`
  - `torchvision==<version>+cu124`
  - `torchaudio==<version>+cu124`

Pick a single trio that `pip` resolves from the cu124 index and that passes:

`python -c "import torch; print(torch.__version__, torch.version.cuda, torch.cuda.is_available())"`

Expected: `torch.version.cuda` shows **12.4** (or 12.x consistent with cu124 build), and `is_available` is `True` on a GPU host with a sufficient driver.

### 3) Ensure [`setup.sh`](setup.sh) installs [`requirements.txt`](requirements.txt)

- `REQUIREMENTS_PY` should point at `requirements.txt` (not a comfy-only file) so the cu124 index and pins apply on every setup run.

### 4) When debugging a regression

1. Read `logs/comfy_setup_startup.log` after a failed `./setup.sh`
2. If logs show wrong CUDA / driver errors: recreate `.venv`, reinstall `requirements.txt`
3. If port in use: use listener + HTTP probe output to see if it is Comfy or another service

## Driver note (no cu128 required)

`nvidia-smi` “CUDA Version” is the **maximum** CUDA version the **driver** supports. Using **cu124** wheels is appropriate when the driver supports at least CUDA 12.4; you do **not** need cu128 in `requirements.txt` unless you deliberately standardize on 12.8 wheels everywhere.
