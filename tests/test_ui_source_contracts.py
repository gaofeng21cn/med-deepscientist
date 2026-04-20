from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_ui_safe_json_contracts_are_wired_into_workspace_surfaces() -> None:
    safe_json_source = _read("src/ui/src/lib/safe-json.ts")
    toast_source = _read("src/ui/src/components/ui/toast.tsx")
    stage_surface_source = _read("src/ui/src/components/workspace/QuestStageSurface.tsx")
    lab_source = _read("src/ui/src/lib/api/lab.ts")
    tabs_source = _read("src/ui/src/lib/stores/tabs.ts")

    assert "export function safeJsonStringify" in safe_json_source
    assert "export function safeStableStringify" in safe_json_source
    assert "export function sanitizeJsonRecord" in safe_json_source
    assert "const serialized = safeStableStringify(reason)" in toast_source
    assert "Unhandled rejection (${serialized})" in toast_source
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
    assert "base_url: draft.base_url.trim() || DEFAULT_DRAFT.base_url" in dialog_source
    assert "token_env: draft.token_env.trim() || null" in dialog_source
    assert "draft.token.trim() || draft.token_env.trim()" in dialog_source


def test_deepxiv_settings_surface_exposes_base_url_and_env_only_authoring() -> None:
    dialog_source = _read("src/ui/src/components/settings/DeepXivSetupDialog.tsx")
    panel_source = _read("src/ui/src/components/settings/DeepXivSettingsPanel.tsx")
    settings_page_source = _read("src/ui/src/components/settings/SettingsPage.tsx")

    assert "baseUrlLabel" in dialog_source
    assert "tokenEnvLabel" in dialog_source
    assert "tokenOrEnvRequired" in dialog_source
    assert "Use a direct token or provide an env var name for env-only auth." in dialog_source
    assert "可以直接填写 token，也可以只填写环境变量名走 env-only 鉴权。" in dialog_source
    assert "base URL, direct token, env-only token lookup" in panel_source
    assert "selectedName === 'config'" in settings_page_source
    assert "<DeepXivSettingsPanel locale={locale} onSaved={handleDeepXivConfigSaved} />" in settings_page_source


def test_create_project_dialog_keeps_deepxiv_out_of_start_research_mount_tree() -> None:
    dialog_source = _read("src/ui/src/components/projects/CreateProjectDialog.tsx")

    assert "DeepXivSetupDialog" not in dialog_source


def test_benchstore_entry_surface_is_wired_into_landing_and_start_research() -> None:
    hero_source = _read("src/ui/src/components/landing/Hero.tsx")
    dialog_source = _read("src/ui/src/components/projects/CreateProjectDialog.tsx")

    assert "BenchStoreDialog" in hero_source
    assert "setupPacket" in dialog_source
    assert "setupQuestId" in dialog_source
    assert "onRequestSetupAgent" in dialog_source
    assert "start_setup_patch" in dialog_source


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
