"""Middleware package public interface."""

from src.middleware.summary import build_summarization_middleware

__all__ = ["build_summarization_middleware"]
