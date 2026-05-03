#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${repo_root}"

export PATH="${HOME}/.local/bin:/opt/homebrew/bin:/usr/local/bin:${PATH}"

command -v python3 >/dev/null 2>&1
command -v uv >/dev/null 2>&1
ds_bin="$(command -v ds)"

"${ds_bin}" --help >/dev/null

uv run python - <<'PY'
import json
from pathlib import Path

from deepscientist.home import repo_root as resolved_repo_root
from deepscientist.skills import discover_skill_bundles

repo_root = Path.cwd()
if resolved_repo_root().resolve() != repo_root.resolve():
    raise SystemExit(f"DeepScientist repo_root mismatch: {resolved_repo_root()} != {repo_root}")

required_paths = [
    repo_root / "src" / "skills" / "scout" / "SKILL.md",
    repo_root / "src" / "skills" / "baseline" / "SKILL.md",
    repo_root / "src" / "skills" / "experiment" / "SKILL.md",
    repo_root / "src" / "skills" / "write" / "SKILL.md",
    repo_root / "src" / "skills" / "review" / "SKILL.md",
    repo_root / "src" / "skills" / "figure-polish" / "SKILL.md",
]
missing = [str(path) for path in required_paths if not path.is_file()]
if missing:
    raise SystemExit(f"Missing DeepScientist skill files: {missing}")

discovered = {bundle.skill_id: bundle.role for bundle in discover_skill_bundles(repo_root)}
required_skills = {
    "scout": "stage",
    "baseline": "stage",
    "experiment": "stage",
    "write": "stage",
    "review": "companion",
    "figure-polish": "companion",
}
missing_skills = {
    skill_id: expected_role
    for skill_id, expected_role in required_skills.items()
    if discovered.get(skill_id) != expected_role
}
if missing_skills:
    raise SystemExit(f"DeepScientist skill discovery mismatch: {missing_skills}")

print(json.dumps({
    "ok": True,
    "module": "meddeepscientist",
    "checks": {
        "cli": "ds",
        "public_help": "ready",
        "package_import": "ready",
        "skill_discovery": "ready",
        "stage_skills": "ready",
        "companion_skills": "ready",
    },
}, ensure_ascii=False))
PY
