from __future__ import annotations

import os
import shutil
import uuid
from pathlib import Path
from typing import Any

from .shared import read_json, read_yaml, run_command, write_json, write_yaml


HOME_SIGNATURES = (
    "runtime",
    "config",
    "memory",
    "quests",
    "plugins",
    "logs",
    "cache",
    "cli",
)


def looks_like_deepscientist_root(path: Path) -> bool:
    if not path.exists() or not path.is_dir():
        return False
    if (path / "cli" / "bin" / "ds.js").exists():
        return True
    return any((path / name).exists() for name in HOME_SIGNATURES)


def _is_relative_to(candidate: Path, other: Path) -> bool:
    try:
        candidate.relative_to(other)
        return True
    except ValueError:
        return False


def _collect_manifest(root: Path) -> dict[str, Any]:
    manifest: dict[str, Any] = {}
    file_count = 0
    dir_count = 0
    symlink_count = 0
    total_bytes = 0
    stack = [Path("")]
    while stack:
        rel_root = stack.pop()
        current_root = root / rel_root
        for child in sorted(current_root.iterdir(), key=lambda item: item.name):
            rel_path = (rel_root / child.name).as_posix()
            if child.is_symlink():
                manifest[rel_path] = {"kind": "symlink", "target": os.readlink(child)}
                symlink_count += 1
                continue
            if child.is_dir():
                manifest[rel_path] = {"kind": "dir"}
                dir_count += 1
                stack.append(rel_root / child.name)
                continue
            size = child.stat().st_size
            manifest[rel_path] = {"kind": "file", "size": size}
            file_count += 1
            total_bytes += size
    return {
        "entries": manifest,
        "stats": {
            "file_count": file_count,
            "dir_count": dir_count,
            "symlink_count": symlink_count,
            "total_bytes": total_bytes,
            "entry_count": len(manifest),
        },
    }


def _ancestor_rewrite_pairs(source: Path, target: Path) -> list[tuple[str, str]]:
    source_chain: list[Path] = []
    current = source
    while True:
        source_chain.append(current)
        parent = current.parent
        if parent == current:
            break
        current = parent

    target_chain: list[Path] = []
    current = target
    while True:
        target_chain.append(current)
        parent = current.parent
        if parent == current:
            break
        current = parent

    pairs: list[tuple[str, str]] = []
    for old_root, new_root in zip(source_chain, target_chain, strict=False):
        old_value = str(old_root)
        new_value = str(new_root)
        if old_value == new_value:
            continue
        pairs.append((old_value, new_value))
    return sorted(pairs, key=lambda item: len(item[0]), reverse=True)


def _rewrite_nested_strings(value: Any, rewrite_pairs: list[tuple[str, str]]) -> Any:
    if isinstance(value, str):
        rewritten = value
        for old_prefix, new_prefix in rewrite_pairs:
            rewritten = rewritten.replace(old_prefix, new_prefix)
        return rewritten
    if isinstance(value, list):
        return [_rewrite_nested_strings(item, rewrite_pairs) for item in value]
    if isinstance(value, dict):
        return {key: _rewrite_nested_strings(item, rewrite_pairs) for key, item in value.items()}
    return value


def _rewrite_yaml_file(
    path: Path,
    rewrite_pairs: list[tuple[str, str]],
    *,
    target_home: Path | None = None,
) -> bool:
    if not path.exists():
        return False
    payload = read_yaml(path, None)
    if payload is None:
        return False
    rewritten = _rewrite_nested_strings(payload, rewrite_pairs)
    if path.name == "config.yaml" and isinstance(rewritten, dict) and target_home is not None:
        rewritten = dict(rewritten)
        rewritten["home"] = str(target_home)
    if rewritten == payload:
        return False
    write_yaml(path, rewritten)
    return True


def _rewrite_json_file(
    path: Path,
    rewrite_pairs: list[tuple[str, str]],
    *,
    target_home: Path | None = None,
) -> bool:
    if not path.exists():
        return False
    payload = read_json(path, None)
    if payload is None:
        return False
    rewritten = _rewrite_nested_strings(payload, rewrite_pairs)
    if path.name == "daemon.json" and isinstance(rewritten, dict) and target_home is not None:
        rewritten = dict(rewritten)
        rewritten["home"] = str(target_home)
    if rewritten == payload:
        return False
    write_json(path, rewritten)
    return True


def _repair_git_worktree_links(quest_root: Path) -> dict[str, Any] | None:
    if not (quest_root / ".git").exists():
        return None
    config_result = run_command(
        ["git", "config", "worktree.useRelativePaths", "true"],
        cwd=quest_root,
        check=False,
    )
    worktrees_root = quest_root / ".ds" / "worktrees"
    repair_args = ["git", "worktree", "repair", "--relative-paths"]
    if worktrees_root.exists():
        repair_args.extend(str(path) for path in sorted(worktrees_root.iterdir()) if path.is_dir())
    repair_result = run_command(repair_args, cwd=quest_root, check=False)
    return {
        "quest_root": str(quest_root),
        "config_returncode": config_result.returncode,
        "repair_returncode": repair_result.returncode,
        "repair_stdout": repair_result.stdout,
        "repair_stderr": repair_result.stderr,
        "ok": config_result.returncode == 0 and repair_result.returncode == 0,
    }


def repair_deepscientist_root_paths(
    target_home: Path,
    *,
    source_home: Path | None = None,
) -> dict[str, Any]:
    resolved_target_home = target_home.expanduser().resolve()
    if not resolved_target_home.exists():
        raise ValueError(f"Target home does not exist: {resolved_target_home}")
    if not resolved_target_home.is_dir():
        raise ValueError(f"Target home is not a directory: {resolved_target_home}")

    inferred_source_home: Path | None = None
    if source_home is not None:
        inferred_source_home = source_home.expanduser().resolve()
    else:
        config_payload = read_yaml(resolved_target_home / "config" / "config.yaml", {})
        config_home = str((config_payload or {}).get("home") or "").strip() if isinstance(config_payload, dict) else ""
        if config_home:
            inferred_source_home = Path(config_home).expanduser().resolve(strict=False)
        if inferred_source_home is None or inferred_source_home == resolved_target_home:
            daemon_payload = read_json(resolved_target_home / "runtime" / "daemon.json", {})
            daemon_home = str((daemon_payload or {}).get("home") or "").strip() if isinstance(daemon_payload, dict) else ""
            if daemon_home:
                inferred_source_home = Path(daemon_home).expanduser().resolve(strict=False)

    if inferred_source_home is None or inferred_source_home == resolved_target_home:
        return {
            "ok": True,
            "repaired": False,
            "source_home": str(inferred_source_home) if inferred_source_home is not None else None,
            "target_home": str(resolved_target_home),
            "rewritten_files": [],
            "git_repair_results": [],
        }

    rewrite_pairs = _ancestor_rewrite_pairs(
        inferred_source_home.resolve(strict=False),
        resolved_target_home.resolve(strict=False),
    )
    rewritten_files: list[str] = []

    config_path = resolved_target_home / "config" / "config.yaml"
    if _rewrite_yaml_file(config_path, rewrite_pairs, target_home=resolved_target_home):
        rewritten_files.append(str(config_path))

    daemon_path = resolved_target_home / "runtime" / "daemon.json"
    if _rewrite_json_file(daemon_path, rewrite_pairs, target_home=resolved_target_home):
        rewritten_files.append(str(daemon_path))

    quests_root = resolved_target_home / "quests"
    for quest_root in sorted(path for path in quests_root.iterdir() if path.is_dir()) if quests_root.exists() else []:
        quest_yaml_path = quest_root / "quest.yaml"
        if _rewrite_yaml_file(quest_yaml_path, rewrite_pairs):
            rewritten_files.append(str(quest_yaml_path))
        research_state_path = quest_root / ".ds" / "research_state.json"
        if _rewrite_json_file(research_state_path, rewrite_pairs):
            rewritten_files.append(str(research_state_path))

    git_repair_results: list[dict[str, Any]] = []
    for quest_root in sorted(path for path in quests_root.iterdir() if path.is_dir()) if quests_root.exists() else []:
        result = _repair_git_worktree_links(quest_root)
        if result is not None:
            git_repair_results.append(result)

    return {
        "ok": True,
        "repaired": True,
        "source_home": str(inferred_source_home),
        "target_home": str(resolved_target_home),
        "rewrite_pairs": [{"old": old_prefix, "new": new_prefix} for old_prefix, new_prefix in rewrite_pairs],
        "rewritten_files": rewritten_files,
        "git_repair_results": git_repair_results,
    }


def migrate_deepscientist_root(source: Path, target: Path) -> dict[str, Any]:
    source = source.expanduser().resolve()
    target = target.expanduser().resolve()
    if not source.exists():
        raise ValueError(f"Source path does not exist: {source}")
    if not source.is_dir():
        raise ValueError(f"Source path is not a directory: {source}")
    if not looks_like_deepscientist_root(source):
        raise ValueError(f"Source path does not look like a DeepScientist home or install root: {source}")
    if source == target:
        raise ValueError("Source path and target path must be different.")
    if _is_relative_to(target, source):
        raise ValueError("Target path cannot be placed inside the current DeepScientist root.")
    if _is_relative_to(source, target):
        raise ValueError("Target path cannot be a parent of the current DeepScientist root.")
    if target.exists():
        raise ValueError(f"Target path already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)

    staging = target.parent / f".{target.name}.migrating-{uuid.uuid4().hex[:10]}"
    if staging.exists():
        shutil.rmtree(staging, ignore_errors=True)
    try:
        shutil.copytree(source, staging, symlinks=True, copy_function=shutil.copy2)
        source_manifest = _collect_manifest(source)
        staging_manifest = _collect_manifest(staging)
        if source_manifest["entries"] != staging_manifest["entries"]:
            raise ValueError("Copied tree validation failed: source and target contents do not match.")
        staging.rename(target)
        repair_payload = repair_deepscientist_root_paths(target, source_home=source)
        return {
            "ok": True,
            "source": str(source),
            "target": str(target),
            "staging": str(staging),
            "stats": source_manifest["stats"],
            "repair": repair_payload,
            "summary": "DeepScientist root copied and verified successfully.",
        }
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
