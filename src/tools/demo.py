"""Task-oriented demo tools for validating agent tool calling."""

from langchain.tools import ToolRuntime, tool

from src.runtime import Context
from src.tools.registry import register_tool


@tool
def inspect_runtime_context(runtime: ToolRuntime[Context]) -> str:
    """Inspect the runtime context passed into the current tool call."""
    context = runtime.context
    return (
        "Runtime context is connected. "
        f"user_id={context.user_id} | "
        f"thread_id={context.thread_id or 'not-set'} | "
        f"locale={context.locale} | "
        f"timezone={context.timezone} | "
        f"environment={context.environment}"
    )


@tool
def create_demo_task(title: str, priority: str = "medium") -> str:
    """Create a deterministic demo task ticket from a title and priority."""
    normalized_title = " ".join(title.split()).strip()
    normalized_priority = _normalize_priority(priority)

    checksum = sum(ord(char) for char in normalized_title) % 10000
    task_id = f"DEMO-{checksum:04d}"
    return (
        f"{task_id} | priority={normalized_priority} | status=open | "
        f"title={normalized_title}"
    )


def _normalize_priority(priority: str) -> str:
    raw_priority = priority.strip().lower()
    if not raw_priority:
        return "medium"

    if raw_priority in {"high", "p1", "urgent", "高", "高优先级", "紧急"}:
        return "high"
    if raw_priority in {"low", "p3", "低", "低优先级"}:
        return "low"
    if raw_priority in {"medium", "normal", "p2", "中", "中优先级", "普通"}:
        return "medium"

    if any(token in raw_priority for token in ("high", "urgent", "高", "紧急")):
        return "high"
    if any(token in raw_priority for token in ("low", "低")):
        return "low"
    return "medium"


register_tool(inspect_runtime_context)
register_tool(create_demo_task)
