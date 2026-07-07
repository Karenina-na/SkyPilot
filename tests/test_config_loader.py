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

memory:
  checkpointer:
    type: "in_memory"
  store:
    enabled: true
    type: "in_memory"

observability:
  logging:
    enabled: true
    level: "DEBUG"
    format: "json"
    redact: false

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
    assert settings.memory.checkpointer.type == "in_memory"
    assert settings.memory.store.enabled is True
    assert settings.memory.store.type == "in_memory"
    assert settings.observability.logging.enabled is True
    assert settings.observability.logging.level == "DEBUG"
    assert settings.observability.logging.format == "json"
    assert settings.observability.logging.redact is False
    assert settings.observability.logging.directory == "./logs"
    assert settings.observability.logging.full_payloads.enabled is True
    assert settings.observability.logging.full_payloads.redact is False
    assert settings.observability.logging.full_payloads.include_prompts is True
    assert settings.observability.logging.full_payloads.include_messages is True
    assert settings.observability.logging.full_payloads.include_tools is True
    assert settings.observability.logging.full_payloads.include_outputs is True


def test_load_settings_falls_back_to_example_config():
    settings = load_settings()

    assert settings.llm.base_url == "http://127.0.0.1:1234/v1"
    assert settings.llm.api_key == "not-needed"
    assert settings.llm.model == "qwen3.5-4b-mlx"
    assert settings.llm.temperature == 0.3
    assert settings.llm.context_window_tokens == 8192
    assert settings.agent.default_thread_id == "1"
    assert settings.memory.checkpointer.type == "in_memory"
    assert settings.memory.store.enabled is True
    assert settings.memory.store.type == "in_memory"
    assert settings.observability.logging.enabled is True
    assert settings.observability.logging.level == "INFO"
    assert settings.observability.logging.format == "text"
    assert settings.observability.logging.redact is True
    assert settings.observability.logging.directory == "./logs"
    assert settings.observability.logging.full_payloads.enabled is True
    assert settings.observability.logging.full_payloads.redact is False
    assert settings.observability.logging.full_payloads.include_prompts is True
    assert settings.observability.logging.full_payloads.include_messages is True
    assert settings.observability.logging.full_payloads.include_tools is True
    assert settings.observability.logging.full_payloads.include_outputs is True
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
    assert settings.memory.checkpointer.type == "in_memory"
    assert settings.memory.store.enabled is True
    assert settings.memory.store.type == "in_memory"
    assert settings.observability.logging.level == "INFO"
    assert settings.observability.logging.directory == "./logs"
    assert settings.observability.logging.full_payloads.enabled is True
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

memory:
  checkpointer:
    type: "in_memory"
  store:
    enabled: true
    type: "in_memory"

observability:
  logging:
    enabled: true
    level: "INFO"
    format: "text"
    redact: true

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


def test_load_settings_reports_invalid_memory_checkpointer_type(tmp_path: Path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
memory:
  checkpointer:
    type: "sqlite"
  store:
    enabled: true
    type: "in_memory"
""",
        encoding="utf-8",
    )

    try:
        load_settings(config_path)
    except ValueError as exc:
        assert "memory.checkpointer.type" in str(exc)
    else:
        raise AssertionError(
            "Expected invalid memory checkpointer type to raise ValueError"
        )


def test_load_settings_reports_invalid_memory_store_type(tmp_path: Path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
memory:
  checkpointer:
    type: "in_memory"
  store:
    enabled: true
    type: "sqlite"
""",
        encoding="utf-8",
    )

    try:
        load_settings(config_path)
    except ValueError as exc:
        assert "memory.store.type" in str(exc)
    else:
        raise AssertionError("Expected invalid memory store type to raise ValueError")
