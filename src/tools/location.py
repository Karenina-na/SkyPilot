from langchain.tools import ToolRuntime, tool

from src.runtime import Context
from src.tools.registry import register_tool


@tool
def get_user_location(runtime: ToolRuntime[Context]) -> str:
    """根据用户 ID 获取用户信息。"""
    user_id = runtime.context.user_id
    return "Florida" if user_id == "1" else "SF"


register_tool(get_user_location)
