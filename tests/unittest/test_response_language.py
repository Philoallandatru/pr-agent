import tomllib
from pathlib import Path

from pr_agent.algo.utils import apply_response_language_instruction, get_response_language_instruction
from pr_agent.config_loader import get_settings


def test_default_response_language_is_zh_cn():
    config_path = Path(__file__).parents[2] / "pr_agent" / "settings" / "configuration.toml"
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))

    assert config["config"]["response_language"] == "zh-CN"


def test_response_language_instruction_maps_zh_cn_to_simplified_chinese():
    instruction = get_response_language_instruction("zh-CN")

    assert "Simplified Chinese" in instruction
    assert "natural-language output" in instruction
    assert "YAML keys" in instruction


def test_apply_response_language_instruction_is_idempotent():
    settings = get_settings()
    original_language = settings.config.get("response_language")
    original_extra = settings.pr_reviewer.extra_instructions

    try:
        settings.set("config.response_language", "zh-CN")
        settings.set("pr_reviewer.extra_instructions", "")

        apply_response_language_instruction(target_sections=["pr_reviewer"])
        first_extra = settings.pr_reviewer.extra_instructions
        apply_response_language_instruction(target_sections=["pr_reviewer"])

        assert "Simplified Chinese" in first_extra
        assert settings.pr_reviewer.extra_instructions == first_extra
    finally:
        settings.set("config.response_language", original_language)
        settings.set("pr_reviewer.extra_instructions", original_extra)


def test_apply_response_language_instruction_skips_english():
    settings = get_settings()
    original_language = settings.config.get("response_language")
    original_extra = settings.pr_reviewer.extra_instructions

    try:
        settings.set("config.response_language", "en-US")
        settings.set("pr_reviewer.extra_instructions", "")

        apply_response_language_instruction(target_sections=["pr_reviewer"])

        assert settings.pr_reviewer.extra_instructions == ""
    finally:
        settings.set("config.response_language", original_language)
        settings.set("pr_reviewer.extra_instructions", original_extra)
