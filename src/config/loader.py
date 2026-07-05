"""YAML-backed configuration loading."""

from pathlib import Path
from typing import Any

import yaml

from src.config.schema import (
    AgentSettings,
    LLMSettings,
    Settings,
    SummarizationSettings,
    WindowClauseSettings,
)

DEFAULT_CONFIG_PATH = Path("config.yaml")
EXAMPLE_CONFIG_PATH = Path("config.example.yaml")


def load_settings(config_path: str | Path = DEFAULT_CONFIG_PATH) -> Settings:
    """Load settings from YAML, using the example file as default values."""
    path = Path(config_path)
    if path.name == DEFAULT_CONFIG_PATH.name:
        raw_config = _load_yaml(EXAMPLE_CONFIG_PATH)
        if path.exists():
            raw_config = _deep_merge(raw_config, _load_yaml(path))
    else:
        raw_config = _load_yaml(path)

    llm_config = _require_mapping(raw_config, "llm")
    agent_config = _require_mapping(raw_config, "agent")
    summarization_config = _require_mapping(raw_config, "summarization")

    return Settings(
        llm=LLMSettings(
            provider=_get_str(llm_config, "provider"),
            base_url=_get_str(llm_config, "base_url"),
            api_key=_get_str(llm_config, "api_key"),
            model=_get_str(llm_config, "model"),
            temperature=_get_float(llm_config, "temperature"),
            context_window_tokens=_get_int(llm_config, "context_window_tokens"),
        ),
        agent=AgentSettings(
            default_thread_id=_get_str(agent_config, "default_thread_id"),
        ),
        summarization=SummarizationSettings(
            enabled=_get_bool(summarization_config, "enabled"),
            model=_get_str(summarization_config, "model"),
            trigger=_get_window_clause(summarization_config, "trigger"),
            keep=_get_window_clause(summarization_config, "keep"),
            trim_tokens_to_summarize=_get_optional_int(
                summarization_config,
                "trim_tokens_to_summarize",
            ),
        ),
    )


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with path.open("r", encoding="utf-8") as config_file:
        data = yaml.safe_load(config_file) or {}

    if not isinstance(data, dict):
        raise ValueError(f"Config root must be a mapping: {path}")
    return data


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _require_mapping(config: dict[str, Any], key: str) -> dict[str, Any]:
    value = config.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"Config section '{key}' must be a mapping")
    return value


def _get_str(config: dict[str, Any], key: str) -> str:
    value = config.get(key)
    if value is None:
        raise ValueError(f"Missing required config value: {key}")
    return str(value)


def _get_float(config: dict[str, Any], key: str) -> float:
    value = config.get(key)
    if value is None:
        raise ValueError(f"Missing required config value: {key}")
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Config value '{key}' must be a float") from exc


def _get_int(config: dict[str, Any], key: str) -> int:
    value = config.get(key)
    if value is None:
        raise ValueError(f"Missing required config value: {key}")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Config value '{key}' must be an int") from exc


def _get_optional_int(config: dict[str, Any], key: str) -> int | None:
    value = config.get(key)
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Config value '{key}' must be an int") from exc


def _get_bool(config: dict[str, Any], key: str) -> bool:
    value = config.get(key)
    if value is None:
        raise ValueError(f"Missing required config value: {key}")
    if isinstance(value, bool):
        return value
    raise ValueError(f"Config value '{key}' must be a bool")


def _get_window_clause(config: dict[str, Any], key: str) -> WindowClauseSettings:
    clause_config = _require_mapping(config, key)
    clause_type = _get_str(clause_config, "type")
    if clause_type not in {"fraction", "tokens", "messages"}:
        raise ValueError(
            f"Config value '{key}.type' must be one of: fraction, tokens, messages"
        )

    if clause_type == "fraction":
        value = _get_float(clause_config, "value")
        if not 0 < value <= 1:
            raise ValueError(f"Config value '{key}.value' must be > 0 and <= 1")
        return WindowClauseSettings(type=clause_type, value=value)

    value = _get_int(clause_config, "value")
    if value <= 0:
        raise ValueError(f"Config value '{key}.value' must be > 0")
    return WindowClauseSettings(type=clause_type, value=value)
