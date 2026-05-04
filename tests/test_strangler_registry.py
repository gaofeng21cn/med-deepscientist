from __future__ import annotations

from pathlib import Path

import pytest

from deepscientist.strangler_registry import (
    MAS_OWNER_AUTHORITIES,
    RUNTIME_PROTOCOL_REF,
    boundary_guard_report,
    default_strangler_registry,
    mas_consumption_contract_report,
    normalize_surface_record,
)


def test_default_registry_marks_runtime_protocol_and_artifact_surfaces() -> None:
    registry = default_strangler_registry()

    assert registry["daemon_api_minimum"]["strangler_stage"] == "promote_to_runtime_protocol"
    assert registry["daemon_api_minimum"]["mas_consumable_contract"] is True
    assert registry["paper_baseline_inventory"]["strangler_stage"] == "oracle_only"
    assert registry["paper_baseline_inventory"]["mas_consumable_contract"] is False
    assert registry["publication_readiness_authority"]["strangler_stage"] == "mas_owned_or_absorbed"
    assert MAS_OWNER_AUTHORITIES <= {
        str(record.get("owner_authority") or "")
        for record in registry.values()
        if str(record.get("owner_authority") or "") in MAS_OWNER_AUTHORITIES
    }


def test_surface_boundary_read_model_distinguishes_all_owner_boundary_states() -> None:
    from deepscientist import strangler_registry

    surfaces = [
        {
            "surface": "backend_runtime_impl",
            "current_owner": "MedDeepScientist controlled backend",
            "target_owner": "MedDeepScientist controlled backend",
            "strangler_stage": "retain_in_mds_backend",
            "mas_consumable_contract": False,
            "promotion_gate": "docs/policies/mas_mds_transition_contract.md",
            "parity_proof": "runtime backend regression",
            "rollback_surface": "quest-local backend fixture",
        },
        {
            "surface": "prompt_oracle_fixture",
            "current_owner": "MedDeepScientist behavior oracle",
            "target_owner": "MedAutoScience parity oracle",
            "strangler_stage": "oracle_only",
            "mas_consumable_contract": False,
            "promotion_gate": "docs/policies/mas_mds_transition_contract.md",
            "parity_proof": "prompt oracle regression",
            "rollback_surface": "prompt fixture",
        },
        {
            "surface": "runtime_event_adapter_contract",
            "current_owner": "MedDeepScientist controlled backend",
            "target_owner": "MedAutoScience runtime adapter",
            "strangler_stage": "promote_to_runtime_protocol",
            "mas_consumable_contract": True,
            "promotion_gate": RUNTIME_PROTOCOL_REF,
            "parity_proof": "runtime protocol regression",
            "rollback_surface": "runtime event fixture",
        },
        {
            "surface": "publication_quality_authority",
            "current_owner": "MedAutoScience product owner",
            "target_owner": "MedAutoScience product owner",
            "strangler_stage": "mas_owned_or_absorbed",
            "mas_consumable_contract": False,
            "promotion_gate": "docs/policies/mas_mds_transition_contract.md",
            "parity_proof": "MAS publication gate proof",
            "rollback_surface": "MDS oracle fixture only",
            "owner_authority": "publication_readiness",
        },
    ]

    read_model = strangler_registry.surface_boundary_read_model(surfaces)

    assert read_model["ok"] is True
    assert read_model["boundary_statuses"] == [
        "retain_backend",
        "oracle_only",
        "promote_runtime_protocol",
        "mas_owned_or_absorbed",
    ]
    by_surface = {surface["surface"]: surface for surface in read_model["surfaces"]}
    assert by_surface["backend_runtime_impl"]["boundary_status"] == "retain_backend"
    assert by_surface["prompt_oracle_fixture"]["boundary_status"] == "oracle_only"
    assert by_surface["runtime_event_adapter_contract"]["boundary_status"] == "promote_runtime_protocol"
    assert by_surface["publication_quality_authority"]["boundary_status"] == "mas_owned_or_absorbed"


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


def test_mas_consumption_contract_report_lists_required_fields_for_each_surface() -> None:
    report = mas_consumption_contract_report()

    assert report["ok"] is True
    assert report["surface_count"] >= 9
    required_fields = {
        "owner",
        "target_owner",
        "stage",
        "promotion_gate",
        "parity_proof",
        "rollback_surface",
        "mas_consumable_status",
    }
    for surface in report["surfaces"]:
        assert required_fields <= set(surface)

    by_surface = {surface["surface"]: surface for surface in report["surfaces"]}
    assert by_surface["daemon_api_minimum"]["mas_consumable_status"] == "mas_consumable"
    assert by_surface["publication_readiness_authority"]["mas_consumable_status"] == "mas_owned_or_absorbed"
    assert by_surface["paper_baseline_inventory"]["mas_consumable_status"] == "not_mas_consumable"


def test_mas_consumption_contract_report_fail_closes_missing_runtime_gate_or_parity_proof() -> None:
    surfaces = [
        {
            "surface": "unregistered_runtime_adapter",
            "current_owner": "MedDeepScientist",
            "target_owner": "MedAutoScience runtime adapter",
            "strangler_stage": "promote_to_runtime_protocol",
            "mas_consumable_contract": True,
            "promotion_gate": "docs/policies/mas_mds_transition_contract.md",
            "parity_proof": "targeted runtime regression",
            "rollback_surface": "quest-local fixture",
        },
        {
            "surface": "runtime_projection_without_oracle",
            "current_owner": "MedDeepScientist",
            "target_owner": "MedAutoScience runtime adapter",
            "strangler_stage": "promote_to_runtime_protocol",
            "mas_consumable_contract": True,
            "promotion_gate": RUNTIME_PROTOCOL_REF,
            "parity_proof": "",
            "rollback_surface": "runtime projection fixture",
        },
    ]

    report = mas_consumption_contract_report(surfaces)

    assert report["ok"] is False
    assert {issue["code"] for issue in report["issues"]} == {
        "mas_consumable_missing_runtime_protocol_gate",
        "mas_consumable_missing_parity_proof",
    }
    by_surface = {surface["surface"]: surface for surface in report["surfaces"]}
    assert (
        by_surface["unregistered_runtime_adapter"]["mas_consumable_status"]
        == "blocked_missing_runtime_protocol_gate"
    )
    assert (
        by_surface["runtime_projection_without_oracle"]["mas_consumable_status"]
        == "blocked_missing_parity_proof"
    )


def test_mas_consumption_contract_report_flags_owner_reflux_for_mas_authority() -> None:
    report = mas_consumption_contract_report(
        [
            {
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
        ]
    )

    assert report["ok"] is False
    assert report["issues"][0]["code"] == "owner_reflux_risk"
    assert report["surfaces"][0]["mas_consumable_status"] == "blocked_owner_reflux"


@pytest.mark.parametrize("owner_authority", sorted(MAS_OWNER_AUTHORITIES))
def test_mas_owner_authority_tags_fail_closed_unless_mas_owned_or_absorbed(owner_authority: str) -> None:
    report = mas_consumption_contract_report(
        [
            {
                "surface": f"{owner_authority}_mds_reflux",
                "current_owner": "MedDeepScientist",
                "target_owner": "MedDeepScientist backend",
                "strangler_stage": "oracle_only",
                "mas_consumable_contract": False,
                "promotion_gate": "docs/policies/mas_mds_transition_contract.md",
                "parity_proof": "owner boundary regression",
                "rollback_surface": "MDS oracle fixture only",
                "owner_authority": owner_authority,
            }
        ]
    )

    assert report["ok"] is False
    assert report["issues"][0]["code"] == "owner_reflux_risk"
    assert report["issues"][0]["owner_authorities"] == [owner_authority]
    assert report["surfaces"][0]["mas_consumable_status"] == "blocked_owner_reflux"


def test_multiple_owner_authority_tags_fail_closed_together() -> None:
    report = mas_consumption_contract_report(
        [
            {
                "surface": "research_design_and_interpretation_reflux",
                "current_owner": "MedDeepScientist",
                "target_owner": "MedDeepScientist backend",
                "strangler_stage": "retain_in_mds_backend",
                "mas_consumable_contract": False,
                "promotion_gate": "docs/policies/mas_mds_transition_contract.md",
                "parity_proof": "owner boundary regression",
                "rollback_surface": "MDS oracle fixture only",
                "owner_authorities": [
                    "medical_research_design",
                    "medical_evidence_interpretation",
                ],
            }
        ]
    )

    assert report["ok"] is False
    assert report["issues"][0]["code"] == "owner_reflux_risk"
    assert report["issues"][0]["owner_authorities"] == [
        "medical_research_design",
        "medical_evidence_interpretation",
    ]


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
