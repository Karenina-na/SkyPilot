from langchain_core.messages import AIMessageChunk

from main import _has_reasoning_block, _message_text, _reasoning_text


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
