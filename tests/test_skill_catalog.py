from pathlib import Path

from src.skills.catalog import SkillCatalog
from src.skills.loader import load_skills_from_dir


def _write_skill(root: Path) -> None:
    skill_dir = root / "writer"
    (skill_dir / "references").mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        """---
name: concise-writer
description: Writes concise answers
---

# Concise Writer

Full instructions stay out of the catalog.
""",
        encoding="utf-8",
    )
    (skill_dir / "references" / "style.md").write_text(
        "Use short sentences.",
        encoding="utf-8",
    )


def test_skill_catalog_builds_prompt_catalog(tmp_path: Path):
    _write_skill(tmp_path)
    catalog = SkillCatalog(load_skills_from_dir(tmp_path))

    assert catalog.build_prompt_catalog() == "- concise-writer: Writes concise answers"


def test_skill_catalog_loads_lists_and_reads_skill_files(tmp_path: Path):
    _write_skill(tmp_path)
    catalog = SkillCatalog(load_skills_from_dir(tmp_path))

    loaded = catalog.load_skill("concise-writer")
    listed = catalog.list_skill_files("concise-writer")
    file_text = catalog.read_skill_file("concise-writer", "references/style.md")

    assert "Loaded skill: concise-writer" in loaded
    assert "Full instructions stay out of the catalog." in loaded
    assert listed == "references/style.md"
    assert file_text == "Use short sentences."


def test_skill_catalog_rejects_path_escape(tmp_path: Path):
    _write_skill(tmp_path)
    catalog = SkillCatalog(load_skills_from_dir(tmp_path))

    result = catalog.read_skill_file("concise-writer", "../secret.txt")

    assert "path must stay inside the skill directory" in result


def test_skill_catalog_reports_missing_skill_and_empty_catalog():
    catalog = SkillCatalog([])

    assert catalog.build_prompt_catalog() == "当前没有已注册技能。"
    assert catalog.load_skill("missing") == (
        "Skill 'missing' not found. No skills are registered."
    )
