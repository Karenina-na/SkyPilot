"""Filesystem skill discovery."""

from pathlib import Path
from typing import Any

import yaml

from src.skills.schema import SkillDescriptor

DEFAULT_SKILL_DESCRIPTION = "No description"
SKILL_FILE_NAME = "SKILL.md"
SKILL_ASSET_DIRS = ("scripts", "references", "assets")


def load_skills_from_dir(skills_root_dir: Path) -> list[SkillDescriptor]:
    """Load filesystem-backed skills from a root directory."""
    root = skills_root_dir.expanduser()
    if not root.exists() or not root.is_dir():
        return []

    skills: list[SkillDescriptor] = []
    for skill_dir in sorted(root.iterdir()):
        if not skill_dir.is_dir():
            continue

        skill_md = skill_dir / SKILL_FILE_NAME
        if not skill_md.is_file():
            continue

        text = skill_md.read_text(encoding="utf-8")
        metadata = _parse_frontmatter(text)
        name = str(metadata.get("name") or skill_dir.name)
        description = str(metadata.get("description") or DEFAULT_SKILL_DESCRIPTION)

        skills.append(
            SkillDescriptor(
                name=name,
                description=description,
                root=skill_dir,
                skill_md=skill_md,
                files=_discover_skill_files(skill_dir),
            )
        )

    return skills


def _parse_frontmatter(text: str) -> dict[str, Any]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}

    try:
        end_idx = next(
            idx for idx, line in enumerate(lines[1:], start=1) if line.strip() == "---"
        )
    except StopIteration:
        return {}

    raw_metadata = yaml.safe_load("\n".join(lines[1:end_idx])) or {}
    return raw_metadata if isinstance(raw_metadata, dict) else {}


def _discover_skill_files(skill_dir: Path) -> list[Path]:
    files: list[Path] = []
    for dirname in SKILL_ASSET_DIRS:
        asset_dir = skill_dir / dirname
        if not asset_dir.is_dir():
            continue
        files.extend(path for path in asset_dir.rglob("*") if path.is_file())
    return sorted(files)


__all__ = ["load_skills_from_dir"]
