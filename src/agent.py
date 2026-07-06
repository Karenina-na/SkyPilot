from pathlib import Path

from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

from src.config import load_settings
from src.memory import build_checkpointer, build_memory_middleware, build_store
from src.prompt import build_system_prompt
from src.runtime import Context
from src.skills import build_skill_middleware
from src.summarization import build_summarization_middleware
from src.tools import get_tools

settings = load_settings()

model = ChatOpenAI(
    base_url=settings.llm.base_url,
    api_key=settings.llm.api_key,
    model=settings.llm.model,
    temperature=settings.llm.temperature,
    output_version="responses/v1",
    use_responses_api=True,
    profile={"max_input_tokens": settings.llm.context_window_tokens},
)

tools = get_tools()
checkpointer = build_checkpointer(settings.memory.checkpointer)
store = build_store(settings.memory.store)
middleware = [
    *build_summarization_middleware(
        settings=settings.summarization,
        main_model=model,
    ),
    build_skill_middleware(skills_root=Path("skills")),
    build_memory_middleware(),
]

agent = create_agent(
    model=model,
    system_prompt=build_system_prompt(tools=tools),
    tools=tools,
    context_schema=Context,
    middleware=middleware,
    checkpointer=checkpointer,
    store=store,
)
