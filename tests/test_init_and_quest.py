from __future__ import annotations

import json
import shutil
from pathlib import Path

from deepscientist.config import ConfigManager
from deepscientist.cli import _local_ui_url, init_command, pause_command
from deepscientist.home import ensure_home_layout, repo_root
from deepscientist.mcp.context import McpContext
from deepscientist.quest import QuestService
from deepscientist.shared import ensure_dir, write_json, write_text, write_yaml
from deepscientist.skills import SkillInstaller


def _materialize_reference_materials(quest_root: Path, paper_root: Path, *, count: int = 20) -> None:
    entries = []
    records = []
    for index in range(1, count + 1):
        citation_id = f"demo2026{index:02d}"
        pmid = f"4000{index:04d}"
        entries.append(f"@article{{{citation_id}, title={{Demo Reference {index}}}}}\n")
        records.append(
            json.dumps(
                {
                    "record_id": f"pubmed-demo-{index:03d}",
                    "source": "pubmed",
                    "title": f"Demo Reference {index}",
                    "pmid": pmid,
                }
            )
        )
    write_text(paper_root / "references.bib", "".join(entries))
    literature_root = ensure_dir(quest_root / "literature" / "pubmed")
    write_text(literature_root / "records.jsonl", "\n".join(records) + "\n")


def _write_citation_rich_draft(paper_root: Path, *, count: int = 20) -> None:
    citation_keys = [f"@demo2026{index:02d}" for index in range(1, count + 1)]
    intro_keys = "; ".join(citation_keys[:10])
    discussion_keys = "; ".join(citation_keys[10:20])
    write_text(
        paper_root / "draft.md",
        "\n".join(
            [
                "# Draft",
                "",
                "## Introduction",
                "",
                f"Prediction-model literature motivates the manuscript framing [{intro_keys}].",
                "",
                "## Discussion",
                "",
                f"The discussion remains anchored to the verified literature set [{discussion_keys}].",
                "",
            ]
        ),
    )


def test_init_creates_required_files(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    manager = ConfigManager(temp_home)
    created = manager.ensure_files()
    assert created
    assert (temp_home / "runtime" / "python").exists()
    assert (temp_home / "runtime" / "uv-cache").exists()
    assert not (temp_home / "runtime" / "venv").exists()
    assert (temp_home / "config" / "config.yaml").exists()
    assert (temp_home / "config" / "runners.yaml").exists()
    assert (temp_home / "config" / "connectors.yaml").exists()
    config = manager.load_named("config")
    runners = manager.load_named_normalized("runners")
    assert config["ui"]["host"] == "0.0.0.0"
    assert config["ui"]["port"] == 20999
    assert config["ui"]["default_mode"] == "web"
    assert config["ui"]["auto_open_browser"] is True
    assert config["bootstrap"]["codex_ready"] is False
    assert config["bootstrap"]["codex_last_checked_at"] is None
    assert config["bootstrap"]["locale_source"] == "default"
    assert config["bootstrap"]["locale_initialized_from_browser"] is False
    assert config["bootstrap"]["locale_initialized_at"] is None
    assert config["bootstrap"]["locale_initialized_browser_locale"] is None
    assert config["connectors"]["system_enabled"]["qq"] is True
    assert config["connectors"]["system_enabled"]["weixin"] is True
    assert config["connectors"]["system_enabled"]["telegram"] is True
    assert config["connectors"]["system_enabled"]["discord"] is False
    assert config["connectors"]["system_enabled"]["slack"] is False
    assert config["connectors"]["system_enabled"]["feishu"] is True
    assert config["connectors"]["system_enabled"]["whatsapp"] is True
    assert config["connectors"]["system_enabled"]["lingzhu"] is True
    assert runners["codex"]["profile"] == ""
    assert runners["codex"]["model"] == "gpt-5.4"
    assert runners["codex"]["model_reasoning_effort"] == "xhigh"
    assert runners["codex"]["retry_initial_backoff_sec"] == 10.0
    assert runners["codex"]["retry_backoff_multiplier"] == 6.0
    assert runners["codex"]["retry_max_backoff_sec"] == 1800.0


def test_legacy_codex_retry_profile_is_upgraded_when_loading_normalized_runners(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    manager = ConfigManager(temp_home)
    manager.ensure_files()
    runners_path = manager.path_for("runners")
    runners_path.write_text(
        "\n".join(
            [
                "codex:",
                "  enabled: true",
                "  binary: codex",
                "  retry_on_failure: true",
                "  retry_max_attempts: 5",
                "  retry_initial_backoff_sec: 1",
                "  retry_backoff_multiplier: 2",
                "  retry_max_backoff_sec: 8",
                "",
            ]
        ),
        encoding="utf-8",
    )

    runners = manager.load_named_normalized("runners")

    assert runners["codex"]["retry_initial_backoff_sec"] == 10.0
    assert runners["codex"]["retry_backoff_multiplier"] == 6.0
    assert runners["codex"]["retry_max_backoff_sec"] == 1800.0


def test_new_creates_standalone_git_repo(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    service = QuestService(temp_home, skill_installer=SkillInstaller(repo_root(), temp_home))
    snapshot = service.create("test quest")
    quest_root = Path(snapshot["quest_root"])
    assert (quest_root / ".git").exists()
    assert (quest_root / ".gitignore").exists()
    assert (quest_root / "quest.yaml").exists()
    assert (quest_root / "tmp").exists()
    assert (quest_root / "userfiles").exists()
    assert (quest_root / ".codex" / "prompts" / "system.md").exists()
    assert (quest_root / ".codex" / "prompts" / "connectors" / "qq.md").exists()
    assert (quest_root / ".codex" / "skills").exists()
    assert (quest_root / ".claude" / "agents").exists()
    assert (quest_root / ".claude" / "agents" / "deepscientist-decision.md").exists()
    assert (quest_root / ".codex" / "skills" / "deepscientist-finalize" / "SKILL.md").exists()
    assert snapshot["quest_id"] == "001"
    assert snapshot["runner"] == "codex"
    assert "paths" in snapshot
    assert snapshot["summary"]["status_line"] == "Quest created. Waiting for baseline setup or reuse."


def test_auto_generated_quest_ids_are_sequential(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    service = QuestService(temp_home)

    first = service.create("first quest")
    second = service.create("second quest")
    third = service.create("third quest")

    assert [first["quest_id"], second["quest_id"], third["quest_id"]] == ["001", "002", "003"]


def test_events_slice_uses_placeholder_for_oversized_event_lines(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    service = QuestService(temp_home)
    snapshot = service.create("oversized event slice quest")
    quest_root = Path(snapshot["quest_root"])
    events_path = quest_root / ".ds" / "events.jsonl"
    huge_output = "x" * (9 * 1024 * 1024)
    oversized_event = {
        "event_id": "evt-huge",
        "type": "runner.tool_result",
        "quest_id": snapshot["quest_id"],
        "run_id": "run-huge",
        "tool_name": "bash_exec.bash_exec",
        "output": huge_output,
    }
    small_event = {
        "event_id": "evt-small",
        "type": "runner.agent_message",
        "quest_id": snapshot["quest_id"],
        "text": "small tail event",
    }
    events_path.write_text(
        json.dumps(oversized_event, ensure_ascii=False) + "\n" + json.dumps(small_event, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    payload = service.events(snapshot["quest_id"], tail=True, limit=2)

    assert payload["events"][0]["type"] == "runner.tool_result"
    assert payload["events"][0]["oversized_event"] is True
    assert payload["events"][0]["oversized_bytes"] > 8 * 1024 * 1024
    assert payload["events"][1]["type"] == "runner.agent_message"


def test_deleted_quest_ids_are_not_reused(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    service = QuestService(temp_home)

    first = service.create("first quest")
    second = service.create("second quest")
    third = service.create("third quest")
    shutil.rmtree(Path(second["quest_root"]))

    fourth = service.create("fourth quest")

    assert [first["quest_id"], second["quest_id"], third["quest_id"], fourth["quest_id"]] == ["001", "002", "003", "004"]


def test_snapshot_exposes_paper_contract_and_analysis_inventory(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    service = QuestService(temp_home)
    snapshot = service.create("paper analysis snapshot quest")
    quest_root = Path(snapshot["quest_root"])
    idea_root = ensure_dir(quest_root / "artifacts" / "ideas")
    run_root = ensure_dir(quest_root / "artifacts" / "runs")

    write_json(
        idea_root / "idea-001.json",
        {
            "kind": "idea",
            "idea_id": "idea-001",
            "branch": "idea/001-idea-001",
            "parent_branch": "main",
            "updated_at": "2026-03-28T00:00:00Z",
            "details": {
                "title": "Audit-ready idea",
                "lineage_intent": "continue_line",
            },
            "paths": {
                "idea_md": str(quest_root / "memory" / "ideas" / "idea-001" / "idea.md"),
                "idea_draft_md": str(quest_root / "memory" / "ideas" / "idea-001" / "draft.md"),
            },
        },
    )
    write_json(
        run_root / "run-main-001.json",
        {
            "kind": "run",
            "idea_id": "idea-001",
            "run_id": "run-main-001",
            "run_kind": "experiment",
            "branch": "run/run-main-001",
            "parent_branch": "idea/001-idea-001",
            "updated_at": "2026-03-28T00:05:00Z",
            "metric_rows": [{"metric_id": "acc", "value": 0.91}],
        },
    )

    paper_root = ensure_dir(quest_root / "paper")
    write_json(
        paper_root / "selected_outline.json",
        {
            "outline_id": "outline-001",
            "title": "Outline Title",
            "story": "Outline story",
            "detailed_outline": {
                "research_questions": ["RQ1", "RQ2"],
                "experimental_designs": ["EXP1", "EXP2"],
                "contributions": ["C1"],
            },
            "sections": [
                {
                    "section_id": "results-main",
                    "title": "Main Results",
                    "paper_role": "main_text",
                    "required_items": ["run-main-001"],
                    "result_table": [],
                }
            ],
            "evidence_contract": {"main_text_items_must_be_ready": True},
        },
    )
    write_text(paper_root / "paper_experiment_matrix.md", "# Matrix\n")
    write_json(paper_root / "paper_bundle_manifest.json", {"paper_branch": "paper/test", "selected_outline_ref": "outline-001"})
    write_json(paper_root / "claim_evidence_map.json", {"claims": []})
    write_json(
        paper_root / "paper_line_state.json",
        {
            "paper_line_id": "paper-line-001",
            "paper_branch": "paper/test",
            "source_branch": "run/run-main-001",
            "source_run_id": "run-main-001",
            "source_idea_id": "idea-001",
            "selected_outline_ref": "outline-001",
            "title": "Outline Title",
            "required_count": 1,
            "ready_required_count": 1,
            "unmapped_count": 0,
            "open_supplementary_count": 0,
            "updated_at": "2026-03-28T00:00:00Z",
        },
    )
    write_json(
        paper_root / "evidence_ledger.json",
        {
            "selected_outline_ref": "outline-001",
            "items": [
                {
                    "item_id": "run-main-001",
                    "title": "Main run",
                    "kind": "main_experiment",
                    "paper_role": "main_text",
                    "section_id": "results-main",
                    "status": "completed",
                }
            ],
        },
    )
    write_text(paper_root / "evidence_ledger.md", "# Ledger\n")
    review_root = ensure_dir(paper_root / "review")
    write_json(review_root / "submission_checklist.json", {"blocking_items": []})
    _write_citation_rich_draft(paper_root)
    _materialize_reference_materials(quest_root, paper_root)
    analysis_manifest_root = ensure_dir(quest_root / ".ds" / "analysis_campaigns")
    write_json(
        analysis_manifest_root / "analysis-test.json",
        {
            "campaign_id": "analysis-test",
            "active_idea_id": "idea-001",
            "parent_run_id": "run-main-001",
            "parent_branch": "run/run-main-001",
            "paper_line_id": "paper-line-001",
            "paper_line_branch": "paper/test",
            "paper_line_root": str(quest_root),
            "selected_outline_ref": "outline-001",
            "slices": [
                {
                    "slice_id": "slice-a",
                    "branch": "analysis/idea-001/analysis-test-slice-a",
                    "worktree_root": str(quest_root / ".ds" / "worktrees" / "analysis-test-slice-a"),
                    "status": "completed",
                }
            ],
        },
    )

    analysis_root = ensure_dir(quest_root / "experiments" / "analysis-results" / "analysis-test")
    write_json(
        analysis_root / "todo_manifest.json",
        {
            "selected_outline_ref": "outline-001",
            "todo_items": [
                {
                    "slice_id": "slice-a",
                    "title": "Slice A",
                    "status": "completed",
                    "section_id": "results-main",
                    "item_id": "AN-001",
                    "claim_links": ["C1"],
                    "research_question": "RQ-A",
                    "experimental_design": "ED-A",
                    "paper_role": "main_text",
                }
            ],
        },
    )
    write_text(analysis_root / "campaign.md", "# Campaign\n")
    write_text(analysis_root / "SUMMARY.md", "# Summary\n\nCampaign summary.\n")
    write_text(analysis_root / "slice-a.md", "# Slice A\n\nResult summary.\n")

    refreshed = service.snapshot(snapshot["quest_id"])

    assert refreshed["paper_contract"]["selected_outline_ref"] == "outline-001"
    assert refreshed["paper_contract"]["title"] == "Outline Title"
    assert refreshed["paper_contract"]["research_questions"] == ["RQ1", "RQ2"]
    assert refreshed["paper_contract"]["paths"]["experiment_matrix"].endswith("paper/paper_experiment_matrix.md")
    assert refreshed["paper_contract"]["paths"]["evidence_ledger_json"].endswith("paper/evidence_ledger.json")
    assert refreshed["paper_contract"]["paths"]["paper_line_state"].endswith("paper/paper_line_state.json")
    assert refreshed["paper_contract"]["sections"][0]["section_id"] == "results-main"
    assert refreshed["paper_contract"]["evidence_summary"]["item_count"] == 1
    assert refreshed["paper_evidence"]["item_count"] == 1
    assert refreshed["idea_lines"][0]["idea_line_id"] == "idea-001"
    assert refreshed["active_idea_line_ref"] == "idea-001"
    assert refreshed["idea_lines"][0]["latest_main_run_id"] == "run-main-001"
    assert refreshed["idea_lines"][0]["paper_line_id"] == "paper-line-001"
    assert refreshed["paper_contract_health"]["contract_ok"] is True
    assert refreshed["paper_contract_health"]["writing_ready"] is True
    assert refreshed["paper_contract_health"]["recommended_next_stage"] == "finalize"
    assert refreshed["paper_lines"][0]["paper_line_id"] == "paper-line-001"
    assert refreshed["active_paper_line_ref"] == "paper-line-001"
    assert refreshed["analysis_inventory"]["campaign_count"] == 1
    assert refreshed["analysis_inventory"]["slice_count"] == 1
    assert refreshed["analysis_inventory"]["mapped_slice_count"] == 1
    assert refreshed["analysis_inventory"]["campaigns"][0]["campaign_id"] == "analysis-test"
    assert refreshed["analysis_inventory"]["campaigns"][0]["active_idea_id"] == "idea-001"
    assert refreshed["analysis_inventory"]["campaigns"][0]["paper_line_id"] == "paper-line-001"
    assert refreshed["analysis_inventory"]["campaigns"][0]["slices"][0]["slice_id"] == "slice-a"
    assert refreshed["analysis_inventory"]["campaigns"][0]["slices"][0]["branch"] == "analysis/idea-001/analysis-test-slice-a"
    assert refreshed["analysis_inventory"]["campaigns"][0]["slices"][0]["mapped"] is True


def test_snapshot_blocks_finalize_when_reference_materialization_is_missing(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    service = QuestService(temp_home, skill_installer=SkillInstaller(repo_root(), temp_home))
    snapshot = service.create("paper materialization gate quest")
    quest_root = Path(snapshot["quest_root"])

    paper_root = ensure_dir(quest_root / "paper")
    write_json(
        paper_root / "selected_outline.json",
        {
            "outline_id": "outline-001",
            "title": "Reference Gate Outline",
            "sections": [],
        },
    )
    write_json(
        paper_root / "paper_line_state.json",
        {
            "paper_line_id": "paper-line-reference-gate",
            "paper_branch": "paper/reference-gate",
            "selected_outline_ref": "outline-001",
            "title": "Reference Gate Outline",
            "draft_status": "present",
            "bundle_status": "present",
            "updated_at": "2026-03-28T00:00:00Z",
        },
    )
    write_json(
        paper_root / "paper_bundle_manifest.json",
        {
            "paper_branch": "paper/reference-gate",
            "selected_outline_ref": "outline-001",
        },
    )
    write_json(paper_root / "claim_evidence_map.json", {"claims": []})
    write_json(paper_root / "evidence_ledger.json", {"selected_outline_ref": "outline-001", "items": []})
    write_text(paper_root / "draft.md", "# Draft\n")

    refreshed = service.snapshot(snapshot["quest_id"])
    health = refreshed["paper_contract_health"]

    assert health["contract_ok"] is True
    assert health["writing_ready"] is False
    assert health["finalize_ready"] is False
    assert health["reference_materialization_ready"] is False
    assert health["bibliography_ready"] is False
    assert health["literature_ready"] is False
    assert health["recommended_next_stage"] == "write"
    assert health["recommended_action"] == "materialize_reference_materials"
    assert "at least 12 verified references are required" in " ".join(health["blocking_reasons"])
    assert "requires total>=12, pubmed>=6" in " ".join(health["blocking_reasons"])


def test_snapshot_blocks_thin_and_drifted_reference_materialization(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    service = QuestService(temp_home, skill_installer=SkillInstaller(repo_root(), temp_home))
    snapshot = service.create("paper thin reference gate quest")
    quest_root = Path(snapshot["quest_root"])
    worktree_root = ensure_dir(quest_root / ".ds" / "worktrees" / "paper-thin")
    service.update_research_state(quest_root, current_workspace_root=str(worktree_root))

    paper_root = ensure_dir(worktree_root / "paper")
    write_json(
        paper_root / "selected_outline.json",
        {
            "outline_id": "outline-001",
            "title": "Thin Reference Gate Outline",
            "sections": [],
        },
    )
    write_json(
        paper_root / "paper_line_state.json",
        {
            "paper_line_id": "paper-line-thin-reference-gate",
            "paper_branch": "paper/thin-reference-gate",
            "selected_outline_ref": "outline-001",
            "title": "Thin Reference Gate Outline",
            "draft_status": "present",
            "bundle_status": "present",
            "updated_at": "2026-04-02T00:00:00Z",
        },
    )
    write_json(
        paper_root / "paper_bundle_manifest.json",
        {
            "paper_branch": "paper/thin-reference-gate",
            "selected_outline_ref": "outline-001",
        },
    )
    write_json(paper_root / "claim_evidence_map.json", {"claims": []})
    write_json(paper_root / "evidence_ledger.json", {"selected_outline_ref": "outline-001", "items": []})
    ensure_dir(quest_root / "paper")
    write_json(
        quest_root / "paper" / "medical_reporting_contract.json",
        {
            "publication_profile": "general_medical_journal",
            "manuscript_family": "prediction_model",
            "reporting_guideline_family": "TRIPOD",
        },
    )
    write_text(paper_root / "draft.md", "# Draft\n")
    write_text(
        paper_root / "references.bib",
        "".join(f"@article{{thin2026{index:02d}, title={{Thin Reference {index}}}}}\n" for index in range(1, 5)),
    )
    literature_root = ensure_dir(worktree_root / "literature" / "pubmed")
    write_text(
        literature_root / "records.jsonl",
        "\n".join(
            json.dumps(
                {
                    "record_id": f"pubmed-thin-{index:03d}",
                    "source": "pubmed",
                    "title": f"Thin Reference {index}",
                    "pmid": f"4999{index:04d}",
                }
            )
            for index in range(1, 5)
        )
        + "\n",
    )
    write_text(quest_root / "paper" / "references.bib", "")
    ensure_dir(quest_root / "literature" / "pubmed")
    write_text(quest_root / "literature" / "pubmed" / "records.jsonl", "")

    refreshed = service.snapshot(snapshot["quest_id"])
    health = refreshed["paper_contract_health"]

    assert health["contract_ok"] is True
    assert health["writing_ready"] is False
    assert health["finalize_ready"] is False
    assert health["reference_materialization_ready"] is False
    assert health["recommended_next_stage"] == "write"
    assert health["recommended_action"] in {"materialize_reference_materials", "synchronize_reference_materials"}
    assert "at least 20 verified references are required" in " ".join(health["blocking_reasons"])


def test_snapshot_blocks_paper_with_thin_in_text_citation_usage(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    service = QuestService(temp_home, skill_installer=SkillInstaller(repo_root(), temp_home))
    snapshot = service.create("paper in-text citation gate quest")
    quest_root = Path(snapshot["quest_root"])

    paper_root = ensure_dir(quest_root / "paper")
    write_json(
        paper_root / "selected_outline.json",
        {
            "outline_id": "outline-001",
            "title": "Citation Usage Outline",
            "sections": [],
        },
    )
    write_json(
        paper_root / "paper_line_state.json",
        {
            "paper_line_id": "paper-line-citation-usage-gate",
            "paper_branch": "paper/citation-usage-gate",
            "selected_outline_ref": "outline-001",
            "title": "Citation Usage Outline",
            "draft_status": "present",
            "bundle_status": "present",
            "updated_at": "2026-04-02T00:00:00Z",
        },
    )
    write_json(
        paper_root / "paper_bundle_manifest.json",
        {
            "paper_branch": "paper/citation-usage-gate",
            "selected_outline_ref": "outline-001",
        },
    )
    write_json(
        paper_root / "medical_reporting_contract.json",
        {
            "publication_profile": "general_medical_journal",
            "manuscript_family": "prediction_model",
            "reporting_guideline_family": "TRIPOD",
        },
    )
    write_json(paper_root / "claim_evidence_map.json", {"claims": []})
    write_json(paper_root / "evidence_ledger.json", {"selected_outline_ref": "outline-001", "items": []})
    write_text(
        paper_root / "draft.md",
        "\n".join(
            [
                "# Draft",
                "",
                "## Introduction",
                "",
                "Clinical prediction reports should stay transparent and transportability-aware "
                "[@demo202601; @demo202602].",
                "",
                "## Discussion",
                "",
                "Diabetes mortality models remain clinically relevant but need honest scope control "
                "[@demo202603; @demo202604].",
                "",
            ]
        ),
    )
    _materialize_reference_materials(quest_root, paper_root, count=20)

    refreshed = service.snapshot(snapshot["quest_id"])
    health = refreshed["paper_contract_health"]

    assert health["contract_ok"] is True
    assert health["reference_materialization_ready"] is True
    assert health["citation_usage_ready"] is False
    assert health["cited_bibliography_entry_count"] == 4
    assert health["recommended_next_stage"] == "write"
    assert health["recommended_action"] == "revise_paper_citations"
    assert "paper draft cites 4 verified references" in " ".join(health["blocking_reasons"])
    assert "at least 20 in-text references are required" in " ".join(health["blocking_reasons"])


def test_list_quests_handles_null_updated_at_without_crashing(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    service = QuestService(temp_home)

    newer = service.create("newer quest")
    legacy = service.create("legacy quest")

    legacy_root = Path(legacy["quest_root"])
    legacy_yaml = service.read_quest_yaml(legacy_root)
    legacy_yaml["updated_at"] = None
    write_yaml(legacy_root / "quest.yaml", legacy_yaml)

    items = service.list_quests()

    item_by_id = {item["quest_id"]: item for item in items}
    assert set(item_by_id) == {newer["quest_id"], legacy["quest_id"]}
    assert item_by_id[legacy["quest_id"]]["updated_at"] is None


def test_auto_generated_quest_ids_initialize_from_existing_numeric_quests(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    for quest_id in ("001", "002", "010"):
        quest_root = ensure_dir(temp_home / "quests" / quest_id)
        write_text(quest_root / "quest.yaml", f'quest_id: "{quest_id}"\n')

    service = QuestService(temp_home)
    snapshot = service.create("after existing quests")

    assert snapshot["quest_id"] == "011"


def test_skill_installer_can_resync_existing_quests_after_version_change(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    installer = SkillInstaller(repo_root(), temp_home)
    service = QuestService(temp_home, skill_installer=installer)
    snapshot = service.create("sync existing quest skills")
    quest_root = Path(snapshot["quest_root"])
    stale_file = quest_root / ".codex" / "skills" / "deepscientist-scout" / "obsolete.txt"
    stale_prompt = quest_root / ".codex" / "prompts" / "obsolete.txt"
    stale_file.write_text("stale", encoding="utf-8")
    stale_prompt.write_text("stale", encoding="utf-8")

    result = installer.ensure_release_sync(
        installed_version="9.9.9",
        sync_global_enabled=False,
        sync_existing_quests_enabled=True,
        force=True,
    )

    assert result["updated"] is True
    assert result["existing_quests_synced"] is True
    assert result["existing_quests"]["count"] == 1
    assert not stale_file.exists()
    assert not stale_prompt.exists()
    assert (quest_root / ".codex" / "prompts" / "system.md").exists()
    assert (quest_root / ".codex" / "skills" / "deepscientist-scout" / "SKILL.md").exists()
    state_path = temp_home / "runtime" / "skill-sync-state.json"
    assert state_path.exists()
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["installed_version"] == "9.9.9"


def test_explicit_custom_quest_id_still_works(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    service = QuestService(temp_home)

    snapshot = service.create("custom quest", quest_id="demo-quest")

    assert snapshot["quest_id"] == "demo-quest"


def test_explicit_numeric_quest_id_advances_next_auto_id(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    service = QuestService(temp_home)

    explicit = service.create("explicit numeric quest", quest_id="010")
    automatic = service.create("automatic after explicit numeric")

    assert explicit["quest_id"] == "010"
    assert automatic["quest_id"] == "011"


def test_preview_next_numeric_quest_id_matches_allocator_without_consuming_it(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    service = QuestService(temp_home)

    assert service.preview_next_numeric_quest_id() == "001"
    assert service.preview_next_numeric_quest_id() == "001"

    created = service.create("preview quest")

    assert created["quest_id"] == "001"
    assert service.preview_next_numeric_quest_id() == "002"

def test_init_command_syncs_global_skills(temp_home: Path, monkeypatch) -> None:
    ensure_home_layout(temp_home)

    calls: list[str] = []

    def _record_sync(self):  # type: ignore[no-untyped-def]
        calls.append("sync_global")
        return {"codex": [], "claude": [], "notes": []}

    monkeypatch.setattr(SkillInstaller, "sync_global", _record_sync)
    exit_code = init_command(temp_home)
    assert exit_code in {0, 1}
    assert calls == ["sync_global"]


def test_pause_command_prefers_daemon_control_when_available(temp_home: Path, monkeypatch, capsys) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()

    class _FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self) -> bytes:
            return json.dumps(
                {
                    "ok": True,
                    "action": "pause",
                    "snapshot": {
                        "quest_id": "q-demo",
                        "status": "paused",
                    },
                }
            ).encode("utf-8")

    monkeypatch.setattr("deepscientist.cli.urlopen", lambda request, timeout=3: _FakeResponse())

    exit_code = pause_command(temp_home, "q-demo")

    captured = capsys.readouterr()
    assert exit_code == 0
    assert '"status": "paused"' in captured.out


def test_local_ui_url_keeps_default_host_visible() -> None:
    assert _local_ui_url("0.0.0.0", 20999) == "http://0.0.0.0:20999"
    assert _local_ui_url("", 20999) == "http://0.0.0.0:20999"


def test_mcp_context_prefers_deepscientist_home_env(monkeypatch, tmp_path: Path) -> None:
    primary_home = tmp_path / "primary-home"
    fallback_home = tmp_path / "fallback-home"
    monkeypatch.setenv("DEEPSCIENTIST_HOME", str(primary_home))
    monkeypatch.setenv("DS_HOME", str(fallback_home))

    context = McpContext.from_env()

    assert context.home == primary_home


def test_repo_root_prefers_explicit_env(monkeypatch, tmp_path: Path) -> None:
    install_root = tmp_path / "install-root"
    ensure_dir(install_root / "src" / "deepscientist")
    ensure_dir(install_root / "src" / "skills")
    write_text(install_root / "pyproject.toml", "[project]\nname='deepscientist'\n")
    monkeypatch.setenv("DEEPSCIENTIST_REPO_ROOT", str(install_root))

    assert repo_root() == install_root.resolve()
