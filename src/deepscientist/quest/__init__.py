from __future__ import annotations

from typing import TYPE_CHECKING, Any

__all__ = ["QuestService"]

if TYPE_CHECKING:
    from .service import QuestService


def __getattr__(name: str) -> Any:
    if name == "QuestService":
        from .service import QuestService

        return QuestService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
