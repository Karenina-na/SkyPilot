"""Simple interactive CLI for chatting with the configured agent."""

from __future__ import annotations

from collections.abc import Iterable

from langchain.messages import HumanMessage

from src.agent import agent, settings
from src.observability import observe_agent_stream
from src.runtime import build_default_context

EXIT_COMMANDS = {"/exit", "/quit", "exit", "quit", "q"}


def run_cli() -> None:
    """Run a simple REPL that streams agent responses."""
    thread_id = settings.agent.default_thread_id
    config = {"configurable": {"thread_id": thread_id}}
    context = build_default_context(
        user_id="local-cli",
        thread_id=thread_id,
        workspace_id="local-cli",
        metadata={"entrypoint": "main.py"},
    )

    print("SkyPilot CLI agent. Type /exit to quit.")
    while True:
        try:
            user_text = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            return

        if not user_text:
            continue
        if user_text.lower() in EXIT_COMMANDS:
            print("Bye.")
            return

        print("Agent: ", end="", flush=True)
        stream_agent_reply(user_text, config=config, context=context)
        print()


def stream_agent_reply(user_text: str, *, config: dict, context: object) -> None:
    """Stream one user turn through the agent and print assistant text."""
    agent_input = {"messages": [HumanMessage(content=user_text)]}
    for message_chunk, _metadata in observe_agent_stream(
        agent.stream(
            agent_input,
            config=config,
            context=context,
            stream_mode="messages",
        ),
        context,
        entrypoint="main.run_cli",
        stream_mode="messages",
        redact=settings.observability.logging.redact,
        full_payloads=settings.observability.logging.full_payloads,
        agent_input=agent_input,
    ):
        content = _message_text(message_chunk)
        if content:
            print(content, end="", flush=True)


def _message_text(message_chunk: object) -> str:
    content = getattr(message_chunk, "content", message_chunk)
    if isinstance(content, str):
        return content

    parts: list[str] = []
    for block in _content_blocks(message_chunk):
        if isinstance(block, dict) and block.get("type") == "text":
            parts.append(str(block.get("text", "")))

    if parts:
        return "".join(parts)

    return _chunk_text(content)


def _chunk_text(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, Iterable):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text", "")))
        return "".join(parts)
    return ""


def _reasoning_text(message_chunk: object) -> str:
    """Extract reasoning text from LangChain standard content blocks."""
    block_parts: list[str] = []
    for block in _content_blocks(message_chunk):
        if isinstance(block, dict):
            block_parts.extend(_reasoning_from_mapping(block))

    return "".join(block_parts)


def _content_blocks(message_chunk: object) -> list[object]:
    content_blocks = getattr(message_chunk, "content_blocks", None)
    if isinstance(content_blocks, list):
        return content_blocks

    content = getattr(message_chunk, "content", None)
    if isinstance(content, list):
        return content

    return []


def _has_reasoning_block(message_chunk: object) -> bool:
    return any(
        isinstance(block, dict) and block.get("type") == "reasoning"
        for block in _content_blocks(message_chunk)
    )


def _reasoning_from_mapping(mapping: dict) -> list[str]:
    if mapping.get("type") != "reasoning":
        return []

    parts: list[str] = []
    for key in ("reasoning", "text", "content", "summary", "details"):
        parts.extend(_reasoning_from_value(mapping.get(key)))

    return parts


def _reasoning_from_value(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            if isinstance(item, dict):
                parts.extend(_reasoning_from_mapping(item))
            else:
                parts.extend(_reasoning_from_value(item))
        return parts
    if isinstance(value, dict):
        return _reasoning_from_mapping(value)
    return []


if __name__ == "__main__":
    run_cli()
