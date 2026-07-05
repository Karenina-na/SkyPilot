

from dataclasses import dataclass


@dataclass
class Context:
    """自定义运行时上下文模式。"""
    user_id: str