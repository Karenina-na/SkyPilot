"""Console demo for validating agent streaming and tool calls."""

from collections.abc import Iterable

from langchain.messages import HumanMessage

from src.agent import agent
from src.observability import observe_agent_stream
from src.runtime import build_default_context

THREAD_CONFIG = {"configurable": {"thread_id": "demo-thread"}}
DEMO_CONTEXT = build_default_context(
    user_id="1",
    thread_id="demo-thread",
    request_id="demo-request",
    run_id="demo-run",
    workspace_id="local-demo",
    metadata={"entrypoint": "main.py"},
)


def run_demo() -> None:
    """Run concise streaming demos against the configured agent."""
    show_tool_call_updates()
    print()
    show_message_stream()


def show_tool_call_updates() -> None:
    """Show agent/tool execution steps without dumping full graph state."""
    print("=== Agent 执行过程 ===\n")

    for chunk in observe_agent_stream(
        agent.stream(
            {
                "messages": [
                    HumanMessage(
                        content=(
                            "请先检查 runtime context 是否能传入工具，"
                            "再调用 create_demo_task 创建任务："
                            "title='验证 agent 可以发现并调用工具'，priority='high'。"
                        )
                    )
                ]
            },
            config=THREAD_CONFIG,
            context=DEMO_CONTEXT,
            stream_mode="updates",
        ),
        DEMO_CONTEXT,
        entrypoint="main.show_tool_call_updates",
        stream_mode="updates",
    ):
        print_update_chunk(chunk)


def print_update_chunk(chunk: dict) -> None:
    """Print a compact view of update-mode stream chunks."""
    if not isinstance(chunk, dict):
        return

    for node_name, update in chunk.items():
        if not isinstance(update, dict):
            continue

        for message in update.get("messages") or []:
            if message.type == "ai" and getattr(message, "tool_calls", None):
                tool_names = [tool_call["name"] for tool_call in message.tool_calls]
                print(f"[{node_name}] 请求调用: {', '.join(tool_names)}")
            elif message.type == "tool":
                print(f"[{node_name}] 工具返回 [{message.name}]: {message.content}")
            elif message.type == "ai" and message.content:
                print(f"[{node_name}] 回复: {_preview(message.content)}")


def show_message_stream() -> None:
    """Show a short token stream, optional reasoning, and source metadata."""
    print("=== 实时流式回复 ===\n")

    first_metadata: dict | None = None
    first_chunk_type: str | None = None
    answer_started = False
    reasoning_started = False
    saw_reasoning = False
    saw_reasoning_block = False
    for message_chunk, metadata in observe_agent_stream(
        agent.stream(
            {
                "messages": [
                    HumanMessage(content="用一句话说明这个 agent demo 能验证什么。")
                ]
            },
            config=THREAD_CONFIG,
            context=DEMO_CONTEXT,
            stream_mode="messages",
        ),
        DEMO_CONTEXT,
        entrypoint="main.show_message_stream",
        stream_mode="messages",
    ):
        saw_reasoning_block = saw_reasoning_block or _has_reasoning_block(
            message_chunk
        )
        reasoning = _reasoning_text(message_chunk)
        if reasoning:
            if not reasoning_started:
                print("思考流（provider 暴露时显示）:")
                reasoning_started = True
            print(reasoning, end="", flush=True)
            saw_reasoning = True

        content = _message_text(message_chunk)
        if not content:
            continue

        if not answer_started:
            if saw_reasoning:
                print("\n")
            elif saw_reasoning_block:
                print(
                    "思考流（LangChain content_blocks 暴露时显示）: "
                    "检测到 reasoning block，但 LangChain 未暴露 reasoning 文本。\n"
                )
            else:
                print(
                    "思考流（LangChain content_blocks 暴露时显示）: "
                    "当前没有 reasoning。\n"
                )
            print("回复:")
            answer_started = True

        print(content, end="", flush=True)

        if first_metadata is None:
            first_metadata = metadata
            first_chunk_type = type(message_chunk).__name__

    print()
    if first_metadata is not None:
        print(
            f"\n来源节点: {first_metadata.get('langgraph_node')}\n"
            f"消息类型: {first_chunk_type}"
        )


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


def _preview(content: object, limit: int = 120) -> str:
    text = _message_text(content)
    return text if len(text) <= limit else f"{text[: limit - 3]}..."


if __name__ == "__main__":
    run_demo()
