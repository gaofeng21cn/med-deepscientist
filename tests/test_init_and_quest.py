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


def _write_managed_publication_eval_latest(
    study_root: Path,
    *,
    quest_id: str,
    payload: dict[str, object],
) -> Path:
    latest_path = study_root / "artifacts" / "publication_eval" / "latest.json"
    write_json(latest_path, {"schema_version": 1, "study_id": study_root.name, "quest_id": quest_id, **payload})
    return latest_path


def _materialize_ready_paper_line_for_publication_gate(
    quest_root: Path,
    *,
    study_root_ref: str,
) -> Path:
    paper_root = ensure_dir(quest_root / "paper")
    write_json(
        paper_root / "selected_outline.json",
        {
            "outline_id": "outline-001",
            "title": "Managed Gate Outline",
            "sections": [],
        },
    )
    write_json(
        paper_root / "paper_line_state.json",
        {
            "paper_line_id": "paper-line-managed-gate",
            "paper_branch": "paper/managed-gate",
            "selected_outline_ref": "outline-001",
            "title": "Managed Gate Outline",
            "draft_status": "present",
            "bundle_status": "present",
            "updated_at": "2026-04-10T00:00:00Z",
        },
    )
    write_json(
        paper_root / "paper_bundle_manifest.json",
        {
            "paper_branch": "paper/managed-gate",
            "selected_outline_ref": "outline-001",
            "status": "ready_for_submission",
        },
    )
    write_json(
        paper_root / "medical_reporting_contract.json",
        {
            "status": "resolved",
            "study_root": study_root_ref,
            "publication_profile": "general_medical_journal",
            "manuscript_family": "prediction_model",
            "reporting_guideline_family": "TRIPOD",
        },
    )
    write_json(paper_root / "claim_evidence_map.json", {"claims": []})
    write_json(paper_root / "evidence_ledger.json", {"selected_outline_ref": "outline-001", "items": []})
    _write_citation_rich_draft(paper_root)
    _materialize_reference_materials(quest_root, paper_root)

    review_root = ensure_dir(paper_root / "review")
    write_text(review_root / "review.md", "# Review\n\nReady.\n")
    write_text(review_root / "revision_log.md", "# Revision Log\n\nReady.\n")
    write_json(review_root / "submission_checklist.json", {"status": "ready_for_submission", "blocking_items": []})
    proofing_root = ensure_dir(paper_root / "proofing")
    write_text(proofing_root / "proofing_report.md", "# Proofing Report\n\nReady.\n")
    write_text(proofing_root / "language_issues.md", "# Language Issues\n\nNone.\n")
    write_text(paper_root / "final_claim_ledger.md", "# Final Claim Ledger\n\nAll claims closed.\n")
    write_text(quest_root / "handoffs" / "finalize_resume_packet.md", "# Finalize Resume Packet\n\nReady.\n")
    return paper_root


def _materialize_submission_minimal_projection(
    paper_root: Path,
    *,
    include_display_exports: bool,
) -> None:
    submission_root = ensure_dir(paper_root / "submission_minimal")
    write_text(submission_root / "manuscript.docx", "docx")
    write_text(submission_root / "paper.pdf", "%PDF-1.4\n")
    package_files = [
        {"path": "paper/submission_minimal/submission_manifest.json", "role": "manifest"},
        {"path": "paper/submission_minimal/paper.pdf", "role": "pdf"},
        {"path": "paper/submission_minimal/manuscript.docx", "role": "docx"},
    ]
    if include_display_exports:
        ensure_dir(submission_root / "figures")
        ensure_dir(submission_root / "tables")
        write_text(submission_root / "figures" / "F1.png", "figure")
        write_text(submission_root / "tables" / "T1.csv", "a,b\n1,2\n")
        package_files.extend(
            [
                {"path": "paper/submission_minimal/figures/F1.png", "role": "figure"},
                {"path": "paper/submission_minimal/tables/T1.csv", "role": "table"},
            ]
        )
    write_json(
        submission_root / "submission_manifest.json",
        {
            "manuscript": {
                "docx_path": "paper/submission_minimal/manuscript.docx",
                "pdf_path": "paper/submission_minimal/paper.pdf",
            },
            "package_files": package_files,
        },
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
    assert runners["codex"]["model"] == "inherit"
    assert runners["codex"]["model_reasoning_effort"] == ""
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



def test_stale_codex_model_pin_is_migrated_when_loading_runners(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    manager = ConfigManager(temp_home)
    manager.ensure_files()
    runners_path = manager.path_for("runners")
    runners = manager.load_named("runners")
    runners["codex"]["model"] = "gpt-5.4"
    write_yaml(runners_path, runners)

    normalized = manager.load_runners_config()

    assert normalized["codex"]["model"] == "inherit_local_codex_default"
    assert manager.load_named("runners")["codex"]["model"] == "gpt-5.4"


def test_stale_codex_model_pin_is_persistently_migrated_by_ensure_files(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    manager = ConfigManager(temp_home)
    manager.ensure_files()
    runners = manager.load_named("runners")
    runners["codex"]["model"] = "gpt-5.4"
    write_yaml(manager.path_for("runners"), runners)

    manager.ensure_files()

    assert manager.load_named("runners")["codex"]["model"] == "inherit_local_codex_default"


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
    gitignore_text = (quest_root / ".gitignore").read_text(encoding="utf-8")
    assert ".ds/**/*.tmp" in gitignore_text
    assert ".ds/bash_exec/" in gitignore_text
    assert ".ds/codex_history/" in gitignore_text
    assert ".ds/codex_homes/" in gitignore_text
    assert ".ds/runs/" in gitignore_text
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
    write_text(review_root / "review.md", "# Review\n\nReady for finalize.\n")
    write_text(review_root / "revision_log.md", "# Revision Log\n\nNo blocking revisions remain.\n")
    write_json(review_root / "submission_checklist.json", {"blocking_items": []})
    proofing_root = ensure_dir(paper_root / "proofing")
    write_text(proofing_root / "proofing_report.md", "# Proofing Report\n\nNo blocking proofing issues.\n")
    write_text(proofing_root / "language_issues.md", "# Language Issues\n\nNone.\n")
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
    assert refreshed["paper_contract_health"]["recommended_next_stage"] == "write"
    assert refreshed["paper_contract_health"]["recommendation_scope"] == "paper_line_local_only"
    assert refreshed["paper_contract_health"]["global_stage_authority"] == "publication_gate"
    assert refreshed["paper_contract_health"]["global_stage_rule"] == (
        "paper-line recommendations are subordinate until publication gate allows write"
    )
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
    assert health["recommendation_scope"] == "paper_line_local_only"
    assert health["global_stage_authority"] == "publication_gate"
    assert health["global_stage_rule"] == (
        "paper-line recommendations are subordinate until publication gate allows write"
    )
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


def test_snapshot_synchronizes_active_paper_surface_into_quest_root_and_removes_stale_residue(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    service = QuestService(temp_home, skill_installer=SkillInstaller(repo_root(), temp_home))
    snapshot = service.create("paper surface sync quest")
    quest_root = Path(snapshot["quest_root"])
    worktree_root = ensure_dir(quest_root / ".ds" / "worktrees" / "paper-sync")
    service.update_research_state(quest_root, current_workspace_root=str(worktree_root))

    paper_root = ensure_dir(worktree_root / "paper")
    write_json(
        paper_root / "selected_outline.json",
        {
            "outline_id": "outline-001",
            "title": "Surface Sync Outline",
            "sections": [],
        },
    )
    write_json(
        paper_root / "paper_line_state.json",
        {
            "paper_line_id": "paper-line-surface-sync",
            "paper_branch": "paper/surface-sync",
            "selected_outline_ref": "outline-001",
            "title": "Surface Sync Outline",
            "draft_status": "present",
            "bundle_status": "present",
            "updated_at": "2026-04-03T00:00:00Z",
        },
    )
    write_json(
        paper_root / "paper_bundle_manifest.json",
        {
            "paper_branch": "paper/surface-sync",
            "selected_outline_ref": "outline-001",
        },
    )
    write_json(paper_root / "claim_evidence_map.json", {"claims": []})
    write_json(paper_root / "evidence_ledger.json", {"selected_outline_ref": "outline-001", "items": []})
    _write_citation_rich_draft(paper_root, count=21)
    write_text(
        paper_root / "references.bib",
        "".join(f"@article{{demo2026{index:02d}, title={{Demo Reference {index}}}}}\n" for index in range(1, 22)),
    )
    literature_root = ensure_dir(worktree_root / "literature" / "pubmed")
    write_text(
        literature_root / "records.jsonl",
        "\n".join(
            json.dumps(
                {
                    "record_id": f"pubmed-demo-{index:03d}",
                    "source": "pubmed",
                    "title": f"Demo Reference {index}",
                    "pmid": f"4000{index:04d}",
                }
            )
            for index in range(1, 22)
        )
        + "\n",
    )

    root_paper = ensure_dir(quest_root / "paper")
    write_text(root_paper / "references.bib", "")
    write_text(root_paper / "stale.md", "stale root residue\n")
    root_literature = ensure_dir(quest_root / "literature" / "pubmed")
    write_text(root_literature / "records.jsonl", "")

    refreshed = service.snapshot(snapshot["quest_id"])
    health = refreshed["paper_contract_health"]

    assert health["reference_materialization_ready"] is True
    assert "quest root and active worktree reference surfaces are inconsistent" not in health["blocking_reasons"]
    assert (quest_root / "paper" / "draft.md").exists()
    assert (quest_root / "paper" / "paper_bundle_manifest.json").exists()
    assert not (quest_root / "paper" / "stale.md").exists()
    assert service._bibtex_entry_count((quest_root / "paper" / "references.bib").read_text(encoding="utf-8")) == 21
    assert len(
        [line for line in (quest_root / "literature" / "pubmed" / "records.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    ) == 21


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


def test_snapshot_blocks_finalize_without_review_proofing_and_submission_checks(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    service = QuestService(temp_home, skill_installer=SkillInstaller(repo_root(), temp_home))
    snapshot = service.create("paper finalize gate quest")
    quest_root = Path(snapshot["quest_root"])

    paper_root = ensure_dir(quest_root / "paper")
    write_json(
        paper_root / "selected_outline.json",
        {
            "outline_id": "outline-001",
            "title": "Finalize Gate Outline",
            "sections": [],
        },
    )
    write_json(
        paper_root / "paper_line_state.json",
        {
            "paper_line_id": "paper-line-finalize-gate",
            "paper_branch": "paper/finalize-gate",
            "selected_outline_ref": "outline-001",
            "title": "Finalize Gate Outline",
            "draft_status": "present",
            "bundle_status": "present",
            "updated_at": "2026-04-02T00:00:00Z",
        },
    )
    write_json(
        paper_root / "paper_bundle_manifest.json",
        {
            "paper_branch": "paper/finalize-gate",
            "selected_outline_ref": "outline-001",
        },
    )
    write_json(paper_root / "claim_evidence_map.json", {"claims": []})
    write_json(paper_root / "evidence_ledger.json", {"selected_outline_ref": "outline-001", "items": []})
    _write_citation_rich_draft(paper_root)
    _materialize_reference_materials(quest_root, paper_root)

    refreshed = service.snapshot(snapshot["quest_id"])
    health = refreshed["paper_contract_health"]

    assert health["contract_ok"] is True
    assert health["writing_ready"] is True
    assert health["review_outputs_ready"] is False
    assert health["proofing_outputs_ready"] is False
    assert health["submission_checklist_ready"] is False
    assert health["finalize_ready"] is False
    assert health["completion_approval_ready"] is False
    assert health["recommended_next_stage"] == "review"
    assert health["recommended_action"] == "run_skeptical_audit"
    joined = " ".join(health["blocking_reasons"])
    assert "skeptical review outputs are missing" in joined
    assert "proofing outputs are missing" in joined
    assert "submission packaging checklist is missing" in joined


def test_snapshot_keeps_bundle_not_ready_when_submission_checklist_has_blocking_items(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    service = QuestService(temp_home, skill_installer=SkillInstaller(repo_root(), temp_home))
    snapshot = service.create("paper blocking checklist quest")
    quest_root = Path(snapshot["quest_root"])

    paper_root = ensure_dir(quest_root / "paper")
    write_json(
        paper_root / "selected_outline.json",
        {
            "outline_id": "outline-001",
            "title": "Blocking Checklist Outline",
            "sections": [],
        },
    )
    write_json(
        paper_root / "paper_line_state.json",
        {
            "paper_line_id": "paper-line-blocking-checklist",
            "paper_branch": "paper/blocking-checklist",
            "selected_outline_ref": "outline-001",
            "title": "Blocking Checklist Outline",
            "draft_status": "present",
            "bundle_status": "present",
            "updated_at": "2026-04-03T00:00:00Z",
        },
    )
    write_json(
        paper_root / "paper_bundle_manifest.json",
        {
            "paper_branch": "paper/blocking-checklist",
            "selected_outline_ref": "outline-001",
            "status": "proof_ready_with_author_metadata_and_submission_declarations_pending",
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
    _write_citation_rich_draft(paper_root)
    _materialize_reference_materials(quest_root, paper_root)

    review_root = ensure_dir(paper_root / "review")
    write_text(review_root / "review.md", "# Review\n\nReady except for external declarations.\n")
    write_text(review_root / "revision_log.md", "# Revision Log\n\nPending author-side declarations.\n")
    write_json(
        review_root / "submission_checklist.json",
        {
            "status": "proof_ready_with_author_metadata_and_submission_declarations_pending",
            "blocking_items": [
                {
                    "id": "author_metadata",
                    "status": "external_input_required",
                    "detail": "Final author block is still missing.",
                }
            ],
        },
    )
    proofing_root = ensure_dir(paper_root / "proofing")
    write_text(proofing_root / "proofing_report.md", "# Proofing Report\n\nLayout is clean.\n")
    write_text(proofing_root / "language_issues.md", "# Language Issues\n\nNone.\n")

    refreshed = service.snapshot(snapshot["quest_id"])
    health = refreshed["paper_contract_health"]

    assert health["bundle_status"] == "present"
    assert health["submission_checklist_ready"] is True
    assert health["submission_blocking_item_count"] == 1
    assert health["audit_package_ready"] is True
    assert health["finalize_ready"] is False
    assert health["closure_state"] == "audit_ready_with_blockers"
    assert health["delivery_state"] == "audit_ready"
    assert health["recommended_next_stage"] == "write"
    assert health["recommended_action"] == "finish_proofing_and_submission_checks"
    assert "submission packaging checklist still has 1 blocking item(s)" in " ".join(health["blocking_reasons"])


def test_snapshot_blocks_finalize_when_submission_minimal_surface_is_missing(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    service = QuestService(temp_home, skill_installer=SkillInstaller(repo_root(), temp_home))
    snapshot = service.create("paper missing submission minimal quest")
    quest_root = Path(snapshot["quest_root"])
    study_root = temp_home / "studies" / "001-risk"

    _materialize_ready_paper_line_for_publication_gate(
        quest_root,
        study_root_ref=str(study_root),
    )

    refreshed = service.snapshot(snapshot["quest_id"])
    health = refreshed["paper_contract_health"]

    assert health["submission_checklist_ready"] is True
    assert health["submission_checklist_handoff_ready"] is True
    assert health["submission_minimal_ready"] is False
    assert health["submission_minimal_manifest_path"] is None
    assert health["submission_minimal_docx_present"] is False
    assert health["submission_minimal_pdf_present"] is False
    assert health["audit_package_ready"] is True
    assert health["finalize_ready"] is False
    assert health["closure_state"] == "audit_ready_with_blockers"
    assert health["delivery_state"] == "audit_ready"
    assert health["recommended_next_stage"] == "write"
    assert health["recommended_action"] == "finish_proofing_and_submission_checks"
    assert "submission-minimal package is incomplete" in " ".join(health["blocking_reasons"])


def test_snapshot_blocks_finalize_when_submission_minimal_omits_display_exports(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    service = QuestService(temp_home, skill_installer=SkillInstaller(repo_root(), temp_home))
    snapshot = service.create("paper missing submission display exports quest")
    quest_root = Path(snapshot["quest_root"])
    study_root = temp_home / "studies" / "001-risk"

    paper_root = _materialize_ready_paper_line_for_publication_gate(
        quest_root,
        study_root_ref=str(study_root),
    )
    _materialize_submission_minimal_projection(paper_root, include_display_exports=False)
    write_json(
        paper_root / "figure_catalog.json",
        {
            "figures": [
                {
                    "figure_id": "F1",
                    "paper_role": "main_text",
                    "title": "Main architecture figure",
                }
            ]
        },
    )
    write_json(
        paper_root / "table_catalog.json",
        {
            "tables": [
                {
                    "table_id": "T1",
                    "title": "Baseline table",
                }
            ]
        },
    )

    refreshed = service.snapshot(snapshot["quest_id"])
    health = refreshed["paper_contract_health"]

    assert health["submission_minimal_ready"] is False
    assert health["submission_minimal_docx_present"] is True
    assert health["submission_minimal_pdf_present"] is True
    assert health["submission_minimal_expected_main_text_figure_count"] == 1
    assert health["submission_minimal_materialized_main_text_figure_count"] == 0
    assert health["submission_minimal_missing_main_text_figure_ids"] == ["F1"]
    assert health["submission_minimal_expected_table_count"] == 1
    assert health["submission_minimal_materialized_table_count"] == 0
    assert health["submission_minimal_missing_table_ids"] == ["T1"]
    assert health["recommended_next_stage"] == "write"
    assert health["recommended_action"] == "finish_proofing_and_submission_checks"
    assert "submission-minimal package is missing figure exports for the active display set" in " ".join(
        health["blocking_reasons"]
    )
    assert "submission-minimal package is missing table exports for the active display set" in " ".join(
        health["blocking_reasons"]
    )


def test_snapshot_routes_back_to_write_when_result_display_surface_is_setup_only(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    service = QuestService(temp_home, skill_installer=SkillInstaller(repo_root(), temp_home))
    snapshot = service.create("paper display sufficiency quest")
    quest_root = Path(snapshot["quest_root"])
    study_root = temp_home / "studies" / "001-risk"

    paper_root = _materialize_ready_paper_line_for_publication_gate(
        quest_root,
        study_root_ref=str(study_root),
    )
    write_json(
        paper_root / "medical_reporting_contract.json",
        {
            "status": "resolved",
            "study_root": str(study_root),
            "publication_profile": "general_medical_journal",
            "manuscript_family": "clinical_observation",
            "reporting_guideline_family": "STROBE",
            "display_shell_plan": [
                {
                    "display_id": "cohort_flow",
                    "display_kind": "figure",
                    "requirement_key": "cohort_flow_figure",
                    "catalog_id": "F1",
                },
                {
                    "display_id": "baseline_characteristics",
                    "display_kind": "table",
                    "requirement_key": "table1_baseline_characteristics",
                    "catalog_id": "T1",
                },
            ],
        },
    )
    write_json(
        paper_root / "results_narrative_map.json",
        {
            "sections": [
                {
                    "section_id": "historical-to-current-patient-migration",
                    "section_title": "Historical-to-current patient migration",
                    "research_question": "Did patient treatment use migrate?",
                    "direct_answer": "Yes.",
                    "supporting_display_items": ["F1", "T1"],
                    "key_quantitative_findings": ["Biologic use increased."],
                    "clinical_meaning": "Patterns shifted.",
                    "boundary": "Descriptive only.",
                }
            ]
        },
    )
    write_json(
        paper_root / "figure_catalog.json",
        {
            "figures": [
                {
                    "figure_id": "F1",
                    "paper_role": "main_text",
                    "title": "Cohort flow",
                }
            ]
        },
    )
    write_json(
        paper_root / "table_catalog.json",
        {
            "tables": [
                {
                    "table_id": "T1",
                    "title": "Baseline characteristics",
                }
            ]
        },
    )

    refreshed = service.snapshot(snapshot["quest_id"])
    health = refreshed["paper_contract_health"]

    assert health["recommended_next_stage"] == "write"
    assert health["recommended_action"] == "expand_result_display_surface"
    assert "main-text results sections still rely only on study-setup displays" in " ".join(health["blocking_reasons"])


def test_snapshot_routes_back_to_write_when_display_frontier_is_below_contract_ambition(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    service = QuestService(temp_home, skill_installer=SkillInstaller(repo_root(), temp_home))
    snapshot = service.create("paper display frontier quest")
    quest_root = Path(snapshot["quest_root"])
    study_root = temp_home / "studies" / "001-risk"

    paper_root = _materialize_ready_paper_line_for_publication_gate(
        quest_root,
        study_root_ref=str(study_root),
    )
    write_json(
        paper_root / "medical_reporting_contract.json",
        {
            "status": "resolved",
            "study_root": str(study_root),
            "publication_profile": "general_medical_journal",
            "manuscript_family": "clinical_observation",
            "reporting_guideline_family": "STROBE",
            "display_ambition": "strong",
            "minimum_main_text_figures": 4,
            "recommended_main_text_figures": [
                {
                    "catalog_id": "F2",
                    "display_kind": "figure",
                    "story_role": "result_primary",
                    "narrative_purpose": "historical_to_current_patient_migration",
                    "tier": "core",
                },
                {
                    "catalog_id": "F3",
                    "display_kind": "figure",
                    "story_role": "result_alignment",
                    "narrative_purpose": "clinician_surface_and_guideline_alignment",
                    "tier": "core",
                },
                {
                    "catalog_id": "F4",
                    "display_kind": "figure",
                    "story_role": "result_interpretive",
                    "narrative_purpose": "divergence_decomposition_or_robustness",
                    "tier": "core",
                },
            ],
            "display_shell_plan": [
                {
                    "display_id": "cohort_flow",
                    "display_kind": "figure",
                    "requirement_key": "cohort_flow_figure",
                    "catalog_id": "F1",
                    "story_role": "study_setup",
                },
                {
                    "display_id": "treatment_class_comparison",
                    "display_kind": "table",
                    "requirement_key": "table2_treatment_class_comparison",
                    "catalog_id": "T2",
                    "story_role": "result_primary",
                },
                {
                    "display_id": "practical_factor_comparison",
                    "display_kind": "table",
                    "requirement_key": "table3_practical_factor_comparison",
                    "catalog_id": "T3",
                    "story_role": "result_interpretive",
                },
                {
                    "display_id": "preferred_class_sensitivity",
                    "display_kind": "table",
                    "requirement_key": "table4_preferred_class_sensitivity",
                    "catalog_id": "T4",
                    "story_role": "result_sensitivity",
                },
            ],
        },
    )
    write_json(
        paper_root / "results_narrative_map.json",
        {
            "sections": [
                {
                    "section_id": "historical-to-current-patient-migration",
                    "section_title": "Historical-to-current patient migration",
                    "research_question": "Did patient treatment use migrate?",
                    "direct_answer": "Yes.",
                    "supporting_display_items": ["T2"],
                    "key_quantitative_findings": ["Biologic use increased."],
                    "clinical_meaning": "Patterns shifted.",
                    "boundary": "Descriptive only.",
                },
                {
                    "section_id": "clinician-surface-and-guideline-alignment",
                    "section_title": "Clinician preference and guideline alignment",
                    "research_question": "Did clinician preference align?",
                    "direct_answer": "Mostly.",
                    "supporting_display_items": ["T2", "T3"],
                    "key_quantitative_findings": ["IL-17 alignment remained close."],
                    "clinical_meaning": "Directionally aligned.",
                    "boundary": "Descriptive only.",
                },
            ]
        },
    )
    write_json(
        paper_root / "figure_catalog.json",
        {
            "figures": [
                {
                    "figure_id": "F1",
                    "paper_role": "main_text",
                    "title": "Cohort flow",
                }
            ]
        },
    )
    write_json(
        paper_root / "table_catalog.json",
        {
            "tables": [
                {"table_id": "T2", "title": "Treatment class comparison"},
                {"table_id": "T3", "title": "Practical factor comparison"},
                {"table_id": "T4", "title": "Preferred class sensitivity"},
            ]
        },
    )

    refreshed = service.snapshot(snapshot["quest_id"])
    health = refreshed["paper_contract_health"]

    assert health["results_display_surface_ready"] is True
    assert health["display_strength_ready"] is False
    assert health["active_main_text_figure_count"] == 1
    assert health["minimum_main_text_figures"] == 4
    assert health["missing_recommended_main_text_figure_ids"] == ["F2", "F3", "F4"]
    assert health["recommended_next_stage"] == "write"
    assert health["recommended_action"] == "expand_result_display_frontier"
    assert "main-text figure ambition remains below contract target" in " ".join(health["blocking_reasons"])


def test_snapshot_prefers_richer_nested_figure_catalog_over_legacy_root_projection(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    service = QuestService(temp_home, skill_installer=SkillInstaller(repo_root(), temp_home))
    snapshot = service.create("paper display frontier nested figure catalog quest")
    quest_root = Path(snapshot["quest_root"])
    study_root = temp_home / "studies" / "001-risk"

    paper_root = _materialize_ready_paper_line_for_publication_gate(
        quest_root,
        study_root_ref=str(study_root),
    )
    write_json(
        paper_root / "medical_reporting_contract.json",
        {
            "status": "resolved",
            "study_root": str(study_root),
            "study_archetype": "survey_trend_analysis",
            "endpoint_type": "descriptive",
            "publication_profile": "general_medical_journal",
            "manuscript_family": "clinical_observation",
            "reporting_guideline_family": "STROBE",
            "display_shell_plan": [
                {
                    "display_id": "cohort_flow",
                    "display_kind": "figure",
                    "requirement_key": "cohort_flow_figure",
                    "catalog_id": "F1",
                    "story_role": "study_setup",
                },
                {
                    "display_id": "treatment_class_comparison",
                    "display_kind": "table",
                    "requirement_key": "table2_treatment_class_comparison",
                    "catalog_id": "T2",
                    "story_role": "result_primary",
                },
            ],
        },
    )
    write_json(
        paper_root / "results_narrative_map.json",
        {
            "sections": [
                {
                    "section_id": "historical-to-current-patient-migration",
                    "section_title": "Historical-to-current patient migration",
                    "research_question": "Did patient treatment use migrate?",
                    "direct_answer": "Yes.",
                    "supporting_display_items": ["T2"],
                    "key_quantitative_findings": ["Biologic use increased."],
                    "clinical_meaning": "Patterns shifted.",
                    "boundary": "Descriptive only.",
                }
            ]
        },
    )
    write_json(
        paper_root / "figure_catalog.json",
        {
            "figures": [
                {
                    "figure_id": "F1",
                    "display_id": "cohort_flow",
                    "catalog_id": "F1",
                    "title": "Legacy projected cohort flow",
                }
            ]
        },
    )
    write_json(
        paper_root / "figures" / "figure_catalog.json",
        {
            "figures": [
                {
                    "figure_id": "F1",
                    "paper_role": "main_text",
                    "display_id": "cohort_flow",
                    "title": "Richer cohort flow catalog",
                }
            ]
        },
    )
    write_json(
        paper_root / "table_catalog.json",
        {
            "tables": [
                {"table_id": "T2", "title": "Treatment class comparison"},
            ]
        },
    )

    refreshed = service.snapshot(snapshot["quest_id"])
    health = refreshed["paper_contract_health"]

    assert health["display_ambition"] == "strong"
    assert health["active_main_text_figure_count"] == 1
    assert health["minimum_main_text_figures"] == 4
    assert health["missing_recommended_main_text_figure_ids"] == ["F2", "F3", "F4"]
    assert health["recommended_action"] == "expand_result_display_frontier"


def test_snapshot_accepts_result_display_when_catalog_materializes_main_text_figure_outside_contract_shell_plan(
    temp_home: Path,
) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    service = QuestService(temp_home, skill_installer=SkillInstaller(repo_root(), temp_home))
    snapshot = service.create("paper display sufficiency fallback quest")
    quest_root = Path(snapshot["quest_root"])
    study_root = temp_home / "studies" / "001-risk"

    paper_root = _materialize_ready_paper_line_for_publication_gate(
        quest_root,
        study_root_ref=str(study_root),
    )
    write_json(
        paper_root / "medical_reporting_contract.json",
        {
            "status": "resolved",
            "study_root": str(study_root),
            "publication_profile": "general_medical_journal",
            "manuscript_family": "clinical_observation",
            "reporting_guideline_family": "STROBE",
            "display_shell_plan": [
                {
                    "display_id": "cohort_flow",
                    "display_kind": "figure",
                    "requirement_key": "cohort_flow_figure",
                    "catalog_id": "S1",
                },
                {
                    "display_id": "baseline_characteristics",
                    "display_kind": "table",
                    "requirement_key": "table1_baseline_characteristics",
                    "catalog_id": "T1",
                },
            ],
        },
    )
    write_json(
        paper_root / "results_narrative_map.json",
        {
            "sections": [
                {
                    "section_id": "results-local-architecture",
                    "section_title": "Local architecture",
                    "research_question": "What does the local structure show?",
                    "direct_answer": "The local structure is already supported by a result-facing figure.",
                    "supporting_display_items": ["S1", "F1", "T1"],
                    "key_quantitative_findings": ["Result-facing figure exists."],
                    "clinical_meaning": "Result display is present.",
                    "boundary": "Descriptive only.",
                }
            ]
        },
    )
    write_json(
        paper_root / "figures" / "figure_catalog.json",
        {
            "figures": [
                {
                    "figure_id": "S1",
                    "paper_role": "main_text",
                    "title": "Cohort flow",
                },
                {
                    "figure_id": "F1",
                    "paper_role": "main_text",
                    "title": "Architecture summary",
                },
            ]
        },
    )
    write_json(
        paper_root / "tables" / "table_catalog.json",
        {
            "tables": [
                {
                    "table_id": "T1",
                    "title": "Baseline characteristics",
                }
            ]
        },
    )

    refreshed = service.snapshot(snapshot["quest_id"])
    health = refreshed["paper_contract_health"]

    assert health["recommended_action"] != "expand_result_display_surface"
    assert "main-text results sections still rely only on study-setup displays" not in " ".join(
        health["blocking_reasons"]
    )


def test_snapshot_infers_display_frontier_from_legacy_survey_trend_contract(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    service = QuestService(temp_home, skill_installer=SkillInstaller(repo_root(), temp_home))
    snapshot = service.create("legacy survey trend display frontier quest")
    quest_root = Path(snapshot["quest_root"])
    study_root = temp_home / "studies" / "001-risk"

    paper_root = _materialize_ready_paper_line_for_publication_gate(
        quest_root,
        study_root_ref=str(study_root),
    )
    write_json(
        paper_root / "medical_reporting_contract.json",
        {
            "status": "resolved",
            "study_root": str(study_root),
            "study_archetype": "survey_trend_analysis",
            "endpoint_type": "descriptive",
            "publication_profile": "general_medical_journal",
            "manuscript_family": "clinical_observation",
            "reporting_guideline_family": "STROBE",
            "display_shell_plan": [
                {
                    "display_id": "cohort_flow",
                    "display_kind": "figure",
                    "requirement_key": "cohort_flow_figure",
                    "catalog_id": "F1",
                    "story_role": "study_setup",
                },
                {
                    "display_id": "treatment_class_comparison",
                    "display_kind": "table",
                    "requirement_key": "table2_treatment_class_comparison",
                    "catalog_id": "T2",
                    "story_role": "result_primary",
                },
                {
                    "display_id": "practical_factor_comparison",
                    "display_kind": "table",
                    "requirement_key": "table3_practical_factor_comparison",
                    "catalog_id": "T3",
                    "story_role": "result_interpretive",
                },
            ],
        },
    )
    write_json(
        paper_root / "results_narrative_map.json",
        {
            "sections": [
                {
                    "section_id": "historical-to-current-patient-migration",
                    "section_title": "Historical-to-current patient migration",
                    "research_question": "Did patient treatment use migrate?",
                    "direct_answer": "Yes.",
                    "supporting_display_items": ["T2"],
                    "key_quantitative_findings": ["Biologic use increased."],
                    "clinical_meaning": "Patterns shifted.",
                    "boundary": "Descriptive only.",
                }
            ]
        },
    )
    write_json(
        paper_root / "figure_catalog.json",
        {
            "figures": [
                {
                    "figure_id": "F1",
                    "paper_role": "main_text",
                    "title": "Cohort flow",
                }
            ]
        },
    )
    write_json(
        paper_root / "table_catalog.json",
        {
            "tables": [
                {"table_id": "T2", "title": "Treatment class comparison"},
                {"table_id": "T3", "title": "Practical factor comparison"},
            ]
        },
    )

    refreshed = service.snapshot(snapshot["quest_id"])
    health = refreshed["paper_contract_health"]

    assert health["display_ambition"] == "strong"
    assert health["minimum_main_text_figures"] == 4
    assert health["display_strength_ready"] is False
    assert health["missing_recommended_main_text_figure_ids"] == ["F2", "F3", "F4"]
    assert health["recommended_action"] == "expand_result_display_frontier"


def test_snapshot_blocks_completion_approval_when_managed_publication_eval_is_not_clear(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    service = QuestService(temp_home, skill_installer=SkillInstaller(repo_root(), temp_home))
    snapshot = service.create("paper blocked by managed publication gate")
    quest_root = Path(snapshot["quest_root"])
    study_root = temp_home / "studies" / "001-risk"

    _write_managed_publication_eval_latest(
        study_root,
        quest_id=snapshot["quest_id"],
        payload={
            "verdict": {
                "overall_verdict": "blocked",
                "primary_claim_status": "partial",
                "summary": "publication gate still blocks completion",
                "stop_loss_pressure": "watch",
            },
            "gaps": [
                {
                    "gap_id": "gap-001",
                    "gap_type": "reporting",
                    "severity": "must_fix",
                    "summary": "forbidden_manuscript_terminology",
                }
            ],
            "recommended_actions": [
                {
                    "action_id": "action-001",
                    "action_type": "return_to_controller",
                    "priority": "now",
                    "reason": "publication gate still blocks completion",
                    "requires_controller_decision": True,
                }
            ],
        },
    )

    _materialize_ready_paper_line_for_publication_gate(
        quest_root,
        study_root_ref=str(study_root),
    )

    refreshed = service.snapshot(snapshot["quest_id"])
    health = refreshed["paper_contract_health"]

    assert health["writing_ready"] is True
    assert health["audit_package_ready"] is True
    assert health["managed_publication_gate_status"] == "blocked"
    assert health["managed_publication_gate_clear"] is False
    assert health["finalize_ready"] is False
    assert health["completion_approval_ready"] is False
    joined = " ".join(health["completion_blocking_reasons"])
    assert "forbidden_manuscript_terminology" in joined


def test_snapshot_prefers_display_frontier_when_managed_gate_clear_reports_figure_floor_gap(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    service = QuestService(temp_home, skill_installer=SkillInstaller(repo_root(), temp_home))
    snapshot = service.create("paper display frontier is still required by managed gate")
    quest_root = Path(snapshot["quest_root"])
    study_root = temp_home / "studies" / "001-risk"

    _write_managed_publication_eval_latest(
        study_root,
        quest_id=snapshot["quest_id"],
        payload={
            "verdict": {
                "overall_verdict": "clear",
                "primary_claim_status": "supported",
                "summary": "publication gate clears write-stage continuation",
                "stop_loss_pressure": "watch",
            },
            "gaps": [
                {
                    "gap_id": "gap-001",
                    "gap_type": "display_frontier",
                    "severity": "should_fix",
                    "summary": "submission_grade_active_figure_floor_unmet",
                }
            ],
            "recommended_actions": [
                {
                    "action_id": "action-001",
                    "action_type": "continue_runtime",
                    "priority": "now",
                    "reason": "main-text figure ambition still needs expansion",
                }
            ],
        },
    )

    _materialize_ready_paper_line_for_publication_gate(
        quest_root,
        study_root_ref=str(study_root),
    )

    refreshed = service.snapshot(snapshot["quest_id"])
    health = refreshed["paper_contract_health"]

    assert health["managed_publication_gate_status"] == "clear"
    assert health["managed_publication_gate_clear"] is True
    assert health["managed_publication_gate_gap_summaries"] == ["submission_grade_active_figure_floor_unmet"]
    assert health["recommended_next_stage"] == "write"
    assert health["recommended_action"] == "expand_result_display_frontier"
    assert "submission_grade_active_figure_floor_unmet" in health["blocking_reasons"]


def test_snapshot_resolves_relative_study_root_for_managed_publication_eval(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    service = QuestService(temp_home, skill_installer=SkillInstaller(repo_root(), temp_home))
    snapshot = service.create("paper blocked by managed publication gate with relative study root")
    quest_root = Path(snapshot["quest_root"])
    study_root = temp_home / "studies" / "001-risk"

    _write_managed_publication_eval_latest(
        study_root,
        quest_id=snapshot["quest_id"],
        payload={
            "eval_id": "eval-001",
            "emitted_at": "2026-04-10T00:00:00Z",
            "evaluation_scope": "paper_gate",
            "charter_context_ref": {
                "ref": "artifacts/controller/study_charter.json",
                "charter_id": "charter-001",
                "publication_objective": "manuscript_ready",
            },
            "runtime_context_refs": {
                "runtime_escalation_ref": "artifacts/runtime/runtime_supervision/latest.json",
                "main_result_ref": "artifacts/results/main.json",
            },
            "delivery_context_refs": {
                "paper_root_ref": "paper",
                "submission_minimal_ref": "paper/submission_minimal",
            },
            "verdict": {
                "overall_verdict": "blocked",
                "primary_claim_status": "partial",
                "summary": "publication gate still blocks completion",
                "stop_loss_pressure": "watch",
            },
            "gaps": [
                {
                    "gap_id": "gap-001",
                    "gap_type": "reporting",
                    "severity": "must_fix",
                    "summary": "forbidden_manuscript_terminology",
                    "evidence_refs": ["paper/draft.md"],
                }
            ],
            "recommended_actions": [
                {
                    "action_id": "action-001",
                    "action_type": "return_to_controller",
                    "priority": "now",
                    "reason": "publication gate still blocks completion",
                    "evidence_refs": ["paper/draft.md"],
                    "requires_controller_decision": True,
                }
            ],
        },
    )

    _materialize_ready_paper_line_for_publication_gate(
        quest_root,
        study_root_ref="../../studies/001-risk",
    )

    refreshed = service.snapshot(snapshot["quest_id"])
    health = refreshed["paper_contract_health"]

    assert health["managed_publication_gate_status"] == "blocked"
    assert health["managed_publication_eval_path"] == str(study_root / "artifacts" / "publication_eval" / "latest.json")
    assert "forbidden_manuscript_terminology" in " ".join(health["completion_blocking_reasons"])


def test_snapshot_marks_invalid_when_managed_publication_eval_schema_is_incomplete(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    service = QuestService(temp_home, skill_installer=SkillInstaller(repo_root(), temp_home))
    snapshot = service.create("paper blocked by invalid managed publication gate payload")
    quest_root = Path(snapshot["quest_root"])
    study_root = temp_home / "studies" / "001-risk"

    _write_managed_publication_eval_latest(
        study_root,
        quest_id=snapshot["quest_id"],
        payload={
            "verdict": {
                "overall_verdict": "blocked",
            },
            "gaps": [],
            "recommended_actions": [],
        },
    )

    _materialize_ready_paper_line_for_publication_gate(
        quest_root,
        study_root_ref=str(study_root),
    )

    refreshed = service.snapshot(snapshot["quest_id"])
    health = refreshed["paper_contract_health"]

    assert health["managed_publication_gate_status"] == "invalid"
    assert health["managed_publication_gate_clear"] is False
    assert "invalid" in str(health["managed_publication_gate_summary"] or "")


def test_snapshot_keeps_publication_gate_nonclear_when_promising_eval_requires_controller_decision(
    temp_home: Path,
) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    service = QuestService(temp_home, skill_installer=SkillInstaller(repo_root(), temp_home))
    snapshot = service.create("paper gate stays nonclear when continue_same_line still needs controller decision")
    quest_root = Path(snapshot["quest_root"])
    study_root = temp_home / "studies" / "001-risk"

    _write_managed_publication_eval_latest(
        study_root,
        quest_id=snapshot["quest_id"],
        payload={
            "verdict": {
                "overall_verdict": "promising",
                "summary": "bundle-stage work is unlocked and can proceed on the critical path",
            },
            "gaps": [
                {
                    "summary": "bundle-stage work is unlocked and can proceed on the critical path",
                    "severity": "optional",
                }
            ],
            "recommended_actions": [
                {
                    "action_type": "continue_same_line",
                    "requires_controller_decision": True,
                }
            ],
        },
    )

    _materialize_ready_paper_line_for_publication_gate(
        quest_root,
        study_root_ref=str(study_root),
    )

    refreshed = service.snapshot(snapshot["quest_id"])
    health = refreshed["paper_contract_health"]

    assert health["managed_publication_gate_status"] == "promising"
    assert health["managed_publication_gate_clear"] is False
    assert "controller decision" in str(health["managed_publication_gate_summary"] or "")


def test_snapshot_updated_at_tracks_managed_publication_eval_emitted_at(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    service = QuestService(temp_home, skill_installer=SkillInstaller(repo_root(), temp_home))
    snapshot = service.create("paper progress timestamp follows managed publication eval")
    quest_root = Path(snapshot["quest_root"])
    study_root = temp_home / "studies" / "001-risk"

    quest_yaml = service.read_quest_yaml(quest_root)
    quest_yaml["updated_at"] = "2026-04-17T01:54:53+00:00"
    write_yaml(quest_root / "quest.yaml", quest_yaml)

    emitted_at = "2026-04-18T00:52:16+00:00"
    _write_managed_publication_eval_latest(
        study_root,
        quest_id=snapshot["quest_id"],
        payload={
            "emitted_at": emitted_at,
            "verdict": {
                "overall_verdict": "blocked",
                "summary": "Reporting checklist remains incomplete.",
            },
            "gaps": [
                {
                    "summary": "missing_reporting_guideline_checklist",
                }
            ],
            "recommended_actions": [
                {
                    "action_type": "continue_runtime",
                }
            ],
        },
    )

    _materialize_ready_paper_line_for_publication_gate(
        quest_root,
        study_root_ref=str(study_root),
    )

    refreshed = service.snapshot(snapshot["quest_id"])
    compact = service.summary_compact(snapshot["quest_id"])

    assert refreshed["updated_at"] == emitted_at
    assert compact["updated_at"] == emitted_at
    assert service.list_quests()[0]["updated_at"] == emitted_at


def test_snapshot_updated_at_refreshes_when_managed_publication_eval_changes(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    service = QuestService(temp_home, skill_installer=SkillInstaller(repo_root(), temp_home))
    snapshot = service.create("paper progress timestamp refreshes after managed publication eval updates")
    quest_root = Path(snapshot["quest_root"])
    study_root = temp_home / "studies" / "001-risk"

    quest_yaml = service.read_quest_yaml(quest_root)
    quest_yaml["updated_at"] = "2026-04-17T01:54:53+00:00"
    write_yaml(quest_root / "quest.yaml", quest_yaml)

    _materialize_ready_paper_line_for_publication_gate(
        quest_root,
        study_root_ref=str(study_root),
    )

    first_emitted_at = "2026-04-18T00:52:16+00:00"
    _write_managed_publication_eval_latest(
        study_root,
        quest_id=snapshot["quest_id"],
        payload={
            "emitted_at": first_emitted_at,
            "verdict": {
                "overall_verdict": "blocked",
                "summary": "Reporting checklist remains incomplete.",
            },
            "gaps": [
                {
                    "summary": "missing_reporting_guideline_checklist",
                }
            ],
            "recommended_actions": [
                {
                    "action_type": "continue_runtime",
                }
            ],
        },
    )

    initial_snapshot = service.snapshot(snapshot["quest_id"])
    initial_compact = service.summary_compact(snapshot["quest_id"])

    assert initial_snapshot["updated_at"] == first_emitted_at
    assert initial_compact["updated_at"] == first_emitted_at

    refreshed_emitted_at = "2026-04-18T12:08:03+00:00"
    _write_managed_publication_eval_latest(
        study_root,
        quest_id=snapshot["quest_id"],
        payload={
            "emitted_at": refreshed_emitted_at,
            "verdict": {
                "overall_verdict": "blocked",
                "summary": "Reporting checklist still needs guideline coverage and revised evidence links.",
            },
            "gaps": [
                {
                    "summary": "missing_reporting_guideline_checklist",
                },
                {
                    "summary": "missing_evidence_linkage_refresh",
                },
            ],
            "recommended_actions": [
                {
                    "action_type": "continue_runtime",
                }
            ],
        },
    )

    refreshed_snapshot = service.snapshot(snapshot["quest_id"])
    refreshed_compact = service.summary_compact(snapshot["quest_id"])

    assert refreshed_snapshot["updated_at"] == refreshed_emitted_at
    assert refreshed_compact["updated_at"] == refreshed_emitted_at
    assert service.list_quests()[0]["updated_at"] == refreshed_emitted_at


def test_stopped_snapshot_updated_at_ignores_managed_publication_eval_refresh(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    service = QuestService(temp_home, skill_installer=SkillInstaller(repo_root(), temp_home))
    snapshot = service.create("stopped paper keeps stop timestamp in list")
    quest_root = Path(snapshot["quest_root"])
    study_root = temp_home / "studies" / "001-risk"

    stopped_at = "2026-04-24T06:57:05+00:00"
    quest_yaml = service.read_quest_yaml(quest_root)
    quest_yaml["status"] = "stopped"
    quest_yaml["updated_at"] = stopped_at
    write_yaml(quest_root / "quest.yaml", quest_yaml)
    write_text(
        quest_root / "status.md",
        "\n".join(
            [
                "# Status",
                "",
                "Current Quest Route: `decision` / `stop` on `paper/main`.",
                "",
                f"- Updated at: {stopped_at}",
                "- Quest-Level Next Stage: `decision`",
                "- Quest-Level Next Action: `stop`",
                "",
            ]
        ),
    )
    service.update_runtime_state(
        quest_root=quest_root,
        status="stopped",
        active_run_id=None,
        stop_reason="content milestone reached",
        last_transition_at=stopped_at,
    )

    refreshed_eval_at = "2026-04-24T13:03:47+00:00"
    _write_managed_publication_eval_latest(
        study_root,
        quest_id=snapshot["quest_id"],
        payload={
            "emitted_at": refreshed_eval_at,
            "verdict": {
                "overall_verdict": "blocked",
                "summary": "Publication gate projection was refreshed after stop.",
            },
            "gaps": [
                {
                    "summary": "stale_submission_minimal_authority",
                }
            ],
            "recommended_actions": [
                {
                    "action_type": "return_to_publishability_gate",
                }
            ],
        },
    )
    _materialize_ready_paper_line_for_publication_gate(
        quest_root,
        study_root_ref=str(study_root),
    )

    refreshed = service.snapshot(snapshot["quest_id"])
    compact = service.summary_compact(snapshot["quest_id"])

    assert refreshed["runtime_status"] == "stopped"
    assert refreshed["updated_at"] == stopped_at
    assert compact["updated_at"] == stopped_at
    assert service.list_quests()[0]["updated_at"] == stopped_at


def test_list_quests_handles_null_updated_at_without_crashing(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    service = QuestService(temp_home)


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

def test_init_command_does_not_sync_global_skills(temp_home: Path, monkeypatch) -> None:
    ensure_home_layout(temp_home)

    calls: list[str] = []

    def _record_sync(self):  # type: ignore[no-untyped-def]
        calls.append("sync_global")
        return {"codex": [], "claude": [], "notes": []}

    monkeypatch.setattr(SkillInstaller, "sync_global", _record_sync)
    exit_code = init_command(temp_home)
    assert exit_code in {0, 1}
    assert calls == []


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
