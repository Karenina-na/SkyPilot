"""Summarization middleware construction."""

from typing import Any

from langchain.agents.middleware import SummarizationMiddleware

from src.config import SummarizationSettings


def build_summarization_middleware(
    settings: SummarizationSettings,
    main_model: Any,
) -> list[SummarizationMiddleware]:
    """Build summarization middleware from typed settings."""
    if not settings.enabled:
        return []

    summary_model = main_model if settings.model == "main" else settings.model

    return [
        SummarizationMiddleware(
            model=summary_model,
            trigger=(settings.trigger.type, settings.trigger.value),
            keep=(settings.keep.type, settings.keep.value),
            trim_tokens_to_summarize=settings.trim_tokens_to_summarize,
        )
    ]
