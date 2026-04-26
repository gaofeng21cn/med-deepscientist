from __future__ import annotations

from pathlib import Path

import pytest

from deepscientist.artifact.service_parts import artifact_inventory
from deepscientist.shared import read_json


def test_artifact_inventory_surface_audit_keeps_baseline_inventory_oracle_only() -> None:
    audit = artifact_inventory.artifact_inventory_surface_audit("paper_baseline_inventory")

    assert audit["surface"] == "paper_baseline_inventory"
    assert audit["current_owner"] == "MedDeepScientist"
    assert audit["strangler_stage"] == "oracle_only"
    assert audit["mas_consumable_contract"] is False
    assert audit["promotion_gate"] == "docs/policies/runtime_protocol.md"
    assert audit["parity_proof"] == "targeted artifact inventory regression tests"


def test_validate_promotion_ladder_stage_requires_runtime_protocol_for_promotion() -> None:
    with pytest.raises(ValueError, match="runtime protocol"):
        artifact_inventory.validate_promotion_ladder_stage(
            "promote_to_runtime_protocol",
            runtime_protocol_ref=None,
        )


def test_build_paper_baseline_inventory_payload_carries_oracle_surface_audit() -> None:
    payload = artifact_inventory.build_paper_baseline_inventory_payload(
        quest_yaml={
            "confirmed_baseline_ref": {
                "baseline_id": "main",
                "baseline_path": "baselines/local/main",
            }
        },
        analysis_inventory={
            "entries": [
                {
                    "baseline_id": "cmp",
                    "status": "registered",
                }
            ]
        },
    )

    assert payload["schema_version"] == 1
    assert payload["canonical_baseline_ref"]["baseline_id"] == "main"
    assert payload["supplementary_baselines"][0]["baseline_id"] == "cmp"
    assert payload["surface_audit"]["strangler_stage"] == "oracle_only"
    assert payload["surface_audit"]["mas_consumable_contract"] is False


def test_upsert_analysis_baseline_inventory_merges_same_origin_entry(tmp_path: Path) -> None:
    quest_root = tmp_path / "quest"
    quest_root.mkdir()

    artifact_inventory.upsert_analysis_baseline_inventory(
        quest_root,
        [
            {
                "baseline_id": "cmp",
                "status": "required",
                "benchmark": "validation",
                "origin": {"campaign_id": "analysis-001", "slice_id": "ablation"},
            }
        ],
    )
    inventory = artifact_inventory.upsert_analysis_baseline_inventory(
        quest_root,
        [
            {
                "baseline_id": "cmp",
                "status": "registered",
                "benchmark": "validation",
                "origin": {"campaign_id": "analysis-001", "slice_id": "ablation"},
            }
        ],
    )

    assert len(inventory["entries"]) == 1
    assert inventory["entries"][0]["status"] == "registered"
    assert inventory["entries"][0]["benchmark"] == "validation"
    persisted = read_json(quest_root / "artifacts" / "baselines" / "analysis_inventory.json", {})
    assert persisted["entries"] == inventory["entries"]
