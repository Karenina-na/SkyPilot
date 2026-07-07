from pathlib import Path

from src.config import load_settings


def test_load_settings_reports_invalid_logging_level(tmp_path: Path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
observability:
  logging:
    enabled: true
    level: "VERBOSE"
    format: "text"
    redact: true
""",
        encoding="utf-8",
    )

    try:
        load_settings(config_path)
    except ValueError as exc:
        assert "observability.logging.level" in str(exc)
    else:
        raise AssertionError("Expected invalid logging level to raise ValueError")


def test_load_settings_reports_invalid_logging_format(tmp_path: Path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
observability:
  logging:
    enabled: true
    level: "INFO"
    format: "xml"
    redact: true
""",
        encoding="utf-8",
    )

    try:
        load_settings(config_path)
    except ValueError as exc:
        assert "observability.logging.format" in str(exc)
    else:
        raise AssertionError("Expected invalid logging format to raise ValueError")


def test_load_settings_reads_logging_file_and_payload_options(tmp_path: Path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
observability:
  logging:
    enabled: true
    level: "INFO"
    format: "json"
    redact: true
    directory: "./custom-logs"
    full_payloads:
      enabled: false
      redact: true
      include_prompts: false
      include_messages: true
      include_tools: false
      include_outputs: true
""",
        encoding="utf-8",
    )

    settings = load_settings(config_path)

    assert settings.observability.logging.directory == "./custom-logs"
    payloads = settings.observability.logging.full_payloads
    assert payloads.enabled is False
    assert payloads.redact is True
    assert payloads.include_prompts is False
    assert payloads.include_messages is True
    assert payloads.include_tools is False
    assert payloads.include_outputs is True


def test_load_settings_reports_invalid_full_payload_option(tmp_path: Path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
observability:
  logging:
    enabled: true
    level: "INFO"
    format: "text"
    redact: true
    full_payloads:
      enabled: "yes"
""",
        encoding="utf-8",
    )

    try:
        load_settings(config_path)
    except ValueError as exc:
        assert "enabled" in str(exc)
    else:
        raise AssertionError("Expected invalid full payload option to raise ValueError")
