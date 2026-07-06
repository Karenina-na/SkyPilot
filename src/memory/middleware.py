"""Long-term memory middleware and scoped demo tools."""

from collections.abc import Callable
from typing import Any

from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse
from langchain.messages import SystemMessage
from langchain.tools import ToolRuntime, tool

from src.observability.events import log_event
from src.runtime import Context


class MemoryMiddleware(AgentMiddleware):
    """Expose LangGraph store-backed memory as middleware-private tools."""

    tools: list[Any]

    def __init__(self) -> None:
        self.tools = self._build_tools()

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        """Append memory usage guidance before synchronous model calls."""
        return handler(self._request_with_memory_prompt(request))

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Any],
    ) -> ModelResponse:
        """Append memory usage guidance before asynchronous model calls."""
        return await handler(self._request_with_memory_prompt(request))

    def _request_with_memory_prompt(self, request: ModelRequest) -> ModelRequest:
        system_text = request.system_prompt or ""
        return request.override(
            system_message=SystemMessage(
                content=f"{system_text}{self._build_prompt_addendum()}"
            )
        )

    def _build_prompt_addendum(self) -> str:
        return (
            "\n\n## Long-Term Memory\n\n"
            "可以按需使用 remember_user_fact(key, value) 保存稳定的用户偏好、"
            "项目背景或后续对话仍有价值的信息；需要回忆时调用 "
            "recall_user_facts()。只保存用户明确表达或对任务持续有用的信息。"
        )

    def _build_tools(self) -> list[Any]:
        @tool
        def remember_user_fact(
            key: str,
            value: str,
            runtime: ToolRuntime[Context],
        ) -> str:
            """Remember a stable user fact in the configured LangGraph store."""
            if runtime.store is None:
                log_event(
                    "memory_disabled",
                    context=runtime.context,
                    operation="write",
                )
                return "Memory store is disabled; nothing was saved."

            normalized_key = _normalize_key(key)
            namespace = _user_memory_namespace(runtime.context)
            runtime.store.put(namespace, normalized_key, {"value": value})
            log_event(
                "memory_write",
                context=runtime.context,
                memory_key=normalized_key,
            )
            return f"Saved memory: {normalized_key}"

        @tool
        def recall_user_facts(runtime: ToolRuntime[Context]) -> str:
            """Recall saved user facts from the configured LangGraph store."""
            if runtime.store is None:
                log_event(
                    "memory_disabled",
                    context=runtime.context,
                    operation="read",
                )
                return "Memory store is disabled; no memories are available."

            namespace = _user_memory_namespace(runtime.context)
            memories = runtime.store.search(namespace, limit=20)
            log_event(
                "memory_read",
                context=runtime.context,
                memory_count=len(memories),
            )
            if not memories:
                return "No saved memories for this user."

            lines = []
            for memory in memories:
                value = memory.value.get("value", memory.value)
                lines.append(f"- {memory.key}: {value}")
            return "\n".join(lines)

        return [remember_user_fact, recall_user_facts]


def _normalize_key(key: str) -> str:
    normalized = "_".join(key.strip().lower().split())
    return normalized or "fact"


def _user_memory_namespace(context: Context) -> tuple[str, str, str]:
    return ("users", context.user_id, "memories")


def build_memory_middleware() -> MemoryMiddleware:
    """Build middleware exposing store-backed memory tools."""
    return MemoryMiddleware()


__all__ = ["MemoryMiddleware", "build_memory_middleware"]
