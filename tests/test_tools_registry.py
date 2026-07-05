from src.tools import get_tools


def test_get_tools_discovers_registered_tools():
    tool_names = {tool.name for tool in get_tools()}

    assert tool_names == {"get_user_location", "get_weather_for_location"}


def test_get_tools_returns_copy():
    tools = get_tools()
    tools.clear()

    assert {tool.name for tool in get_tools()} == {
        "get_user_location",
        "get_weather_for_location",
    }
