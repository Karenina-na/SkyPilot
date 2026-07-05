from langchain.agents.middleware import SummarizationMiddleware

from src.agent import middleware
from src.middleware.skill import SkillMiddleware


def test_agent_middleware_is_flat_and_includes_skills():
    assert len(middleware) == 2
    assert isinstance(middleware[0], SummarizationMiddleware)
    assert isinstance(middleware[1], SkillMiddleware)
    assert all(not isinstance(item, list) for item in middleware)
