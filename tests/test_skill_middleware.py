from pathlib import Path

from langchain.agents.middleware import ModelRequest, ModelResponse
from langchain.messages import AIMessage
from langchain_openai import ChatOpenAI

from src.middleware.skill import SkillMiddleware


def _model():
    return ChatOpenAI(
        base_url="http://127.0.0.1:1234/v1",
        api_key="not-needed",
        model="google/gemma-4-e2b",
        profile={"max_input_tokens": 8192},
    )


def _write_skill(root: Path) -> Path:
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
    return skill_dir


def test_skill_middleware_exposes_private_skill_tools(tmp_path: Path):
    _write_skill(tmp_path)
    middleware = SkillMiddleware(skills_root=tmp_path)

    assert {tool.name for tool in middleware.tools} == {
        "load_skill",
        "list_skill_files",
        "read_skill_file",
    }


def test_skill_middleware_prompt_contains_catalog_not_full_content(tmp_path: Path):
    _write_skill(tmp_path)
    middleware = SkillMiddleware(skills_root=tmp_path)
    captured_prompt = ""

    def handler(request: ModelRequest) -> ModelResponse:
        nonlocal captured_prompt
        captured_prompt = request.system_prompt or ""
        return ModelResponse(result=[AIMessage(content="ok")])

    request = ModelRequest(model=_model(), messages=[], system_prompt="Base prompt.")

    middleware.wrap_model_call(request, handler)

    assert "Base prompt." in captured_prompt
    assert "## Available Skills" in captured_prompt
    assert "- concise-writer: Writes concise answers" in captured_prompt
    assert "load_skill(skill_name)" in captured_prompt
    assert "Full instructions stay out of the catalog." not in captured_prompt


def test_skill_tools_delegate_to_catalog(tmp_path: Path):
    _write_skill(tmp_path)
    middleware = SkillMiddleware(skills_root=tmp_path)
    tools = {tool.name: tool for tool in middleware.tools}

    loaded = tools["load_skill"].invoke({"skill_name": "concise-writer"})
    listed = tools["list_skill_files"].invoke({"skill_name": "concise-writer"})
    read = tools["read_skill_file"].invoke(
        {"skill_name": "concise-writer", "relative_path": "references/style.md"}
    )

    assert "Loaded skill: concise-writer" in loaded
    assert listed == "references/style.md"
    assert read == "Use short sentences."


def test_skill_middleware_handles_empty_skill_root(tmp_path: Path):
    middleware = SkillMiddleware(skills_root=tmp_path / "missing")
    captured_prompt = ""

    def handler(request: ModelRequest) -> ModelResponse:
        nonlocal captured_prompt
        captured_prompt = request.system_prompt or ""
        return ModelResponse(result=[AIMessage(content="ok")])

    request = ModelRequest(model=_model(), messages=[], system_prompt="Base prompt.")

    middleware.wrap_model_call(request, handler)

    assert middleware.skills == []
    assert "当前没有已注册技能。" in captured_prompt
