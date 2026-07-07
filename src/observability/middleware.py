"""Agent middleware for structured observability events."""

from __future__ import annotations

import logging
from collections.abc import Callable
from itertools import count
from time import perf_counter
from typing import Any

from langchain.agents.middleware import (
    AgentMiddleware,
    ModelRequest,
    ModelResponse,
    ToolCallRequest,
)

from src.config import FullPayloadLoggingSettings
from src.observability.events import log_event
from src.observability.logging import log_full_payload, serialize_for_json
from src.runtime import Context


class ObservabilityMiddleware(AgentMiddleware):
    """Record model-call lifecycle events without exposing message content."""

    tools: list[Any] = []

    def __init__(
        self,
        *,
        redact: bool = True,
        full_payloads: FullPayloadLoggingSettings | None = None,
    ) -> None:
        self.redact = redact
        self.full_payloads = full_payloads or FullPayloadLoggingSettings()
        self._model_call_ids = count(1)

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        """Record synchronous model-call lifecycle events."""
        context = _request_context(request)
        call_id = self._next_model_call_id(context)
        started_at = perf_counter()
        log_event(
            "model_call_start",
            context=context,
            redact=self.redact,
            message_count=len(request.messages),
            tool_count=len(request.tools),
        )
        self._log_model_request_payload(request, context, call_id)

        try:
            response = handler(request)
        except Exception as exc:
            self._log_model_error_payload(request, context, exc, call_id)
            log_event(
                "model_call_error",
                context=context,
                level=logging.ERROR,
                redact=self.redact,
                duration_ms=_duration_ms(started_at),
                error_type=type(exc).__name__,
            )
            raise

        log_event(
            "model_call_end",
            context=context,
            redact=self.redact,
            duration_ms=_duration_ms(started_at),
            message_count=len(response.result),
        )
        self._log_model_response_payload(response, context, call_id)
        return response

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Any],
    ) -> ModelResponse:
        """Record asynchronous model-call lifecycle events."""
        context = _request_context(request)
        call_id = self._next_model_call_id(context)
        started_at = perf_counter()
        log_event(
            "model_call_start",
            context=context,
            redact=self.redact,
            message_count=len(request.messages),
            tool_count=len(request.tools),
        )
        self._log_model_request_payload(request, context, call_id)

        try:
            response = await handler(request)
        except Exception as exc:
            self._log_model_error_payload(request, context, exc, call_id)
            log_event(
                "model_call_error",
                context=context,
                level=logging.ERROR,
                redact=self.redact,
                duration_ms=_duration_ms(started_at),
                error_type=type(exc).__name__,
            )
            raise

        log_event(
            "model_call_end",
            context=context,
            redact=self.redact,
            duration_ms=_duration_ms(started_at),
            message_count=len(response.result),
        )
        self._log_model_response_payload(response, context, call_id)
        return response

    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Any],
    ) -> Any:
        """Record synchronous tool-call lifecycle events."""
        context = _tool_request_context(request)
        started_at = perf_counter()
        tool_name = _tool_name(request)
        argument_keys = _tool_argument_keys(request)
        log_event(
            "tool_call_start",
            context=context,
            redact=self.redact,
            tool_name=tool_name,
            argument_keys=argument_keys,
        )
        self._log_tool_request_payload(request, context, tool_name)

        try:
            response = handler(request)
        except Exception as exc:
            self._log_tool_error_payload(request, context, tool_name, exc)
            log_event(
                "tool_call_error",
                context=context,
                level=logging.ERROR,
                redact=self.redact,
                tool_name=tool_name,
                argument_keys=argument_keys,
                duration_ms=_duration_ms(started_at),
                error_type=type(exc).__name__,
            )
            raise

        log_event(
            "tool_call_end",
            context=context,
            redact=self.redact,
            tool_name=tool_name,
            argument_keys=argument_keys,
            duration_ms=_duration_ms(started_at),
            status=getattr(response, "status", "success"),
        )
        self._log_tool_response_payload(response, context, tool_name)
        return response

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Any],
    ) -> Any:
        """Record asynchronous tool-call lifecycle events."""
        context = _tool_request_context(request)
        started_at = perf_counter()
        tool_name = _tool_name(request)
        argument_keys = _tool_argument_keys(request)
        log_event(
            "tool_call_start",
            context=context,
            redact=self.redact,
            tool_name=tool_name,
            argument_keys=argument_keys,
        )
        self._log_tool_request_payload(request, context, tool_name)

        try:
            response = await handler(request)
        except Exception as exc:
            self._log_tool_error_payload(request, context, tool_name, exc)
            log_event(
                "tool_call_error",
                context=context,
                level=logging.ERROR,
                redact=self.redact,
                tool_name=tool_name,
                argument_keys=argument_keys,
                duration_ms=_duration_ms(started_at),
                error_type=type(exc).__name__,
            )
            raise

        log_event(
            "tool_call_end",
            context=context,
            redact=self.redact,
            tool_name=tool_name,
            argument_keys=argument_keys,
            duration_ms=_duration_ms(started_at),
            status=getattr(response, "status", "success"),
        )
        self._log_tool_response_payload(response, context, tool_name)
        return response

    def _log_model_request_payload(
        self,
        request: ModelRequest,
        context: Context | None,
        call_id: str,
    ) -> None:
        payload: dict[str, Any] = {
            "model": _model_payload(request.model),
        }
        if self.full_payloads.include_prompts:
            payload["system_prompt"] = request.system_prompt
        if self.full_payloads.include_messages:
            payload["messages"] = request.messages
        if self.full_payloads.include_tools:
            payload["tools"] = [_tool_payload(tool) for tool in request.tools]

        log_full_payload(
            "model_call_request_payload",
            payload,
            context=context,
            settings=self.full_payloads,
            kind="model",
            phase="request",
            call_id=call_id,
        )

    def _log_model_response_payload(
        self,
        response: ModelResponse,
        context: Context | None,
        call_id: str,
    ) -> None:
        if not self.full_payloads.include_outputs:
            return

        log_full_payload(
            "model_call_response_payload",
            {"result": response.result},
            context=context,
            settings=self.full_payloads,
            kind="model",
            phase="response",
            call_id=call_id,
        )

    def _log_model_error_payload(
        self,
        request: ModelRequest,
        context: Context | None,
        exc: Exception,
        call_id: str,
    ) -> None:
        if not self.full_payloads.include_outputs:
            return

        log_full_payload(
            "model_call_error_payload",
            {
                "messages": request.messages,
                "system_prompt": request.system_prompt,
                "error_type": type(exc).__name__,
                "error_message": str(exc),
            },
            context=context,
            settings=self.full_payloads,
            kind="model",
            phase="error",
            call_id=call_id,
        )

    def _log_tool_request_payload(
        self,
        request: ToolCallRequest,
        context: Context | None,
        tool_name: str,
    ) -> None:
        payload: dict[str, Any] = {"tool_name": tool_name}
        if self.full_payloads.include_tools:
            payload["tool"] = _tool_payload(request.tool)
        if self.full_payloads.include_messages:
            payload["tool_call"] = request.tool_call

        log_full_payload(
            "tool_call_request_payload",
            payload,
            context=context,
            settings=self.full_payloads,
            kind="tool",
            phase="request",
            call_id=_tool_call_id(request),
        )

    def _log_tool_response_payload(
        self,
        response: Any,
        context: Context | None,
        tool_name: str,
    ) -> None:
        if not self.full_payloads.include_outputs:
            return

        log_full_payload(
            "tool_call_response_payload",
            {
                "tool_name": tool_name,
                "response": response,
            },
            context=context,
            settings=self.full_payloads,
            kind="tool",
            phase="response",
            call_id=_response_tool_call_id(response) or tool_name,
        )

    def _next_model_call_id(self, context: Context | None) -> str:
        prefix = _trace_call_prefix(context)
        return f"{prefix}:model:{next(self._model_call_ids)}"

    def _log_tool_error_payload(
        self,
        request: ToolCallRequest,
        context: Context | None,
        tool_name: str,
        exc: Exception,
    ) -> None:
        if not self.full_payloads.include_outputs:
            return

        log_full_payload(
            "tool_call_error_payload",
            {
                "tool_name": tool_name,
                "tool_call": request.tool_call,
                "error_type": type(exc).__name__,
                "error_message": str(exc),
            },
            context=context,
            settings=self.full_payloads,
            kind="tool",
            phase="error",
            call_id=_tool_call_id(request),
        )


def build_observability_middleware(
    *,
    redact: bool = True,
    full_payloads: FullPayloadLoggingSettings | None = None,
) -> ObservabilityMiddleware:
    """Build middleware that emits structured model lifecycle events."""
    middleware = ObservabilityMiddleware(redact=redact, full_payloads=full_payloads)
    log_event("agent_middleware_attached", redact=redact, middleware="observability")
    return middleware


def _request_context(request: ModelRequest) -> Context | None:
    runtime = getattr(request, "runtime", None)
    context = getattr(runtime, "context", None)
    return context if isinstance(context, Context) else None


def _tool_request_context(request: ToolCallRequest) -> Context | None:
    context = getattr(request.runtime, "context", None)
    return context if isinstance(context, Context) else None


def _tool_name(request: ToolCallRequest) -> str:
    if request.tool is not None:
        return request.tool.name

    name = request.tool_call.get("name")
    return str(name or "unknown_tool")


def _tool_argument_keys(request: ToolCallRequest) -> list[str]:
    args = request.tool_call.get("args")
    if not isinstance(args, dict):
        return []
    return sorted(str(key) for key in args)


def _trace_call_prefix(context: Context | None) -> str:
    if context is None:
        return "unknown-trace"
    return context.run_id or context.request_id or context.thread_id or context.user_id


def _tool_call_id(request: ToolCallRequest) -> str:
    return str(request.tool_call.get("id") or _tool_name(request))


def _response_tool_call_id(response: Any) -> str | None:
    tool_call_id = getattr(response, "tool_call_id", None)
    return str(tool_call_id) if tool_call_id else None


def _model_payload(model: Any) -> dict[str, Any]:
    payload = {
        "type": type(model).__name__,
        "repr": repr(model),
    }
    for attr in ("model", "model_name", "base_url", "temperature"):
        if hasattr(model, attr):
            payload[attr] = getattr(model, attr)
    return serialize_for_json(payload)


def _tool_payload(tool_obj: Any) -> dict[str, Any] | None:
    if tool_obj is None:
        return None

    payload = {
        "type": type(tool_obj).__name__,
        "name": getattr(tool_obj, "name", None),
        "description": getattr(tool_obj, "description", None),
        "args_schema": getattr(tool_obj, "args_schema", None),
    }
    return serialize_for_json(payload)


def _duration_ms(started_at: float) -> int:
    return round((perf_counter() - started_at) * 1000)


__all__ = ["ObservabilityMiddleware", "build_observability_middleware"]
