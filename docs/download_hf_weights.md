## Download Qwen weights (Hugging Face Hub, no vLLM required)

This repo historically used vLLM for running Qwen VL. vLLM can be sensitive to CUDA/ABI mismatches, but **downloading weights does not need vLLM**.

This doc shows how to download the **Qwen/Qwen3-VL-4B-Instruct** repo using Hugging Face Hub tooling (`huggingface_hub`). This is a pure HTTP/cache operation and does not import CUDA or vLLM.

### Prerequisites

- Python environment with `huggingface_hub` available (it is typically installed via `transformers`).
- Optional: `HF_TOKEN` for higher rate limits / gated repos.

### Option A: Download into the default HF cache (recommended)

```bash
export HF_TOKEN=...   # optional
python -c 'from huggingface_hub import snapshot_download; print(snapshot_download(repo_id="Qwen/Qwen3-VL-4B-Instruct", token=None))'
```

Notes:
- The returned path is the local snapshot directory inside your HF cache.
- To control cache location, set `HF_HOME` or `HUGGINGFACE_HUB_CACHE` before running.

### Option B: Download into a repo-local folder (explicit, easy to mount)

```bash
export HF_TOKEN=...   # optional
python -c 'from huggingface_hub import snapshot_download; print(snapshot_download(repo_id="Qwen/Qwen3-VL-4B-Instruct", local_dir="models/hf/Qwen__Qwen3-VL-4B-Instruct", local_dir_use_symlinks=False, token=None))'
```

### Using the downloaded weights

- **vLLM** / **SGLang**: point the runtime at the printed local directory path instead of a `repo_id` to avoid network downloads at runtime.
- **Transformers**: whether it can *load* a given Qwen3-VL repository depends on the specific repo/format. Even when Transformers can’t load it, `snapshot_download` is still useful for provisioning and offline use with other runtimes.
