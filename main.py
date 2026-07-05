from src.agent import agent
from src.runtime import Context


def run_demo() -> None:
    """Run a short local conversation against the configured agent."""
    # `thread_id` 是给定对话的唯一标识符。
    config = {"configurable": {"thread_id": "1"}}

    response = agent.invoke(
        {"messages": [{"role": "user", "content": "外面的天气怎么样？"}]},
        config=config,
        context=Context(user_id="1"),
    )
    print(response)

    # 注意，我们可以使用相同的 `thread_id` 继续对话。
    response = agent.invoke(
        {"messages": [{"role": "user", "content": "谢谢！"}]},
        config=config,
        context=Context(user_id="1"),
    )
    print(response)


if __name__ == "__main__":
    run_demo()
