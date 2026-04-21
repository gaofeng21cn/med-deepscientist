from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from deepscientist.config import ConfigManager
from deepscientist.gitops import create_worktree, init_repo
from deepscientist.home import ensure_home_layout
from deepscientist.migration import (
    looks_like_deepscientist_root,
    migrate_deepscientist_root,
    repair_deepscientist_root_paths,
)
from deepscientist.shared import read_json, read_yaml, write_json, write_yaml


def test_migrate_deepscientist_root_copies_full_tree_and_verifies(temp_home: Path) -> None:
    source = temp_home
    ensure_home_layout(source)
    (source / "config" / "config.yaml").write_text("ui:\n  host: 0.0.0.0\n", encoding="utf-8")
    (source / "quests" / "001").mkdir(parents=True, exist_ok=True)
    (source / "quests" / "001" / "brief.md").write_text("# quest\n", encoding="utf-8")
    (source / "cli" / "bin").mkdir(parents=True, exist_ok=True)
    (source / "cli" / "bin" / "ds.js").write_text("#!/usr/bin/env node\n", encoding="utf-8")

    target = source.parent / "DeepScientistMigrated"
    payload = migrate_deepscientist_root(source, target)

    assert payload["ok"] is True
    assert payload["source"] == str(source.resolve())
    assert payload["target"] == str(target.resolve())
    assert (target / "config" / "config.yaml").exists()
    assert (target / "quests" / "001" / "brief.md").read_text(encoding="utf-8") == "# quest\n"
    assert (target / "cli" / "bin" / "ds.js").exists()
    assert read_yaml(target / "config" / "config.yaml", {}).get("home") == str(target.resolve())
    assert source.exists()


def test_migrate_deepscientist_root_rejects_nested_target(temp_home: Path) -> None:
    source = temp_home
    ensure_home_layout(source)
    nested_target = source / "migrated"

    with pytest.raises(ValueError, match="inside the current DeepScientist root"):
        migrate_deepscientist_root(source, nested_target)


def test_looks_like_deepscientist_root_accepts_install_only_layout(tmp_path: Path) -> None:
    source = tmp_path / "install-root"
    (source / "cli" / "bin").mkdir(parents=True, exist_ok=True)
    (source / "cli" / "bin" / "ds.js").write_text("#!/usr/bin/env node\n", encoding="utf-8")

    assert looks_like_deepscientist_root(source) is True


def test_create_worktree_uses_relative_gitdir_links(tmp_path: Path) -> None:
    repo = tmp_path / "quest-repo"
    repo.mkdir(parents=True, exist_ok=True)
    init_repo(repo)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.com"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test User"], check=True)
    (repo / "brief.md").write_text("# quest\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "brief.md"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-m", "init"], check=True, capture_output=True, text=True)

    worktree_root = repo / ".ds" / "worktrees" / "paper-main"
    created = create_worktree(repo, branch="paper/main", worktree_root=worktree_root)

    assert created["ok"] is True
    assert subprocess.run(
        ["git", "-C", str(repo), "config", "--get", "worktree.useRelativePaths"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip() == "true"
    gitdir_line = (worktree_root / ".git").read_text(encoding="utf-8").strip()
    assert gitdir_line.startswith("gitdir: ")
    assert not Path(gitdir_line.removeprefix("gitdir: ").strip()).is_absolute()
    assert str(repo.resolve()) not in gitdir_line


def test_repair_deepscientist_root_paths_rewrites_moved_workspace_paths_and_repairs_git_worktrees(
    tmp_path: Path,
) -> None:
    source_workspace = tmp_path / "LinMZ" / "as_biologics_workspace"
    source_home = source_workspace / "ops" / "med-deepscientist" / "runtime"
    ensure_home_layout(source_home)
    ConfigManager(source_home).ensure_files()

    source_study_root = source_workspace / "studies" / "001-risk"
    (source_study_root / "artifacts" / "controller").mkdir(parents=True, exist_ok=True)
    (source_study_root / "artifacts" / "controller" / "study_charter.json").write_text("{}", encoding="utf-8")

    quest_root = source_home / "quests" / "001-risk"
    quest_root.mkdir(parents=True, exist_ok=True)
    init_repo(quest_root)
    subprocess.run(["git", "-C", str(quest_root), "config", "user.email", "test@example.com"], check=True)
    subprocess.run(["git", "-C", str(quest_root), "config", "user.name", "Test User"], check=True)
    (quest_root / "brief.md").write_text("# quest\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(quest_root), "add", "brief.md"], check=True)
    subprocess.run(["git", "-C", str(quest_root), "commit", "-m", "init"], check=True, capture_output=True, text=True)

    source_worktree_root = quest_root / ".ds" / "worktrees" / "run-main"
    subprocess.run(
        [
            "git",
            "-C",
            str(quest_root),
            "-c",
            "worktree.useRelativePaths=false",
            "worktree",
            "add",
            "-b",
            "run-main",
            str(source_worktree_root),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    (source_worktree_root / "memory" / "ideas" / "idea-001").mkdir(parents=True, exist_ok=True)
    (source_worktree_root / "memory" / "ideas" / "idea-001" / "idea.md").write_text("# idea\n", encoding="utf-8")

    write_json(
        source_home / "runtime" / "daemon.json",
        {
            "pid": 99999,
            "home": str(source_home.resolve()),
            "log_path": str((source_home / "logs" / "daemon.log").resolve()),
            "url": "http://127.0.0.1:20999",
        },
    )
    write_yaml(
        quest_root / "quest.yaml",
        {
            "quest_id": "001-risk",
            "quest_root": str(quest_root.resolve()),
            "study_root": str(source_study_root.resolve()),
            "artifact_path": str((source_study_root / "artifacts" / "controller" / "study_charter.json").resolve()),
            "startup_contract": {
                "study_root": str(source_study_root.resolve()),
                "summary_markdown": f"Study root: {source_study_root.resolve()}",
            },
        },
    )
    write_json(
        quest_root / ".ds" / "research_state.json",
        {
            "version": 1,
            "research_head_branch": "run-main",
            "research_head_worktree_root": str(source_worktree_root.resolve()),
            "current_workspace_root": str(source_worktree_root.resolve()),
            "active_idea_md_path": str((source_worktree_root / "memory" / "ideas" / "idea-001" / "idea.md").resolve()),
            "paper_parent_worktree_root": str(source_worktree_root.resolve()),
            "workspace_mode": "paper",
        },
    )
    write_json(
        quest_root / "paper" / "medical_analysis_contract.json",
        {
            "study_root": str(source_study_root.resolve()),
            "source_ref": str((source_study_root / "artifacts" / "controller" / "study_charter.json").resolve()),
        },
    )
    artifact_index = quest_root / "artifacts" / "_index.jsonl"
    artifact_index.parent.mkdir(parents=True, exist_ok=True)
    artifact_index.write_text(
        json.dumps(
            {
                "artifact_id": "report-001",
                "path": str((quest_root / "artifacts" / "reports" / "report-001.json").resolve()),
                "summary": f"Study root: {source_study_root.resolve()}",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    target_workspace = tmp_path / "LinZM" / "as_biologics_workspace"
    shutil.copytree(source_workspace, target_workspace)
    shutil.rmtree(source_workspace)
    target_home = target_workspace / "ops" / "med-deepscientist" / "runtime"
    target_quest_root = target_home / "quests" / "001-risk"
    target_worktree_root = target_quest_root / ".ds" / "worktrees" / "run-main"
    target_study_root = target_workspace / "studies" / "001-risk"

    before = subprocess.run(
        ["git", "-C", str(target_worktree_root), "status", "--short"],
        capture_output=True,
        text=True,
    )
    assert before.returncode != 0
    assert Path((target_worktree_root / ".git").read_text(encoding="utf-8").strip().removeprefix("gitdir: ").strip()).is_absolute()

    repaired = repair_deepscientist_root_paths(target_home, source_home=source_home)

    assert repaired["ok"] is True
    assert repaired["source_home"] == str(source_home.resolve())
    assert repaired["target_home"] == str(target_home.resolve())
    assert repaired["rewritten_files"]
    assert repaired["git_repair_results"]
    assert read_yaml(target_home / "config" / "config.yaml", {}).get("home") == str(target_home.resolve())

    daemon_payload = read_json(target_home / "runtime" / "daemon.json", {})
    assert daemon_payload["home"] == str(target_home.resolve())
    assert daemon_payload["log_path"] == str((target_home / "logs" / "daemon.log").resolve())

    quest_payload = read_yaml(target_quest_root / "quest.yaml", {})
    assert quest_payload["quest_root"] == str(target_quest_root.resolve())
    assert quest_payload["study_root"] == str(target_study_root.resolve())
    assert quest_payload["artifact_path"] == str((target_study_root / "artifacts" / "controller" / "study_charter.json").resolve())
    assert quest_payload["startup_contract"]["study_root"] == str(target_study_root.resolve())
    assert "LinMZ" not in quest_payload["startup_contract"]["summary_markdown"]

    research_state = read_json(target_quest_root / ".ds" / "research_state.json", {})
    assert research_state["research_head_worktree_root"] == str(target_worktree_root.resolve())
    assert research_state["current_workspace_root"] == str(target_worktree_root.resolve())
    assert research_state["active_idea_md_path"] == str(
        (target_worktree_root / "memory" / "ideas" / "idea-001" / "idea.md").resolve()
    )

    medical_analysis_contract = read_json(target_quest_root / "paper" / "medical_analysis_contract.json", {})
    assert medical_analysis_contract["study_root"] == str(target_study_root.resolve())
    assert medical_analysis_contract["source_ref"] == str(
        (target_study_root / "artifacts" / "controller" / "study_charter.json").resolve()
    )

    artifact_index_lines = (target_quest_root / "artifacts" / "_index.jsonl").read_text(encoding="utf-8").splitlines()
    artifact_index_payload = json.loads(artifact_index_lines[0])
    assert artifact_index_payload["path"] == str((target_quest_root / "artifacts" / "reports" / "report-001.json").resolve())
    assert artifact_index_payload["summary"] == f"Study root: {target_study_root.resolve()}"

    gitdir_line = (target_worktree_root / ".git").read_text(encoding="utf-8").strip()
    assert gitdir_line.startswith("gitdir: ")
    assert not Path(gitdir_line.removeprefix("gitdir: ").strip()).is_absolute()
    assert subprocess.run(
        ["git", "-C", str(target_quest_root), "config", "--get", "worktree.useRelativePaths"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip() == "true"

    after = subprocess.run(
        ["git", "-C", str(target_worktree_root), "status", "--short"],
        capture_output=True,
        text=True,
    )
    assert after.returncode == 0
