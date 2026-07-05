"""Typed skill metadata used by the skill middleware."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SkillDescriptor:
    """Filesystem-backed skill descriptor."""

    name: str
    description: str
    root: Path
    skill_md: Path
    files: list[Path]
