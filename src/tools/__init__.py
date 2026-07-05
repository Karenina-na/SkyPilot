"""Tool package public interface.

Importing from this package gives business code a stable way to load all
registered tools without depending on individual tool modules.
"""

from importlib import import_module
from pkgutil import iter_modules

from src.tools.registry import clear_tools_for_test, get_tools as _get_registered_tools
from src.tools.registry import register_tool

_DISCOVERED = False
_SKIPPED_MODULES = {"registry", "tools"}


def _discover_tools() -> None:
    """Import local tool modules once so they can register themselves."""
    global _DISCOVERED
    if _DISCOVERED:
        return

    for module_info in iter_modules(__path__):
        module_name = module_info.name
        if module_name.startswith("_") or module_name in _SKIPPED_MODULES:
            continue
        import_module(f"{__name__}.{module_name}")

    _DISCOVERED = True


def get_tools():
    """Return all registered LangChain tools."""
    _discover_tools()
    return _get_registered_tools()


__all__ = ["clear_tools_for_test", "get_tools", "register_tool"]
