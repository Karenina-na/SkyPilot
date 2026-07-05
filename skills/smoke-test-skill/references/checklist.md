# Smoke Test Checklist

- The skill appears in the available skill catalog.
- `load_skill("smoke-test-skill")` returns the full `SKILL.md` content.
- `list_skill_files("smoke-test-skill")` includes this file.
- `read_skill_file("smoke-test-skill", "references/checklist.md")` returns this checklist.
