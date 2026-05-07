from __future__ import annotations

import importlib.util
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "audit_repo_hygiene.py"
POLICY_PATH = REPO_ROOT / "scripts" / "repo_hygiene_policy.json"


def _load_audit_module():
    spec = importlib.util.spec_from_file_location("audit_repo_hygiene", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_repo_hygiene_audit_passes_current_tracked_tree() -> None:
    module = _load_audit_module()

    assert module.run_audit() == []


def test_hygiene_policy_blocks_retired_local_state_and_baseline_file() -> None:
    module = _load_audit_module()
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))

    failures = module.audit_tracked_paths(
        [
            ".agent-contract-baseline.json",
            ".codex/config.toml",
            "pkg/build/output.js",
            "pkg/out/output.js",
            "pkg/__pycache__/module.pyc",
            "pkg/runtime-state/state.json",
            "pkg/.runtime-program/current.json",
            "pkg/example.egg-info/PKG-INFO",
            "src/ui/dist/index.html",
            "src/tui/dist/index.js",
            "src/ui/vendor/novel-headless/dist/index.js",
        ],
        policy,
    )

    assert failures == [
        "forbidden tracked path: .agent-contract-baseline.json",
        "forbidden tracked path: .codex/config.toml",
        "forbidden tracked path: pkg/build/output.js",
        "forbidden tracked path: pkg/out/output.js",
        "forbidden tracked path: pkg/__pycache__/module.pyc",
        "forbidden tracked path: pkg/runtime-state/state.json",
        "forbidden tracked path: pkg/.runtime-program/current.json",
        "forbidden tracked path: pkg/example.egg-info/PKG-INFO",
    ]


def test_line_budget_policy_records_current_legacy_ceiling() -> None:
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    baseline = policy["line_budget"]["legacy_baseline"]

    assert policy["line_budget"]["max_lines"] == 1000
    assert baseline["src/deepscientist/artifact/service.py"] == 14481
    assert baseline["tests/test_memory_and_artifact.py"] == 12807
    assert "src/ui/dist/index.html" not in baseline
