from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_ui_safe_json_contracts_are_wired_into_workspace_surfaces() -> None:
    safe_json_source = _read("src/ui/src/lib/safe-json.ts")
    stage_surface_source = _read("src/ui/src/components/workspace/QuestStageSurface.tsx")
    lab_source = _read("src/ui/src/lib/api/lab.ts")
    tabs_source = _read("src/ui/src/lib/stores/tabs.ts")

    assert "export function safeJsonStringify" in safe_json_source
    assert "export function safeStableStringify" in safe_json_source
    assert "export function sanitizeJsonRecord" in safe_json_source
    assert "safeJsonStringify(value, 2)" in stage_surface_source
    assert "safeStableStringify(stageSelection || {})" in stage_surface_source
    assert "safeJsonStringify(value)" in lab_source
    assert "safeStableStringify(a.customData) === safeStableStringify(b.customData)" in tabs_source
    assert "sanitizeJsonRecord(tab.context.customData)" in tabs_source
