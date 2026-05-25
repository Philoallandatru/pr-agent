import pytest

from pr_agent.algo import token_handler
from pr_agent.algo.token_handler import ApproximateTokenEncoder, TokenEncoder
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
    get_settings().set("TOKENIZER.LOCAL_CACHE_DIR", str(tmp_path))
    get_settings().set("TOKENIZER.ENABLE_LOCAL_CACHE", True)
    get_settings().set("TOKENIZER.FALLBACK_TO_DOWNLOAD", False)
    get_settings().set("TOKENIZER.OFFLINE_ESTIMATE_FALLBACK", True)

    TokenEncoder._encoder_instance = None
    TokenEncoder._model = None

    encoder = TokenEncoder.get_token_encoder()

    assert isinstance(encoder, ApproximateTokenEncoder)
    assert len(encoder.encode("hello world")) > 0


def test_strict_offline_can_fail_fast_when_approximate_fallback_disabled(tmp_path, monkeypatch):
    def fail_get_encoding(name):
        raise AssertionError(f"unexpected tiktoken download path for {name}")

    monkeypatch.setattr(token_handler, "get_encoding", fail_get_encoding)
    get_settings().set("CONFIG.MODEL", "ollama/Qwen3.6-35B")
    get_settings().set("TOKENIZER.LOCAL_CACHE_DIR", str(tmp_path))
    get_settings().set("TOKENIZER.ENABLE_LOCAL_CACHE", True)
    get_settings().set("TOKENIZER.FALLBACK_TO_DOWNLOAD", False)
    get_settings().set("TOKENIZER.OFFLINE_ESTIMATE_FALLBACK", False)

    TokenEncoder._encoder_instance = None
    TokenEncoder._model = None

    with pytest.raises(RuntimeError, match="Tokenizer not available in local cache"):
        TokenEncoder.get_token_encoder()
