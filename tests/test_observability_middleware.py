import logging
from types import SimpleNamespace

import pytest
from langchain.agents.middleware import ModelRequest, ModelResponse, ToolCallRequest
from langchain.messages import AIMessage, ToolMessage
from langchain.tools import ToolRuntime, tool
from langchain_openai import ChatOpenAI

from tests.log_helpers import logging_settings_for, read_debug_events, read_log

from src.config import FullPayloadLoggingSettings
from src.observability import ObservabilityMiddleware
from src.observability.logging import configure_logging
from src.runtime import Context


def _model():
    return ChatOpenAI(
        base_url="http://127.0.0.1:1234/v1",
        api_key="not-needed",
        model="google/gemma-4-e2b",
        profile={"max_input_tokens": 8192},
    )


def _request() -> ModelRequest:
    return ModelRequest(
        model=_model(),
        messages=[],
        system_prompt="Base prompt.",
        runtime=SimpleNamespace(
            context=Context(
                user_id="u1",
                thread_id="thread-1",
                request_id="request-1",
                run_id="run-1",
            )
        ),
    )


@tool
def demo_tool(title: str, api_key: str = "secret") -> str:
    """Demo tool used for observability middleware tests."""
    return f"created {title}"


def _tool_request() -> ToolCallRequest:
    return ToolCallRequest(
        tool_call={
            "id": "call-1",
            "name": "demo_tool",
            "args": {"title": "task", "api_key": "secret"},
        },
        tool=demo_tool,
        state={},
        runtime=ToolRuntime(
            state={},
            context=Context(
                user_id="u1",
                thread_id="thread-1",
                request_id="request-1",
                run_id="run-1",
            ),
            config={},
            stream_writer=lambda _: None,
            tool_call_id="call-1",
            store=None,
        ),
    )


def test_observability_middleware_does_not_expose_tools():
    middleware = ObservabilityMiddleware()

    assert middleware.tools == []


def test_observability_middleware_logs_successful_model_call(tmp_path, capsys):
    configure_logging(logging_settings_for(tmp_path))
    middleware = ObservabilityMiddleware()

    def handler(request: ModelRequest) -> ModelResponse:
        return ModelResponse(result=[AIMessage(content="ok")])

    response = middleware.wrap_model_call(_request(), handler)

    captured = capsys.readouterr()
    info_log = read_log(tmp_path, "INFO")
    debug_events = read_debug_events(tmp_path)
    assert response.result[0].content == "ok"
    assert captured.err == ""
    assert "event=model_call_start" in info_log
    assert "event=model_call_end" in info_log
    assert "user_id=u1" in info_log
    assert "duration_ms=" in info_log
    request_payload = next(
        event for event in debug_events if event["event"] == "model_call_request_payload"
    )
    response_payload = next(
        event for event in debug_events if event["event"] == "model_call_response_payload"
    )
    assert request_payload["system_prompt"] == "Base prompt."
    assert request_payload["debug_payload"] is True
    assert request_payload["trace_schema_version"] == "2026-07-07"
    assert request_payload["trace_id"] == "run-1"
    assert request_payload["kind"] == "model"
    assert request_payload["phase"] == "request"
    assert request_payload["call_id"] == response_payload["call_id"]
    assert request_payload["sequence"] < response_payload["sequence"]
    assert response_payload["kind"] == "model"
    assert response_payload["phase"] == "response"
    assert response_payload["result"][0]["content"] == "ok"


def test_observability_middleware_logs_error_and_reraises(tmp_path, capsys):
    configure_logging(logging_settings_for(tmp_path))
    middleware = ObservabilityMiddleware()

    def handler(request: ModelRequest) -> ModelResponse:
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        middleware.wrap_model_call(_request(), handler)

    captured = capsys.readouterr()
    info_log = read_log(tmp_path, "INFO")
    error_log = read_log(tmp_path, "ERROR")
    debug_log = read_log(tmp_path, "DEBUG")
    assert captured.err == ""
    assert "event=model_call_start" in info_log
    assert "ERROR event=model_call_error" in error_log
    assert "error_type=RuntimeError" in error_log
    assert "boom" not in error_log
    assert "model_call_error_payload" in debug_log
    assert "boom" in debug_log


def test_observability_middleware_logs_successful_tool_call(tmp_path, capsys):
    configure_logging(logging_settings_for(tmp_path))
    middleware = ObservabilityMiddleware()

    def handler(request: ToolCallRequest) -> ToolMessage:
        return ToolMessage(
            content="ok",
            name="demo_tool",
            tool_call_id=request.tool_call["id"],
        )

    response = middleware.wrap_tool_call(_tool_request(), handler)

    captured = capsys.readouterr()
    info_log = read_log(tmp_path, "INFO")
    debug_events = read_debug_events(tmp_path)
    assert response.content == "ok"
    assert captured.err == ""
    assert "event=tool_call_start" in info_log
    assert "event=tool_call_end" in info_log
    assert "tool_name=demo_tool" in info_log
    assert "argument_keys=['api_key', 'title']" in info_log
    assert "duration_ms=" in info_log
    assert "secret" not in info_log
    assert "task" not in info_log
    request_payload = next(
        event for event in debug_events if event["event"] == "tool_call_request_payload"
    )
    response_payload = next(
        event for event in debug_events if event["event"] == "tool_call_response_payload"
    )
    assert request_payload["trace_id"] == "run-1"
    assert request_payload["kind"] == "tool"
    assert request_payload["phase"] == "request"
    assert request_payload["call_id"] == "call-1"
    assert response_payload["kind"] == "tool"
    assert response_payload["phase"] == "response"
    assert response_payload["call_id"] == "call-1"
    assert request_payload["sequence"] < response_payload["sequence"]
    assert request_payload["tool_call"]["args"]["title"] == "task"
    assert request_payload["tool_call"]["args"]["api_key"] == "secret"
    assert response_payload["response"]["content"] == "ok"


def test_observability_middleware_preserves_multistep_sequence_order(tmp_path):
    configure_logging(logging_settings_for(tmp_path))
    middleware = ObservabilityMiddleware()

    def handler(request: ModelRequest) -> ModelResponse:
        return ModelResponse(result=[AIMessage(content="ok")])

    middleware.wrap_model_call(_request(), handler)
    middleware.wrap_tool_call(
        _tool_request(),
        lambda request: ToolMessage(
            content="tool-ok",
            name="demo_tool",
            tool_call_id=request.tool_call["id"],
        ),
    )
    middleware.wrap_model_call(_request(), handler)

    events = read_debug_events(tmp_path)
    replay = [
        (event["kind"], event["phase"], event["call_id"], event["sequence"])
        for event in events
    ]

    assert [item[:2] for item in replay] == [
        ("model", "request"),
        ("model", "response"),
        ("tool", "request"),
        ("tool", "response"),
        ("model", "request"),
        ("model", "response"),
    ]
    assert [item[3] for item in replay] == sorted(item[3] for item in replay)
    assert replay[0][2] == replay[1][2]
    assert replay[2][2] == replay[3][2] == "call-1"
    assert replay[4][2] == replay[5][2]
    assert replay[0][2] != replay[4][2]


def test_observability_middleware_logs_tool_error_and_reraises(tmp_path, capsys):
    configure_logging(logging_settings_for(tmp_path))
    middleware = ObservabilityMiddleware()

    def handler(request: ToolCallRequest) -> ToolMessage:
        raise RuntimeError("tool exploded")

    with pytest.raises(RuntimeError, match="tool exploded"):
        middleware.wrap_tool_call(_tool_request(), handler)

    captured = capsys.readouterr()
    info_log = read_log(tmp_path, "INFO")
    error_log = read_log(tmp_path, "ERROR")
    debug_log = read_log(tmp_path, "DEBUG")
    assert captured.err == ""
    assert "event=tool_call_start" in info_log
    assert "ERROR event=tool_call_error" in error_log
    assert "tool_name=demo_tool" in error_log
    assert "error_type=RuntimeError" in error_log
    assert "tool exploded" not in error_log
    assert "tool_call_error_payload" in debug_log
    assert "tool exploded" in debug_log


def test_observability_middleware_can_disable_full_payload_logging(tmp_path):
    configure_logging(logging_settings_for(tmp_path))
    middleware = ObservabilityMiddleware(
        full_payloads=FullPayloadLoggingSettings(enabled=False)
    )

    def handler(request: ModelRequest) -> ModelResponse:
        return ModelResponse(result=[AIMessage(content="ok")])

    middleware.wrap_model_call(_request(), handler)

    assert read_log(tmp_path, "DEBUG") == ""
