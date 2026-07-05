from langchain.agents.middleware import SummarizationMiddleware
from langchain_openai import ChatOpenAI

from src.config.schema import SummarizationSettings, WindowClauseSettings
from src.middleware import build_summarization_middleware


def _main_model():
    return ChatOpenAI(
        base_url="http://127.0.0.1:1234/v1",
        api_key="not-needed",
        model="google/gemma-4-e2b",
        profile={"max_input_tokens": 8192},
    )


def test_build_summarization_middleware_returns_empty_when_disabled():
    settings = SummarizationSettings(
        enabled=False,
        model="main",
        trigger=WindowClauseSettings(type="fraction", value=0.8),
        keep=WindowClauseSettings(type="messages", value=20),
        trim_tokens_to_summarize=4000,
    )

    assert build_summarization_middleware(settings, _main_model()) == []


def test_build_summarization_middleware_uses_fraction_trigger_with_main_model():
    main_model = _main_model()
    settings = SummarizationSettings(
        enabled=True,
        model="main",
        trigger=WindowClauseSettings(type="fraction", value=0.8),
        keep=WindowClauseSettings(type="messages", value=20),
        trim_tokens_to_summarize=4000,
    )

    middleware = build_summarization_middleware(settings, main_model)

    assert len(middleware) == 1
    assert isinstance(middleware[0], SummarizationMiddleware)
    assert middleware[0].model is main_model
    assert middleware[0].trigger == ("fraction", 0.8)
    assert middleware[0].keep == ("messages", 20)
    assert middleware[0].trim_tokens_to_summarize == 4000
