from __future__ import annotations

import json
from pathlib import Path
from urllib.error import HTTPError

import pytest

from deepscientist.artifact import ArtifactService
from deepscientist.config import ConfigManager
from deepscientist.home import ensure_home_layout, repo_root
from deepscientist.memory import MemoryService
from deepscientist.memory.frontmatter import dump_markdown_document, load_markdown_document
from deepscientist.quest import QuestService
from deepscientist.registries import BaselineRegistry
from deepscientist.shared import read_json, read_jsonl, read_yaml, write_json, write_yaml
from deepscientist.skills import SkillInstaller


def _confirm_local_baseline(artifact: ArtifactService, quest_root: Path, baseline_id: str = "baseline-local") -> dict:
    baseline_root = quest_root / "baselines" / "local" / baseline_id
    baseline_root.mkdir(parents=True, exist_ok=True)
    (baseline_root / "README.md").write_text("# Baseline\n", encoding="utf-8")
    return artifact.confirm_baseline(
        quest_root,
        baseline_path=str(baseline_root),
        baseline_id=baseline_id,
        summary=f"Confirmed {baseline_id}",
        metrics_summary={"acc": 0.8},
        primary_metric={"name": "acc", "value": 0.8},
        metric_contract={
            "primary_metric_id": "acc",
            "metrics": [{"metric_id": "acc", "direction": "higher"}],
        },
    )


def test_confirm_baseline_writes_metric_contract_json_and_exposes_path(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    quest_service = QuestService(temp_home, skill_installer=SkillInstaller(repo_root(), temp_home))
    quest = quest_service.create("baseline metric contract json quest")
    quest_root = Path(quest["quest_root"])
    artifact = ArtifactService(temp_home)

    result = _confirm_local_baseline(artifact, quest_root, baseline_id="baseline-metric-contract")

    assert result["ok"] is True
    confirmed_ref = result["confirmed_baseline_ref"]
    assert confirmed_ref["metric_contract_json_rel_path"] == "baselines/local/baseline-metric-contract/json/metric_contract.json"
    metric_contract_json = quest_root / confirmed_ref["metric_contract_json_rel_path"]
    assert metric_contract_json.exists()
    payload = read_json(metric_contract_json, {})
    assert payload["kind"] == "baseline_metric_contract"
    assert payload["baseline_id"] == "baseline-metric-contract"
    assert payload["metric_contract"]["primary_metric_id"] == "acc"
    attachment = read_yaml(quest_root / "baselines" / "imported" / "baseline-metric-contract" / "attachment.yaml", {})
    assert attachment["confirmation"]["metric_contract_json_rel_path"] == confirmed_ref["metric_contract_json_rel_path"]


class _FakeHeaders:
    def __init__(self, charset: str = "utf-8") -> None:
        self._charset = charset

    def get_content_charset(self) -> str:
        return self._charset


class _FakeUrlopenResponse:
    def __init__(self, body: str, *, charset: str = "utf-8") -> None:
        self._body = body.encode(charset)
        self.headers = _FakeHeaders(charset)

    def __enter__(self) -> "_FakeUrlopenResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def read(self) -> bytes:
        return self._body


def test_memory_documents_and_promotion(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    quest_service = QuestService(temp_home, skill_installer=SkillInstaller(repo_root(), temp_home))
    quest = quest_service.create("memory quest")
    quest_root = Path(quest["quest_root"])
    memory = MemoryService(temp_home)

    card = memory.write_card(
        scope="quest",
        kind="ideas",
        title="Reusable idea",
        body="A compact durable note.",
        quest_root=quest_root,
        quest_id=quest["quest_id"],
        tags=["test"],
    )
    assert Path(card["path"]).exists()

    documents = quest_service.list_documents(quest["quest_id"])
    memory_doc = next(item for item in documents if item["document_id"].startswith("memory::"))
    opened = quest_service.open_document(quest["quest_id"], memory_doc["document_id"])
    assert opened["writable"] is True
    assert "A compact durable note." in opened["content"]

    promoted = memory.promote_to_global(path=card["path"], quest_root=quest_root)
    assert Path(promoted["path"]).exists()
    assert promoted["scope"] == "global"

    skill_doc = next(item for item in documents if item["document_id"].startswith("skill::"))
    skill_opened = quest_service.open_document(quest["quest_id"], skill_doc["document_id"])
    assert skill_opened["writable"] is False


def test_memory_list_recent_and_search_prefer_latest_updates(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    quest_service = QuestService(temp_home, skill_installer=SkillInstaller(repo_root(), temp_home))
    quest = quest_service.create("memory ordering quest")
    quest_root = Path(quest["quest_root"])
    memory = MemoryService(temp_home)

    older = memory.write_card(
        scope="quest",
        kind="knowledge",
        title="Older lesson",
        body="adapter metric contract",
        quest_root=quest_root,
        quest_id=quest["quest_id"],
    )
    newer = memory.write_card(
        scope="quest",
        kind="knowledge",
        title="Newer lesson",
        body="adapter metric contract with better evidence",
        quest_root=quest_root,
        quest_id=quest["quest_id"],
    )

    for card, updated_at in (
        (older, "2026-03-11T10:00:00+00:00"),
        (newer, "2026-03-11T11:00:00+00:00"),
    ):
        path = Path(card["path"])
        metadata, body = load_markdown_document(path)
        metadata["created_at"] = updated_at
        metadata["updated_at"] = updated_at
        path.write_text(dump_markdown_document(metadata, body), encoding="utf-8")

    recent = memory.list_recent(scope="quest", quest_root=quest_root, kind="knowledge", limit=2)
    assert [item["title"] for item in recent] == [newer["title"], older["title"]]

    search = memory.search(
        "adapter metric contract",
        scope="quest",
        quest_root=quest_root,
        kind="knowledge",
        limit=2,
    )
    assert [item["title"] for item in search] == [newer["title"], older["title"]]


def test_artifact_interact_and_prepare_branch(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    quest_service = QuestService(temp_home, skill_installer=SkillInstaller(repo_root(), temp_home))
    quest = quest_service.create("artifact quest")
    quest_root = Path(quest["quest_root"])
    artifact = ArtifactService(temp_home)

    quest_service.append_message(quest["quest_id"], role="user", content="请先告诉我 baseline 情况。", source="web")
    result = artifact.interact(
        quest_root,
        kind="progress",
        message="Baseline is ready; I am summarizing the current metrics.",
        deliver_to_bound_conversations=True,
        include_recent_inbound_messages=True,
    )
    assert result["status"] == "ok"
    assert result["delivered"] is True
    assert result["recent_inbound_messages"]

    outbox = temp_home / "logs" / "connectors" / "local" / "outbox.jsonl"
    assert outbox.exists()
    records = [json.loads(line) for line in outbox.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert any("Baseline is ready" in (item.get("message") or "") for item in records)

    branch = artifact.prepare_branch(quest_root, run_id="run-main-001")
    assert branch["ok"] is True
    assert branch["branch"] == "run/run-main-001"
    assert Path(branch["worktree_root"]).exists()


def test_artifact_mailbox_preserves_user_message_attachments(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    quest_service = QuestService(temp_home, skill_installer=SkillInstaller(repo_root(), temp_home))
    quest = quest_service.create("artifact attachment mailbox quest")
    quest_root = Path(quest["quest_root"])
    artifact = ArtifactService(temp_home)

    quest_service.append_message(
        quest["quest_id"],
        role="user",
        content="Please inspect the attached PDF.",
        source="qq:direct:openid-123",
        attachments=[
            {
                "kind": "remote",
                "name": "report.pdf",
                "content_type": "application/pdf",
                "path": "attachments/report.pdf",
                "extracted_text_path": "attachments/report.txt",
            }
        ],
    )
    result = artifact.interact(
        quest_root,
        kind="progress",
        message="I am picking up the latest inbound request.",
        deliver_to_bound_conversations=False,
        include_recent_inbound_messages=True,
    )

    assert result["recent_inbound_messages"]
    latest = result["recent_inbound_messages"][-1]
    assert latest["conversation_id"] == "qq:direct:openid-123"
    assert latest["attachments"][0]["name"] == "report.pdf"
    assert latest["attachments"][0]["extracted_text_path"] == "attachments/report.txt"


def test_artifact_managed_git_flow_updates_research_state_and_mirrors_analysis(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    quest_service = QuestService(temp_home, skill_installer=SkillInstaller(repo_root(), temp_home))
    quest = quest_service.create("artifact flow quest")
    quest_root = Path(quest["quest_root"])
    artifact = ArtifactService(temp_home)
    _confirm_local_baseline(artifact, quest_root)

    created = artifact.submit_idea(
        quest_root,
        mode="create",
        title="Adapter route",
        problem="Baseline saturates.",
        hypothesis="A lightweight adapter improves generalization.",
        mechanism="Insert a small residual adapter before the head.",
        decision_reason="This is the strongest next idea.",
        next_target="experiment",
        draft_markdown="# Adapter route draft\n\n## Code-Level Change Plan\n\nPatch the adapter path.\n",
    )
    idea_worktree = Path(created["worktree_root"])
    idea_md_path = Path(created["idea_md_path"])
    idea_draft_path = Path(created["idea_draft_path"])
    assert created["branch"].startswith(f"idea/{quest['quest_id']}-")
    assert idea_worktree.exists()
    assert idea_md_path.exists()
    assert idea_draft_path.exists()
    assert "Adapter route draft" in idea_draft_path.read_text(encoding="utf-8")
    assert created["guidance"]
    assert created["recommended_skill_reads"] == ["experiment"]
    assert created["suggested_artifact_calls"]
    assert created["next_instruction"]
    assert quest_service.snapshot(quest["quest_id"])["active_anchor"] == "experiment"

    revised = artifact.submit_idea(
        quest_root,
        mode="revise",
        idea_id=created["idea_id"],
        title="Adapter route v2",
        problem="Baseline still underfits hard examples.",
        hypothesis="A tuned adapter improves hard-example recall.",
        mechanism="Tune the adapter depth and placement.",
        decision_reason="Refine the same active route before coding.",
        next_target="experiment",
        draft_markdown="# Adapter route v2 draft\n\n## Risks / Caveats / Implementation Notes\n\nMind the hard examples.\n",
    )
    assert revised["worktree_root"] == created["worktree_root"]
    assert "Adapter route v2" in idea_md_path.read_text(encoding="utf-8")
    assert "Adapter route v2 draft" in idea_draft_path.read_text(encoding="utf-8")
    assert revised["guidance"]
    assert revised["recommended_skill_reads"] == ["experiment"]
    assert revised["suggested_artifact_calls"]
    assert revised["next_instruction"]

    campaign = artifact.create_analysis_campaign(
        quest_root,
        campaign_title="Ablation suite",
        campaign_goal="Stress-test the promoted idea.",
        slices=[
            {
                "slice_id": "ablation",
                "title": "Adapter ablation",
                "goal": "Remove the adapter and compare.",
                "required_changes": "Disable the adapter path only.",
                "metric_contract": "Report full validation metrics.",
                "required_baselines": [
                    {
                        "baseline_id": "adapter-ablation-baseline",
                        "reason": "Need a clean comparator for the ablation slice.",
                        "benchmark": "val",
                        "split": "full",
                    }
                ],
            },
            {
                "slice_id": "robustness",
                "title": "Robustness check",
                "goal": "Run the intended robustness configuration.",
                "required_changes": "Apply the robustness config only.",
                "metric_contract": "Report the same full evaluation metrics.",
            },
        ],
    )
    assert campaign["ok"] is True
    assert campaign["campaign_id"]
    assert len(campaign["slices"]) == 2
    assert campaign["guidance"]
    assert campaign["recommended_skill_reads"]
    assert campaign["suggested_artifact_calls"]
    assert campaign["next_instruction"]
    first_slice = campaign["slices"][0]
    second_slice = campaign["slices"][1]
    assert first_slice["required_baselines"][0]["baseline_id"] == "adapter-ablation-baseline"
    assert Path(first_slice["worktree_root"]).exists()
    assert Path(second_slice["worktree_root"]).exists()
    analysis_inventory_path = quest_root / "artifacts" / "baselines" / "analysis_inventory.json"
    analysis_inventory = read_json(analysis_inventory_path, {})
    assert analysis_inventory_path.exists()
    assert analysis_inventory["entries"][0]["baseline_id"] == "adapter-ablation-baseline"
    assert analysis_inventory["entries"][0]["status"] == "required"

    state_after_campaign = quest_service.read_research_state(quest_root)
    assert state_after_campaign["active_analysis_campaign_id"] == campaign["campaign_id"]
    assert state_after_campaign["current_workspace_root"] == first_slice["worktree_root"]
    assert quest_service.snapshot(quest["quest_id"])["active_anchor"] == "analysis-campaign"

    analysis_baseline_root = quest_root / "baselines" / "local" / "adapter-ablation-baseline"
    analysis_baseline_root.mkdir(parents=True, exist_ok=True)
    (analysis_baseline_root / "README.md").write_text("# Analysis baseline\n", encoding="utf-8")

    first_record = artifact.record_analysis_slice(
        quest_root,
        campaign_id=campaign["campaign_id"],
        slice_id="ablation",
        setup="Disable the adapter path only.",
        execution="Ran the full validation sweep.",
        results="Accuracy dropped as expected.",
        evidence_paths=["experiments/analysis/ablation/result.json"],
        metric_rows=[{"name": "acc", "value": 0.84}],
        comparison_baselines=[
            {
                "baseline_id": "adapter-ablation-baseline",
                "baseline_root_rel_path": "baselines/local/adapter-ablation-baseline",
                "benchmark": "val",
                "split": "full",
                "metrics_summary": {"acc": 0.8},
                "published": True,
            }
        ],
    )
    assert first_record["ok"] is True
    assert first_record["completed"] is False
    assert first_record["next_slice"]["slice_id"] == "robustness"
    assert Path(first_record["mirror_path"]).exists()
    assert Path(first_record["result_json_path"]).exists()
    slice_result_payload = read_json(first_record["result_json_path"], {})
    assert slice_result_payload["comparison_baselines"][0]["baseline_id"] == "adapter-ablation-baseline"
    analysis_inventory = read_json(analysis_inventory_path, {})
    registered_entry = next(
        item for item in analysis_inventory["entries"] if item["baseline_id"] == "adapter-ablation-baseline"
    )
    assert registered_entry["status"] == "registered"
    assert registered_entry["baseline_root_rel_path"] == "baselines/local/adapter-ablation-baseline"

    second_record = artifact.record_analysis_slice(
        quest_root,
        campaign_id=campaign["campaign_id"],
        slice_id="robustness",
        setup="Apply the robustness configuration only.",
        execution="Ran the full robustness sweep.",
        results="The method stayed stable under the robustness setting.",
        evidence_paths=["experiments/analysis/robustness/result.json"],
        metric_rows=[{"name": "acc", "value": 0.86}],
    )
    assert second_record["ok"] is True
    assert second_record["completed"] is True
    assert second_record["returned_to_branch"] == created["branch"]
    assert Path(second_record["summary_path"]).exists()

    final_state = quest_service.read_research_state(quest_root)
    assert final_state["active_analysis_campaign_id"] is None
    assert final_state["current_workspace_root"] == str(idea_worktree)
    assert final_state["research_head_branch"] == created["branch"]
    assert quest_service.snapshot(quest["quest_id"])["active_anchor"] == "decision"

    events = read_jsonl(quest_root / ".ds" / "events.jsonl")
    campaign_event = next(
        item
        for item in reversed(events)
        if item.get("type") == "artifact.recorded"
        and item.get("flow_type") == "analysis_campaign"
        and item.get("protocol_step") == "complete"
    )
    assert campaign_event["workspace_root"] == str(idea_worktree)
    assert campaign_event["details"]["slice_count"] == 2


def test_paper_outline_flow_and_outline_bound_analysis_campaign(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    quest_service = QuestService(temp_home, skill_installer=SkillInstaller(repo_root(), temp_home))
    quest = quest_service.create("paper outline quest")
    quest_root = Path(quest["quest_root"])
    artifact = ArtifactService(temp_home)

    baseline_root = quest_root / "baselines" / "local" / "baseline-outline"
    baseline_root.mkdir(parents=True, exist_ok=True)
    (baseline_root / "README.md").write_text("# Baseline\n", encoding="utf-8")
    artifact.confirm_baseline(
        quest_root,
        baseline_path="baselines/local/baseline-outline",
        baseline_id="baseline-outline",
        summary="Baseline confirmed for outline-bound analysis.",
        metrics_summary={"acc": 0.88},
        metric_contract={"primary_metric_id": "acc", "direction": "maximize"},
        primary_metric={"metric_id": "acc", "value": 0.88},
    )
    created = artifact.submit_idea(
        quest_root,
        title="Outline-aware idea",
        problem="Need a stronger analysis plan.",
        hypothesis="Outline-driven analysis improves research discipline.",
        mechanism="Bind analysis tasks to paper questions and experiment designs.",
        expected_gain="Cleaner downstream writing.",
        decision_reason="Promote this line for paper-oriented experimentation.",
    )
    assert created["ok"] is True

    candidate_1 = artifact.submit_paper_outline(
        quest_root,
        mode="candidate",
        title="Outline A",
        note="First draft outline.",
        story="Tell the motivation-first story.",
        ten_questions=["Why now?", "Why this baseline?"],
        detailed_outline={
            "title": "Outline A",
            "abstract": "Abstract A",
            "research_questions": ["RQ1"],
            "methodology": "Method A",
            "experimental_designs": ["Exp-A"],
            "contributions": ["C1"],
        },
        review_result="candidate",
    )
    candidate_2 = artifact.submit_paper_outline(
        quest_root,
        mode="candidate",
        title="Outline B",
        note="Second draft outline.",
        story="Tell the evidence-first story.",
        ten_questions=["What changed?", "Why does it matter?"],
        detailed_outline={
            "title": "Outline B",
            "abstract": "Abstract B",
            "research_questions": ["RQ-main"],
            "methodology": "Method B",
            "experimental_designs": ["Exp-main"],
            "contributions": ["C-main"],
        },
        review_result="preferred",
    )
    candidate_3 = artifact.submit_paper_outline(
        quest_root,
        mode="candidate",
        title="Outline C",
        note="Third draft outline.",
        story="Tell the robustness-first story.",
        ten_questions=["What might fail?", "How do we know?"],
        detailed_outline={
            "title": "Outline C",
            "abstract": "Abstract C",
            "research_questions": ["RQ-aux"],
            "methodology": "Method C",
            "experimental_designs": ["Exp-aux"],
            "contributions": ["C-aux"],
        },
        review_result="backup",
    )
    assert candidate_1["outline_id"] == "outline-001"
    assert candidate_2["outline_id"] == "outline-002"
    assert candidate_3["outline_id"] == "outline-003"

    selected = artifact.submit_paper_outline(
        quest_root,
        mode="select",
        outline_id="outline-002",
        selected_reason="This version best matches the intended main claim and experiment design.",
    )
    assert selected["ok"] is True
    assert Path(selected["selected_outline_path"]).exists()
    assert Path(selected["outline_selection_path"]).exists()
    assert quest_service.snapshot(quest["quest_id"])["active_anchor"] == "write"

    campaign = artifact.create_analysis_campaign(
        quest_root,
        campaign_title="Outline-bound analysis",
        campaign_goal="Answer the selected paper questions cleanly.",
        selected_outline_ref="outline-002",
        research_questions=["RQ-main"],
        experimental_designs=["Exp-main"],
        todo_items=[
            {
                "todo_id": "todo-001",
                "slice_id": "ablation",
                "title": "Ablation for RQ-main",
                "research_question": "RQ-main",
                "experimental_design": "Exp-main",
                "completion_condition": "Show whether the core module is necessary.",
            }
        ],
        slices=[
            {
                "slice_id": "ablation",
                "title": "Ablation",
                "goal": "Disable the core module and compare.",
                "hypothesis": "Performance will drop without the core module.",
                "required_changes": "Disable the core module only.",
                "metric_contract": "Report full validation metrics.",
            }
        ],
    )
    assert campaign["ok"] is True
    assert Path(campaign["todo_manifest_path"]).exists()
    manifest = read_json(quest_root / ".ds" / "analysis_campaigns" / f"{campaign['campaign_id']}.json", {})
    assert manifest["selected_outline_ref"] == "outline-002"
    assert manifest["todo_items"][0]["slice_id"] == "ablation"
    assert manifest["slices"][0]["research_question"] == "RQ-main"
    assert manifest["slices"][0]["experimental_design"] == "Exp-main"

    stage_view = quest_service.stage_view(
        quest["quest_id"],
        {
            "selection_ref": f"stage:{created['branch']}:analysis-campaign",
            "selection_type": "stage_node",
            "branch_name": created["branch"],
            "stage_key": "analysis-campaign",
        },
    )
    assert stage_view["stage_key"] == "analysis"
    assert stage_view["details"]["analysis"]["selected_outline_ref"] == "outline-002"
    assert stage_view["details"]["analysis"]["todo_items"][0]["slice_id"] == "ablation"


def test_supplementary_experiment_protocol_supports_runtime_ref_queries_and_unified_fields(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    quest_service = QuestService(temp_home, skill_installer=SkillInstaller(repo_root(), temp_home))
    quest = quest_service.create("supplementary protocol quest")
    quest_root = Path(quest["quest_root"])
    artifact = ArtifactService(temp_home)

    _confirm_local_baseline(artifact, quest_root, baseline_id="baseline-supplementary")
    idea = artifact.submit_idea(
        quest_root,
        mode="create",
        title="Runtime-ref idea",
        problem="Need a unified route for all extra experiments.",
        hypothesis="A single campaign protocol reduces ambiguity.",
        mechanism="Use one campaign surface for all supplementary work.",
        decision_reason="Promote the unified protocol route.",
        next_target="experiment",
    )
    main_run = artifact.record_main_experiment(
        quest_root,
        run_id="main-supp-001",
        title="Unified protocol main run",
        hypothesis="The unified protocol is workable.",
        setup="Use the accepted baseline setup.",
        execution="Completed the main run.",
        results="Main result is ready for extra evidence work.",
        conclusion="Needs one follow-up reviewer-linked run.",
        metric_rows=[{"metric_id": "acc", "value": 0.91}],
    )
    artifact.submit_paper_outline(
        quest_root,
        mode="candidate",
        title="Supplementary Outline",
        detailed_outline={
            "title": "Supplementary Outline",
            "research_questions": ["RQ-supp"],
            "experimental_designs": ["Exp-supp"],
        },
    )
    artifact.submit_paper_outline(
        quest_root,
        mode="select",
        outline_id="outline-001",
        selected_reason="Bind the next supplementary run to the selected outline.",
    )

    refs = artifact.resolve_runtime_refs(quest_root)
    assert refs["active_idea_id"] == idea["idea_id"]
    assert refs["latest_main_run_id"] == "main-supp-001"
    assert refs["selected_outline_ref"] == "outline-001"

    campaign = artifact.create_analysis_campaign(
        quest_root,
        campaign_title="Reviewer-linked supplementary run",
        campaign_goal="Answer the remaining reviewer concern with one clean slice.",
        campaign_origin={
            "kind": "rebuttal",
            "reason": "Reviewer requested one additional controlled comparison.",
            "reviewer_item_ids": ["R1-C1"],
        },
        selected_outline_ref="outline-001",
        research_questions=["RQ-supp"],
        experimental_designs=["Exp-supp"],
        todo_items=[
            {
                "todo_id": "todo-r1-c1",
                "slice_id": "reviewer-check",
                "title": "Reviewer check",
                "research_question": "RQ-supp",
                "experimental_design": "Exp-supp",
                "completion_condition": "Answer whether the claim survives the requested check.",
                "why_now": "This is the only remaining blocker before revision.",
                "success_criteria": "Produce a fair comparison and a usable manuscript update.",
                "abandonment_criteria": "Stop only if the metric contract becomes invalid.",
                "reviewer_item_ids": ["R1-C1"],
                "manuscript_targets": ["Results", "Rebuttal response"],
            }
        ],
        slices=[
            {
                "slice_id": "reviewer-check",
                "title": "Reviewer-linked check",
                "goal": "Run the requested controlled comparison.",
                "why_now": "Needed for the current revision package.",
                "required_changes": "Modify only the requested comparison factor.",
                "success_criteria": "Return a clean comparable result.",
                "abandonment_criteria": "Abort if the comparison breaks the metric contract.",
                "reviewer_item_ids": ["R1-C1"],
                "manuscript_targets": ["Results", "Response letter"],
            }
        ],
    )
    active_campaign = artifact.get_analysis_campaign(quest_root, campaign_id="active")
    assert active_campaign["campaign_id"] == campaign["campaign_id"]
    assert active_campaign["campaign_origin"]["kind"] == "rebuttal"
    assert active_campaign["todo_items"][0]["reviewer_item_ids"] == ["R1-C1"]
    assert active_campaign["next_pending_slice_id"] == "reviewer-check"

    outlines = artifact.list_paper_outlines(quest_root)
    assert outlines["selected_outline_ref"] == "outline-001"
    assert any(item["outline_id"] == "outline-001" for item in outlines["outlines"])

    completed = artifact.record_analysis_slice(
        quest_root,
        campaign_id=campaign["campaign_id"],
        slice_id="reviewer-check",
        setup="Keep the baseline contract fixed.",
        execution="Ran the requested controlled comparison.",
        results="The claim remains supported under the requested check.",
        metric_rows=[{"metric_id": "acc", "value": 0.905}],
        claim_impact="Strengthens confidence in the main claim.",
        reviewer_resolution="Addresses reviewer item R1-C1 directly.",
        manuscript_update_hint="Update the rebuttal response and the main results paragraph.",
        next_recommendation="Return to the parent branch and revise the manuscript.",
        evaluation_summary={
            "takeaway": "The reviewer-linked check supports the original claim.",
            "claim_update": "strengthens",
            "baseline_relation": "better",
            "comparability": "high",
            "failure_mode": "none",
            "next_action": "write",
        },
    )
    assert completed["ok"] is True
    result_text = Path(completed["result_path"]).read_text(encoding="utf-8")
    assert "## Claim Impact" in result_text
    assert "Strengthens confidence in the main claim." in result_text
    manifest_after = artifact.get_analysis_campaign(quest_root, campaign_id=campaign["campaign_id"])
    assert manifest_after["slices"][0]["claim_impact"] == "Strengthens confidence in the main claim."
    assert main_run["run_id"] == "main-supp-001"
    stage_view = quest_service.stage_view(
        quest["quest_id"],
        {
            "selection_ref": f"stage:{idea['branch']}:analysis-campaign",
            "selection_type": "stage_node",
            "branch_name": idea["branch"],
            "stage_key": "analysis-campaign",
        },
    )
    analysis_details = stage_view["details"]["analysis"]
    assert analysis_details["campaign_origin"]["kind"] == "rebuttal"
    assert analysis_details["todo_items"][0]["success_criteria"] == "Produce a fair comparison and a usable manuscript update."
    assert analysis_details["slices"][0]["claim_impact"] == "Strengthens confidence in the main claim."
    assert analysis_details["slices"][0]["evaluation_summary"]["claim_update"] == "strengthens"


def test_submit_paper_bundle_writes_manifest_and_advances_anchor(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    quest_service = QuestService(temp_home, skill_installer=SkillInstaller(repo_root(), temp_home))
    quest = quest_service.create("paper bundle quest")
    quest_root = Path(quest["quest_root"])
    artifact = ArtifactService(temp_home)

    artifact.submit_paper_outline(
        quest_root,
        mode="candidate",
        title="Bundle Outline",
        note="Candidate for bundle test.",
        detailed_outline={
            "title": "Bundle Outline",
            "research_questions": ["RQ-bundle"],
            "experimental_designs": ["Exp-bundle"],
            "contributions": ["C-bundle"],
        },
    )
    artifact.submit_paper_outline(
        quest_root,
        mode="select",
        outline_id="outline-001",
        selected_reason="Use this for bundle generation.",
    )
    (quest_root / "paper" / "draft.md").write_text("# Draft\n", encoding="utf-8")
    (quest_root / "paper" / "writing_plan.md").write_text("# Plan\n", encoding="utf-8")
    (quest_root / "paper" / "references.bib").write_text("@article{demo, title={Demo}}\n", encoding="utf-8")
    (quest_root / "paper" / "build").mkdir(parents=True, exist_ok=True)
    write_json(quest_root / "paper" / "build" / "compile_report.json", {"ok": True})
    (quest_root / "paper" / "paper.pdf").write_bytes(b"%PDF-1.4\n%paper\n")

    result = artifact.submit_paper_bundle(
        quest_root,
        title="Bundle Paper",
        summary="Paper bundle is ready for final review.",
        pdf_path="paper/paper.pdf",
    )
    assert result["ok"] is True
    assert Path(result["manifest_path"]).exists()
    assert Path(result["baseline_inventory_path"]).exists()
    assert Path(result["open_source_manifest_path"]).exists()
    baseline_inventory = read_json(Path(result["baseline_inventory_path"]), {})
    assert baseline_inventory["schema_version"] == 1
    open_source_manifest = read_json(Path(result["open_source_manifest_path"]), {})
    assert open_source_manifest["source_bundle_manifest_path"] == "paper/paper_bundle_manifest.json"
    assert open_source_manifest["cleanup_plan_path"] == "release/open_source/cleanup_plan.md"
    snapshot = quest_service.snapshot(quest["quest_id"])
    assert snapshot["active_anchor"] == "finalize"

    stage_view = quest_service.stage_view(
        quest["quest_id"],
        {
            "selection_ref": "stage:main:write",
            "selection_type": "stage_node",
            "branch_name": "main",
            "stage_key": "write",
        },
    )
    assert stage_view["stage_key"] == "paper"
    assert any(item["label"] == "Bundle Manifest" for item in stage_view["sections"]["key_files"])


def test_record_main_experiment_writes_result_and_baseline_comparison(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    quest_service = QuestService(temp_home, skill_installer=SkillInstaller(repo_root(), temp_home))
    quest = quest_service.create("main experiment result quest")
    quest_root = Path(quest["quest_root"])
    artifact = ArtifactService(temp_home)
    baseline_root = quest_root / "baselines" / "local" / "baseline-main"
    baseline_root.mkdir(parents=True, exist_ok=True)
    (baseline_root / "README.md").write_text("# Main baseline\n", encoding="utf-8")

    artifact.record(
        quest_root,
        {
            "kind": "baseline",
            "publish_global": True,
            "baseline_id": "baseline-main",
            "name": "Main baseline",
            "primary_metric": {"name": "acc", "value": 0.84},
            "metrics_summary": {"acc": 0.84, "f1": 0.8},
            "baseline_variants": [
                {"variant_id": "main", "label": "Main", "metrics_summary": {"acc": 0.84, "f1": 0.8}}
            ],
            "default_variant_id": "main",
        },
    )
    artifact.attach_baseline(quest_root, "baseline-main", "main")
    artifact.confirm_baseline(
        quest_root,
        baseline_path="baselines/imported/baseline-main",
        baseline_id="baseline-main",
        variant_id="main",
        summary="Baseline main confirmed",
    )

    idea = artifact.submit_idea(
        quest_root,
        mode="create",
        title="Adapter route",
        problem="Baseline saturates.",
        hypothesis="A small adapter improves the main score.",
        mechanism="Insert a light residual adapter.",
        decision_reason="Best next route.",
        next_target="experiment",
    )
    worktree_root = Path(idea["worktree_root"])
    (worktree_root / "src").mkdir(exist_ok=True)
    (worktree_root / "src" / "model.py").write_text("print('adapter')\n", encoding="utf-8")

    result = artifact.record_main_experiment(
        quest_root,
        run_id="main-001",
        title="Adapter main run",
        hypothesis="Adapter improves validation accuracy.",
        setup="Use the attached baseline training recipe.",
        execution="Ran the full validation sweep.",
        results="Accuracy improved.",
        conclusion="The adapter is promising enough for follow-up analysis.",
        metric_rows=[
            {"metric_id": "acc", "value": 0.89, "split": "val"},
            {"metric_id": "f1", "value": 0.85, "split": "val"},
        ],
        evidence_paths=["outputs/main-001/metrics.json"],
        config_paths=["configs/adapter.yaml"],
        evaluation_summary={
            "takeaway": "The adapter clears the baseline on the main validation metric.",
            "claim_update": "strengthens",
            "baseline_relation": "better",
            "comparability": "high",
            "failure_mode": "none",
            "next_action": "analysis_campaign",
        },
    )

    assert result["ok"] is True
    assert result["guidance"]
    assert result["recommended_skill_reads"] == ["decision"]
    assert result["suggested_artifact_calls"]
    assert result["next_instruction"]
    run_md = Path(result["run_md_path"])
    result_json = Path(result["result_json_path"])
    assert run_md.exists()
    assert result_json.exists()

    payload = read_json(result_json, {})
    assert payload["result_kind"] == "main_experiment"
    assert payload["baseline_ref"]["baseline_id"] == "baseline-main"
    assert payload["baseline_ref"]["metric_contract_json_rel_path"] == "baselines/imported/baseline-main/json/metric_contract.json"
    assert payload["metrics_summary"]["acc"] == 0.89
    assert payload["baseline_comparisons"]["primary_metric_id"] == "acc"
    assert payload["evaluation_summary"]["claim_update"] == "strengthens"
    primary = next(item for item in payload["baseline_comparisons"]["items"] if item["metric_id"] == "acc")
    assert primary["delta"] == pytest.approx(0.05)
    assert payload["progress_eval"]["breakthrough"] is True
    assert payload["progress_eval"]["breakthrough_level"] in {"minor", "major"}
    assert result["evaluation_summary"]["next_action"] == "analysis_campaign"

    snapshot = quest_service.snapshot(quest["quest_id"])
    assert snapshot["summary"]["latest_metric"]["key"] == "acc"
    assert snapshot["summary"]["latest_metric"]["delta_vs_baseline"] == pytest.approx(0.05)
    stage_view = quest_service.stage_view(
        quest["quest_id"],
        {
            "selection_ref": f"stage:{idea['branch']}:experiment",
            "selection_type": "stage_node",
            "branch_name": idea["branch"],
            "stage_key": "experiment",
        },
    )
    assert stage_view["details"]["experiment"]["evaluation_summary"]["baseline_relation"] == "better"


def test_submit_idea_supports_foundation_selection_and_branch_listing(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    quest_service = QuestService(temp_home, skill_installer=SkillInstaller(repo_root(), temp_home))
    quest = quest_service.create("idea foundation quest")
    quest_root = Path(quest["quest_root"])
    artifact = ArtifactService(temp_home)
    _confirm_local_baseline(artifact, quest_root, baseline_id="baseline-foundation")

    first_idea = artifact.submit_idea(
        quest_root,
        mode="create",
        title="Adapter route",
        problem="Baseline saturates on difficult cases.",
        hypothesis="A small adapter improves the main score.",
        mechanism="Insert a light residual adapter.",
        decision_reason="Best next route from the current head.",
        next_target="experiment",
    )
    assert first_idea["branch_no"] == "001"
    first_metadata, _ = load_markdown_document(Path(first_idea["idea_md_path"]))
    assert first_metadata["foundation_ref"]["kind"] == "current_head"
    assert first_metadata["foundation_ref"]["branch"] == first_idea["parent_branch"]

    revised_first_idea = artifact.submit_idea(
        quest_root,
        mode="revise",
        idea_id=first_idea["idea_id"],
        title="Adapter route refined",
        problem="Baseline still misses difficult cases.",
        hypothesis="A tuned adapter improves the main score.",
        mechanism="Tune adapter placement and depth.",
        decision_reason="Refine the same branch before the main run.",
        next_target="experiment",
    )
    assert revised_first_idea["branch"] == first_idea["branch"]

    artifact.record_main_experiment(
        quest_root,
        run_id="main-001",
        title="Adapter main run",
        hypothesis="Adapter improves validation accuracy.",
        setup="Use the attached baseline training recipe.",
        execution="Ran the full validation sweep.",
        results="Accuracy improved.",
        conclusion="The adapter is promising enough for follow-up analysis.",
        metric_rows=[
            {"metric_id": "acc", "value": 0.88, "split": "val"},
        ],
        evidence_paths=["outputs/main-001/metrics.json"],
    )

    second_idea = artifact.submit_idea(
        quest_root,
        mode="create",
        title="Run-informed route",
        problem="Need a follow-up idea grounded in the measured win.",
        hypothesis="The measured gain suggests a stronger route.",
        mechanism="Extend the winning adapter logic into the next branch.",
        decision_reason="Use the best measured branch as the next foundation.",
        foundation_ref={"kind": "run", "ref": "main-001"},
        foundation_reason="Build on the best measured main run.",
        next_target="experiment",
    )
    assert second_idea["branch_no"] == "002"
    second_metadata, _ = load_markdown_document(Path(second_idea["idea_md_path"]))
    assert second_metadata["foundation_ref"]["kind"] == "run"
    assert second_metadata["foundation_ref"]["ref"] == "main-001"
    assert second_metadata["foundation_ref"]["branch"] == first_idea["branch"]
    assert second_metadata["foundation_reason"] == "Build on the best measured main run."

    third_idea = artifact.submit_idea(
        quest_root,
        mode="create",
        title="Baseline reset route",
        problem="Need a clean restart from the confirmed baseline.",
        hypothesis="A fresh line from baseline may unlock a cleaner improvement.",
        mechanism="Restart from the baseline branch with a different modification point.",
        decision_reason="Try a fresh route from the baseline instead of compounding changes.",
        foundation_ref={"kind": "baseline", "ref": "baseline-foundation"},
        foundation_reason="Restart from the confirmed baseline branch.",
        next_target="experiment",
    )
    assert third_idea["branch_no"] == "003"
    third_metadata, _ = load_markdown_document(Path(third_idea["idea_md_path"]))
    assert third_metadata["foundation_ref"]["kind"] == "baseline"
    assert third_metadata["foundation_ref"]["ref"] == "baseline-foundation"
    assert third_metadata["foundation_reason"] == "Restart from the confirmed baseline branch."

    branches = artifact.list_research_branches(quest_root)
    assert branches["ok"] is True
    assert branches["count"] == 3
    assert branches["active_head_branch"] == third_idea["branch"]

    by_branch = {item["branch_name"]: item for item in branches["branches"]}
    first_branch = by_branch[first_idea["branch"]]
    assert first_branch["branch_no"] == "001"
    assert first_branch["idea_title"] == "Adapter route refined"
    assert first_branch["parent_branch"] == "main"
    assert first_branch["foundation_ref"]["kind"] == "current_head"
    assert first_branch["latest_main_experiment"]["run_id"] == "main-001"
    assert first_branch["latest_main_experiment"]["primary_metric_id"] == "acc"
    assert first_branch["latest_main_experiment"]["primary_value"] == pytest.approx(0.88)
    assert first_branch["has_main_result"] is True
    assert first_branch["round_state"] == "post_result"

    second_branch = by_branch[second_idea["branch"]]
    assert second_branch["branch_no"] == "002"
    assert second_branch["idea_title"] == "Run-informed route"
    assert second_branch["parent_branch"] == first_idea["branch"]
    assert second_branch["foundation_ref"]["kind"] == "run"
    assert second_branch["foundation_ref"]["ref"] == "main-001"
    assert second_branch["foundation_reason"] == "Build on the best measured main run."
    assert second_branch["latest_main_experiment"] is None
    assert second_branch["has_main_result"] is False
    assert second_branch["round_state"] == "pre_result"

    third_branch = by_branch[third_idea["branch"]]
    assert third_branch["branch_no"] == "003"
    assert third_branch["idea_title"] == "Baseline reset route"
    assert third_branch["parent_branch"] == "main"
    assert third_branch["foundation_ref"]["kind"] == "baseline"
    assert third_branch["foundation_ref"]["ref"] == "baseline-foundation"
    assert third_branch["foundation_reason"] == "Restart from the confirmed baseline branch."
    assert branches["branches"][0]["branch_name"] == third_idea["branch"]

    branch_view = quest_service.stage_view(
        quest["quest_id"],
        {
            "selection_ref": second_idea["branch"],
            "selection_type": "branch_node",
            "branch_name": second_idea["branch"],
            "stage_key": "idea",
            "compare_base": first_idea["branch"],
            "compare_head": second_idea["branch"],
        },
    )
    assert branch_view["branch_no"] == "002"
    assert branch_view["title"] == "Branch #002 · Run-informed route"
    assert branch_view["foundation_label"] == "run · main-001"
    assert branch_view["parent_branch"] == first_idea["branch"]
    assert branch_view["compare_base"] == first_idea["branch"]
    assert branch_view["compare_head"] == second_idea["branch"]
    assert branch_view["lineage_intent"] == "continue_line"
    assert branch_view["draft_available"] is True
    assert branch_view["idea_draft_path"].endswith("/draft.md")
    assert "draft" in branch_view["subviews"]
    assert any(item["label"] == "Idea Markdown" for item in branch_view["sections"]["key_files"])
    assert any(item["label"] == "Idea Draft" for item in branch_view["sections"]["key_files"])


def test_submit_idea_lineage_intent_creates_child_and_sibling_like_nodes(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    quest_service = QuestService(temp_home, skill_installer=SkillInstaller(repo_root(), temp_home))
    quest = quest_service.create("idea lineage quest")
    quest_root = Path(quest["quest_root"])
    artifact = ArtifactService(temp_home)
    _confirm_local_baseline(artifact, quest_root, baseline_id="baseline-lineage")

    first_idea = artifact.submit_idea(
        quest_root,
        mode="create",
        title="First route",
        problem="Baseline saturates.",
        hypothesis="A first improvement path exists.",
        mechanism="Add a small adapter.",
        decision_reason="Open the first durable idea line.",
    )
    artifact.record_main_experiment(
        quest_root,
        run_id="main-lineage-001",
        title="First route main run",
        hypothesis="The first route helps.",
        setup="Use baseline recipe.",
        execution="Ran validation.",
        results="Improved accuracy.",
        conclusion="Use the measured result to continue branching.",
        metric_rows=[{"metric_id": "acc", "value": 0.87}],
    )
    assert quest_service.snapshot(quest["quest_id"])["active_anchor"] == "decision"

    child_idea = artifact.submit_idea(
        quest_root,
        mode="create",
        lineage_intent="continue_line",
        title="Child route",
        problem="Extend the winning line.",
        hypothesis="The measured win supports a stronger child route.",
        mechanism="Deepen the adapter path.",
        decision_reason="Continue the active line from the measured result.",
        draft_markdown="# Child route draft\n\n## Selected Claim\n\nDeepen the adapter path.\n",
    )
    sibling_like_idea = artifact.submit_idea(
        quest_root,
        mode="create",
        lineage_intent="branch_alternative",
        title="Sibling-like route",
        problem="Try an alternative from the same parent foundation.",
        hypothesis="A sibling route may outperform the direct continuation.",
        mechanism="Change the intervention point while keeping the same parent foundation.",
        decision_reason="Branch an alternative from the parent foundation.",
        draft_markdown="# Sibling route draft\n\n## Selected Claim\n\nChange the intervention point.\n",
    )

    child_metadata, _ = load_markdown_document(Path(child_idea["idea_md_path"]))
    sibling_metadata, _ = load_markdown_document(Path(sibling_like_idea["idea_md_path"]))

    assert child_idea["lineage_intent"] == "continue_line"
    assert child_idea["parent_branch"] == first_idea["branch"]
    assert child_idea["foundation_ref"]["kind"] == "run"
    assert child_idea["foundation_ref"]["ref"] == "main-lineage-001"
    assert child_metadata["lineage_intent"] == "continue_line"

    assert sibling_like_idea["lineage_intent"] == "branch_alternative"
    assert sibling_like_idea["parent_branch"] == first_idea["branch"]
    assert sibling_like_idea["foundation_ref"]["kind"] == "run"
    assert sibling_like_idea["foundation_ref"]["ref"] == "main-lineage-001"
    assert sibling_metadata["lineage_intent"] == "branch_alternative"

    branches = artifact.list_research_branches(quest_root)
    by_branch = {item["branch_name"]: item for item in branches["branches"]}
    assert by_branch[child_idea["branch"]]["lineage_intent"] == "continue_line"
    assert by_branch[child_idea["branch"]]["parent_branch"] == first_idea["branch"]
    assert by_branch[child_idea["branch"]]["idea_draft_path"].endswith("/draft.md")
    assert by_branch[sibling_like_idea["branch"]]["lineage_intent"] == "branch_alternative"
    assert by_branch[sibling_like_idea["branch"]]["parent_branch"] == first_idea["branch"]
    assert by_branch[sibling_like_idea["branch"]]["idea_draft_path"].endswith("/draft.md")


def test_stage_view_exposes_idea_draft_content_and_subviews(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    quest_service = QuestService(temp_home, skill_installer=SkillInstaller(repo_root(), temp_home))
    quest = quest_service.create("idea draft stage view quest")
    quest_root = Path(quest["quest_root"])
    artifact = ArtifactService(temp_home)
    _confirm_local_baseline(artifact, quest_root, baseline_id="baseline-draft")

    idea = artifact.submit_idea(
        quest_root,
        mode="create",
        title="Drafted route",
        problem="Baseline saturates early.",
        hypothesis="A clearer route helps later execution.",
        mechanism="Introduce a compact adapter.",
        decision_reason="Record the chosen route with a durable draft.",
        draft_markdown="# Drafted route\n\n## Theory and Method\n\nUse a compact adapter.\n",
    )

    stage_view = quest_service.stage_view(
        quest["quest_id"],
        {
            "selection_ref": idea["branch"],
            "selection_type": "branch_node",
            "branch_name": idea["branch"],
            "stage_key": "idea",
            "compare_base": "main",
            "compare_head": idea["branch"],
        },
    )

    assert stage_view["draft_available"] is True
    assert stage_view["idea_draft_path"].endswith("/draft.md")
    assert stage_view["subviews"] == ["overview", "details", "draft"]
    assert "Use a compact adapter." in stage_view["details"]["branch"]["idea_draft_markdown"]


def test_attach_baseline_fails_when_registry_source_is_not_materializable(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    quest_service = QuestService(temp_home, skill_installer=SkillInstaller(repo_root(), temp_home))
    quest = quest_service.create("broken baseline attach quest")
    quest_root = Path(quest["quest_root"])
    artifact = ArtifactService(temp_home)

    artifact.baselines.publish(
        {
            "baseline_id": "broken-baseline",
            "summary": "Broken baseline entry",
            "path": str(temp_home / "missing-baseline-root"),
        }
    )

    result = artifact.attach_baseline(quest_root, "broken-baseline")

    assert result["ok"] is False
    assert "could not be materialized" in str(result["message"])
    attachment = read_yaml(quest_root / "baselines" / "imported" / "broken-baseline" / "attachment.yaml", {})
    assert attachment["materialization"]["status"] == "error"
    assert list((quest_root / "artifacts" / "reports").glob("*.json")) == []


def test_baseline_registry_backfills_confirmed_legacy_quests(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    quest_service = QuestService(temp_home, skill_installer=SkillInstaller(repo_root(), temp_home))
    quest = quest_service.create("legacy confirmed baseline quest")
    quest_root = Path(quest["quest_root"])
    baseline_root = quest_root / "baselines" / "local" / "legacy-baseline"
    baseline_root.mkdir(parents=True, exist_ok=True)
    (baseline_root / "README.md").write_text("# Legacy baseline\n", encoding="utf-8")

    quest_service.update_baseline_state(
        quest_root,
        baseline_gate="confirmed",
        confirmed_baseline_ref={
            "baseline_id": "legacy-baseline",
            "variant_id": None,
            "baseline_path": str(baseline_root),
            "baseline_root_rel_path": "baselines/local/legacy-baseline",
            "source_mode": "local",
            "confirmed_at": "2026-03-12T00:00:00Z",
        },
        active_anchor="idea",
    )

    registry = BaselineRegistry(temp_home)
    entries = registry.list_entries()
    entry = next(item for item in entries if item["baseline_id"] == "legacy-baseline")

    assert entry["status"] == "quest_confirmed"
    assert entry["source_quest_id"] == quest["quest_id"]
    assert entry["source_baseline_path"] == str(baseline_root)
    assert entry["materializable"] is True
    assert entry["availability"] == "ready"


def test_artifact_arxiv_overview_falls_back_to_arxiv_abstract(temp_home: Path, monkeypatch) -> None:
    ensure_home_layout(temp_home)
    artifact = ArtifactService(temp_home)

    def fake_urlopen(request, timeout=8):  # noqa: ANN001
        url = request.full_url
        if url.endswith("/overview/2010.11929.md"):
            raise TimeoutError("overview timed out")
        if url.endswith("/abs/2010.11929"):
            return _FakeUrlopenResponse(
                """
                <html>
                  <head>
                    <meta name="citation_title" content="An Image is Worth 16x16 Words: Transformers for Image Recognition at Scale" />
                    <meta name="citation_author" content="Dosovitskiy, Alexey" />
                  </head>
                  <body>
                    <blockquote class="abstract mathjax">
                      <span class="descriptor">Abstract:</span>
                      Vision Transformers apply pure transformer layers directly to image patches.
                    </blockquote>
                  </body>
                </html>
                """
            )
        raise AssertionError(url)

    monkeypatch.setattr("deepscientist.artifact.arxiv.urlopen", fake_urlopen)
    result = artifact.arxiv("2010.11929")

    assert result["ok"] is True
    assert result["source"] == "arxiv_abstract"
    assert result["content_mode"] == "abstract"
    assert "An Image is Worth 16x16 Words" in result["content"]
    assert "Vision Transformers apply pure transformer layers" in result["content"]
    assert result["attempts"][0]["source"] == "alphaxiv_overview"
    assert result["attempts"][0]["ok"] is False


def test_artifact_arxiv_full_text_falls_back_to_html(temp_home: Path, monkeypatch) -> None:
    ensure_home_layout(temp_home)
    artifact = ArtifactService(temp_home)

    def fake_urlopen(request, timeout=8):  # noqa: ANN001
        url = request.full_url
        if url.endswith("/abs/2010.11929.md"):
            raise HTTPError(url, 404, "not found", hdrs=None, fp=None)
        if url.endswith("/html/2010.11929"):
            return _FakeUrlopenResponse(
                """
                <html>
                  <head>
                    <title>An Image is Worth 16x16 Words</title>
                  </head>
                  <body>
                    <article>
                      <h1>An Image is Worth 16x16 Words</h1>
                      <p>Introduction.</p>
                      <p>Methods.</p>
                    </article>
                  </body>
                </html>
                """
            )
        raise AssertionError(url)

    monkeypatch.setattr("deepscientist.artifact.arxiv.urlopen", fake_urlopen)
    result = artifact.arxiv("2010.11929", full_text=True)

    assert result["ok"] is True
    assert result["source"] == "arxiv_html"
    assert result["content_mode"] == "full_text"
    assert "Introduction." in result["content"]
    assert "Methods." in result["content"]
    assert result["attempts"][0]["source"] == "alphaxiv_full_text"
    assert result["attempts"][0]["ok"] is False


def test_artifact_interact_respects_primary_connector_policy(temp_home: Path, monkeypatch) -> None:
    ensure_home_layout(temp_home)
    manager = ConfigManager(temp_home)
    manager.ensure_files()
    connectors = manager.load_named("connectors")
    connectors["telegram"]["enabled"] = True
    connectors["slack"]["enabled"] = True
    connectors["_routing"]["primary_connector"] = "telegram"
    connectors["_routing"]["artifact_delivery_policy"] = "primary_plus_local"
    write_yaml(manager.path_for("connectors"), connectors)

    def fake_telegram_deliver(_self, _payload, _config):  # noqa: ANN001
        return {"ok": True, "transport": "telegram-http"}

    monkeypatch.setattr("deepscientist.bridges.connectors.TelegramConnectorBridge.deliver", fake_telegram_deliver)

    quest_service = QuestService(temp_home, skill_installer=SkillInstaller(repo_root(), temp_home))
    quest = quest_service.create("artifact routing quest")
    quest_root = Path(quest["quest_root"])
    artifact = ArtifactService(temp_home)

    quest_service.bind_source(quest["quest_id"], "web")
    quest_service.bind_source(quest["quest_id"], "telegram:direct:tg-user-1")
    quest_service.bind_source(quest["quest_id"], "slack:direct:slack-user-1")

    result = artifact.interact(
        quest_root,
        kind="milestone",
        message="Primary connector routing test.",
        deliver_to_bound_conversations=True,
        include_recent_inbound_messages=False,
    )

    assert result["status"] == "ok"
    assert result["delivery_policy"] == "primary_plus_local"
    assert result["preferred_connector"] == "telegram"
    assert result["delivery_targets"] == ["local:default", "telegram:direct:tg-user-1"]

    local_records = read_jsonl(temp_home / "logs" / "connectors" / "local" / "outbox.jsonl")
    telegram_records = read_jsonl(temp_home / "logs" / "connectors" / "telegram" / "outbox.jsonl")
    slack_outbox = temp_home / "logs" / "connectors" / "slack" / "outbox.jsonl"

    assert any("Primary connector routing test." in str(item.get("message") or "") for item in local_records)
    assert any("Primary connector routing test." in str(item.get("text") or "") for item in telegram_records)
    assert not slack_outbox.exists()


def test_artifact_interact_fans_out_to_all_bound_connectors_without_primary(
    temp_home: Path,
    monkeypatch,
) -> None:
    ensure_home_layout(temp_home)
    manager = ConfigManager(temp_home)
    manager.ensure_files()
    connectors = manager.load_named("connectors")
    connectors["qq"]["enabled"] = True
    connectors["qq"]["app_id"] = "1903299925"
    connectors["qq"]["app_secret"] = "qq-secret"
    connectors["telegram"]["enabled"] = True
    connectors["_routing"]["primary_connector"] = None
    connectors["_routing"]["artifact_delivery_policy"] = "primary_plus_local"
    write_yaml(manager.path_for("connectors"), connectors)

    deliveries: list[str] = []

    def fake_qq_deliver(_self, payload, _config):  # noqa: ANN001
        deliveries.append(str(payload.get("conversation_id") or ""))
        return {"ok": True, "transport": "qq-http"}

    def fake_telegram_deliver(_self, payload, _config):  # noqa: ANN001
        deliveries.append(str(payload.get("conversation_id") or ""))
        return {"ok": True, "transport": "telegram-http"}

    monkeypatch.setattr("deepscientist.bridges.connectors.QQConnectorBridge.deliver", fake_qq_deliver)
    monkeypatch.setattr("deepscientist.bridges.connectors.TelegramConnectorBridge.deliver", fake_telegram_deliver)

    quest_service = QuestService(temp_home, skill_installer=SkillInstaller(repo_root(), temp_home))
    quest = quest_service.create("artifact fanout quest")
    quest_root = Path(quest["quest_root"])
    artifact = ArtifactService(temp_home)

    quest_service.bind_source(quest["quest_id"], "local:default")
    quest_service.bind_source(quest["quest_id"], "qq:direct:qq-user-1")
    quest_service.bind_source(quest["quest_id"], "telegram:direct:tg-user-1")

    result = artifact.interact(
        quest_root,
        kind="milestone",
        message="Fanout all bound connectors.",
        deliver_to_bound_conversations=True,
        include_recent_inbound_messages=False,
    )

    assert result["status"] == "ok"
    assert result["delivery_policy"] == "primary_plus_local"
    assert result["preferred_connector"] is None
    assert result["delivery_targets"] == [
        "local:default",
        "qq:direct:qq-user-1",
        "telegram:direct:tg-user-1",
    ]
    assert "qq:direct:qq-user-1" in deliveries
    assert "telegram:direct:tg-user-1" in deliveries

    qq_records = read_jsonl(temp_home / "logs" / "connectors" / "qq" / "outbox.jsonl")
    telegram_records = read_jsonl(temp_home / "logs" / "connectors" / "telegram" / "outbox.jsonl")

    assert qq_records[-1]["delivery"]["ok"] is True
    assert telegram_records[-1]["delivery"]["ok"] is True


def test_artifact_interact_auto_uses_single_enabled_connector_for_primary_only(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    manager = ConfigManager(temp_home)
    manager.ensure_files()
    connectors = manager.load_named("connectors")
    connectors["whatsapp"]["enabled"] = True
    connectors["_routing"]["primary_connector"] = None
    connectors["_routing"]["artifact_delivery_policy"] = "primary_only"
    write_yaml(manager.path_for("connectors"), connectors)

    quest_service = QuestService(temp_home, skill_installer=SkillInstaller(repo_root(), temp_home))
    quest = quest_service.create("single connector routing quest")
    quest_root = Path(quest["quest_root"])
    artifact = ArtifactService(temp_home)

    quest_service.bind_source(quest["quest_id"], "web")
    quest_service.bind_source(quest["quest_id"], "whatsapp:direct:+15550001111")

    result = artifact.interact(
        quest_root,
        kind="progress",
        message="Single connector auto-selection test.",
        deliver_to_bound_conversations=True,
        include_recent_inbound_messages=False,
    )

    assert result["preferred_connector"] == "whatsapp"
    assert result["delivery_policy"] == "primary_only"
    assert result["delivery_targets"] == ["whatsapp:direct:+15550001111"]

    whatsapp_records = read_jsonl(temp_home / "logs" / "connectors" / "whatsapp" / "outbox.jsonl")
    local_outbox = temp_home / "logs" / "connectors" / "local" / "outbox.jsonl"

    assert any("Single connector auto-selection test." in str(item.get("text") or "") for item in whatsapp_records)
    assert not local_outbox.exists()


def test_artifact_interact_persists_surface_actions_and_connector_payload(temp_home: Path, monkeypatch) -> None:
    ensure_home_layout(temp_home)
    manager = ConfigManager(temp_home)
    manager.ensure_files()
    connectors = manager.load_named("connectors")
    connectors["qq"]["enabled"] = True
    connectors["_routing"]["artifact_delivery_policy"] = "primary_only"
    write_yaml(manager.path_for("connectors"), connectors)

    def fake_qq_deliver(_self, _payload, _config):  # noqa: ANN001
        return {"ok": True, "transport": "qq-http"}

    monkeypatch.setattr("deepscientist.bridges.connectors.QQConnectorBridge.deliver", fake_qq_deliver)

    quest_service = QuestService(temp_home, skill_installer=SkillInstaller(repo_root(), temp_home))
    quest = quest_service.create("artifact surface actions quest")
    quest_root = Path(quest["quest_root"])
    artifact = ArtifactService(temp_home)
    quest_service.bind_source(quest["quest_id"], "qq:direct:qq-user-surface")

    surface_actions = [
        {
            "type": "send_notification",
            "title": "Checkpoint reached",
            "body": "Main baseline audit completed.",
        }
    ]
    result = artifact.interact(
        quest_root,
        kind="milestone",
        message="Surface action delivery test.",
        deliver_to_bound_conversations=True,
        include_recent_inbound_messages=False,
        surface_actions=surface_actions,
    )

    assert result["status"] == "ok"
    assert result["surface_actions"] == surface_actions
    assert result["delivery_targets"] == ["qq:direct:qq-user-surface"]

    qq_records = read_jsonl(temp_home / "logs" / "connectors" / "qq" / "outbox.jsonl")
    assert qq_records
    assert qq_records[-1]["surface_actions"] == surface_actions

    interaction_records = quest_service.latest_artifact_interaction_records(quest_root, limit=5)
    assert interaction_records
    assert interaction_records[-1]["surface_actions"] == surface_actions

    events = read_jsonl(quest_root / ".ds" / "events.jsonl")
    outbound = [item for item in events if item.get("type") == "connector.outbound"]
    assert outbound
    assert outbound[-1]["surface_actions"] == surface_actions


def test_artifact_interact_normalizes_attachment_paths_and_returns_delivery_results(temp_home: Path, monkeypatch) -> None:
    ensure_home_layout(temp_home)
    manager = ConfigManager(temp_home)
    manager.ensure_files()
    connectors = manager.load_named("connectors")
    connectors["qq"]["enabled"] = True
    connectors["_routing"]["artifact_delivery_policy"] = "primary_only"
    write_yaml(manager.path_for("connectors"), connectors)

    captured: list[dict] = []

    def fake_qq_deliver(_self, payload, _config):  # noqa: ANN001
        captured.append(dict(payload))
        return {"ok": True, "transport": "qq-http"}

    monkeypatch.setattr("deepscientist.bridges.connectors.QQConnectorBridge.deliver", fake_qq_deliver)

    quest_service = QuestService(temp_home, skill_installer=SkillInstaller(repo_root(), temp_home))
    quest = quest_service.create("artifact attachment normalize quest")
    quest_root = Path(quest["quest_root"])
    artifact = ArtifactService(temp_home)
    quest_service.bind_source(quest["quest_id"], "qq:direct:qq-user-absolute")

    relative_path = Path("artifacts") / "reports" / "summary.png"
    absolute_path = quest_root / relative_path
    absolute_path.parent.mkdir(parents=True, exist_ok=True)
    absolute_path.write_bytes(b"fake-image")

    result = artifact.interact(
        quest_root,
        kind="milestone",
        message="Attachment normalization test.",
        deliver_to_bound_conversations=True,
        include_recent_inbound_messages=False,
        attachments=[
            {
                "kind": "path",
                "path": str(relative_path),
                "label": "summary",
            }
        ],
    )

    assert result["status"] == "ok"
    assert result["attachment_issues"] == []
    assert result["normalized_attachments"][0]["path"] == str(absolute_path.resolve())
    assert result["delivery_results"]
    assert result["delivery_results"][0]["ok"] is True
    assert result["delivery_results"][0]["conversation_id"] == "qq:direct:qq-user-absolute"
    assert captured
    assert captured[-1]["attachments"][0]["path"] == str(absolute_path.resolve())


def test_artifact_interact_reports_missing_attachment_path_to_agent(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    quest_service = QuestService(temp_home, skill_installer=SkillInstaller(repo_root(), temp_home))
    quest = quest_service.create("artifact attachment error quest")
    quest_root = Path(quest["quest_root"])
    artifact = ArtifactService(temp_home)

    result = artifact.interact(
        quest_root,
        kind="progress",
        message="Missing attachment path test.",
        deliver_to_bound_conversations=False,
        include_recent_inbound_messages=False,
        attachments=[
            {
                "kind": "path",
                "path": "artifacts/reports/missing.png",
                "label": "missing",
                "connector_delivery": {"qq": {"media_kind": "image"}},
            }
        ],
    )

    assert result["status"] == "ok"
    assert result["attachment_issues"]
    assert result["attachment_issues"][0]["error"] == "attachment path does not exist"
    assert result["normalized_attachments"][0]["path"].endswith("/artifacts/reports/missing.png")


def test_explorer_lists_real_files_and_path_documents_can_be_saved(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    quest_service = QuestService(temp_home, skill_installer=SkillInstaller(repo_root(), temp_home))
    quest = quest_service.create("explorer quest")
    quest_root = Path(quest["quest_root"])

    note_path = quest_root / "literature" / "notes.md"
    note_path.write_text("# Notes\n\nInitial baseline scouting.", encoding="utf-8")

    explorer = quest_service.explorer(quest["quest_id"])
    assert explorer["quest_root"] == str(quest_root.resolve())
    research = next(section for section in explorer["sections"] if section["id"] == "research")

    def flatten(nodes: list[dict]) -> list[dict]:
        items: list[dict] = []
        for node in nodes:
            items.append(node)
            items.extend(flatten(node.get("children") or []))
        return items

    research_nodes = flatten(research["nodes"])
    note_node = next(node for node in research_nodes if node.get("path") == "literature/notes.md")
    assert note_node["document_id"] == "path::literature/notes.md"
    assert note_node["writable"] is True

    opened = quest_service.open_document(quest["quest_id"], note_node["document_id"])
    assert "Initial baseline scouting." in opened["content"]

    saved = quest_service.save_document(
        quest["quest_id"],
        note_node["document_id"],
        "# Notes\n\nUpdated from explorer.",
        previous_revision=opened["revision"],
    )
    assert saved["ok"] is True

    reopened = quest_service.open_document(quest["quest_id"], note_node["document_id"])
    assert "Updated from explorer." in reopened["content"]


def test_explorer_opens_image_files_as_assets(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    quest_service = QuestService(temp_home, skill_installer=SkillInstaller(repo_root(), temp_home))
    quest = quest_service.create("image explorer quest")
    quest_root = Path(quest["quest_root"])

    figure_path = quest_root / "literature" / "figure.png"
    figure_path.write_bytes(b"\x89PNG\r\n\x1a\nfake-png")

    explorer = quest_service.explorer(quest["quest_id"])
    research = next(section for section in explorer["sections"] if section["id"] == "research")

    def flatten(nodes: list[dict]) -> list[dict]:
        items: list[dict] = []
        for node in nodes:
            items.append(node)
            items.extend(flatten(node.get("children") or []))
        return items

    research_nodes = flatten(research["nodes"])
    figure_node = next(node for node in research_nodes if node.get("path") == "literature/figure.png")

    opened = quest_service.open_document(quest["quest_id"], figure_node["document_id"])
    assert opened["meta"]["renderer_hint"] == "image"
    assert opened["mime_type"] == "image/png"
    assert opened["content"] == ""
    assert "documents/asset" in opened["asset_url"]


def test_explorer_marks_paper_latex_folder_for_workspace_opening(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    quest_service = QuestService(temp_home, skill_installer=SkillInstaller(repo_root(), temp_home))
    quest = quest_service.create("paper latex explorer quest")
    quest_root = Path(quest["quest_root"])

    latex_root = quest_root / "paper" / "latex"
    latex_root.mkdir(parents=True, exist_ok=True)
    (latex_root / "main.tex").write_text(
        "\n".join(
            [
                r"\documentclass{article}",
                r"\begin{document}",
                "Hello",
                r"\end{document}",
                "",
            ]
        ),
        encoding="utf-8",
    )

    explorer = quest_service.explorer(quest["quest_id"])
    research = next(section for section in explorer["sections"] if section["id"] == "research")

    def flatten(nodes: list[dict]) -> list[dict]:
        items: list[dict] = []
        for node in nodes:
            items.append(node)
            items.extend(flatten(node.get("children") or []))
        return items

    research_nodes = flatten(research["nodes"])
    latex_node = next(node for node in research_nodes if node.get("path") == "paper/latex")
    assert latex_node["kind"] == "directory"
    assert latex_node["folder_kind"] == "latex"


def test_markdown_asset_upload_uses_sibling_assets_folder(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    quest_service = QuestService(temp_home, skill_installer=SkillInstaller(repo_root(), temp_home))
    quest = quest_service.create("markdown asset upload quest")
    quest_root = Path(quest["quest_root"])

    uploaded = quest_service.save_document_asset(
        quest["quest_id"],
        "brief.md",
        file_name="diagram.png",
        mime_type="image/png",
        content=b"\x89PNG\r\n\x1a\nquest-markdown-asset",
        kind="image",
    )

    assert uploaded["ok"] is True
    assert uploaded["relative_path"].startswith("brief.assets/")
    asset_path = quest_root / uploaded["relative_path"]
    assert asset_path.exists()
    assert asset_path.read_bytes().startswith(b"\x89PNG")

    opened = quest_service.open_document(quest["quest_id"], uploaded["asset_document_id"])
    assert opened["meta"]["renderer_hint"] == "image"


def test_questpath_documents_and_stage_view_cover_quest_root_files(temp_home: Path) -> None:
    quest_service = QuestService(temp_home)
    artifact = ArtifactService(temp_home)
    quest = quest_service.create("stage view quest")
    quest_root = temp_home / "quests" / quest["quest_id"]
    docs_dir = quest_root / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    appendix = docs_dir / "appendix.md"
    appendix.write_text("# Appendix\n\nQuest-root file.\n", encoding="utf-8")

    opened = quest_service.open_document(quest["quest_id"], "questpath::docs/appendix.md")

    assert opened["document_id"] == "questpath::docs/appendix.md"
    assert "Quest-root file" in opened["content"]

    baseline_dir = quest_root / "baselines" / "local" / "baseline-001"
    baseline_dir.mkdir(parents=True, exist_ok=True)
    (baseline_dir / "metrics.json").write_text('{"acc": 0.91}\n', encoding="utf-8")
    result = artifact.confirm_baseline(
        quest_root,
        baseline_path="baselines/local/baseline-001",
        baseline_id="baseline-001",
        summary="Baseline confirmed for stage view.",
        metrics_summary={"acc": 0.91},
        metric_contract={"primary_metric_id": "acc", "direction": "maximize"},
        primary_metric={"metric_id": "acc", "value": 0.91},
    )
    assert result["ok"] is True

    stage_view = quest_service.stage_view(
        quest["quest_id"],
        {
            "selection_ref": "stage:main:baseline",
            "selection_type": "stage_node",
            "branch_name": "main",
            "stage_key": "baseline",
        },
    )

    assert stage_view["stage_key"] == "baseline"
    assert stage_view["title"] == "Baseline · baseline-001"
    assert any(item["label"] == "Attachment" for item in stage_view["sections"]["key_files"])


def test_workflow_uses_questpath_for_quest_root_outputs_when_active_workspace_is_worktree(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    quest_service = QuestService(temp_home, skill_installer=SkillInstaller(repo_root(), temp_home))
    quest = quest_service.create("workflow questpath contract")
    quest_root = Path(quest["quest_root"])
    worktree_root = quest_root / ".ds" / "worktrees" / "branch-001"
    worktree_root.mkdir(parents=True, exist_ok=True)
    (worktree_root / "brief.md").write_text("# Worktree brief\n", encoding="utf-8")

    run_output = quest_root / ".ds" / "runs" / "run-001" / "result.txt"
    run_output.parent.mkdir(parents=True, exist_ok=True)
    run_output.write_text("quest-root output\n", encoding="utf-8")
    history_root = quest_root / ".ds" / "codex_history" / "run-001"
    history_root.mkdir(parents=True, exist_ok=True)
    write_json(
        history_root / "meta.json",
        {
            "run_id": "run-001",
            "skill_id": "experiment",
            "summary": "Recorded output",
            "output_path": str(run_output),
        },
    )

    quest_service.update_research_state(
        quest_root,
        current_workspace_root=str(worktree_root),
        research_head_worktree_root=str(worktree_root),
    )

    workflow = quest_service.workflow(quest["quest_id"])
    output_item = next(
        item for item in workflow["changed_files"] if str(item.get("path") or "").endswith(".ds/runs/run-001/result.txt")
    )

    assert output_item["document_id"] == "questpath::.ds/runs/run-001/result.txt"


def test_explorer_can_switch_to_git_snapshot_and_open_historical_files(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    quest_service = QuestService(temp_home, skill_installer=SkillInstaller(repo_root(), temp_home))
    quest = quest_service.create("git snapshot explorer quest")
    quest_root = Path(quest["quest_root"])

    note_path = quest_root / "literature" / "notes.md"
    note_path.write_text("# Notes\n\nCommitted snapshot.", encoding="utf-8")
    from deepscientist.gitops import checkpoint_repo

    checkpoint_repo(quest_root, "Add literature note for snapshot explorer", allow_empty=False)
    note_path.write_text("# Notes\n\nLive working tree update.", encoding="utf-8")

    snapshot_explorer = quest_service.explorer(quest["quest_id"], revision="HEAD", mode="commit")
    assert snapshot_explorer["view"]["mode"] == "commit"
    assert snapshot_explorer["view"]["revision"] == "HEAD"
    assert snapshot_explorer["view"]["read_only"] is True

    research = next(section for section in snapshot_explorer["sections"] if section["id"] == "research")

    def flatten(nodes: list[dict]) -> list[dict]:
        items: list[dict] = []
        for node in nodes:
            items.append(node)
            items.extend(flatten(node.get("children") or []))
        return items

    research_nodes = flatten(research["nodes"])
    note_node = next(node for node in research_nodes if node.get("path") == "literature/notes.md")
    assert note_node["document_id"] == "git::HEAD::literature/notes.md"
    assert note_node["writable"] is False

    opened = quest_service.open_document(quest["quest_id"], note_node["document_id"])
    assert opened["source_scope"] == "git_snapshot"
    assert opened["writable"] is False
    assert "Committed snapshot." in opened["content"]
    assert "Live working tree update." not in opened["content"]

    save_attempt = quest_service.save_document(
        quest["quest_id"],
        note_node["document_id"],
        "# Notes\n\nShould not save to snapshot.",
        previous_revision=opened["revision"],
    )
    assert save_attempt["ok"] is False
    assert save_attempt["conflict"] is False


def test_explorer_lists_custom_root_files_and_binary_assets(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    quest_service = QuestService(temp_home, skill_installer=SkillInstaller(repo_root(), temp_home))
    quest = quest_service.create("custom explorer quest")
    quest_root = Path(quest["quest_root"])

    code_path = quest_root / "src" / "train.py"
    code_path.parent.mkdir(parents=True, exist_ok=True)
    code_path.write_text("print('quest explorer works')\n", encoding="utf-8")

    image_path = quest_root / "figures" / "plot.png"
    image_path.parent.mkdir(parents=True, exist_ok=True)
    image_path.write_bytes(b"\x89PNG\r\n\x1a\nquest-plot")

    pdf_path = quest_root / "docs" / "appendix.pdf"
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    pdf_path.write_bytes(b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n")

    explorer = quest_service.explorer(quest["quest_id"])
    quest_section = next(section for section in explorer["sections"] if section["id"] == "quest")

    def flatten(nodes: list[dict]) -> list[dict]:
        items: list[dict] = []
        for node in nodes:
            items.append(node)
            items.extend(flatten(node.get("children") or []))
        return items

    quest_nodes = flatten(quest_section["nodes"])

    code_node = next(node for node in quest_nodes if node.get("path") == "src/train.py")
    assert code_node["document_id"] == "path::src/train.py"
    opened_code = quest_service.open_document(quest["quest_id"], code_node["document_id"])
    assert opened_code["meta"]["renderer_hint"] == "code"
    assert "quest explorer works" in opened_code["content"]

    image_node = next(node for node in quest_nodes if node.get("path") == "figures/plot.png")
    opened_image = quest_service.open_document(quest["quest_id"], image_node["document_id"])
    assert opened_image["meta"]["renderer_hint"] == "image"
    assert opened_image["mime_type"] == "image/png"
    assert "documents/asset" in opened_image["asset_url"]

    pdf_node = next(node for node in quest_nodes if node.get("path") == "docs/appendix.pdf")
    opened_pdf = quest_service.open_document(quest["quest_id"], pdf_node["document_id"])
    assert opened_pdf["meta"]["renderer_hint"] == "pdf"
    assert opened_pdf["mime_type"] == "application/pdf"
    assert "documents/asset" in opened_pdf["asset_url"]


def test_artifact_interact_tracks_pending_request_and_user_reply(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    quest_service = QuestService(temp_home, skill_installer=SkillInstaller(repo_root(), temp_home))
    quest = quest_service.create("interactive artifact quest")
    quest_root = Path(quest["quest_root"])
    artifact = ArtifactService(temp_home)

    request = artifact.interact(
        quest_root,
        kind="decision_request",
        message="Should I launch the robustness campaign now?",
        deliver_to_bound_conversations=False,
        include_recent_inbound_messages=False,
        options=[
            {"id": "launch", "label": "Launch now", "description": "Run the campaign immediately."},
            {"id": "wait", "label": "Wait", "description": "Hold off until more evidence arrives."},
        ],
    )
    assert request["status"] == "ok"
    assert request["expects_reply"] is True
    assert request["open_request_count"] == 1
    snapshot_waiting = quest_service.snapshot(quest["quest_id"])
    assert snapshot_waiting["status"] == "waiting_for_user"
    assert snapshot_waiting["pending_decisions"]
    assert snapshot_waiting["active_interactions"]

    reply = quest_service.append_message(
        quest["quest_id"],
        role="user",
        content="Launch it now and focus on robustness first.",
        source="qq:group:demo",
    )
    snapshot_after_reply = quest_service.snapshot(quest["quest_id"])
    assert snapshot_after_reply["status"] == "running"
    assert any(item.get("status") == "answered" for item in snapshot_after_reply["active_interactions"])

    follow_up = artifact.interact(
        quest_root,
        kind="progress",
        message="Received your instruction; I am preparing the campaign charter.",
        deliver_to_bound_conversations=False,
        include_recent_inbound_messages=True,
    )
    assert follow_up["status"] == "ok"
    assert follow_up["recent_inbound_messages"]
    latest = follow_up["recent_inbound_messages"][-1]
    assert latest["message_id"] == reply["id"]
    assert latest["conversation_id"] == "qq:group:demo"
    assert latest["text"].startswith("Launch it now")


def test_artifact_interact_redirects_ordinary_decision_requests_in_autonomous_mode(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    quest_service = QuestService(temp_home, skill_installer=SkillInstaller(repo_root(), temp_home))
    quest = quest_service.create(
        "autonomous decision quest",
        startup_contract={"decision_policy": "autonomous"},
    )
    quest_root = Path(quest["quest_root"])
    artifact = ArtifactService(temp_home)

    result = artifact.interact(
        quest_root,
        kind="decision_request",
        message="Should I choose branch A or branch B?",
        deliver_to_bound_conversations=False,
        include_recent_inbound_messages=False,
        reply_mode="blocking",
        options=[
            {"id": "a", "label": "A", "description": "Choose branch A."},
            {"id": "b", "label": "B", "description": "Choose branch B."},
        ],
    )

    assert result["status"] == "autonomous_redirected"
    assert result["reply_mode"] == "none"
    assert result["interaction_id"] is None
    snapshot_after = quest_service.snapshot(quest["quest_id"])
    assert snapshot_after["status"] != "waiting_for_user"
    assert not snapshot_after["pending_decisions"]


def test_artifact_interact_allows_completion_approval_in_autonomous_mode(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    quest_service = QuestService(temp_home, skill_installer=SkillInstaller(repo_root(), temp_home))
    quest = quest_service.create(
        "autonomous completion approval quest",
        startup_contract={"decision_policy": "autonomous"},
    )
    quest_root = Path(quest["quest_root"])
    artifact = ArtifactService(temp_home)

    request = artifact.interact(
        quest_root,
        kind="decision_request",
        message="The quest appears complete. May I end it now?",
        deliver_to_bound_conversations=False,
        include_recent_inbound_messages=False,
        reply_mode="blocking",
        reply_schema={"decision_type": "quest_completion_approval"},
    )

    assert request["status"] == "ok"
    assert request["reply_mode"] == "blocking"
    snapshot_after = quest_service.snapshot(quest["quest_id"])
    assert snapshot_after["status"] == "waiting_for_user"
    assert snapshot_after["pending_decisions"]


def test_bind_source_repairs_lowercased_connector_binding_and_preserves_chat_id_case(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    quest_service = QuestService(temp_home, skill_installer=SkillInstaller(repo_root(), temp_home))
    quest = quest_service.create("binding repair quest")

    quest_service.bind_source(quest["quest_id"], "qq:direct:cf8d2d559aa956b48751539adfb98865")
    repaired = quest_service.bind_source(quest["quest_id"], "qq:direct:CF8D2D559AA956B48751539ADFB98865")

    assert repaired["sources"] == ["qq:direct:CF8D2D559AA956B48751539ADFB98865"]


def test_artifact_delivery_prefers_connector_binding_case_for_qq(temp_home: Path, monkeypatch) -> None:
    ensure_home_layout(temp_home)
    manager = ConfigManager(temp_home)
    manager.ensure_files()
    connectors = manager.load_named("connectors")
    connectors["qq"]["enabled"] = True
    write_yaml(manager.path_for("connectors"), connectors)

    quest_service = QuestService(temp_home, skill_installer=SkillInstaller(repo_root(), temp_home))
    quest = quest_service.create("qq artifact delivery quest")
    quest_root = Path(quest["quest_root"])
    artifact = ArtifactService(temp_home)

    write_json(
        quest_root / ".ds" / "bindings.json",
        {"sources": ["local:default", "qq:direct:cf8d2d559aa956b48751539adfb98865"]},
    )
    write_json(
        temp_home / "logs" / "connectors" / "qq" / "bindings.json",
        {
            "bindings": {
                "qq:direct:CF8D2D559AA956B48751539ADFB98865": {
                    "quest_id": quest["quest_id"],
                    "updated_at": "2026-03-11T17:47:49+00:00",
                }
            }
        },
    )

    deliveries: list[str] = []

    class FakeBridge:
        def deliver(self, outbound: dict, config: dict) -> dict:  # noqa: ANN001
            deliveries.append(str(outbound.get("conversation_id") or ""))
            return {"ok": True, "transport": "qq-http"}

    monkeypatch.setattr("deepscientist.channels.qq.get_connector_bridge", lambda name: FakeBridge())

    result = artifact.interact(
        quest_root,
        kind="progress",
        message="QQ delivery should preserve the original openid casing.",
        deliver_to_bound_conversations=True,
        include_recent_inbound_messages=False,
    )

    assert result["delivered"] is True
    assert deliveries == ["qq:direct:CF8D2D559AA956B48751539ADFB98865"]


def test_artifact_record_and_snapshot_include_guidance_vm(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    quest_service = QuestService(temp_home, skill_installer=SkillInstaller(repo_root(), temp_home))
    quest = quest_service.create("guidance quest")
    quest_root = Path(quest["quest_root"])
    artifact = ArtifactService(temp_home)

    recorded = artifact.record(
        quest_root,
        {
            "kind": "baseline",
            "status": "completed",
            "baseline_id": "baseline-guidance",
            "summary": "Baseline recorded for guidance coverage.",
            "reason": "Need a durable baseline before ideation.",
            "primary_metric": "acc",
            "metrics_summary": {"acc": 0.87},
        },
    )

    assert recorded["ok"] is True
    assert recorded["guidance_vm"]["current_anchor"] == "baseline"
    assert recorded["guidance_vm"]["recommended_skill"] == "baseline"
    assert recorded["guidance_vm"]["suggested_artifact_calls"][0]["name"] == "artifact.confirm_baseline(...)"
    assert recorded["next_anchor"] == "baseline"
    assert recorded["recommended_skill_reads"] == ["baseline"]
    assert recorded["suggested_artifact_calls"][0]["name"] == "artifact.confirm_baseline(...)"
    assert recorded["next_instruction"] == recorded["guidance"]

    payload = json.loads(Path(recorded["path"]).read_text(encoding="utf-8"))
    assert payload["guidance_vm"]["recommended_action"] == "continue"

    events = read_jsonl(quest_root / ".ds" / "events.jsonl")
    artifact_event = next(item for item in events if item.get("type") == "artifact.recorded")
    assert artifact_event["guidance_vm"]["recommended_skill"] == "baseline"

    snapshot = quest_service.snapshot(quest["quest_id"])
    assert snapshot["guidance"]["recommended_skill"] == "baseline"
    assert "baseline" in snapshot["guidance"]["current_anchor"]


def test_approval_record_closes_pending_interaction(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    quest_service = QuestService(temp_home, skill_installer=SkillInstaller(repo_root(), temp_home))
    quest = quest_service.create("approval closes interaction")
    quest_root = Path(quest["quest_root"])
    artifact = ArtifactService(temp_home)

    request = artifact.interact(
        quest_root,
        kind="decision_request",
        message="Approve the expensive baseline reproduction?",
        deliver_to_bound_conversations=False,
        include_recent_inbound_messages=False,
    )
    decision_id = request["artifact_id"]
    snapshot_waiting = quest_service.snapshot(quest["quest_id"])
    assert snapshot_waiting["status"] == "waiting_for_user"

    artifact.record(
        quest_root,
        {
            "kind": "approval",
            "decision_id": decision_id,
            "reason": "Approved by user command.",
        },
    )

    snapshot_after = quest_service.snapshot(quest["quest_id"])
    assert snapshot_after["status"] == "active"
    assert not snapshot_after["pending_decisions"]


def test_complete_quest_requires_explicit_user_approval(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    quest_service = QuestService(temp_home, skill_installer=SkillInstaller(repo_root(), temp_home))
    quest = quest_service.create("completion approval required")
    quest_root = Path(quest["quest_root"])
    artifact = ArtifactService(temp_home)

    request = artifact.interact(
        quest_root,
        kind="decision_request",
        message="The quest appears complete. May I end it now?",
        deliver_to_bound_conversations=False,
        include_recent_inbound_messages=False,
        reply_mode="blocking",
        reply_schema={"decision_type": "quest_completion_approval"},
        options=[
            {"id": "approve", "label": "Approve", "description": "End the quest now."},
            {"id": "continue", "label": "Continue", "description": "Keep working."},
        ],
    )

    quest_service.append_message(
        quest["quest_id"],
        role="user",
        content="好的",
        source="web-react",
        reply_to_interaction_id=request["interaction_id"],
    )

    result = artifact.complete_quest(quest_root, summary="Attempting to complete the quest.")

    assert result["ok"] is False
    assert result["status"] == "approval_not_explicit"
    snapshot_after = quest_service.snapshot(quest["quest_id"])
    assert snapshot_after["status"] != "completed"


def test_complete_quest_marks_quest_completed_after_explicit_user_approval(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    quest_service = QuestService(temp_home, skill_installer=SkillInstaller(repo_root(), temp_home))
    quest = quest_service.create("completion approved")
    quest_root = Path(quest["quest_root"])
    artifact = ArtifactService(temp_home)

    request = artifact.interact(
        quest_root,
        kind="decision_request",
        message="The quest appears complete. May I end it now?",
        deliver_to_bound_conversations=False,
        include_recent_inbound_messages=False,
        reply_mode="blocking",
        reply_schema={"decision_type": "quest_completion_approval"},
        options=[
            {"id": "approve", "label": "Approve", "description": "End the quest now."},
            {"id": "continue", "label": "Continue", "description": "Keep working."},
        ],
    )

    reply = quest_service.append_message(
        quest["quest_id"],
        role="user",
        content="同意完成",
        source="web-react",
        reply_to_interaction_id=request["interaction_id"],
    )

    result = artifact.complete_quest(quest_root, summary="Research line finished with reviewed deliverables.")

    assert result["ok"] is True
    assert result["status"] == "completed"
    assert result["approval_message_id"] == reply["id"]
    assert result["snapshot"]["status"] == "completed"
    assert result["approval"]["record"]["source"]["kind"] == "user"
    assert result["decision"]["record"]["action"] == "stop"


def test_threaded_progress_auto_links_user_reply_without_waiting(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    quest_service = QuestService(temp_home, skill_installer=SkillInstaller(repo_root(), temp_home))
    quest = quest_service.create("threaded progress reply quest")
    quest_root = Path(quest["quest_root"])
    artifact = ArtifactService(temp_home)

    progress = artifact.interact(
        quest_root,
        kind="progress",
        message="老师，我已经完成仓库结构审计，正在整理下一步复现实验计划。",
        deliver_to_bound_conversations=False,
        include_recent_inbound_messages=False,
    )

    assert progress["status"] == "ok"
    assert progress["reply_mode"] == "threaded"

    snapshot_after_progress = quest_service.snapshot(quest["quest_id"])
    assert snapshot_after_progress["status"] != "waiting_for_user"
    assert snapshot_after_progress["default_reply_interaction_id"] == progress["interaction_id"]

    reply = quest_service.append_message(
        quest["quest_id"],
        role="user",
        content="继续，先把依赖和数据集入口确认下来。",
        source="web-react",
    )

    assert reply["reply_to_interaction_id"] == progress["interaction_id"]

    interaction_state = json.loads((quest_root / ".ds" / "interaction_state.json").read_text(encoding="utf-8"))
    latest_thread = interaction_state["recent_threads"][-1]
    assert latest_thread["interaction_id"] == progress["interaction_id"]
    assert latest_thread["last_reply_message_id"] == reply["id"]
    assert latest_thread["reply_count"] == 1

    follow_up = artifact.interact(
        quest_root,
        kind="progress",
        message="老师，我已经开始核对依赖版本。",
        deliver_to_bound_conversations=False,
        include_recent_inbound_messages=True,
    )

    assert follow_up["recent_inbound_messages"]
    latest = follow_up["recent_inbound_messages"][-1]
    assert latest["message_id"] == reply["id"]
    assert latest["reply_to_interaction_id"] == progress["interaction_id"]


def test_user_message_queue_is_delivered_only_when_artifact_interact_polls(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    quest_service = QuestService(temp_home, skill_installer=SkillInstaller(repo_root(), temp_home))
    quest = quest_service.create("queued mailbox quest")
    quest_root = Path(quest["quest_root"])
    artifact = ArtifactService(temp_home)

    first = quest_service.append_message(
        quest["quest_id"],
        role="user",
        content="先检查训练入口。",
        source="web-react",
    )
    second = quest_service.append_message(
        quest["quest_id"],
        role="user",
        content="然后核对依赖版本。",
        source="qq:group:demo",
    )

    queue_before = json.loads((quest_root / ".ds" / "user_message_queue.json").read_text(encoding="utf-8"))
    assert [item["message_id"] for item in queue_before["pending"]] == [first["id"], second["id"]]
    runtime_before = json.loads((quest_root / ".ds" / "runtime_state.json").read_text(encoding="utf-8"))
    assert runtime_before["pending_user_message_count"] == 2

    polled = artifact.interact(
        quest_root,
        kind="progress",
        message="老师，我已经进入检查阶段。",
        deliver_to_bound_conversations=False,
        include_recent_inbound_messages=True,
    )

    assert polled["delivery_batch"] is not None
    assert [item["message_id"] for item in polled["recent_inbound_messages"]] == [first["id"], second["id"]]
    assert "这是最新用户的要求" in polled["agent_instruction"]
    assert "优先于当前后台子任务" in polled["agent_instruction"]
    assert "立即再调用一次 artifact.interact" in polled["agent_instruction"]
    assert "先检查训练入口。" in polled["agent_instruction"]
    assert "然后核对依赖版本。" in polled["agent_instruction"]

    queue_after = json.loads((quest_root / ".ds" / "user_message_queue.json").read_text(encoding="utf-8"))
    assert queue_after["pending"] == []
    assert [item["message_id"] for item in queue_after["completed"][-2:]] == [first["id"], second["id"]]

    runtime_after = json.loads((quest_root / ".ds" / "runtime_state.json").read_text(encoding="utf-8"))
    assert runtime_after["pending_user_message_count"] == 0
    assert runtime_after["last_delivered_batch_id"] == polled["delivery_batch"]["batch_id"]
    assert runtime_after["last_artifact_interact_at"] is not None

    no_new_message = artifact.interact(
        quest_root,
        kind="progress",
        message="老师，我继续推进检查。",
        deliver_to_bound_conversations=False,
        include_recent_inbound_messages=True,
    )

    assert no_new_message["recent_inbound_messages"] == []
    assert "当前用户并没有发送任何消息" in no_new_message["agent_instruction"]
    assert len(no_new_message["recent_interaction_records"]) >= 3


def test_user_message_queue_agent_instruction_respects_english_locale(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    manager = ConfigManager(temp_home)
    manager.ensure_files()
    config = manager.load_named("config")
    config["default_locale"] = "en-US"
    write_yaml(manager.path_for("config"), config)

    quest_service = QuestService(temp_home, skill_installer=SkillInstaller(repo_root(), temp_home))
    quest = quest_service.create("english mailbox quest")
    quest_root = Path(quest["quest_root"])
    artifact = ArtifactService(temp_home)

    quest_service.append_message(
        quest["quest_id"],
        role="user",
        content="Check the training entrypoint first.",
        source="web-react",
    )

    polled = artifact.interact(
        quest_root,
        kind="progress",
        message="I am checking the repository.",
        deliver_to_bound_conversations=False,
        include_recent_inbound_messages=True,
    )

    assert "These are the latest user requirements in chronological order." in polled["agent_instruction"]
    assert "take priority over the current background subtask" in polled["agent_instruction"]
    assert "Immediately call artifact.interact(...) again" in polled["agent_instruction"]
    assert "Check the training entrypoint first." in polled["agent_instruction"]

    no_new_message = artifact.interact(
        quest_root,
        kind="progress",
        message="I am continuing the check.",
        deliver_to_bound_conversations=False,
        include_recent_inbound_messages=True,
    )

    assert (
        no_new_message["agent_instruction"]
        .startswith("No new user message has arrived. Continue the task according to the user's requirements.")
    )
    assert "Here are the latest 10 artifact-related interaction records:" in no_new_message["agent_instruction"]


def test_artifact_interact_default_agent_instruction_respects_english_locale(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    manager = ConfigManager(temp_home)
    manager.ensure_files()
    config = manager.load_named("config")
    config["default_locale"] = "en-US"
    write_yaml(manager.path_for("config"), config)

    quest_service = QuestService(temp_home, skill_installer=SkillInstaller(repo_root(), temp_home))
    quest = quest_service.create("english fallback instruction quest")
    quest_root = Path(quest["quest_root"])
    artifact = ArtifactService(temp_home)

    result = artifact.interact(
        quest_root,
        kind="progress",
        message="Still auditing.",
        deliver_to_bound_conversations=False,
        include_recent_inbound_messages=False,
    )

    assert result["agent_instruction"] == "No new user message has arrived. Continue the task according to the user's requirements."


def test_analysis_campaign_uses_current_workspace_parent_and_returns_there(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    quest_service = QuestService(temp_home, skill_installer=SkillInstaller(repo_root(), temp_home))
    quest = quest_service.create("current workspace analysis parent quest")
    quest_root = Path(quest["quest_root"])
    artifact = ArtifactService(temp_home)

    _confirm_local_baseline(artifact, quest_root)
    parent = artifact.submit_idea(
        quest_root,
        title="Parent route",
        problem="Need a durable parent node.",
        hypothesis="The parent route is promising enough for follow-up evidence.",
        mechanism="Establish the first durable branch.",
        expected_gain="A stable branch to analyze.",
        decision_reason="Promote the first route.",
    )
    artifact.record_main_experiment(
        quest_root,
        run_id="run-parent",
        title="Parent run",
        hypothesis="The parent route works.",
        setup="Use the standard configuration.",
        execution="Ran the main training and evaluation flow.",
        results="The run is promising and needs one extra follow-up experiment.",
        conclusion="Use this result as the parent node for a follow-up branch.",
        metrics_summary={"acc": 0.84},
        metric_rows=[{"metric_id": "acc", "value": 0.84}],
        evidence_paths=["experiments/main/run-parent/result.json"],
    )
    head = artifact.submit_idea(
        quest_root,
        title="New head route",
        problem="A newer route now exists.",
        hypothesis="This becomes the latest head branch.",
        mechanism="Branch a new route after the parent result.",
        expected_gain="A distinct newer head.",
        decision_reason="Keep exploring a different route.",
    )

    quest_service.update_research_state(
        quest_root,
        active_idea_id=parent["idea_id"],
        current_workspace_branch=parent["branch"],
        current_workspace_root=parent["worktree_root"],
        workspace_mode="idea",
    )

    campaign = artifact.create_analysis_campaign(
        quest_root,
        campaign_title="Single extra experiment",
        campaign_goal="Run one follow-up experiment from the previously selected node.",
        slices=[
            {
                "slice_id": "follow-up",
                "title": "Follow-up experiment",
                "goal": "Run the extra experiment as a true child branch.",
                "required_changes": "Apply only the follow-up change.",
                "metric_contract": "Use the same baseline comparison contract.",
            }
        ],
    )

    assert campaign["parent_branch"] == parent["branch"]
    assert campaign["parent_worktree_root"] == parent["worktree_root"]
    assert campaign["slices"][0]["branch"].startswith(f"analysis/{parent['idea_id']}/")

    completed = artifact.record_analysis_slice(
        quest_root,
        campaign_id=campaign["campaign_id"],
        slice_id="follow-up",
        setup="Apply the follow-up change only.",
        execution="Ran the extra experiment fully.",
        results="The extra experiment finished cleanly.",
        metric_rows=[{"name": "acc", "value": 0.845}],
        evidence_paths=["experiments/analysis/follow-up/result.json"],
    )

    assert completed["completed"] is True
    assert completed["returned_to_branch"] == parent["branch"]
    final_state = quest_service.read_research_state(quest_root)
    assert final_state["current_workspace_branch"] == parent["branch"]
    assert final_state["current_workspace_root"] == parent["worktree_root"]
    assert final_state["research_head_branch"] == head["branch"]
    assert final_state["active_idea_id"] == parent["idea_id"]
