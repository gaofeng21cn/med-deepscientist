from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

import pytest

from deepscientist.artifact import ArtifactService
from deepscientist.config import ConfigManager
from deepscientist.daemon.app import DaemonApp
from deepscientist.gitops import checkpoint_repo
from deepscientist.home import ensure_home_layout, repo_root
from deepscientist.quest import QuestService
from deepscientist.shared import run_command, write_text
from deepscientist.skills import SkillInstaller


def _confirm_local_baseline(artifact: ArtifactService, quest_root: Path, baseline_id: str = "baseline-local") -> None:
    baseline_root = quest_root / "baselines" / "local" / baseline_id
    baseline_root.mkdir(parents=True, exist_ok=True)
    (baseline_root / "README.md").write_text("# Baseline\n", encoding="utf-8")
    artifact.confirm_baseline(
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


def test_git_branch_canvas_distinguishes_major_and_analysis_branches(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    quest_service = QuestService(temp_home, skill_installer=SkillInstaller(repo_root(), temp_home))
    quest = quest_service.create("branch canvas quest")
    quest_id = quest["quest_id"]
    quest_root = Path(quest["quest_root"])
    artifact = ArtifactService(temp_home)

    idea_branch = artifact.prepare_branch(
        quest_root,
        idea_id="idea-001",
        branch_kind="idea",
        create_worktree_flag=False,
    )
    assert idea_branch["parent_branch"] == "main"

    run_command(["git", "checkout", idea_branch["branch"]], cwd=quest_root, check=True)
    write_text(quest_root / "plan.md", "# Idea branch\n\nPromote this idea.\n")
    checkpoint_repo(quest_root, "idea branch update", allow_empty=False)
    artifact.record(
        quest_root,
        {
            "kind": "decision",
            "verdict": "continue",
            "action": "branch",
            "reason": "The first idea is worth implementing.",
            "summary": "Promoted idea-001 to implementation.",
            "idea_id": "idea-001",
        },
    )

    main_branch = artifact.prepare_branch(
        quest_root,
        run_id="main-exp-001",
        branch_kind="run",
        create_worktree_flag=False,
    )
    assert main_branch["parent_branch"] == idea_branch["branch"]

    run_command(["git", "checkout", main_branch["branch"]], cwd=quest_root, check=True)
    write_text(quest_root / "status.md", "# Main experiment\n\nacc: 0.91\n")
    checkpoint_repo(quest_root, "main experiment update", allow_empty=False)
    artifact.record(
        quest_root,
        {
            "kind": "run",
            "run_id": "main-exp-001",
            "run_kind": "experiment",
            "summary": "Main implementation improved the baseline.",
            "metrics_summary": {"acc": 0.91, "f1": 0.88},
        },
    )

    analysis_branch = artifact.prepare_branch(
        quest_root,
        run_id="analysis-001",
        branch_kind="run",
        create_worktree_flag=False,
    )
    assert analysis_branch["parent_branch"] == main_branch["branch"]

    run_command(["git", "checkout", analysis_branch["branch"]], cwd=quest_root, check=True)
    write_text(quest_root / "experiments" / "analysis" / "report.md", "# Ablation\n\nAnalysis details here.\n")
    checkpoint_repo(quest_root, "analysis branch update", allow_empty=False)
    artifact.record(
        quest_root,
        {
            "kind": "run",
            "run_id": "analysis-001",
            "run_kind": "analysis-campaign",
            "summary": "Ablation branch explored robustness.",
            "metrics_summary": {"acc": 0.89},
        },
    )

    app = DaemonApp(temp_home)
    branches = app.handlers.git_branches(quest_id)
    nodes = {item["ref"]: item for item in branches["nodes"]}

    assert nodes["main"]["branch_kind"] == "quest"
    assert nodes[idea_branch["branch"]]["branch_kind"] == "idea"
    assert nodes[idea_branch["branch"]]["tier"] == "major"
    assert nodes[main_branch["branch"]]["branch_kind"] == "implementation"
    assert nodes[analysis_branch["branch"]]["branch_kind"] == "analysis"
    assert nodes[analysis_branch["branch"]]["tier"] == "minor"
    assert nodes[analysis_branch["branch"]]["parent_ref"] == main_branch["branch"]
    assert nodes[analysis_branch["branch"]]["latest_metric"]["key"] == "acc"

    compare = app.handlers.git_compare(
        quest_id,
        path=f"/api/quests/{quest_id}/git/compare?base={quote(main_branch['branch'])}&head={quote(analysis_branch['branch'])}",
    )
    assert compare["ok"] is True
    assert any(item["path"] == "experiments/analysis/report.md" for item in compare["files"])

    log_payload = app.handlers.git_log(
        quest_id,
        path=f"/api/quests/{quest_id}/git/log?ref={quote(analysis_branch['branch'])}&base={quote(main_branch['branch'])}&limit=10",
    )
    assert log_payload["ok"] is True
    assert log_payload["commits"]
    target_sha = None
    for item in log_payload["commits"]:
        detail = app.handlers.git_commit(
            quest_id,
            path=f"/api/quests/{quest_id}/git/commit?sha={quote(item['sha'])}",
        )
        if any(file_item["path"] == "experiments/analysis/report.md" for file_item in detail["files"]):
            target_sha = item["sha"]
            break
    assert target_sha is not None

    commit_payload = app.handlers.git_commit(
        quest_id,
        path=f"/api/quests/{quest_id}/git/commit?sha={quote(target_sha)}",
    )
    assert commit_payload["ok"] is True
    assert commit_payload["sha"] == target_sha
    assert any(item["path"] == "experiments/analysis/report.md" for item in commit_payload["files"])

    diff = app.handlers.git_diff_file(
        quest_id,
        path=(
            f"/api/quests/{quest_id}/git/diff-file?base={quote(main_branch['branch'])}"
            f"&head={quote(analysis_branch['branch'])}&path={quote('experiments/analysis/report.md')}"
        ),
    )
    assert diff["ok"] is True
    assert diff["path"] == "experiments/analysis/report.md"
    assert any("Analysis details here." in line for line in diff["lines"])

    commit_diff = app.handlers.git_commit_file(
        quest_id,
        path=f"/api/quests/{quest_id}/git/commit-file?sha={quote(target_sha)}&path={quote('experiments/analysis/report.md')}",
    )
    assert commit_diff["ok"] is True
    assert commit_diff["path"] == "experiments/analysis/report.md"
    assert any("Analysis details here." in line for line in commit_diff["lines"])


def test_git_branch_canvas_reads_artifacts_from_worktrees(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    quest_service = QuestService(temp_home, skill_installer=SkillInstaller(repo_root(), temp_home))
    quest = quest_service.create("worktree canvas quest")
    quest_id = quest["quest_id"]
    quest_root = Path(quest["quest_root"])
    artifact = ArtifactService(temp_home)
    _confirm_local_baseline(artifact, quest_root)

    idea = artifact.submit_idea(
        quest_root,
        mode="create",
        title="Adapter route",
        problem="Baseline saturates.",
        hypothesis="A lightweight adapter helps.",
        mechanism="Insert a residual adapter.",
        decision_reason="Promote the strongest current route.",
    )
    campaign = artifact.create_analysis_campaign(
        quest_root,
        campaign_title="Ablation suite",
        campaign_goal="Stress-test the promoted idea.",
        slices=[
            {
                "slice_id": "ablation",
                "title": "Adapter ablation",
                "goal": "Disable the adapter and compare.",
                "required_changes": "Disable adapter only.",
                "metric_contract": "Report full validation metrics.",
            }
        ],
    )
    artifact.record_analysis_slice(
        quest_root,
        campaign_id=campaign["campaign_id"],
        slice_id="ablation",
        setup="Disable the adapter only.",
        execution="Ran the full validation sweep.",
        results="Accuracy dropped as expected.",
        metric_rows=[{"name": "acc", "value": 0.84}],
        evidence_paths=["experiments/analysis/ablation/result.json"],
        evaluation_summary={
            "takeaway": "The ablation removes the observed gain.",
            "claim_update": "strengthens",
            "baseline_relation": "better",
            "comparability": "high",
            "failure_mode": "none",
            "next_action": "write",
        },
    )

    app = DaemonApp(temp_home)
    branches = app.handlers.git_branches(quest_id)
    nodes = {item["ref"]: item for item in branches["nodes"]}
    analysis_branch = campaign["slices"][0]["branch"]

    assert nodes[idea["branch"]]["branch_kind"] == "idea"
    assert nodes[idea["branch"]]["branch_no"] == "001"
    assert nodes[idea["branch"]]["idea_title"] == "Adapter route"
    assert nodes[idea["branch"]]["lineage_intent"] == "continue_line"
    assert nodes[idea["branch"]]["parent_branch"] == "main"
    assert nodes[idea["branch"]]["idea_draft_path"].endswith("/draft.md")
    assert nodes[idea["branch"]]["foundation_ref"]["kind"] == "current_head"
    assert nodes[analysis_branch]["branch_kind"] == "analysis"
    assert nodes[analysis_branch]["latest_metric"]["key"] == "acc"
    assert nodes[analysis_branch]["worktree_root"] == campaign["slices"][0]["worktree_root"]
    assert nodes[analysis_branch]["latest_result"]["evaluation_summary"]["next_action"] == "write"


def test_git_branch_canvas_marks_breakthrough_and_metrics_timeline(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    quest_service = QuestService(temp_home, skill_installer=SkillInstaller(repo_root(), temp_home))
    quest = quest_service.create("branch breakthrough quest")
    quest_id = quest["quest_id"]
    quest_root = Path(quest["quest_root"])
    artifact = ArtifactService(temp_home)
    baseline_root = quest_root / "baselines" / "local" / "baseline-graph"
    baseline_root.mkdir(parents=True, exist_ok=True)
    (baseline_root / "README.md").write_text("# Graph baseline\n", encoding="utf-8")

    artifact.record(
        quest_root,
        {
            "kind": "baseline",
            "publish_global": True,
            "baseline_id": "baseline-graph",
            "name": "Graph baseline",
            "primary_metric": {"name": "acc", "value": 0.8},
            "metrics_summary": {"acc": 0.8},
            "baseline_variants": [{"variant_id": "main", "label": "Main", "metrics_summary": {"acc": 0.8}}],
            "default_variant_id": "main",
        },
    )
    artifact.attach_baseline(quest_root, "baseline-graph", "main")
    artifact.confirm_baseline(
        quest_root,
        baseline_path="baselines/imported/baseline-graph",
        baseline_id="baseline-graph",
        variant_id="main",
        summary="Baseline graph confirmed",
    )
    idea = artifact.submit_idea(
        quest_root,
        mode="create",
        title="Adapter route",
        problem="Baseline saturates.",
        hypothesis="A lightweight adapter helps.",
        mechanism="Insert a residual adapter.",
        decision_reason="Promote the strongest current route.",
    )
    worktree_root = Path(idea["worktree_root"])
    write_text(worktree_root / "status.md", "# Main experiment\n\nacc: 0.86\n")

    artifact.record_main_experiment(
        quest_root,
        run_id="main-graph-001",
        title="Graph main run",
        hypothesis="Adapter improves accuracy.",
        setup="Baseline recipe.",
        execution="Ran full validation.",
        results="Accuracy improved.",
        conclusion="Good enough for follow-up.",
        metric_rows=[{"metric_id": "acc", "value": 0.86}],
        evaluation_summary={
            "takeaway": "The graph test branch beats the baseline on accuracy.",
            "claim_update": "strengthens",
            "baseline_relation": "better",
            "comparability": "high",
            "failure_mode": "none",
            "next_action": "analysis_campaign",
        },
    )

    app = DaemonApp(temp_home)
    branches = app.handlers.git_branches(quest_id)
    nodes = {item["ref"]: item for item in branches["nodes"]}

    assert nodes[idea["branch"]]["breakthrough"] is True
    assert nodes[idea["branch"]]["breakthrough_level"] in {"minor", "major"}
    assert nodes[idea["branch"]]["latest_result"]["run_id"] == "main-graph-001"
    assert nodes[idea["branch"]]["latest_metric"]["delta_vs_baseline"] == pytest.approx(0.06)
    assert nodes[idea["branch"]]["latest_result"]["evaluation_summary"]["claim_update"] == "strengthens"

    timeline = app.handlers.metrics_timeline(quest_id)
    assert timeline["primary_metric_id"] == "acc"
    acc_series = next(item for item in timeline["series"] if item["metric_id"] == "acc")
    assert acc_series["points"][0]["value"] == 0.86
    assert acc_series["points"][0]["breakthrough"] is True
    assert acc_series["baselines"][0]["value"] == 0.8


def test_git_branch_canvas_parents_follow_up_analysis_to_current_workspace_node(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    quest_service = QuestService(temp_home, skill_installer=SkillInstaller(repo_root(), temp_home))
    quest = quest_service.create("canvas current workspace parent quest")
    quest_id = quest["quest_id"]
    quest_root = Path(quest["quest_root"])
    artifact = ArtifactService(temp_home)
    _confirm_local_baseline(artifact, quest_root)

    parent = artifact.submit_idea(
        quest_root,
        title="Parent route",
        problem="Need a stable node for analysis.",
        hypothesis="This route will own the follow-up analysis branch.",
        mechanism="Create the first durable route.",
        expected_gain="A parent node for the canvas test.",
        decision_reason="Use this route first.",
    )
    artifact.record_main_experiment(
        quest_root,
        run_id="run-parent",
        title="Parent run",
        hypothesis="The parent route is good enough.",
        setup="Standard setup.",
        execution="Executed the main run.",
        results="Needs one more follow-up experiment.",
        conclusion="Launch a child analysis branch from this node.",
        metrics_summary={"acc": 0.84},
        metric_rows=[{"metric_id": "acc", "value": 0.84}],
    )
    head = artifact.submit_idea(
        quest_root,
        title="Latest head route",
        problem="Create a newer head branch.",
        hypothesis="This becomes the head, but not the active canvas parent.",
        mechanism="Branch a newer route.",
        expected_gain="Separate current head from current workspace.",
        decision_reason="Advance the head branch.",
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
        campaign_title="Follow-up child branch",
        campaign_goal="Ensure the canvas edge comes from the current workspace node.",
        slices=[
            {
                "slice_id": "follow-up",
                "title": "Follow-up",
                "goal": "Create exactly one child analysis branch.",
                "required_changes": "One isolated follow-up change.",
                "metric_contract": "Keep the same evaluation contract.",
            }
        ],
    )
    analysis_branch = campaign["slices"][0]["branch"]

    app = DaemonApp(temp_home)
    branches = app.handlers.git_branches(quest_id)
    nodes = {item["ref"]: item for item in branches["nodes"]}

    assert head["branch"] != parent["branch"]
    assert nodes[analysis_branch]["parent_ref"] == parent["branch"]
    assert nodes[analysis_branch]["parent_branch_recorded"] == parent["branch"]
