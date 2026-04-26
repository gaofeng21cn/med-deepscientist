from __future__ import annotations

from pathlib import Path

import pytest

from deepscientist.strangler_registry import (
    RUNTIME_PROTOCOL_REF,
    boundary_guard_report,
    default_strangler_registry,
    normalize_surface_record,
)


def test_default_registry_marks_runtime_protocol_and_artifact_surfaces() -> None:
    registry = default_strangler_registry()

    assert registry["daemon_api_minimum"]["strangler_stage"] == "promote_to_runtime_protocol"
    assert registry["daemon_api_minimum"]["mas_consumable_contract"] is True
    assert registry["paper_baseline_inventory"]["strangler_stage"] == "oracle_only"
    assert registry["paper_baseline_inventory"]["mas_consumable_contract"] is False
    assert registry["publication_readiness_authority"]["strangler_stage"] == "mas_owned_or_absorbed"


def test_surface_record_requires_runtime_protocol_for_mas_consumable_promotion() -> None:
    with pytest.raises(ValueError, match="runtime protocol"):
        normalize_surface_record(
            {
                "surface": "unregistered_product_api",
                "current_owner": "MedDeepScientist",
                "target_owner": "MedAutoScience runtime adapter",
                "strangler_stage": "promote_to_runtime_protocol",
                "mas_consumable_contract": True,
                "promotion_gate": "docs/policies/other.md",
                "parity_proof": "targeted regression",
                "rollback_surface": "quest-local fixture",
            }
        )

    record = normalize_surface_record(
        {
            "surface": "runtime_event_surface",
            "current_owner": "MedDeepScientist",
            "target_owner": "MedAutoScience runtime adapter",
            "strangler_stage": "promote_to_runtime_protocol",
            "mas_consumable_contract": True,
            "promotion_gate": RUNTIME_PROTOCOL_REF,
            "parity_proof": "runtime protocol regression",
            "rollback_surface": "runtime_event/latest.json",
        }
    )
    assert record["strangler_stage"] == "promote_to_runtime_protocol"


def test_boundary_guard_flags_oversized_files_and_owner_reflux_risk(tmp_path: Path) -> None:
    oversized = tmp_path / "src" / "deepscientist" / "owner_surface.py"
    oversized.parent.mkdir(parents=True)
    oversized.write_text("\n".join(f"line {index}" for index in range(6)), encoding="utf-8")

    risky_surface = {
        "surface": "publication_gate_status",
        "current_owner": "MedDeepScientist",
        "target_owner": "MedDeepScientist backend",
        "strangler_stage": "retain_in_mds_backend",
        "mas_consumable_contract": False,
        "promotion_gate": RUNTIME_PROTOCOL_REF,
        "parity_proof": "paper gate regression",
        "rollback_surface": "artifacts/publication_eval/latest.json",
        "owner_authority": "publication_readiness",
    }

    report = boundary_guard_report(
        tmp_path,
        surfaces=[risky_surface],
        max_file_lines=5,
        include_file_suffixes=(".py",),
    )

    assert report["ok"] is False
    assert {issue["code"] for issue in report["issues"]} == {"oversized_file", "owner_reflux_risk"}
    oversized_issue = next(issue for issue in report["issues"] if issue["code"] == "oversized_file")
    assert oversized_issue["path"] == "src/deepscientist/owner_surface.py"
    assert oversized_issue["line_count"] == 6

