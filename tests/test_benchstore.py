from __future__ import annotations

from pathlib import Path

from deepscientist.benchstore import BenchStoreRegistryService
from deepscientist.config import ConfigManager
from deepscientist.daemon.api.router import match_route
from deepscientist.daemon.app import DaemonApp
from deepscientist.home import ensure_home_layout, repo_root
from deepscientist.prompts import PromptBuilder
from deepscientist.quest import QuestService
from deepscientist.shared import ensure_dir, write_yaml
from deepscientist.skills import SkillInstaller


def _write_catalog_entry(repo_root_path: Path, relative_path: str, payload: object) -> Path:
    path = ensure_dir(repo_root_path / "AISB" / "catalog" / Path(relative_path).parent) / Path(relative_path).name
    write_yaml(path, payload)
    return path


def test_repo_benchstore_catalog_has_real_entries() -> None:
    catalog_root = repo_root() / "AISB" / "catalog"

    assert catalog_root.exists()
    assert len(list(catalog_root.rglob("*.yaml"))) >= 10


def test_benchstore_setup_packet_prefills_start_research_form(tmp_path: Path) -> None:
    repo_root_path = tmp_path / "repo"
    _write_catalog_entry(
        repo_root_path,
        "vision/demo.yaml",
        {
            "id": "vision.demo",
            "name": "Vision Demo",
            "one_line": "Faithful vision benchmark",
            "task_description": "Run the benchmark faithfully and record reproducible outputs.",
            "capability_tags": ["vision", "benchmark"],
            "track_fit": ["leaderboard", "paper"],
            "requires_execution": True,
            "requires_paper": True,
            "cost_band": "medium",
            "time_band": "6h",
            "paper": {
                "title": "Vision Demo Paper",
                "url": "https://example.com/paper",
            },
            "dataset_download": {
                "primary_method": "manual",
                "sources": [
                    "https://example.com/dataset",
                ],
            },
            "environment": {
                "python": "3.11",
                "key_packages": ["torch", "timm"],
            },
            "resources": {
                "minimum": {"cpu_cores": 8, "ram_gb": 16},
                "recommended": {"cpu_cores": 16, "ram_gb": 32, "gpu_count": 1, "gpu_vram_gb": 24},
            },
        },
    )

    service = BenchStoreRegistryService(repo_root=repo_root_path)
    packet = service.build_setup_packet("vision.demo", locale="zh")

    assert packet["entry_id"] == "vision.demo"
    assert packet["assistant_label"] == "SetupAgent"
    assert packet["requires_paper"] is True
    assert packet["suggested_form"]["title"] == "Vision Demo"
    assert "Faithful vision benchmark" in str(packet["suggested_form"]["goal"])
    assert "https://example.com/paper" in str(packet["suggested_form"]["paper_urls"])
    assert "https://example.com/dataset" in str(packet["suggested_form"]["baseline_urls"])
    assert packet["launch_payload"]["startup_contract"]["benchstore_context"]["entry_id"] == "vision.demo"
    assert packet["launch_payload"]["startup_contract"]["start_setup_session"]["source"] == "benchstore"
    assert packet["launch_payload"]["startup_contract"]["start_setup_session"]["locale"] == "zh"
    assert packet["launch_payload"]["startup_contract"]["start_setup_session"]["benchmark_context"]["raw_payload"][
        "task_description"
    ] == "Run the benchmark faithfully and record reproducible outputs."


def test_prompt_builder_switches_to_start_setup_prompt_when_session_present(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    quest_service = QuestService(temp_home, skill_installer=SkillInstaller(repo_root(), temp_home))
    snapshot = quest_service.create(
        "benchstore setup quest",
        startup_contract={
            "start_setup_session": {
                "source": "benchstore",
                "locale": "zh",
                "benchmark_context": {
                    "entry_id": "vision.demo",
                    "entry_name": "Vision Demo",
                },
                "suggested_form": {
                    "title": "Vision Demo",
                    "goal": "Run the benchmark faithfully.",
                },
            }
        },
    )

    prompt = PromptBuilder(repo_root(), temp_home).build(
        quest_id=snapshot["quest_id"],
        skill_id="baseline",
        user_message="请帮我把这个 benchmark 的启动表单整理好。",
        model="gpt-5.4",
    )

    assert "# Autonomous Start Setup Agent" in prompt
    assert "built_in_mcp_namespaces: artifact, bash_exec" in prompt
    assert "artifact.prepare_start_setup_form" in prompt
    assert "workspace_mode: start_setup" in prompt
    assert "entry_id: vision.demo" in prompt


def test_daemon_handlers_expose_benchstore_catalog_and_setup_packet(temp_home: Path, tmp_path: Path) -> None:
    repo_root_path = tmp_path / "repo"
    _write_catalog_entry(
        repo_root_path,
        "demo.yaml",
        {
            "id": "demo.bench",
            "name": "Demo Bench",
            "one_line": "A compact benchmark demo",
            "task_description": "Use this to verify the BenchStore HTTP surface.",
            "requires_execution": True,
        },
    )

    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    app = DaemonApp(temp_home)
    app.benchstore_service = BenchStoreRegistryService(repo_root=repo_root_path)

    route_name, params = match_route("GET", "/api/benchstore/entries/demo.bench/setup-packet")
    assert route_name == "benchstore_entry_setup_packet"
    assert params["entry_id"] == "demo.bench"

    listing = app.handlers.benchstore_entries()
    detail = app.handlers.benchstore_entry("demo.bench")
    setup_packet = app.handlers.benchstore_entry_setup_packet("demo.bench")

    assert listing["ok"] is True
    assert listing["total"] == 1
    assert detail["entry"]["id"] == "demo.bench"
    assert setup_packet["ok"] is True
    assert setup_packet["entry_id"] == "demo.bench"
    assert setup_packet["setup_packet"]["suggested_form"]["title"] == "Demo Bench"
