"""Registry for LangChain tools used by the agent."""

from typing import Any

_TOOLS: list[Any] = []


def register_tool(tool_obj: Any) -> Any:
    """Register a tool and return it for decorator-friendly usage."""
    _TOOLS.append(tool_obj)
    return tool_obj


def get_tools() -> list[Any]:
    """Return a shallow copy of the registered tools."""
    return list(_TOOLS)


def clear_tools_for_test() -> None:
    """Clear registered tools for tests that need isolated state."""
    _TOOLS.clear()
