from __future__ import annotations

from pathlib import Path

from deepscientist.artifact import ArtifactService
from deepscientist.artifact.metrics import build_metrics_timeline
from deepscientist.config import ConfigManager
from deepscientist.home import ensure_home_layout, repo_root
from deepscientist.quest import QuestService
from deepscientist.skills import SkillInstaller


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_metrics_timeline_keeps_baseline_only_series_without_main_runs() -> None:
    timeline = build_metrics_timeline(
        quest_id="quest-baseline-only",
        run_records=[],
        baseline_entry={
            "baseline_id": "baseline-only",
            "metrics_summary": {"acc": 0.81, "loss": 0.42},
            "primary_metric": {"name": "acc", "value": 0.81},
            "metric_contract": {
                "primary_metric_id": "acc",
                "metrics": [
                    {"metric_id": "acc", "direction": "higher", "label": "Accuracy"},
                    {"metric_id": "loss", "direction": "lower", "label": "Loss"},
                ],
            },
        },
        selected_variant_id=None,
    )

    assert timeline["total_runs"] == 0
    assert timeline["primary_metric_id"] == "acc"
    series_by_id = {item["metric_id"]: item for item in timeline["series"]}
    assert set(series_by_id.keys()) == {"acc", "loss"}
    assert series_by_id["acc"]["points"] == []
    assert series_by_id["loss"]["points"] == []
    assert series_by_id["acc"]["baselines"][0]["value"] == 0.81
    assert series_by_id["loss"]["baselines"][0]["value"] == 0.42


def test_metrics_timeline_uses_primary_metric_when_baseline_summary_is_missing() -> None:
    timeline = build_metrics_timeline(
        quest_id="quest-baseline-primary-only",
        run_records=[],
        baseline_entry={
            "baseline_id": "baseline-primary-only",
            "metrics_summary": {},
            "primary_metric": {"name": "acc", "value": 0.83},
            "metric_contract": {
                "primary_metric_id": "acc",
                "metrics": [{"metric_id": "acc", "direction": "higher", "label": "Accuracy"}],
            },
        },
        selected_variant_id=None,
    )

    assert timeline["total_runs"] == 0
    series_by_id = {item["metric_id"]: item for item in timeline["series"]}
    assert set(series_by_id.keys()) == {"acc"}
    assert series_by_id["acc"]["points"] == []
    assert series_by_id["acc"]["baselines"][0]["value"] == 0.83


def test_metrics_timeline_prefers_variant_labels_for_baseline_series() -> None:
    timeline = build_metrics_timeline(
        quest_id="quest-baseline-variant-label",
        run_records=[],
        baseline_entry={
            "baseline_id": "baseline-series",
            "default_variant_id": "stable",
            "baseline_variants": [
                {
                    "variant_id": "stable",
                    "label": "Stable comparator",
                    "metrics_summary": {"acc": 0.88},
                    "primary_metric": {"name": "acc", "value": 0.88},
                }
            ],
            "metric_contract": {
                "primary_metric_id": "acc",
                "metrics": [{"metric_id": "acc", "direction": "higher", "label": "Accuracy"}],
            },
        },
        selected_variant_id="stable",
    )

    series_by_id = {item["metric_id"]: item for item in timeline["series"]}
    assert series_by_id["acc"]["baselines"][0]["label"] == "baseline-series:Stable comparator"


def test_details_surface_explicitly_handles_baseline_only_metrics_state() -> None:
    source = (REPO_ROOT / "src/ui/src/components/workspace/QuestWorkspaceSurface.tsx").read_text(
        encoding="utf-8"
    )

    assert "const hasMainExperimentMetricPoints = metricsTimelineSeries.some(" in source
    assert "Showing baseline-only metrics. Main-experiment traces will appear after the first recorded result." in source
    assert "Attach a baseline with recorded metrics to populate this section." in source


def test_metrics_timeline_falls_back_to_confirmed_baseline_artifact_when_attachment_is_missing(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    quest_service = QuestService(temp_home, skill_installer=SkillInstaller(repo_root(), temp_home))
    quest = quest_service.create("baseline attachment fallback quest")
    quest_root = Path(quest["quest_root"])
    artifact = ArtifactService(temp_home)

    baseline_root = quest_root / "baselines" / "local" / "baseline-fallback"
    baseline_root.mkdir(parents=True, exist_ok=True)
    (baseline_root / "README.md").write_text("# Baseline\n", encoding="utf-8")
    artifact.confirm_baseline(
        quest_root,
        baseline_path=str(baseline_root),
        baseline_id="baseline-fallback",
        summary="Confirmed fallback baseline.",
        metrics_summary={"acc": 0.87},
        primary_metric={"metric_id": "acc", "value": 0.87},
        metric_contract={"primary_metric_id": "acc", "metrics": [{"metric_id": "acc", "direction": "higher"}]},
    )

    attachment_path = baseline_root / "attachment.yaml"
    if attachment_path.exists():
        attachment_path.unlink()

    timeline = quest_service.metrics_timeline(quest["quest_id"])
    series_by_id = {item["metric_id"]: item for item in timeline["series"]}

    assert set(series_by_id.keys()) == {"acc"}
    assert series_by_id["acc"]["points"] == []
    assert series_by_id["acc"]["baselines"][0]["value"] == 0.87
