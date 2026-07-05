"""Compose system prompts from independent prompt layers."""

from collections.abc import Iterable
from typing import Any

from src.prompt.base import CORE_PROMPT, DOMAIN_PROMPT
from src.prompt.capabilities import (
    build_mcp_prompt,
    build_skill_prompt,
    build_tool_prompt,
)


def build_system_prompt(
    *,
    tools: Iterable[Any] | None = None,
    skills: Iterable[Any] | None = None,
    mcp_servers: Iterable[Any] | None = None,
) -> str:
    """Compose the final system prompt from independent layers."""
    layers = [
        CORE_PROMPT,
        DOMAIN_PROMPT,
        build_tool_prompt(tools),
        build_skill_prompt(skills),
        build_mcp_prompt(mcp_servers),
    ]
    return "\n\n".join(layer for layer in layers if layer)


SYSTEM_PROMPT = build_system_prompt()
