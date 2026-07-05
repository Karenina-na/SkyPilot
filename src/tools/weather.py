from langchain.tools import tool

from src.tools.registry import register_tool


@tool
def get_weather_for_location(city: str) -> str:
    """获取指定城市的天气。"""
    return f"{city}总是阳光明媚！"


register_tool(get_weather_for_location)
