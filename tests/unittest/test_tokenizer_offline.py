from __future__ import annotations

import json
from pathlib import Path

from pr_agent.algo import token_handler
from pr_agent.algo.token_handler import TokenEncoder
from pr_agent.config_loader import get_settings


def _reset_encoder_state():
    TokenEncoder._encoder_instance = None
    TokenEncoder._model = None
    TokenEncoder._using_fallback = False


def test_tokenizer_offline_cache_miss_falls_back_to_estimation(tmp_path):
    cache_dir = tmp_path / "tokenizer-cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    original_model = get_settings().get("config.model")
    original_cache = get_settings().get("tokenizer.cache_dir", "")
    original_offline = get_settings().get("tokenizer.offline_only", False)
    original_fallback = get_settings().get("tokenizer.fallback_to_estimation", True)

    try:
        _reset_encoder_state()
        get_settings().set("config.model", "gpt-5.4")
        get_settings().set("tokenizer.cache_dir", str(cache_dir))
        get_settings().set("tokenizer.offline_only", True)
        get_settings().set("tokenizer.fallback_to_estimation", True)

        encoder = TokenEncoder.get_token_encoder()
        tokens = encoder.encode("def charge(amount): return amount")
        assert isinstance(tokens, list)
        assert len(tokens) > 0
    finally:
        _reset_encoder_state()
        get_settings().set("config.model", original_model)
        get_settings().set("tokenizer.cache_dir", original_cache)
        get_settings().set("tokenizer.offline_only", original_offline)
        get_settings().set("tokenizer.fallback_to_estimation", original_fallback)


def test_tokenizer_offline_cache_hit_uses_real_encoder(tmp_path, monkeypatch):
    cache_dir = tmp_path / "tokenizer-cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    # Simulate pre-warmed cache manifest expected by the offline guard.
    (Path(cache_dir) / "manifest.json").write_text(
        json.dumps({"encodings": ["cl100k_base", "o200k_base"]}),
        encoding="utf-8",
    )

    class FakeEncoder:
        @staticmethod
        def encode(text, disallowed_special=()):  # noqa: ARG004
            return [1, 2, 3]

    def fake_encoding_for_model(model_name):
        assert model_name == "gpt-5.4"
        return FakeEncoder()

    original_model = get_settings().get("config.model")
    original_cache = get_settings().get("tokenizer.cache_dir", "")
    original_offline = get_settings().get("tokenizer.offline_only", False)
    original_fallback = get_settings().get("tokenizer.fallback_to_estimation", True)

    try:
        _reset_encoder_state()
        get_settings().set("config.model", "gpt-5.4")
        get_settings().set("tokenizer.cache_dir", str(cache_dir))
        get_settings().set("tokenizer.offline_only", True)
        get_settings().set("tokenizer.fallback_to_estimation", True)
        monkeypatch.setattr(token_handler, "encoding_for_model", fake_encoding_for_model)

        encoder = TokenEncoder.get_token_encoder()
        assert encoder.encode("anything") == [1, 2, 3]
    finally:
        _reset_encoder_state()
        get_settings().set("config.model", original_model)
        get_settings().set("tokenizer.cache_dir", original_cache)
        get_settings().set("tokenizer.offline_only", original_offline)
        get_settings().set("tokenizer.fallback_to_estimation", original_fallback)
