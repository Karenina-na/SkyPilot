import pytest

from tests.log_helpers import logging_settings_for, read_debug_events, read_log

from src.config import FullPayloadLoggingSettings
from src.observability import observe_agent_run, observe_agent_stream
from src.observability.logging import configure_logging
from src.runtime import Context


def test_observe_agent_run_logs_start_and_end(tmp_path, capsys):
    configure_logging(logging_settings_for(tmp_path))
    context = Context(
        user_id="u1",
        thread_id="thread-1",
        request_id="request-1",
        run_id="run-1",
    )

    with observe_agent_run(
        context,
        entrypoint="test",
        stream_mode="updates",
    ):
        pass

    captured = capsys.readouterr()
    info_log = read_log(tmp_path, "INFO")
    assert captured.err == ""
    assert "event=agent_run_start" in info_log
    assert "event=agent_run_end" in info_log
    assert "entrypoint=test" in info_log
    assert "stream_mode=updates" in info_log
    assert "user_id=u1" in info_log
    assert "request_id=request-1" in info_log
    assert "run_id=run-1" in info_log
    assert "duration_ms=" in info_log


def test_observe_agent_run_logs_error_and_reraises(tmp_path, capsys):
    configure_logging(logging_settings_for(tmp_path))
    context = Context(user_id="u1", request_id="request-1", run_id="run-1")

    with pytest.raises(RuntimeError, match="request failed"):
        with observe_agent_run(
            context,
            entrypoint="test",
            stream_mode="updates",
        ):
            raise RuntimeError("request failed")

    captured = capsys.readouterr()
    info_log = read_log(tmp_path, "INFO")
    error_log = read_log(tmp_path, "ERROR")
    assert captured.err == ""
    assert "event=agent_run_start" in info_log
    assert "ERROR event=agent_run_error" in error_log
    assert "error_type=RuntimeError" in error_log
    assert "request failed" not in error_log


def test_observe_agent_stream_yields_items_and_logs_run(tmp_path, capsys):
    configure_logging(logging_settings_for(tmp_path))
    context = Context(user_id="u1", request_id="request-1", run_id="run-1")
    agent_input = {"messages": [{"role": "user", "content": "hello"}]}

    items = list(
        observe_agent_stream(
            iter(["first", "second"]),
            context,
            entrypoint="test.stream",
            stream_mode="messages",
            agent_input=agent_input,
        )
    )

    captured = capsys.readouterr()
    info_log = read_log(tmp_path, "INFO")
    debug_log = read_log(tmp_path, "DEBUG")
    debug_events = read_debug_events(tmp_path)
    assert items == ["first", "second"]
    assert captured.err == ""
    assert "event=agent_run_start" in info_log
    assert "event=agent_run_end" in info_log
    assert "entrypoint=test.stream" in info_log
    assert "stream_mode=messages" in info_log
    assert "agent_input_payload" in debug_log
    assert "agent_stream_chunk_payload" in debug_log
    assert '"content": "hello"' in debug_log
    assert '"chunk": "first"' in debug_log
    assert [event["event"] for event in debug_events] == [
        "agent_input_payload",
        "agent_stream_chunk_payload",
        "agent_stream_chunk_payload",
    ]
    assert [event["sequence"] for event in debug_events] == sorted(
        event["sequence"] for event in debug_events
    )
    assert debug_events[0]["kind"] == "agent"
    assert debug_events[0]["phase"] == "input"
    assert debug_events[0]["trace_id"] == "run-1"
    assert debug_events[0]["input"]["messages"][0]["content"] == "hello"
    assert debug_events[0]["user_messages"][0]["content"] == "hello"
    assert debug_events[1]["kind"] == "stream"
    assert debug_events[1]["phase"] == "chunk"
    assert debug_events[1]["chunk"] == "first"
    assert debug_events[2]["chunk"] == "second"


def test_observe_agent_stream_can_disable_chunk_payloads(tmp_path):
    configure_logging(logging_settings_for(tmp_path))
    context = Context(user_id="u1", request_id="request-1", run_id="run-1")

    items = list(
        observe_agent_stream(
            iter(["first"]),
            context,
            entrypoint="test.stream",
            stream_mode="messages",
            full_payloads=FullPayloadLoggingSettings(enabled=False),
        )
    )

    assert items == ["first"]
    assert read_log(tmp_path, "DEBUG") == ""
