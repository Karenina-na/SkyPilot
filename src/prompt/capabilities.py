"""Prompt layers generated from runtime capability metadata."""

from collections.abc import Iterable
from typing import Any

TOOL_USE_PROMPT = """你可以使用以下已注册工具：

{tool_descriptions}"""

SKILL_USE_PROMPT = """你可以参考以下已注册技能：

{skill_descriptions}"""

MCP_USE_PROMPT = """你可以连接以下 MCP 能力：

{mcp_descriptions}"""


def _get_name(item: Any) -> str:
    return str(getattr(item, "name", None) or getattr(item, "__name__", "unnamed"))


def _get_description(item: Any) -> str:
    description = getattr(item, "description", None) or getattr(item, "__doc__", None)
    return str(description).strip() if description else "无描述"


def _build_capability_lines(capabilities: Iterable[Any]) -> str:
    lines = []
    for capability in capabilities:
        lines.append(f"- {_get_name(capability)}：{_get_description(capability)}")
    return "\n".join(lines)


def build_tool_prompt(tools: Iterable[Any] | None = None) -> str:
    """Build the tool layer from registered tool objects."""
    tool_list = list(tools or [])
    if not tool_list:
        return "当前没有已注册工具。"
    return TOOL_USE_PROMPT.format(tool_descriptions=_build_capability_lines(tool_list))


def build_skill_prompt(skills: Iterable[Any] | None = None) -> str:
    """Build the skill layer from optional skill descriptors."""
    skill_list = list(skills or [])
    if not skill_list:
        return "当前没有已注册技能。"
    return SKILL_USE_PROMPT.format(skill_descriptions=_build_capability_lines(skill_list))


def build_mcp_prompt(mcp_servers: Iterable[Any] | None = None) -> str:
    """Build the MCP layer from optional MCP capability descriptors."""
    mcp_list = list(mcp_servers or [])
    if not mcp_list:
        return "当前没有已注册 MCP 能力。"
    return MCP_USE_PROMPT.format(mcp_descriptions=_build_capability_lines(mcp_list))
