import pytest

from src.config import LoggingSettings
from src.observability import observe_agent_run, observe_agent_stream
from src.observability.logging import configure_logging
from src.runtime import Context


def test_observe_agent_run_logs_start_and_end(capsys):
    configure_logging(
        LoggingSettings(enabled=True, level="INFO", format="text", redact=True)
    )
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
    assert "event=agent_run_start" in captured.err
    assert "event=agent_run_end" in captured.err
    assert "entrypoint=test" in captured.err
    assert "stream_mode=updates" in captured.err
    assert "user_id=u1" in captured.err
    assert "request_id=request-1" in captured.err
    assert "run_id=run-1" in captured.err
    assert "duration_ms=" in captured.err


def test_observe_agent_run_logs_error_and_reraises(capsys):
    configure_logging(
        LoggingSettings(enabled=True, level="INFO", format="text", redact=True)
    )
    context = Context(user_id="u1", request_id="request-1", run_id="run-1")

    with pytest.raises(RuntimeError, match="request failed"):
        with observe_agent_run(
            context,
            entrypoint="test",
            stream_mode="updates",
        ):
            raise RuntimeError("request failed")

    captured = capsys.readouterr()
    assert "event=agent_run_start" in captured.err
    assert "ERROR event=agent_run_error" in captured.err
    assert "error_type=RuntimeError" in captured.err
    assert "request failed" not in captured.err


def test_observe_agent_stream_yields_items_and_logs_run(capsys):
    configure_logging(
        LoggingSettings(enabled=True, level="INFO", format="text", redact=True)
    )
    context = Context(user_id="u1", request_id="request-1", run_id="run-1")

    items = list(
        observe_agent_stream(
            iter(["first", "second"]),
            context,
            entrypoint="test.stream",
            stream_mode="messages",
        )
    )

    captured = capsys.readouterr()
    assert items == ["first", "second"]
    assert "event=agent_run_start" in captured.err
    assert "event=agent_run_end" in captured.err
    assert "entrypoint=test.stream" in captured.err
    assert "stream_mode=messages" in captured.err
