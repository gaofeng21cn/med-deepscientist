from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = REPO_ROOT / "scripts" / "repo_hygiene_policy.json"


def _load_policy() -> dict:
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


def _tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    )
    return [line for line in result.stdout.splitlines() if line and (REPO_ROOT / line).exists()]


def _path_parts(path: str) -> set[str]:
    return set(Path(path).parts)


def _matches_forbidden_path(path: str, policy: dict) -> bool:
    parts = _path_parts(path)
    for fragment in policy["tracked_path_hygiene"]["forbidden_path_fragments"]:
        if fragment in parts:
            return True
    for part in parts:
        if any(part.endswith(suffix) for suffix in policy["tracked_path_hygiene"]["forbidden_suffixes"]):
            return True
    return False


def _allowed_dist_prefixes(policy: dict) -> tuple[str, ...]:
    return tuple(item["path"] for item in policy["tracked_path_hygiene"]["allowed_tracked_dist_prefixes"])


def _line_budget_candidate(path: str, policy: dict) -> bool:
    budget = policy["line_budget"]
    if not any(path.startswith(prefix) for prefix in budget["roots"]):
        return False
    if any(path.startswith(prefix) for prefix in budget["exclude_prefixes"]):
        return False
    return Path(path).suffix in set(budget["extensions"])


def _line_count(path: str) -> int:
    with (REPO_ROOT / path).open("rb") as handle:
        return sum(1 for _ in handle)


def audit_tracked_paths(tracked: list[str], policy: dict) -> list[str]:
    allowed_dist_prefixes = _allowed_dist_prefixes(policy)
    failures: list[str] = []
    for path in tracked:
        if _matches_forbidden_path(path, policy):
            failures.append(f"forbidden tracked path: {path}")
        if "/dist/" in f"/{path}/" and not path.startswith(allowed_dist_prefixes):
            failures.append(f"tracked dist path outside allowlist: {path}")
    return failures


def audit_line_budget(tracked: list[str], policy: dict) -> list[str]:
    budget = policy["line_budget"]
    max_lines = int(budget["max_lines"])
    baseline = {str(path): int(limit) for path, limit in budget["legacy_baseline"].items()}
    failures: list[str] = []
    seen_baseline: set[str] = set()

    for path in tracked:
        if not _line_budget_candidate(path, policy):
            continue
        lines = _line_count(path)
        if path in baseline:
            seen_baseline.add(path)
            if lines > baseline[path]:
                failures.append(f"legacy file grew beyond baseline: {path} ({lines} > {baseline[path]})")
            continue
        if lines > max_lines:
            failures.append(f"new over-budget source/test file: {path} ({lines} > {max_lines})")

    for stale_path in sorted(set(baseline) - seen_baseline):
        failures.append(f"stale line-budget baseline entry: {stale_path}")

    return failures


def run_audit() -> list[str]:
    policy = _load_policy()
    tracked = _tracked_files()
    return audit_tracked_paths(tracked, policy) + audit_line_budget(tracked, policy)


def main() -> int:
    failures = run_audit()
    if failures:
        print("Repo hygiene audit failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    print("Repo hygiene audit passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
