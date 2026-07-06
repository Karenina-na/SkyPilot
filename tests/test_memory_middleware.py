from langchain.agents.middleware import ModelRequest, ModelResponse
from langchain.messages import AIMessage
from langchain.tools import ToolRuntime
from langchain_openai import ChatOpenAI
from langgraph.store.memory import InMemoryStore

from src.config import LoggingSettings
from src.memory import MemoryMiddleware
from src.observability.logging import configure_logging
from src.runtime import Context


def _model():
    return ChatOpenAI(
        base_url="http://127.0.0.1:1234/v1",
        api_key="not-needed",
        model="google/gemma-4-e2b",
        profile={"max_input_tokens": 8192},
    )


def _runtime(store):
    return ToolRuntime(
        state={},
        context=Context(user_id="u1"),
        config={},
        stream_writer=lambda _: None,
        tool_call_id=None,
        store=store,
    )


def test_memory_middleware_exposes_private_memory_tools():
    middleware = MemoryMiddleware()

    assert {tool.name for tool in middleware.tools} == {
        "remember_user_fact",
        "recall_user_facts",
    }


def test_memory_middleware_prompt_mentions_memory_tools():
    middleware = MemoryMiddleware()
    captured_prompt = ""

    def handler(request: ModelRequest) -> ModelResponse:
        nonlocal captured_prompt
        captured_prompt = request.system_prompt or ""
        return ModelResponse(result=[AIMessage(content="ok")])

    request = ModelRequest(model=_model(), messages=[], system_prompt="Base prompt.")

    middleware.wrap_model_call(request, handler)

    assert "Base prompt." in captured_prompt
    assert "## Long-Term Memory" in captured_prompt
    assert "remember_user_fact(key, value)" in captured_prompt
    assert "recall_user_facts()" in captured_prompt


def test_memory_tools_write_and_read_langgraph_store():
    store = InMemoryStore()
    runtime = _runtime(store)
    middleware = MemoryMiddleware()
    tools = {tool.name: tool for tool in middleware.tools}

    saved = tools["remember_user_fact"].invoke(
        {
            "key": "Preferred Language",
            "value": "中文",
            "runtime": runtime,
        }
    )
    recalled = tools["recall_user_facts"].invoke({"runtime": runtime})

    assert saved == "Saved memory: preferred_language"
    assert "- preferred_language: 中文" in recalled


def test_memory_tools_log_write_and_read_without_memory_value(capsys):
    configure_logging(
        LoggingSettings(enabled=True, level="INFO", format="text", redact=True)
    )
    store = InMemoryStore()
    runtime = _runtime(store)
    middleware = MemoryMiddleware()
    tools = {tool.name: tool for tool in middleware.tools}

    saved = tools["remember_user_fact"].invoke(
        {
            "key": "Preferred Language",
            "value": "中文",
            "runtime": runtime,
        }
    )
    recalled = tools["recall_user_facts"].invoke({"runtime": runtime})

    captured = capsys.readouterr()
    assert saved == "Saved memory: preferred_language"
    assert "- preferred_language: 中文" in recalled
    assert "event=memory_write" in captured.err
    assert "memory_key=preferred_language" in captured.err
    assert "event=memory_read" in captured.err
    assert "memory_count=1" in captured.err
    assert "中文" not in captured.err


def test_memory_tools_handle_disabled_store():
    runtime = _runtime(None)
    middleware = MemoryMiddleware()
    tools = {tool.name: tool for tool in middleware.tools}

    saved = tools["remember_user_fact"].invoke(
        {
            "key": "preferred_language",
            "value": "中文",
            "runtime": runtime,
        }
    )
    recalled = tools["recall_user_facts"].invoke({"runtime": runtime})

    assert saved == "Memory store is disabled; nothing was saved."
    assert recalled == "Memory store is disabled; no memories are available."


def test_memory_tools_log_disabled_store_operations(capsys):
    configure_logging(
        LoggingSettings(enabled=True, level="INFO", format="text", redact=True)
    )
    runtime = _runtime(None)
    middleware = MemoryMiddleware()
    tools = {tool.name: tool for tool in middleware.tools}

    tools["remember_user_fact"].invoke(
        {
            "key": "preferred_language",
            "value": "中文",
            "runtime": runtime,
        }
    )
    tools["recall_user_facts"].invoke({"runtime": runtime})

    captured = capsys.readouterr()
    assert "event=memory_disabled" in captured.err
    assert "operation=write" in captured.err
    assert "operation=read" in captured.err
    assert "中文" not in captured.err
