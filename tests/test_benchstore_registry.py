from __future__ import annotations

from pathlib import Path

from deepscientist.benchstore import BenchStoreCatalogLoader, BenchStoreRegistryService
from deepscientist.shared import ensure_dir, write_yaml


def _write_catalog_entry(repo_root: Path, relative_path: str, payload: object) -> Path:
    path = ensure_dir(repo_root / "AISB" / "catalog" / Path(relative_path).parent) / Path(relative_path).name
    write_yaml(path, payload)
    return path


def test_benchstore_loader_normalizes_entry_schema(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    entry_path = _write_catalog_entry(
        repo_root,
        "vision/bench-demo.yaml",
        {
            "id": "Vision Bench Demo",
            "name": "Vision Bench Demo",
            "one_line": " Snapshot benchmark ",
            "task_description": "Evaluates a model on microscopy snapshots.",
            "capability_tags": ["vision", "", "multimodal"],
            "track_fit": ["leaderboard", "paper"],
            "requires_paper": "yes",
            "requires_execution": "false",
            "cost_band": "low",
            "time_band": "6h",
            "paper": {
                "title": "Vision Bench Paper",
                "year": "2025",
                "url": "https://example.com/paper",
            },
            "download": {
                "url": "https://example.com/archive.zip",
                "size_bytes": "4096",
            },
            "resources": {
                "minimum": {"cpu_cores": "8", "ram_gb": 16},
            },
            "environment": {
                "python": "3.11",
                "key_packages": ["torch", "", "timm"],
            },
            "dataset_download": {
                "primary_method": "manual",
                "sources": [
                    {"kind": "huggingface", "url": "https://hf.co/datasets/demo"},
                    "https://example.com/mirror",
                ],
            },
        },
    )

    loader = BenchStoreCatalogLoader(repo_root=repo_root)
    entry = loader.load_entry_file(entry_path, include_raw_payload=True)

    assert entry["id"] == "vision_bench_demo"
    assert entry["schema_version"] == 1
    assert entry["requires_paper"] is True
    assert entry["requires_execution"] is False
    assert entry["capability_tags"] == ["vision", "multimodal"]
    assert entry["track_fit"] == ["leaderboard", "paper"]
    assert entry["paper"]["year"] == 2025
    assert entry["download"]["size_bytes"] == 4096
    assert entry["resources"]["minimum"] == {"cpu_cores": 8.0, "ram_gb": 16.0}
    assert entry["environment"]["key_packages"] == ["torch", "timm"]
    assert entry["dataset_download"]["sources"][1]["url"] == "https://example.com/mirror"
    assert entry["source_file"] == "AISB/catalog/vision/bench-demo.yaml"
    assert "vision bench demo" in entry["search_text"]
    assert entry["raw_payload"]["requires_paper"] == "yes"


def test_benchstore_registry_lists_catalog_and_prefers_locale_override(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    _write_catalog_entry(
        repo_root,
        "bench-alpha.yaml",
        {
            "id": "bench_alpha",
            "name": "Bench Alpha",
            "capability_tags": ["analysis"],
            "cost_band": "low",
            "time_band": "2h",
            "requires_paper": True,
        },
    )
    _write_catalog_entry(
        repo_root,
        "bench-alpha.zh.yaml",
        {
            "id": "bench_alpha",
            "name": "基准 Alpha",
            "capability_tags": ["analysis"],
            "cost_band": "low",
            "time_band": "2h",
            "requires_paper": True,
        },
    )
    _write_catalog_entry(
        repo_root,
        "bench-beta.yaml",
        {
            "id": "bench_beta",
            "name": "Bench Beta",
            "capability_tags": ["leaderboard"],
            "cost_band": "high",
            "time_band": "2d",
            "requires_paper": False,
        },
    )
    _write_catalog_entry(repo_root, "broken.yaml", {"id": "broken"})

    service = BenchStoreRegistryService(repo_root=repo_root)
    result = service.list_entries(locale="zh")

    assert result["ok"] is True
    assert result["total"] == 2
    assert [item["id"] for item in result["items"]] == ["bench_alpha", "bench_beta"]
    assert result["items"][0]["name"] == "基准 Alpha"
    assert result["items"][1]["name"] == "Bench Beta"
    assert result["filter_options"]["capability_tags"] == ["analysis", "leaderboard"]
    assert result["filter_options"]["cost_band"] == ["high", "low"]
    assert result["filter_options"]["requires_paper"] == ["false", "true"]
    assert result["invalid_entries"] == [
        {
            "source_file": "AISB/catalog/broken.yaml",
            "message": "BenchStore entry requires non-empty `name`.",
        }
    ]


def test_benchstore_registry_query_filters_core_fields(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    _write_catalog_entry(
        repo_root,
        "paper-low.yaml",
        {
            "id": "paper_low",
            "name": "Paper Low",
            "capability_tags": ["leaderboard", "paper"],
            "requires_paper": True,
            "cost_band": "low",
            "time_band": "2h",
        },
    )
    _write_catalog_entry(
        repo_root,
        "paper-medium.yaml",
        {
            "id": "paper_medium",
            "name": "Paper Medium",
            "capability_tags": ["leaderboard", "analysis"],
            "requires_paper": True,
            "cost_band": "medium",
            "time_band": "6h",
        },
    )
    _write_catalog_entry(
        repo_root,
        "gpu-high.yaml",
        {
            "id": "gpu_high",
            "name": "GPU High",
            "capability_tags": ["gpu"],
            "requires_paper": False,
            "cost_band": "high",
            "time_band": "2d",
        },
    )

    service = BenchStoreRegistryService(repo_root=repo_root)

    filtered = service.query_entries(
        filters={
            "tags": ["leaderboard"],
            "requires_paper": True,
            "cost_band": ["low", "medium"],
            "max_time_hours": 6,
        }
    )
    exact_time = service.query_entries(filters={"time_band": "2h"})

    assert [item["id"] for item in filtered["items"]] == ["paper_low", "paper_medium"]
    assert [item["id"] for item in exact_time["items"]] == ["paper_low"]
    assert filtered["applied_filters"] == {
        "cost_band": ["low", "medium"],
        "max_time_hours": 6.0,
        "requires_paper": True,
        "tags": ["leaderboard"],
    }
