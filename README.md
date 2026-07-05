# SkyPilot

SkyPilot is a small LangChain/LangGraph weather-agent prototype. It uses an
OpenAI-compatible local chat model, a runtime context object, LangGraph memory,
and a registry-based tool loading system.

## Project Layout

- `main.py` - local demo entrypoint.
- `src/agent.py` - builds the LangChain agent.
- `src/runtime.py` - defines runtime context passed into tools.
- `src/memory.py` - configures the in-memory LangGraph checkpointer.
- `src/prompt.py` - stores the system prompt.
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

## Local Setup

This project expects Python 3.12.

```bash
python -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
```

The agent currently points to a local OpenAI-compatible model endpoint:

```text
http://127.0.0.1:1234/v1
```

You can override the default model settings in `.env` and wire them into
`src/agent.py` later if needed.

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
