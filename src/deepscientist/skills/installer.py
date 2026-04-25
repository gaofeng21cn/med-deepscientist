from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

from ..memory.frontmatter import load_markdown_document
from ..shared import ensure_dir, read_json, utc_now, write_json
from .registry import discover_skill_bundles


class SkillInstaller:
    def __init__(self, repo_root: Path, home: Path) -> None:
        self.repo_root = repo_root
        self.home = home

    def discover(self):
        return discover_skill_bundles(self.repo_root)

    def sync_global(self) -> dict:
        return {
            "codex": [],
            "claude": [],
            "notes": [
                "Global skill sync is disabled; DeepScientist skills are installed per quest workspace.",
            ],
        }

    def sync_quest(self, quest_root: Path) -> dict:
        primary = self._sync_surface(quest_root)
        worktree_results: list[dict[str, object]] = []
        for worktree_root in self._quest_worktree_roots(quest_root):
            synced = self._sync_surface(worktree_root)
            worktree_results.append(
                {
                    "root": str(worktree_root),
                    "prompts": synced["prompts"],
                    "codex": synced["codex"],
                    "claude": synced["claude"],
                }
            )
        return {
            "prompts": primary["prompts"],
            "codex": primary["codex"],
            "claude": primary["claude"],
            "worktrees": worktree_results,
            "notes": [],
        }

    def sync_existing_quests(self) -> dict:
        quests_root = self.home / "quests"
        synced: list[dict[str, object]] = []
        if not quests_root.exists():
            return {
                "count": 0,
                "quests": [],
            }
        for quest_root in sorted(quests_root.iterdir()):
            if not quest_root.is_dir():
                continue
            if not (quest_root / "quest.yaml").exists():
                continue
            result = self.sync_quest(quest_root)
            synced.append(
                {
                    "quest_id": quest_root.name,
                    "quest_root": str(quest_root),
                    "codex_count": len(result.get("codex") or []),
                    "claude_count": len(result.get("claude") or []),
                }
            )
        return {
            "count": len(synced),
            "quests": synced,
        }

    def ensure_release_sync(
        self,
        *,
        installed_version: str,
        sync_global_enabled: bool = True,
        sync_existing_quests_enabled: bool = True,
        force: bool = False,
    ) -> dict:
        normalized_version = str(installed_version or "").strip() or "unknown"
        state = self._read_release_sync_state()
        previous_version = str(state.get("installed_version") or "").strip()
        if not force and previous_version == normalized_version:
            return {
                "updated": False,
                "installed_version": normalized_version,
                "previous_version": previous_version or None,
                "global_synced": False,
                "existing_quests_synced": False,
                "state_path": str(self._release_sync_state_path()),
            }

        summary: dict[str, object] = {
            "updated": True,
            "installed_version": normalized_version,
            "previous_version": previous_version or None,
            "global_synced": False,
            "existing_quests_synced": False,
            "state_path": str(self._release_sync_state_path()),
            "synced_at": utc_now(),
        }
        if sync_global_enabled:
            summary["global"] = self.sync_global()
            summary["global_synced"] = True
        if sync_existing_quests_enabled:
            summary["existing_quests"] = self.sync_existing_quests()
            summary["existing_quests_synced"] = True
        self._write_release_sync_state(summary)
        return summary

    def _sync_claude_projection(self, bundle, target_root: Path) -> Path:
        target = target_root / f"deepscientist-{bundle.skill_id}.md"
        if bundle.claude_md and bundle.claude_md.exists():
            self._write_bytes_atomic(target, bundle.claude_md.read_bytes())
            return target
        self._write_bytes_atomic(target, self._render_claude_projection(bundle).encode("utf-8"))
        return target

    @staticmethod
    def _render_claude_projection(bundle) -> str:
        metadata, body = load_markdown_document(bundle.skill_md)
        title = str(metadata.get("name") or bundle.name or bundle.skill_id)
        description = str(metadata.get("description") or "").strip()
        parts = [f"# {title}", ""]
        if description:
            parts.extend([description, ""])
        parts.append(body.strip())
        return "\n".join(parts).rstrip() + "\n"

    def _sync_bundle_tree(self, source_root: Path, target_root: Path) -> None:
        ensure_dir(target_root)
        expected_paths: set[Path] = set()

        for source_path in sorted(source_root.rglob("*")):
            relative = source_path.relative_to(source_root)
            expected_paths.add(relative)
            target_path = target_root / relative
            if source_path.is_dir():
                ensure_dir(target_path)
                continue
            self._sync_file(source_path, target_path)

        for target_path in sorted(target_root.rglob("*"), reverse=True):
            relative = target_path.relative_to(target_root)
            if relative in expected_paths:
                continue
            if target_path.is_dir():
                shutil.rmtree(target_path)
            else:
                target_path.unlink(missing_ok=True)

    def _sync_file(self, source_path: Path, target_path: Path) -> None:
        payload = source_path.read_bytes()
        if target_path.exists():
            try:
                if target_path.read_bytes() == payload:
                    return
            except OSError:
                pass
        self._write_bytes_atomic(target_path, payload)

    @staticmethod
    def _write_bytes_atomic(path: Path, payload: bytes) -> None:
        ensure_dir(path.parent)
        temp_path = path.parent / f".{path.name}.tmp-{uuid4().hex}"
        temp_path.write_bytes(payload)
        temp_path.replace(path)

    def _sync_prompt_tree(self, target_root: Path) -> None:
        source_root = self.repo_root / "src" / "prompts"
        self._sync_bundle_tree(source_root, target_root)

    def _sync_surface(self, root: Path) -> dict[str, list[str]]:
        prompts_root = ensure_dir(root / ".codex" / "prompts")
        self._sync_prompt_tree(prompts_root)
        codex_root = ensure_dir(root / ".codex" / "skills")
        claude_root = ensure_dir(root / ".claude" / "agents")
        copied_codex: list[str] = []
        copied_claude: list[str] = []
        expected_codex: set[str] = set()
        expected_claude: set[str] = set()
        for bundle in self.discover():
            target = codex_root / f"deepscientist-{bundle.skill_id}"
            expected_codex.add(target.name)
            self._sync_bundle_tree(bundle.root, target)
            copied_codex.append(str(target))
            claude_target = self._sync_claude_projection(bundle, claude_root)
            expected_claude.add(claude_target.name)
            copied_claude.append(str(claude_target))
        self._prune_bundle_targets(codex_root, expected_codex)
        self._prune_bundle_targets(claude_root, expected_claude)
        return {
            "prompts": [str(path) for path in sorted(prompts_root.rglob("*")) if path.is_file()],
            "codex": copied_codex,
            "claude": copied_claude,
        }

    @staticmethod
    def _quest_worktree_roots(quest_root: Path) -> list[Path]:
        roots: list[Path] = []
        worktrees_root = quest_root / ".ds" / "worktrees"
        if not worktrees_root.exists():
            return roots
        for candidate in sorted(worktrees_root.iterdir()):
            if candidate.is_dir():
                roots.append(candidate)
        return roots

    @staticmethod
    def _prune_bundle_targets(root: Path, expected_names: set[str]) -> None:
        for target in sorted(root.glob("deepscientist-*"), reverse=True):
            if target.name in expected_names:
                continue
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink(missing_ok=True)

    def _release_sync_state_path(self) -> Path:
        return self.home / "runtime" / "skill-sync-state.json"

    def _read_release_sync_state(self) -> dict:
        payload = read_json(self._release_sync_state_path(), {})
        return payload if isinstance(payload, dict) else {}

    def _write_release_sync_state(self, payload: dict[str, object]) -> None:
        write_json(self._release_sync_state_path(), payload)
