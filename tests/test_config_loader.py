from pathlib import Path

from src.config import load_settings


def test_load_settings_reads_yaml_config(tmp_path: Path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
llm:
  provider: openai_compatible
  base_url: "http://localhost:9999/v1"
  api_key: "test-key"
  model: "test-model"
  temperature: 0.7
  context_window_tokens: 12345

agent:
  default_thread_id: "test-thread"

summarization:
  enabled: true
  model: "main"
  trigger:
    type: "fraction"
    value: 0.8
  keep:
    type: "messages"
    value: 20
  trim_tokens_to_summarize: 4000
""",
        encoding="utf-8",
    )

    settings = load_settings(config_path)

    assert settings.llm.provider == "openai_compatible"
    assert settings.llm.base_url == "http://localhost:9999/v1"
    assert settings.llm.api_key == "test-key"
    assert settings.llm.model == "test-model"
    assert settings.llm.temperature == 0.7
    assert settings.llm.context_window_tokens == 12345
    assert settings.agent.default_thread_id == "test-thread"
    assert settings.summarization.enabled is True
    assert settings.summarization.model == "main"
    assert settings.summarization.trigger.type == "fraction"
    assert settings.summarization.trigger.value == 0.8
    assert settings.summarization.keep.type == "messages"
    assert settings.summarization.keep.value == 20
    assert settings.summarization.trim_tokens_to_summarize == 4000


def test_load_settings_falls_back_to_example_config():
    settings = load_settings()

    assert settings.llm.base_url == "http://127.0.0.1:1234/v1"
    assert settings.llm.api_key == "not-needed"
    assert settings.llm.model == "google/gemma-4-e2b"
    assert settings.llm.temperature == 0.3
    assert settings.llm.context_window_tokens == 8192
    assert settings.agent.default_thread_id == "1"
    assert settings.summarization.enabled is True
    assert settings.summarization.trigger.type == "fraction"
    assert settings.summarization.trigger.value == 0.8


def test_load_settings_merges_default_config_with_local_overrides(tmp_path: Path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
llm:
  model: "override-model"
  temperature: 0.9
""",
        encoding="utf-8",
    )

    settings = load_settings(config_path)

    assert settings.llm.model == "override-model"
    assert settings.llm.temperature == 0.9
    assert settings.llm.context_window_tokens == 8192
    assert settings.summarization.trigger.type == "fraction"
    assert settings.summarization.trigger.value == 0.8


def test_load_settings_reports_missing_required_values(tmp_path: Path):
    config_path = tmp_path / "broken.yaml"
    config_path.write_text(
        """
llm:
  provider: openai_compatible
  base_url: "http://localhost:9999/v1"
  api_key: "test-key"
  temperature: 0.7
  context_window_tokens: 12345

agent:
  default_thread_id: "test-thread"

summarization:
  enabled: true
  model: "main"
  trigger:
    type: "fraction"
    value: 0.8
  keep:
    type: "messages"
    value: 20
  trim_tokens_to_summarize: 4000
""",
        encoding="utf-8",
    )

    try:
        load_settings(config_path)
    except ValueError as exc:
        assert "Missing required config value: model" in str(exc)
    else:
        raise AssertionError("Expected missing model config to raise ValueError")


def test_load_settings_reports_invalid_fraction_trigger(tmp_path: Path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
llm:
  provider: openai_compatible
  base_url: "http://localhost:9999/v1"
  api_key: "test-key"
  model: "test-model"
  temperature: 0.7
  context_window_tokens: 12345

agent:
  default_thread_id: "test-thread"

summarization:
  enabled: true
  model: "main"
  trigger:
    type: "fraction"
    value: 1.5
  keep:
    type: "messages"
    value: 20
  trim_tokens_to_summarize: 4000
""",
        encoding="utf-8",
    )

    try:
        load_settings(config_path)
    except ValueError as exc:
        assert "trigger.value" in str(exc)
    else:
        raise AssertionError("Expected invalid fraction trigger to raise ValueError")
