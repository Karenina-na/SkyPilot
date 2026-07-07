import json
import logging

from tests.log_helpers import log_path, logging_settings_for, read_log

from src.config import LoggingSettings
from src.observability.events import log_event
from src.observability.logging import configure_logging, sanitize_fields
from src.runtime import Context


def test_text_logging_writes_event_and_context_ids_to_file(tmp_path, capsys):
    configure_logging(logging_settings_for(tmp_path))
    context = Context(
        user_id="u1",
        thread_id="thread-1",
        request_id="request-1",
        run_id="run-1",
        workspace_id="workspace-1",
    )

    log_event("model_call_start", context=context, message_count=2)

    captured = capsys.readouterr()
    logged = read_log(tmp_path, "INFO")
    assert captured.err == ""
    assert "INFO event=model_call_start" in logged
    assert "user_id=u1" in logged
    assert "thread_id=thread-1" in logged
    assert "request_id=request-1" in logged
    assert "run_id=run-1" in logged
    assert "message_count=2" in logged


def test_json_logging_writes_parseable_json_to_file(tmp_path, capsys):
    configure_logging(logging_settings_for(tmp_path, format="json"))

    log_event("tool_call_end", context=Context(user_id="u1"), tool_name="demo")

    captured = capsys.readouterr()
    payload = json.loads(read_log(tmp_path, "INFO"))
    assert captured.err == ""
    assert payload["event"] == "tool_call_end"
    assert payload["level"] == "INFO"
    assert payload["user_id"] == "u1"
    assert payload["tool_name"] == "demo"


def test_logging_splits_records_by_exact_level(tmp_path):
    configure_logging(logging_settings_for(tmp_path))

    log_event("info_event", level=logging.INFO)
    log_event("error_event", level=logging.ERROR)

    info_log = read_log(tmp_path, "INFO")
    error_log = read_log(tmp_path, "ERROR")
    assert "event=info_event" in info_log
    assert "event=error_event" not in info_log
    assert "ERROR event=error_event" in error_log
    assert "event=info_event" not in error_log


def test_full_payload_logging_creates_debug_json_file(tmp_path):
    configure_logging(logging_settings_for(tmp_path))

    log_event("regular_event", level=logging.INFO)

    assert log_path(tmp_path, "DEBUG").exists()


def test_sensitive_fields_are_redacted():
    fields = sanitize_fields(
        {
            "api_key": "secret-key",
            "nested": {"authorization": "Bearer secret"},
            "safe": "visible",
        },
        redact=True,
    )

    assert fields["api_key"] == "[REDACTED]"
    assert fields["nested"]["authorization"] == "[REDACTED]"
    assert fields["safe"] == "visible"


def test_disabled_logging_suppresses_events(capsys):
    configure_logging(
        LoggingSettings(enabled=False, level="INFO", format="text", redact=True)
    )

    log_event("model_call_start", level=logging.INFO)

    captured = capsys.readouterr()
    assert captured.err == ""
