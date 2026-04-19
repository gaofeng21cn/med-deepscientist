from __future__ import annotations

import builtins
import importlib
import sys


def test_runtime_storage_import_does_not_require_optional_websocket_dependency(monkeypatch) -> None:
    sys.modules.pop("deepscientist.runtime_storage", None)
    sys.modules.pop("deepscientist.quest", None)
    sys.modules.pop("deepscientist.quest.service", None)

    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "websockets" or name.startswith("websockets."):
            raise ModuleNotFoundError("No module named 'websockets'")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    module = importlib.import_module("deepscientist.runtime_storage")

    assert callable(module.maintain_quest_runtime_storage)
