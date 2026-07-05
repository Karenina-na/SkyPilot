from pathlib import Path

from src.skills import load_skills_from_dir


def test_load_skills_from_dir_reads_skill_metadata_and_files(tmp_path: Path):
    skill_dir = tmp_path / "writer"
    (skill_dir / "references").mkdir(parents=True)
    (skill_dir / "scripts").mkdir()
    (skill_dir / "assets").mkdir()
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
    (skill_dir / "references" / "style.md").write_text("reference", encoding="utf-8")
    (skill_dir / "scripts" / "helper.py").write_text("print('ok')", encoding="utf-8")
    (skill_dir / "assets" / "palette.txt").write_text("blue", encoding="utf-8")

    skills = load_skills_from_dir(tmp_path)

    assert len(skills) == 1
    skill = skills[0]
    assert skill.name == "concise-writer"
    assert skill.description == "Writes concise answers"
    assert skill.root == skill_dir
    assert skill.skill_md == skill_dir / "SKILL.md"
    assert [path.relative_to(skill_dir).as_posix() for path in skill.files] == [
        "assets/palette.txt",
        "references/style.md",
        "scripts/helper.py",
    ]


def test_load_skills_from_dir_uses_defaults_without_frontmatter(tmp_path: Path):
    skill_dir = tmp_path / "planner"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("# Planner\n\nPlan carefully.", encoding="utf-8")

    skills = load_skills_from_dir(tmp_path)

    assert len(skills) == 1
    assert skills[0].name == "planner"
    assert skills[0].description == "No description"


def test_load_skills_from_dir_ignores_missing_or_invalid_skill_dirs(tmp_path: Path):
    (tmp_path / "not-a-skill").mkdir()
    (tmp_path / "loose.md").write_text("ignore me", encoding="utf-8")

    assert load_skills_from_dir(tmp_path) == []
    assert load_skills_from_dir(tmp_path / "missing") == []
