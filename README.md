# SkyPilot

SkyPilot is a small LangChain/LangGraph weather-agent prototype. It uses an
OpenAI-compatible local chat model, a runtime context object, LangGraph memory,
and a registry-based tool loading system.

## Project Layout

- `main.py` - local demo entrypoint.
- `src/agent.py` - builds the LangChain agent.
- `src/config/` - loads YAML configuration.
- `src/runtime.py` - defines runtime context passed into tools.
- `src/memory.py` - configures the in-memory LangGraph checkpointer.
- `src/prompt/` - builds system prompts from independent layers.
- `src/tools/` - registry-based tool package.

## Tool Registration

Business code should import tools only through:

```python
from src.tools import get_tools
```

To add a new tool:

1. Create a new module under `src/tools/`, for example `src/tools/example.py`.
2. Define a LangChain tool with `@tool`.
3. Register it with `register_tool(my_tool)`.

The package auto-discovers local tool modules when `get_tools()` is called, so
`src/agent.py` does not need to change when tools are added or removed.

## Prompt Layers

System prompts are composed from independent modules in `src/prompt/`:

- `base.py` - `CORE_PROMPT` and `DOMAIN_PROMPT`.
- `capabilities.py` - tool, skill, and MCP prompt layer rendering.
- `build.py` - final `build_system_prompt()` composition.
- `__init__.py` - stable public prompt imports.

`src/agent.py` builds the prompt with the same tool list passed into the agent:

```python
tools = get_tools()
system_prompt = build_system_prompt(tools=tools)
```

This keeps concrete tool names out of the base prompt layers while still giving
the model an up-to-date view of the tools available at runtime.

## Local Setup

This project expects Python 3.12.

```bash
python -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
```

## Configuration

Configuration is YAML-only. Start from the committed example file:

```bash
cp config.example.yaml config.yaml
```

`config.yaml` is ignored by Git so local model endpoints and API keys do not get
committed. The loader reads `config.example.yaml` as default values, then overlays
`config.yaml` when it exists. This lets new config fields get safe defaults while
keeping local overrides private.

The default example points to a local OpenAI-compatible model endpoint:

```text
http://127.0.0.1:1234/v1
```

### Summarization

Conversation summarization is configured in YAML:

```yaml
summarization:
  enabled: true
  model: "main"
  trigger:
    type: "fraction"
    value: 0.8
  keep:
    type: "messages"
    value: 20
  trim_tokens_to_summarize: 4000
```

The default `fraction: 0.8` means summarization runs when conversation history
approaches 80% of the main model context window. Because fractional triggers need
a known context window, set `llm.context_window_tokens` for the selected model.

## Run

```bash
.venv/bin/python main.py
```

## Verify

```bash
.venv/bin/python -m pytest
.venv/bin/python -c "from src.tools import get_tools; print([t.name for t in get_tools()])"
.venv/bin/python -c "from src.agent import agent; print(type(agent).__name__)"
```
