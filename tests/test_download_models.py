from __future__ import annotations

from pathlib import Path

from utils import download_models as dm


class _DummyTqdm:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def update(self, _n: int) -> None:
        return None


class _FakeResponse:
    def __init__(self, chunks: list[bytes]):
        self.headers = {"Content-Length": str(sum(len(c) for c in chunks))}
        self._chunks = list(chunks)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self, _size: int) -> bytes:
        if not self._chunks:
            return b""
        return self._chunks.pop(0)


class _FakeStdout:
    def __init__(self, is_tty: bool):
        self._is_tty = is_tty

    def isatty(self) -> bool:
        return self._is_tty

    def write(self, _s: str) -> int:
        return 0

    def flush(self) -> None:
        return None


def test_catalog_select_dedupes_lora():
    catalog = dm.ModelCatalog()
    selected = catalog.select(img_edit=True, edit_angle=True)
    paths = [m.path for m in selected]
    assert len(paths) == len(set(paths))
    assert any("Multiple-angles" in m.name for m in selected)


def test_progress_renderer_uses_raw_stdout_in_tty():
    fake = _FakeStdout(is_tty=True)
    renderer = dm.ProgressRenderer(stdout=fake)
    assert renderer.stream() is fake


def test_progress_renderer_uses_pipeline_stdout_when_not_tty():
    fake = _FakeStdout(is_tty=False)
    renderer = dm.ProgressRenderer(stdout=fake)
    stream = renderer.stream()
    assert isinstance(stream, dm.ProgressRenderer._TqdmPipeLineStdout)


def test_model_downloader_adds_hf_auth_header(monkeypatch, tmp_path: Path):
    target = tmp_path / "models" / "x.safetensors"
    spec = dm.ModelSpec(name="x", url="https://huggingface.co/org/repo/file", path=str(target))
    options = dm.DownloadOptions(hf_token="hf_123", force_redownload=False)
    seen = {}

    def _fake_urlopen(req, context=None):
        seen["auth"] = req.headers.get("Authorization")
        seen["context"] = context
        return _FakeResponse([b"abc", b"def"])

    monkeypatch.setattr(dm.urllib.request, "urlopen", _fake_urlopen)
    monkeypatch.setattr(dm, "tqdm", _DummyTqdm)

    downloader = dm.ModelDownloader(
        progress=dm.ProgressRenderer(stdout=_FakeStdout(is_tty=True)),
        committer=dm.FileCommitter(),
    )
    assert downloader.download_one(spec, options) is True
    assert target.exists()
    assert target.read_bytes() == b"abcdef"
    assert seen["auth"] == "Bearer hf_123"


def test_model_downloader_resolves_relative_models_under_configured_models_root(tmp_path: Path):
    models_root = tmp_path / "comfyui" / "models"
    downloader = dm.ModelDownloader(models_root=models_root)
    spec = dm.ModelSpec(name="x", url="https://example.com/x", path="models/vae/x.safetensors")
    resolved = downloader.resolve_destination(spec)
    assert resolved == models_root / "vae" / "x.safetensors"
    assert str(resolved).startswith(str(models_root))


def test_model_downloader_keeps_absolute_model_paths(tmp_path: Path):
    models_root = tmp_path / "comfyui" / "models"
    downloader = dm.ModelDownloader(models_root=models_root)
    absolute_target = tmp_path / "external" / "custom.safetensors"
    spec = dm.ModelSpec(name="x", url="https://example.com/x", path=str(absolute_target))
    assert downloader.resolve_destination(spec) == absolute_target


def test_orchestrator_aggregates_success_counts(capsys):
    class _StubDownloader:
        def __init__(self):
            self.calls = 0

        def download_one(self, _spec, _options):
            self.calls += 1
            return self.calls != 2

    orchestrator = dm.DownloadOrchestrator(downloader=_StubDownloader())
    models = [
        dm.ModelSpec("a", "https://example.com/a", "models/a"),
        dm.ModelSpec("b", "https://example.com/b", "models/b"),
        dm.ModelSpec("c", "https://example.com/c", "models/c"),
    ]
    ok = orchestrator.download_group("Title", models, dm.DownloadOptions())
    out = capsys.readouterr().out
    assert ok is False
    assert "Download complete: 2/3 models" in out


def test_orchestrator_creates_configs_under_models_root(tmp_path: Path):
    class _AllGoodDownloader:
        def __init__(self, models_root: Path):
            self.models_root = models_root

        def download_one(self, _spec, _options):
            return True

    models_root = tmp_path / "comfyui" / "models"
    orchestrator = dm.DownloadOrchestrator(downloader=_AllGoodDownloader(models_root))
    models = [dm.ModelSpec("a", "https://example.com/a", "models/a")]
    assert orchestrator.download_group("Title", models, dm.DownloadOptions()) is True
    assert (models_root / "configs").is_dir()


def test_cli_requires_at_least_one_selection():
    cli = dm.DownloadCLI()
    assert cli.run([]) == 1
