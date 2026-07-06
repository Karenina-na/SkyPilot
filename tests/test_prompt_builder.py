from src.prompt import (
    CORE_PROMPT,
    DOMAIN_PROMPT,
    build_system_prompt,
    build_tool_prompt,
)
from src.prompt.build import build_system_prompt as build_system_prompt_from_module
from src.prompt.capabilities import build_tool_prompt as build_tool_prompt_from_module
from src.tools import get_tools


def test_base_prompt_layers_do_not_name_concrete_tools():
    assert "inspect_runtime_context" not in CORE_PROMPT
    assert "inspect_runtime_context" not in DOMAIN_PROMPT
    assert "create_demo_task" not in CORE_PROMPT
    assert "create_demo_task" not in DOMAIN_PROMPT


def test_tool_layer_is_generated_from_registered_tools():
    tool_prompt = build_tool_prompt(get_tools())

    assert "inspect_runtime_context" in tool_prompt
    assert "create_demo_task" in tool_prompt
    assert "Inspect the runtime context" in tool_prompt
    assert "Create a deterministic demo task ticket" in tool_prompt


def test_prompt_package_exposes_build_modules():
    assert build_system_prompt_from_module is build_system_prompt
    assert build_tool_prompt_from_module is build_tool_prompt


def test_system_prompt_combines_layers():
    system_prompt = build_system_prompt(tools=get_tools())

    assert CORE_PROMPT in system_prompt
    assert DOMAIN_PROMPT in system_prompt
    assert "inspect_runtime_context" in system_prompt
    assert "create_demo_task" in system_prompt
