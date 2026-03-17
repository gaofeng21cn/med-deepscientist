from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from ..shared import read_json, run_command
from .service import branch_exists, current_branch, head_commit


def list_branch_canvas(repo: Path, *, quest_id: str) -> dict[str, Any]:
    refs = _list_refs(repo)
    if not refs:
        default_ref = current_branch(repo)
        return {
            "quest_id": quest_id,
            "default_ref": default_ref,
            "current_ref": default_ref,
            "head": head_commit(repo),
            "nodes": [],
            "edges": [],
            "views": {
                "ideas": [],
                "analysis": [],
            },
        }

    default_ref = _default_ref(refs, quest_id=quest_id)
    branch_state = _collect_branch_state(repo)

    classifications: dict[str, dict[str, str]] = {}
    for ref in refs:
        classifications[ref["ref"]] = _classify_ref(ref["ref"], branch_state.get(ref["ref"], {}))

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    for ref_item in refs:
        ref_name = ref_item["ref"]
        state = branch_state.get(ref_name, {})
        classification = classifications[ref_name]
        parent_ref = _infer_parent_ref(
            ref_name,
            repo=repo,
            state=state,
            default_ref=default_ref,
            quest_id=quest_id,
            refs={item["ref"] for item in refs},
            classifications=classifications,
        )
        compare_base = parent_ref or default_ref
        ahead, behind = _ahead_behind(repo, compare_base, ref_name)
        node = {
            "ref": ref_name,
            "label": ref_name,
            "branch_kind": classification["branch_kind"],
            "tier": classification["tier"],
            "mode": classification["mode"],
            "parent_ref": parent_ref,
            "compare_base": compare_base,
            "current": ref_name == current_branch(repo),
            "head": ref_item["head"],
            "updated_at": ref_item["updated_at"],
            "subject": ref_item["subject"],
            "commit_count": _commit_count(repo, ref_name),
            "ahead": ahead,
            "behind": behind,
            "run_id": state.get("run_id"),
            "run_kind": state.get("run_kind"),
            "idea_id": state.get("idea_id"),
            "parent_branch_recorded": state.get("parent_branch"),
            "worktree_root": state.get("worktree_root"),
            "latest_metric": state.get("latest_metric"),
            "latest_summary": state.get("latest_summary"),
            "latest_result": state.get("latest_result"),
            "breakthrough": state.get("breakthrough", False),
            "breakthrough_level": state.get("breakthrough_level"),
            "recent_artifacts": state.get("recent_artifacts", []),
        }
        nodes.append(node)
        if parent_ref:
            edges.append(
                {
                    "from": parent_ref,
                    "to": ref_name,
                    "relation": "branch",
                    "tier": classification["tier"],
                    "mode": classification["mode"],
                }
            )

    return {
        "quest_id": quest_id,
        "default_ref": default_ref,
        "current_ref": current_branch(repo),
        "head": head_commit(repo),
        "nodes": nodes,
        "edges": edges,
        "views": {
            "ideas": [item["ref"] for item in nodes if item["tier"] == "major" or item["ref"] == default_ref],
            "analysis": [
                item["ref"]
                for item in nodes
                if item["ref"] == default_ref or item["tier"] == "major" or item["branch_kind"] == "analysis"
            ],
        },
    }


def compare_refs(repo: Path, *, base: str, head: str) -> dict[str, Any]:
    _require_ref(repo, base)
    _require_ref(repo, head)
    merge_base = _git_stdout(repo, ["merge-base", base, head]).strip() or None
    ahead, behind = _ahead_behind(repo, base, head)
    commits = _compare_commits(repo, base=base, head=head)
    files = _compare_files(repo, base=base, head=head)
    return {
        "ok": True,
        "base": base,
        "head": head,
        "merge_base": merge_base,
        "ahead": ahead,
        "behind": behind,
        "commit_count": len(commits),
        "file_count": len(files),
        "commits": commits,
        "files": files,
    }


def diff_file_between_refs(repo: Path, *, base: str, head: str, path: str) -> dict[str, Any]:
    _require_ref(repo, base)
    _require_ref(repo, head)
    safe_path = path.strip().lstrip("/")
    if not safe_path:
        return {
            "ok": False,
            "message": "Path is required.",
            "base": base,
            "head": head,
            "path": path,
            "lines": [],
        }

    compare = compare_refs(repo, base=base, head=head)
    file_meta = next((item for item in compare["files"] if item["path"] == safe_path), None)
    patch = _git_stdout(repo, ["diff", "--find-renames", "--unified=3", "--no-color", f"{base}...{head}", "--", safe_path])
    lines = _normalize_patch_lines(patch)
    return {
        "ok": True,
        "base": base,
        "head": head,
        "path": safe_path,
        "status": file_meta.get("status") if file_meta else "modified",
        "old_path": file_meta.get("old_path") if file_meta else None,
        "added": file_meta.get("added", 0) if file_meta else 0,
        "removed": file_meta.get("removed", 0) if file_meta else 0,
        "binary": file_meta.get("binary", False) if file_meta else False,
        "lines": lines,
        "truncated": False,
    }


def log_ref_history(repo: Path, *, ref: str, base: str | None = None, limit: int = 30) -> dict[str, Any]:
    _require_ref(repo, ref)
    normalized_base = (base or "").strip() or None
    if normalized_base and normalized_base != ref:
        _require_ref(repo, normalized_base)
    revspec = ref if not normalized_base or normalized_base == ref else f"{normalized_base}..{ref}"
    commits = _git_log(repo, revspec=revspec, limit=limit)
    return {
        "ok": True,
        "ref": ref,
        "base": normalized_base,
        "limit": limit,
        "commits": commits,
    }


def commit_detail(repo: Path, *, sha: str) -> dict[str, Any]:
    _require_ref(repo, sha)
    payload = _git_stdout(
        repo,
        [
            "show",
            "--quiet",
            "--date=iso-strict",
            "--pretty=format:%H%x1f%h%x1f%P%x1f%ad%x1f%an%x1f%ae%x1f%s%x1f%b",
            sha,
        ],
    ).strip()
    full_sha, short_sha, parents_raw, authored_at, author_name, author_email, subject, body = (
        payload.split("\x1f") + ["", "", "", "", "", "", "", ""]
    )[:8]
    files = _commit_files(repo, sha=sha)
    return {
        "ok": True,
        "sha": full_sha.strip(),
        "short_sha": short_sha.strip(),
        "parents": [item for item in parents_raw.strip().split() if item],
        "authored_at": authored_at.strip(),
        "author_name": author_name.strip(),
        "author_email": author_email.strip(),
        "subject": subject.strip(),
        "body": body.strip(),
        "file_count": len(files),
        "files": files,
        "stats": {
            "added": sum(int(item.get("added") or 0) for item in files),
            "removed": sum(int(item.get("removed") or 0) for item in files),
        },
    }


def diff_file_for_commit(repo: Path, *, sha: str, path: str) -> dict[str, Any]:
    _require_ref(repo, sha)
    safe_path = path.strip().lstrip("/")
    if not safe_path:
        return {
            "ok": False,
            "message": "Path is required.",
            "sha": sha,
            "path": path,
            "lines": [],
        }
    detail = commit_detail(repo, sha=sha)
    file_meta = next((item for item in detail["files"] if item["path"] == safe_path), None)
    patch = _git_stdout(repo, ["show", "--find-renames", "--unified=3", "--no-color", sha, "--", safe_path])
    lines = _normalize_patch_lines(patch)
    return {
        "ok": True,
        "sha": sha,
        "path": safe_path,
        "status": file_meta.get("status") if file_meta else "modified",
        "old_path": file_meta.get("old_path") if file_meta else None,
        "added": file_meta.get("added", 0) if file_meta else 0,
        "removed": file_meta.get("removed", 0) if file_meta else 0,
        "binary": file_meta.get("binary", False) if file_meta else False,
        "lines": lines,
        "truncated": False,
    }


def _list_refs(repo: Path) -> list[dict[str, Any]]:
    result = _git_stdout(
        repo,
        [
            "for-each-ref",
            "--sort=-committerdate",
            "--format=%(refname:short)%09%(objectname)%09%(committerdate:iso-strict)%09%(subject)",
            "refs/heads",
        ],
    )
    refs: list[dict[str, Any]] = []
    for line in result.splitlines():
        if not line.strip():
            continue
        ref, sha, updated_at, subject = (line.split("\t") + ["", "", "", ""])[:4]
        refs.append(
            {
                "ref": ref.strip(),
                "head": sha.strip(),
                "updated_at": updated_at.strip(),
                "subject": subject.strip(),
            }
        )
    return refs


def _collect_branch_state(repo: Path) -> dict[str, dict[str, Any]]:
    branch_state: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "recent_artifacts": [],
        }
    )
    artifact_paths: list[Path] = []
    artifact_roots = [repo / "artifacts"]
    worktrees_root = repo / ".ds" / "worktrees"
    if worktrees_root.exists():
        artifact_roots.extend(path / "artifacts" for path in sorted(worktrees_root.iterdir()) if path.is_dir())
    seen_paths: set[str] = set()
    for artifacts_root in artifact_roots:
        if not artifacts_root.exists():
            continue
        for path in sorted(artifacts_root.glob("*/*.json")):
            if not path.is_file():
                continue
            key = str(path.resolve())
            if key in seen_paths:
                continue
            seen_paths.add(key)
            artifact_paths.append(path)
    for path in artifact_paths:
        record = read_json(path, {})
        if not isinstance(record, dict) or not record:
            continue
        branch_name = str(record.get("branch") or "").strip()
        if not branch_name:
            continue
        state = branch_state[branch_name]
        state.setdefault("branch", branch_name)
        state["updated_at"] = record.get("updated_at") or state.get("updated_at")
        if record.get("kind") == "run":
            state["run_id"] = record.get("run_id") or state.get("run_id")
            state["run_kind"] = record.get("run_kind") or state.get("run_kind")
        if record.get("idea_id"):
            state["idea_id"] = record.get("idea_id")
        if record.get("parent_branch"):
            state["parent_branch"] = record.get("parent_branch")
        if record.get("worktree_root"):
            state["worktree_root"] = record.get("worktree_root")
        if isinstance(record.get("metrics_summary"), dict) and record["metrics_summary"]:
            key = next(iter(record["metrics_summary"]))
            state["latest_metric"] = {
                "key": ((record.get("progress_eval") or {}).get("primary_metric_id")) or key,
                "value": record["metrics_summary"].get(
                    ((record.get("progress_eval") or {}).get("primary_metric_id")) or key,
                    record["metrics_summary"].get(key),
                ),
                "delta_vs_baseline": ((record.get("progress_eval") or {}).get("delta_vs_baseline")),
            }
        if record.get("kind") == "run":
            state["latest_result"] = {
                "run_id": record.get("run_id"),
                "run_kind": record.get("run_kind"),
                "status": record.get("status"),
                "summary": record.get("summary") or record.get("reason"),
                "verdict": record.get("verdict"),
                "paths": record.get("paths") or {},
                "details": record.get("details") or {},
                "metrics_summary": record.get("metrics_summary") or {},
                "metric_rows": record.get("metric_rows") or [],
                "metric_contract": record.get("metric_contract") or {},
                "baseline_ref": record.get("baseline_ref") or {},
                "baseline_comparisons": record.get("baseline_comparisons") or {},
                "progress_eval": record.get("progress_eval") or {},
                "evaluation_summary": record.get("evaluation_summary")
                or ((record.get("details") or {}) if isinstance(record.get("details"), dict) else {}).get("evaluation_summary")
                or {},
                "files_changed": record.get("files_changed") or [],
                "evidence_paths": record.get("evidence_paths") or [],
                "updated_at": record.get("updated_at"),
            }
            state["breakthrough"] = bool(((record.get("progress_eval") or {}).get("breakthrough")))
            state["breakthrough_level"] = ((record.get("progress_eval") or {}).get("breakthrough_level"))
        if record.get("summary") or record.get("message") or record.get("reason"):
            state["latest_summary"] = record.get("summary") or record.get("message") or record.get("reason")
        state["recent_artifacts"].append(
            {
                "artifact_id": record.get("artifact_id"),
                "kind": record.get("kind"),
                "summary": record.get("summary") or record.get("message"),
                "reason": record.get("reason"),
                "updated_at": record.get("updated_at"),
                "status": record.get("status"),
            }
        )
        state["recent_artifacts"] = state["recent_artifacts"][-4:]
    return branch_state


def _classify_ref(ref: str, state: dict[str, Any]) -> dict[str, str]:
    run_id = str(state.get("run_id") or "")
    run_kind = str(state.get("run_kind") or "")
    if ref in {"main", "master"} or ref.startswith("quest/"):
        return {"branch_kind": "quest", "tier": "major", "mode": "ideas"}
    if ref.startswith("idea/"):
        return {"branch_kind": "idea", "tier": "major", "mode": "ideas"}
    if ref.startswith("analysis/") or run_id.startswith("analysis") or run_kind == "analysis-campaign":
        return {"branch_kind": "analysis", "tier": "minor", "mode": "analysis"}
    return {"branch_kind": "implementation", "tier": "major", "mode": "ideas"}


def _infer_parent_ref(
    ref: str,
    *,
    repo: Path,
    state: dict[str, Any],
    default_ref: str,
    quest_id: str,
    refs: set[str],
    classifications: dict[str, dict[str, str]],
) -> str | None:
    if ref == default_ref:
        return None
    parent_branch = str(state.get("parent_branch") or "").strip()
    if parent_branch and parent_branch in refs and parent_branch != ref:
        return parent_branch
    if ref.startswith("idea/"):
        return default_ref
    if state.get("idea_id"):
        candidate = f"idea/{quest_id}-{state['idea_id']}"
        if candidate in refs:
            return candidate
    if classifications[ref]["branch_kind"] == "analysis":
        major_refs = [
            candidate
            for candidate, meta in classifications.items()
            if candidate != ref and meta["tier"] == "major" and candidate in refs
        ]
        best_parent = _best_merge_base_parent(ref, candidates=major_refs, repo=repo)
        if best_parent:
            return best_parent
    return default_ref


def _best_merge_base_parent(ref: str, *, candidates: list[str], repo: Path) -> str | None:
    best_parent = None
    best_score = None
    for candidate in candidates:
        if not branch_exists(repo, candidate):
            continue
        base = _git_stdout(repo, ["merge-base", candidate, ref]).strip()
        if not base:
            continue
        score = _git_stdout(repo, ["rev-list", "--count", f"{base}..{ref}"]).strip() or "0"
        try:
            numeric_score = int(score)
        except ValueError:
            numeric_score = 0
        if best_score is None or numeric_score < best_score:
            best_score = numeric_score
            best_parent = candidate
    return best_parent


def _default_ref(refs: list[dict[str, Any]], *, quest_id: str) -> str:
    ref_names = {item["ref"] for item in refs}
    quest_ref = f"quest/{quest_id}"
    if quest_ref in ref_names:
        return quest_ref
    if "main" in ref_names:
        return "main"
    return refs[0]["ref"]


def _compare_commits(repo: Path, *, base: str, head: str) -> list[dict[str, Any]]:
    return _git_log(repo, revspec=f"{base}..{head}")


def _compare_files(repo: Path, *, base: str, head: str) -> list[dict[str, Any]]:
    status_lines = _git_stdout(repo, ["diff", "--find-renames", "--name-status", f"{base}...{head}"]).splitlines()
    numstat_lines = _git_stdout(repo, ["diff", "--find-renames", "--numstat", f"{base}...{head}"]).splitlines()
    return _files_from_status_numstat(status_lines, numstat_lines)


def _commit_files(repo: Path, *, sha: str) -> list[dict[str, Any]]:
    status_lines = _git_stdout(repo, ["show", "--find-renames", "--name-status", "--format=", sha]).splitlines()
    numstat_lines = _git_stdout(repo, ["show", "--find-renames", "--numstat", "--format=", sha]).splitlines()
    return _files_from_status_numstat(status_lines, numstat_lines)


def _files_from_status_numstat(status_lines: list[str], numstat_lines: list[str]) -> list[dict[str, Any]]:
    
    by_path: dict[str, dict[str, Any]] = {}
    order: list[str] = []

    for line in status_lines:
        if not line.strip():
            continue
        parts = line.split("\t")
        code = parts[0]
        status = _status_label(code)
        if code.startswith("R") and len(parts) >= 3:
            old_path, new_path = parts[1], parts[2]
            path = new_path
            by_path[path] = {
                "path": path,
                "old_path": old_path,
                "status": status,
            }
        elif len(parts) >= 2:
            path = parts[1]
            by_path[path] = {
                "path": path,
                "status": status,
            }
        else:
            continue
        order.append(path)

    for line in numstat_lines:
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        added_raw, removed_raw = parts[0], parts[1]
        path = parts[-1]
        item = by_path.setdefault(path, {"path": path, "status": "modified"})
        item["binary"] = added_raw == "-" or removed_raw == "-"
        item["added"] = 0 if item["binary"] else int(added_raw or "0")
        item["removed"] = 0 if item["binary"] else int(removed_raw or "0")

    return [by_path[path] for path in order if path in by_path]


def _git_log(repo: Path, *, revspec: str, limit: int = 30) -> list[dict[str, Any]]:
    result = _git_stdout(
        repo,
        [
            "log",
            "--date=iso-strict",
            f"-n{limit}",
            "--pretty=format:%H%x1f%h%x1f%ad%x1f%an%x1f%s",
            revspec,
        ],
    )
    commits: list[dict[str, Any]] = []
    for line in result.splitlines():
        if not line.strip():
            continue
        sha, short_sha, authored_at, author_name, subject = (line.split("\x1f") + ["", "", "", "", ""])[:5]
        commits.append(
            {
                "sha": sha.strip(),
                "short_sha": short_sha.strip(),
                "authored_at": authored_at.strip(),
                "author_name": author_name.strip(),
                "subject": subject.strip(),
            }
        )
    return commits


def _normalize_patch_lines(patch: str) -> list[str]:
    lines = [line.rstrip("\n") for line in patch.splitlines()]
    if not lines:
        return []
    first_hunk = next((index for index, line in enumerate(lines) if line.startswith("@@")), None)
    if first_hunk is None:
        return lines
    prefix = [line for line in lines[:first_hunk] if line.startswith("---") or line.startswith("+++")]
    return prefix + lines[first_hunk:]


def _status_label(code: str) -> str:
    if code.startswith("A"):
        return "added"
    if code.startswith("D"):
        return "deleted"
    if code.startswith("R"):
        return "renamed"
    if code.startswith("C"):
        return "copied"
    return "modified"


def _ahead_behind(repo: Path, base: str, head: str) -> tuple[int, int]:
    if not base or not head:
        return 0, 0
    result = _git_stdout(repo, ["rev-list", "--left-right", "--count", f"{base}...{head}"]).strip()
    if not result:
        return 0, 0
    left, right = (result.split() + ["0", "0"])[:2]
    try:
        behind = int(left)
    except ValueError:
        behind = 0
    try:
        ahead = int(right)
    except ValueError:
        ahead = 0
    return ahead, behind


def _commit_count(repo: Path, ref: str) -> int:
    result = _git_stdout(repo, ["rev-list", "--count", ref]).strip()
    try:
        return int(result)
    except ValueError:
        return 0


def _require_ref(repo: Path, ref: str) -> None:
    if not branch_exists(repo, ref):
        result = run_command(["git", "rev-parse", "--verify", ref], cwd=repo, check=False)
        if result.returncode != 0:
            raise ValueError(f"Unknown git ref: {ref}")


def _git_stdout(repo: Path, args: list[str]) -> str:
    result = run_command(["git", *args], cwd=repo, check=False)
    return result.stdout
