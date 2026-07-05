"""Prompt package public interface."""

from src.prompt.base import CORE_PROMPT, DOMAIN_PROMPT
from src.prompt.build import SYSTEM_PROMPT, build_system_prompt
from src.prompt.capabilities import (
    MCP_USE_PROMPT,
    SKILL_USE_PROMPT,
    TOOL_USE_PROMPT,
    build_mcp_prompt,
    build_skill_prompt,
    build_tool_prompt,
)

__all__ = [
    "CORE_PROMPT",
    "DOMAIN_PROMPT",
    "MCP_USE_PROMPT",
    "SKILL_USE_PROMPT",
    "SYSTEM_PROMPT",
    "TOOL_USE_PROMPT",
    "build_mcp_prompt",
    "build_skill_prompt",
    "build_system_prompt",
    "build_tool_prompt",
]
