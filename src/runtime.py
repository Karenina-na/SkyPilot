"""Runtime context shared across one agent invocation."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Context:
    """Request-scoped context available to tools and middleware."""

    user_id: str
    thread_id: str | None = None
    tenant_id: str | None = None
    workspace_id: str | None = None
    locale: str = "zh-CN"
    timezone: str = "Asia/Shanghai"
    environment: str = "local"
    permissions: tuple[str, ...] = ()
    metadata: dict[str, str] = field(default_factory=dict)


def build_default_context(
    *,
    user_id: str,
    thread_id: str | None = None,
    tenant_id: str | None = None,
    workspace_id: str | None = None,
    locale: str = "zh-CN",
    timezone: str = "Asia/Shanghai",
    environment: str = "local",
    permissions: tuple[str, ...] = (),
    metadata: dict[str, str] | None = None,
) -> Context:
    """Build the default runtime context used by local demos and tests."""
    return Context(
        user_id=user_id,
        thread_id=thread_id,
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        locale=locale,
        timezone=timezone,
        environment=environment,
        permissions=permissions,
        metadata=metadata or {},
    )


__all__ = ["Context", "build_default_context"]
