"""Event helpers for structured agent observability."""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable, Iterator
from contextlib import contextmanager
from time import perf_counter
from typing import Any

from src.config import FullPayloadLoggingSettings
from src.observability.logging import get_logger, log_full_payload, sanitize_fields
from src.runtime import Context


def log_event(
    event: str,
    *,
    context: Context | None = None,
    level: int = logging.INFO,
    redact: bool = True,
    **fields: Any,
) -> None:
    """Log a structured observability event."""
    event_fields = _context_fields(context)
    event_fields.update(fields)
    event_fields = sanitize_fields(event_fields, redact=redact)

    get_logger().log(
        level,
        event,
        extra={
            "event": event,
            "fields": event_fields,
        },
    )


@contextmanager
def observe_agent_run(
    context: Context,
    *,
    entrypoint: str,
    stream_mode: str,
    redact: bool = True,
) -> Iterator[None]:
    """Log start/end/error events around one agent run."""
    started_at = perf_counter()
    log_event(
        "agent_run_start",
        context=context,
        redact=redact,
        entrypoint=entrypoint,
        stream_mode=stream_mode,
    )

    try:
        yield
    except Exception as exc:
        log_event(
            "agent_run_error",
            context=context,
            level=logging.ERROR,
            redact=redact,
            entrypoint=entrypoint,
            stream_mode=stream_mode,
            duration_ms=_duration_ms(started_at),
            error_type=type(exc).__name__,
        )
        raise

    log_event(
        "agent_run_end",
        context=context,
        redact=redact,
        entrypoint=entrypoint,
        stream_mode=stream_mode,
        duration_ms=_duration_ms(started_at),
    )


def observe_agent_stream(
    stream: Iterable[Any],
    context: Context,
    *,
    entrypoint: str,
    stream_mode: str,
    redact: bool = True,
    full_payloads: FullPayloadLoggingSettings | None = None,
    agent_input: Any | None = None,
) -> Iterator[Any]:
    """Yield an agent stream while logging run lifecycle events."""
    with observe_agent_run(
        context,
        entrypoint=entrypoint,
        stream_mode=stream_mode,
        redact=redact,
    ):
        if agent_input is not None:
            log_full_payload(
                "agent_input_payload",
                {
                    "entrypoint": entrypoint,
                    "stream_mode": stream_mode,
                    "input": agent_input,
                    "user_messages": _user_messages(agent_input),
                },
                context=context,
                settings=full_payloads,
                kind="agent",
                phase="input",
                call_id=f"{entrypoint}:{stream_mode}:input",
            )

        for index, item in enumerate(stream):
            log_full_payload(
                "agent_stream_chunk_payload",
                {
                    "entrypoint": entrypoint,
                    "stream_mode": stream_mode,
                    "chunk_index": index,
                    "chunk": item,
                },
                context=context,
                settings=full_payloads,
                kind="stream",
                phase="chunk",
                call_id=f"{entrypoint}:{stream_mode}:chunk:{index}",
            )
            yield item


def observe_agent_invoke(
    invoke: Callable[[], Any],
    context: Context,
    *,
    entrypoint: str,
    execution_mode: str,
    redact: bool = True,
    full_payloads: FullPayloadLoggingSettings | None = None,
    agent_input: Any | None = None,
) -> Any:
    """Run an agent invocation while logging lifecycle and full payloads."""
    with observe_agent_run(
        context,
        entrypoint=entrypoint,
        stream_mode=execution_mode,
        redact=redact,
    ):
        if agent_input is not None:
            log_full_payload(
                "agent_input_payload",
                {
                    "entrypoint": entrypoint,
                    "execution_mode": execution_mode,
                    "input": agent_input,
                    "user_messages": _user_messages(agent_input),
                },
                context=context,
                settings=full_payloads,
                kind="agent",
                phase="input",
                call_id=f"{entrypoint}:{execution_mode}:input",
            )

        result = invoke()
        log_full_payload(
            "agent_invoke_result_payload",
            {
                "entrypoint": entrypoint,
                "execution_mode": execution_mode,
                "result": result,
            },
            context=context,
            settings=full_payloads,
            kind="agent",
            phase="result",
            call_id=f"{entrypoint}:{execution_mode}:result",
        )
        return result


def _user_messages(agent_input: Any) -> list[Any]:
    if not isinstance(agent_input, dict):
        return []

    messages = agent_input.get("messages")
    if not isinstance(messages, list):
        return []

    return [
        message
        for message in messages
        if getattr(message, "type", None) == "human"
        or getattr(message, "role", None) == "user"
        or (
            isinstance(message, dict)
            and message.get("role") in {"user", "human"}
        )
    ]


def _context_fields(context: Context | None) -> dict[str, Any]:
    if context is None:
        return {}

    return {
        "user_id": context.user_id,
        "thread_id": context.thread_id,
        "tenant_id": context.tenant_id,
        "workspace_id": context.workspace_id,
        "request_id": context.request_id,
        "run_id": context.run_id,
        "environment": context.environment,
    }


def _duration_ms(started_at: float) -> int:
    return round((perf_counter() - started_at) * 1000)


__all__ = [
    "log_event",
    "observe_agent_invoke",
    "observe_agent_run",
    "observe_agent_stream",
]
