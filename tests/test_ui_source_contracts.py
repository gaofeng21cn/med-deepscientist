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


def test_deepxiv_setup_dialog_uses_live_draft_for_test_and_save() -> None:
    dialog_source = _read("src/ui/src/components/settings/DeepXivSetupDialog.tsx")

    assert "const nextStructuredDraft = mergeDraft(document, draft)" in dialog_source
    assert "const result = await client.deepxivTest(nextStructuredDraft)" in dialog_source
    assert "structured: nextStructuredDraft" in dialog_source
    assert "setDocument((current) =>" in dialog_source
    assert "structured_config: nextStructuredDraft" in dialog_source


def test_quest_settings_surface_routes_control_mode_through_startup_context() -> None:
    surface_source = _read("src/ui/src/components/workspace/QuestSettingsSurface.tsx")
    api_source = _read("src/ui/src/lib/api.ts")
    messages_source = _read("src/ui/src/lib/i18n/messages/workspace.ts")

    assert "type ControlMode = 'copilot' | 'autonomous'" in surface_source
    assert "client.updateQuestStartupContext" in surface_source
    assert "control_mode: controlMode" in surface_source
    assert "quest_settings_mode_title" in messages_source
    assert "quest_settings_mode_save" in messages_source
    assert "quest_settings_mode_saved_desc_copilot" in messages_source
    assert "quest_settings_mode_saved_desc_autonomous" in messages_source
    assert "updateQuestStartupContext" in api_source
    assert "`/api/quests/${questId}/startup-context`" in api_source or "/api/quests/${questId}/startup-context" in api_source
