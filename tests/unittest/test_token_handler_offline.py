import sys
from types import SimpleNamespace

import pytest

from pr_agent.algo import token_handler
from pr_agent.algo.token_handler import ApproximateTokenEncoder, NoOpTokenEncoder, TokenEncoder, TransformersTokenEncoder
from pr_agent.config_loader import get_settings


@pytest.fixture(autouse=True)
def reset_token_encoder():
    old_encoder = TokenEncoder._encoder_instance
    old_model = TokenEncoder._model
    old_settings = {
        "CONFIG.MODEL": get_settings().get("CONFIG.MODEL", None),
        "TOKENIZER.LOCAL_CACHE_DIR": get_settings().get("TOKENIZER.LOCAL_CACHE_DIR", None),
        "TOKENIZER.ENABLE_LOCAL_CACHE": get_settings().get("TOKENIZER.ENABLE_LOCAL_CACHE", None),
        "TOKENIZER.FALLBACK_TO_DOWNLOAD": get_settings().get("TOKENIZER.FALLBACK_TO_DOWNLOAD", None),
        "TOKENIZER.OFFLINE_ESTIMATE_FALLBACK": get_settings().get("TOKENIZER.OFFLINE_ESTIMATE_FALLBACK", None),
        "TOKENIZER.SKIP_TOKEN_COUNT": get_settings().get("TOKENIZER.SKIP_TOKEN_COUNT", None),
        "TOKENIZER.BACKEND": get_settings().get("TOKENIZER.BACKEND", None),
        "TOKENIZER.MODELSCOPE_MODEL_ID": get_settings().get("TOKENIZER.MODELSCOPE_MODEL_ID", None),
    }
    yield
    TokenEncoder._encoder_instance = old_encoder
    TokenEncoder._model = old_model
    for key, value in old_settings.items():
        get_settings().set(key, value)


def test_strict_offline_uses_approximate_encoder_without_tiktoken_download(tmp_path, monkeypatch):
    def fail_get_encoding(name):
        raise AssertionError(f"unexpected tiktoken download path for {name}")

    monkeypatch.setattr(token_handler, "get_encoding", fail_get_encoding)
    get_settings().set("CONFIG.MODEL", "ollama/Qwen3.6-35B")
    get_settings().set("TOKENIZER.BACKEND", "tiktoken")
    get_settings().set("TOKENIZER.LOCAL_CACHE_DIR", str(tmp_path))
    get_settings().set("TOKENIZER.ENABLE_LOCAL_CACHE", True)
    get_settings().set("TOKENIZER.FALLBACK_TO_DOWNLOAD", False)
    get_settings().set("TOKENIZER.OFFLINE_ESTIMATE_FALLBACK", True)

    TokenEncoder._encoder_instance = None
    TokenEncoder._model = None

    encoder = TokenEncoder.get_token_encoder()

    assert isinstance(encoder, ApproximateTokenEncoder)
    assert len(encoder.encode("hello world")) > 0


def test_modelscope_backend_downloads_and_loads_tokenizer(tmp_path, monkeypatch):
    model_id = "Qwen/Qwen3.6-35B-A3B-FP8"
    calls = {}

    class FakeAutoTokenizer:
        @classmethod
        def from_pretrained(cls, path, trust_remote_code, local_files_only):
            calls["from_pretrained"] = {
                "path": path,
                "trust_remote_code": trust_remote_code,
                "local_files_only": local_files_only,
            }
            return cls()

        def encode(self, text, add_special_tokens=False):
            calls["encoded_text"] = text
            calls["add_special_tokens"] = add_special_tokens
            return [1, 2, 3]

    def fake_snapshot_download(download_model_id, local_dir, allow_patterns):
        calls["download_model_id"] = download_model_id
        calls["local_dir"] = local_dir
        calls["allow_patterns"] = allow_patterns
        (tmp_path / "modelscope" / "Qwen__Qwen3.6-35B-A3B-FP8").mkdir(parents=True, exist_ok=True)
        (tmp_path / "modelscope" / "Qwen__Qwen3.6-35B-A3B-FP8" / "tokenizer_config.json").write_text("{}")
        return local_dir

    monkeypatch.setitem(sys.modules, "transformers", SimpleNamespace(AutoTokenizer=FakeAutoTokenizer))
    monkeypatch.setitem(sys.modules, "modelscope", SimpleNamespace(snapshot_download=fake_snapshot_download))
    get_settings().set("CONFIG.MODEL", "openai/local-review-model")
    get_settings().set("TOKENIZER.BACKEND", "modelscope")
    get_settings().set("TOKENIZER.MODELSCOPE_MODEL_ID", model_id)
    get_settings().set("TOKENIZER.LOCAL_CACHE_DIR", str(tmp_path))
    get_settings().set("TOKENIZER.FALLBACK_TO_DOWNLOAD", True)
    get_settings().set("TOKENIZER.OFFLINE_ESTIMATE_FALLBACK", False)
    get_settings().set("TOKENIZER.SKIP_TOKEN_COUNT", False)

    TokenEncoder._encoder_instance = None
    TokenEncoder._model = None

    encoder = TokenEncoder.get_token_encoder()

    assert isinstance(encoder, TransformersTokenEncoder)
    assert encoder.encode("hello") == [1, 2, 3]
    assert calls["download_model_id"] == model_id
    assert "tokenizer.json" in calls["allow_patterns"]
    assert calls["from_pretrained"]["local_files_only"] is True
    assert calls["from_pretrained"]["path"].endswith("Qwen__Qwen3.6-35B-A3B-FP8")
    assert calls["add_special_tokens"] is False


def test_modelscope_backend_uses_local_dir_when_download_disabled(tmp_path, monkeypatch):
    model_id = "Qwen/Qwen3.6-35B-A3B-FP8"
    cached_dir = tmp_path / "modelscope" / "Qwen__Qwen3.6-35B-A3B-FP8"
    cached_dir.mkdir(parents=True)
    (cached_dir / "tokenizer_config.json").write_text("{}")

    class FakeAutoTokenizer:
        @classmethod
        def from_pretrained(cls, path, trust_remote_code, local_files_only):
            return cls()

        def encode(self, text, add_special_tokens=False):
            return [1]

    monkeypatch.setitem(sys.modules, "transformers", SimpleNamespace(AutoTokenizer=FakeAutoTokenizer))
    monkeypatch.setitem(
        sys.modules,
        "modelscope",
        SimpleNamespace(snapshot_download=lambda *args, **kwargs: pytest.fail("download should not be called")),
    )
    get_settings().set("CONFIG.MODEL", "openai/local-review-model")
    get_settings().set("TOKENIZER.BACKEND", "modelscope")
    get_settings().set("TOKENIZER.MODELSCOPE_MODEL_ID", model_id)
    get_settings().set("TOKENIZER.LOCAL_CACHE_DIR", str(tmp_path))
    get_settings().set("TOKENIZER.FALLBACK_TO_DOWNLOAD", False)
    get_settings().set("TOKENIZER.OFFLINE_ESTIMATE_FALLBACK", False)
    get_settings().set("TOKENIZER.SKIP_TOKEN_COUNT", False)

    TokenEncoder._encoder_instance = None
    TokenEncoder._model = None

    encoder = TokenEncoder.get_token_encoder()

    assert isinstance(encoder, TransformersTokenEncoder)
    assert encoder.encode("hello") == [1]


def test_skip_token_count_bypasses_tiktoken_loading(tmp_path, monkeypatch):
    def fail_get_encoding(name):
        raise AssertionError(f"unexpected tiktoken download path for {name}")

    def fail_encoding_for_model(name):
        raise AssertionError(f"unexpected tiktoken model path for {name}")

    monkeypatch.setattr(token_handler, "get_encoding", fail_get_encoding)
    monkeypatch.setattr(token_handler, "encoding_for_model", fail_encoding_for_model)
    get_settings().set("CONFIG.MODEL", "ollama/Qwen3.6-35B")
    get_settings().set("TOKENIZER.BACKEND", "tiktoken")
    get_settings().set("TOKENIZER.LOCAL_CACHE_DIR", str(tmp_path))
    get_settings().set("TOKENIZER.ENABLE_LOCAL_CACHE", True)
    get_settings().set("TOKENIZER.FALLBACK_TO_DOWNLOAD", True)
    get_settings().set("TOKENIZER.OFFLINE_ESTIMATE_FALLBACK", False)
    get_settings().set("TOKENIZER.SKIP_TOKEN_COUNT", True)

    TokenEncoder._encoder_instance = None
    TokenEncoder._model = None

    encoder = TokenEncoder.get_token_encoder()

    assert isinstance(encoder, NoOpTokenEncoder)
    assert encoder.encode("hello world") == []


def test_strict_offline_can_fail_fast_when_approximate_fallback_disabled(tmp_path, monkeypatch):
    def fail_get_encoding(name):
        raise AssertionError(f"unexpected tiktoken download path for {name}")

    monkeypatch.setattr(token_handler, "get_encoding", fail_get_encoding)
    get_settings().set("CONFIG.MODEL", "ollama/Qwen3.6-35B")
    get_settings().set("TOKENIZER.BACKEND", "tiktoken")
    get_settings().set("TOKENIZER.LOCAL_CACHE_DIR", str(tmp_path))
    get_settings().set("TOKENIZER.ENABLE_LOCAL_CACHE", True)
    get_settings().set("TOKENIZER.FALLBACK_TO_DOWNLOAD", False)
    get_settings().set("TOKENIZER.OFFLINE_ESTIMATE_FALLBACK", False)
    get_settings().set("TOKENIZER.SKIP_TOKEN_COUNT", False)

    TokenEncoder._encoder_instance = None
    TokenEncoder._model = None

    with pytest.raises(RuntimeError, match="Tokenizer not available in local cache"):
        TokenEncoder.get_token_encoder()
