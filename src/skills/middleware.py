"""Skill middleware construction."""

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse
from langchain.messages import SystemMessage
from langchain.tools import ToolRuntime, tool

from src.runtime import Context
from src.skills.catalog import SkillCatalog
from src.skills.loader import load_skills_from_dir
from src.skills.schema import SkillDescriptor

DEFAULT_SKILLS_ROOT = Path("skills")


class SkillMiddleware(AgentMiddleware):
    """Expose filesystem-backed skills through prompt hints and scoped tools."""

    def __init__(
        self,
        *,
        skills_root: Path = DEFAULT_SKILLS_ROOT,
        skills: Sequence[SkillDescriptor] | None = None,
    ) -> None:
        self.skills_root = skills_root
        self.skills = list(
            skills if skills is not None else load_skills_from_dir(skills_root)
        )
        self.catalog = SkillCatalog(self.skills)
        self.tools = self._build_tools()

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        """Append the skill catalog before synchronous model calls."""
        return handler(self._request_with_skill_catalog(request))

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Any],
    ) -> ModelResponse:
        """Append the skill catalog before asynchronous model calls."""
        return await handler(self._request_with_skill_catalog(request))

    def _request_with_skill_catalog(self, request: ModelRequest) -> ModelRequest:
        system_text = request.system_prompt or ""
        return request.override(
            system_message=SystemMessage(
                content=f"{system_text}{self._build_prompt_addendum()}"
            )
        )

    def _build_prompt_addendum(self) -> str:
        return (
            "\n\n## Available Skills\n\n"
            f"{self.catalog.build_prompt_catalog()}\n\n"
            "Skill 使用规则：\n"
            "- 先阅读上面的名称和描述，判断是否需要技能。\n"
            "- 需要完整说明时，调用 load_skill(skill_name)。\n"
            "- 需要附属文件时，先调用 list_skill_files(skill_name)，"
            "再调用 read_skill_file(skill_name, relative_path)。"
        )

    def _build_tools(self) -> list[Any]:
        @tool
        def load_skill(skill_name: str, runtime: ToolRuntime[Context]) -> str:
            """Load the full SKILL.md content for a registered skill."""
            return self.catalog.load_skill(skill_name, context=runtime.context)

        @tool
        def list_skill_files(skill_name: str, runtime: ToolRuntime[Context]) -> str:
            """List readable support files for a registered skill."""
            return self.catalog.list_skill_files(skill_name, context=runtime.context)

        @tool
        def read_skill_file(
            skill_name: str,
            relative_path: str,
            runtime: ToolRuntime[Context],
        ) -> str:
            """Read a support file from a registered skill directory."""
            return self.catalog.read_skill_file(
                skill_name,
                relative_path,
                context=runtime.context,
            )

        return [load_skill, list_skill_files, read_skill_file]


def build_skill_middleware(
    *,
    skills_root: Path = DEFAULT_SKILLS_ROOT,
    skills: Sequence[SkillDescriptor] | None = None,
) -> SkillMiddleware:
    """Build skill middleware from filesystem-backed skill descriptors."""
    return SkillMiddleware(skills_root=skills_root, skills=skills)


__all__ = ["DEFAULT_SKILLS_ROOT", "SkillMiddleware", "build_skill_middleware"]
