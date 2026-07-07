from langchain_core.messages import AIMessageChunk, HumanMessage

from src.runtime import build_default_context

from main import (
    _has_reasoning_block,
    _message_text,
    _reasoning_text,
    run_cli,
    run_agent_reply,
)


def test_reasoning_text_reads_standard_content_blocks():
    chunk = AIMessageChunk(
        content=[
            {"type": "reasoning", "reasoning": "先检查工具。"},
            {"type": "text", "text": "demo 可以验证工具调用。"},
        ],
        response_metadata={"model_provider": "openai"},
    )

    assert _reasoning_text(chunk) == "先检查工具。"
    assert _has_reasoning_block(chunk)
    assert _message_text(chunk) == "demo 可以验证工具调用。"


def test_reasoning_text_reads_summary_blocks():
    chunk = AIMessageChunk(
        content=[
            {
                "type": "reasoning",
                "summary": [{"type": "summary_text", "text": "归纳步骤。"}],
            },
            {"type": "text", "text": "demo 可以验证流式输出。"},
        ],
        response_metadata={"model_provider": "openai"},
    )

    assert _reasoning_text(chunk) == "归纳步骤。"
    assert _has_reasoning_block(chunk)
    assert _message_text(chunk) == "demo 可以验证流式输出。"


def test_reasoning_block_can_exist_without_exposed_text():
    chunk = AIMessageChunk(
        content=[
            {
                "type": "reasoning",
                "extras": {"content": [], "status": "in_progress"},
            },
            {"type": "text", "text": "demo 可以验证流式输出。"},
        ],
        response_metadata={"model_provider": "openai"},
    )

    assert _has_reasoning_block(chunk)
    assert _reasoning_text(chunk) == ""
    assert _message_text(chunk) == "demo 可以验证流式输出。"


def test_run_cli_exits_on_exit_command(monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda _: "/exit")

    run_cli()

    captured = capsys.readouterr()
    assert "SkyPilot CLI agent. Type /exit to quit." in captured.out
    assert "Bye." in captured.out


def test_run_cli_skips_blank_input_then_runs_reply(monkeypatch, capsys):
    inputs = iter(["", "hello", "q"])
    replies: list[str] = []

    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    monkeypatch.setattr(
        "main.run_agent_reply",
        lambda user_text, *, config, context: replies.append(user_text),
    )

    run_cli()

    captured = capsys.readouterr()
    assert replies == ["hello"]
    assert "Agent: " in captured.out
    assert "Bye." in captured.out


def test_run_agent_reply_uses_invoke_instead_of_stream(monkeypatch, capsys):
    calls: list[tuple[str, dict]] = []

    class FakeAgent:
        def invoke(self, agent_input, *, config, context):
            calls.append(("invoke", agent_input))
            return {"messages": [AIMessageChunk(content="非流式回复")]}

        def stream(self, *args, **kwargs):
            raise AssertionError("stream should not be used")

    monkeypatch.setattr("main.agent", FakeAgent())

    run_agent_reply(
        "你好",
        config={"configurable": {"thread_id": "1"}},
        context=build_default_context(user_id="test-user"),
    )

    captured = capsys.readouterr()
    assert calls == [("invoke", {"messages": [HumanMessage(content="你好")]})]
    assert "非流式回复" in captured.out
