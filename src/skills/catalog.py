"""Runtime access to loaded skill descriptors and files."""

from collections.abc import Sequence
from pathlib import Path

from src.observability.events import log_event
from src.runtime import Context
from src.skills.schema import SkillDescriptor


class SkillCatalog:
    """Lookup and file access facade for loaded skills."""

    def __init__(self, skills: Sequence[SkillDescriptor]) -> None:
        self.skills = list(skills)
        self._skills_by_name = {skill.name: skill for skill in self.skills}

    def build_prompt_catalog(self) -> str:
        """Build the compact skill list shown in the system prompt."""
        if not self.skills:
            return "当前没有已注册技能。"

        return "\n".join(
            f"- {skill.name}: {skill.description}" for skill in self.skills
        )

    def load_skill(self, skill_name: str, context: Context | None = None) -> str:
        """Load the full SKILL.md content for a registered skill."""
        skill = self._skills_by_name.get(skill_name)
        if skill is None:
            self._log_skill_lookup_failed(skill_name, context)
            return self._skill_not_found_message(skill_name)

        content = skill.skill_md.read_text(encoding="utf-8")
        log_event("skill_loaded", context=context, skill_name=skill.name)
        return f"Loaded skill: {skill.name}\n\n{content}"

    def list_skill_files(self, skill_name: str, context: Context | None = None) -> str:
        """List readable support files for a registered skill."""
        skill = self._skills_by_name.get(skill_name)
        if skill is None:
            self._log_skill_lookup_failed(skill_name, context)
            return self._skill_not_found_message(skill_name)

        log_event(
            "skill_file_listed",
            context=context,
            skill_name=skill.name,
            file_count=len(skill.files),
        )
        if not skill.files:
            return f"Skill '{skill_name}' has no support files."

        relative_files = [path.relative_to(skill.root).as_posix() for path in skill.files]
        return "\n".join(relative_files)

    def read_skill_file(
        self,
        skill_name: str,
        relative_path: str,
        context: Context | None = None,
    ) -> str:
        """Read a support file while staying inside the skill directory."""
        skill = self._skills_by_name.get(skill_name)
        if skill is None:
            self._log_skill_lookup_failed(skill_name, context)
            return self._skill_not_found_message(skill_name)

        requested_path = (skill.root / relative_path).resolve()
        skill_root = skill.root.resolve()
        if not requested_path.is_relative_to(skill_root):
            log_event(
                "skill_file_rejected",
                context=context,
                skill_name=skill.name,
                relative_path=relative_path,
                reason="path_escape",
            )
            return "Invalid skill file path: path must stay inside the skill directory."

        if not requested_path.is_file():
            log_event(
                "skill_file_rejected",
                context=context,
                skill_name=skill.name,
                relative_path=relative_path,
                reason="file_not_found",
            )
            return f"Skill file not found: {relative_path}"

        log_event(
            "skill_file_read",
            context=context,
            skill_name=skill.name,
            relative_path=relative_path,
        )
        return requested_path.read_text(encoding="utf-8")

    def _skill_not_found_message(self, skill_name: str) -> str:
        if not self.skills:
            return f"Skill '{skill_name}' not found. No skills are registered."

        available = ", ".join(skill.name for skill in self.skills)
        return f"Skill '{skill_name}' not found. Available skills: {available}"

    def _log_skill_lookup_failed(
        self,
        skill_name: str,
        context: Context | None,
    ) -> None:
        log_event("skill_lookup_failed", context=context, skill_name=skill_name)


__all__ = ["SkillCatalog"]
