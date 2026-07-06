# SkyPilot

SkyPilot is a small generic LangChain/LangGraph agent demo. It uses an
OpenAI-compatible local chat model, a runtime context object, LangGraph memory,
skill middleware, and a registry-based tool loading system.

## Project Layout

- `main.py` - local demo entrypoint.
- `src/agent.py` - builds the LangChain agent.
- `src/config/` - loads YAML configuration.
- `src/runtime.py` - defines runtime context passed into tools.
- `src/memory/` - builds LangGraph checkpointers, stores, and memory middleware.
- `src/observability/` - configures structured logging and agent lifecycle events.
- `src/skills/` - loads filesystem-backed skills and exposes skill middleware.
- `src/summarization/` - builds conversation summarization middleware.
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

### Memory

Conversation memory is configured through the `memory` section:

```yaml
memory:
  checkpointer:
    type: "in_memory"
  store:
    enabled: true
    type: "in_memory"
```

The checkpointer stores same-thread graph state, including message history.
The store is LangGraph's long-term memory surface for cross-thread or
user-scoped data. The in-memory implementations are appropriate for local demos
and tests.

`src/memory/` also provides middleware-private demo memory tools:

- `remember_user_fact` - writes a stable user fact to the configured store.
- `recall_user_facts` - reads remembered facts for the runtime user.

These tools are attached through memory middleware and are not registered in the
global business tool registry.

### Observability

Structured logging is configured through the `observability` section:

```yaml
observability:
  logging:
    enabled: true
    level: "INFO"
    format: "text"
    redact: true
```

The first version uses Python's standard `logging` module. It records agent
lifecycle events such as model and tool call start, end, and error with runtime
context ids like `user_id`, `thread_id`, `request_id`, and `run_id`. Logs do not
include full prompts, full model responses, full tool arguments, memory values,
or skill file contents by default.

Runtime id semantics:

- `request_id` - one external request or CLI demo operation.
- `run_id` - one agent execution inside that request.
- `thread_id` - LangGraph conversation thread used by the checkpointer.

Core events:

| Event | Trigger | Default fields |
| --- | --- | --- |
| `agent_run_start` | Agent stream/run begins | `entrypoint`, `stream_mode`, runtime ids |
| `agent_run_end` | Agent stream/run completes | `duration_ms`, `entrypoint`, `stream_mode`, runtime ids |
| `agent_run_error` | Agent stream/run raises | `duration_ms`, `error_type`, runtime ids |
| `model_call_start` | Model call begins | `message_count`, `tool_count`, runtime ids |
| `model_call_end` | Model call completes | `duration_ms`, `message_count`, runtime ids |
| `model_call_error` | Model call raises | `duration_ms`, `error_type`, runtime ids |
| `tool_call_start` | Tool call begins | `tool_name`, `argument_keys`, runtime ids |
| `tool_call_end` | Tool call completes | `duration_ms`, `status`, `tool_name`, runtime ids |
| `tool_call_error` | Tool call raises | `duration_ms`, `error_type`, `tool_name`, runtime ids |

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
