from __future__ import annotations

from pathlib import Path

from deepscientist.config import ConfigManager
from deepscientist.home import ensure_home_layout, repo_root
from deepscientist.prompts import PromptBuilder
from deepscientist.quest import QuestService
from deepscientist.skills import SkillInstaller, discover_skill_bundles


EXPECTED_STAGE_SKILLS = {
    "scout",
    "baseline",
    "idea",
    "optimize",
    "experiment",
    "analysis-campaign",
    "write",
    "finalize",
    "decision",
}

EXPECTED_COMPANION_SKILLS = {
    "paper-plot",
    "figure-polish",
    "intake-audit",
    "review",
    "rebuttal",
}

def test_src_stage_skills_exist_and_are_nontrivial() -> None:
    root = repo_root() / "src" / "skills"
    for skill_id in EXPECTED_STAGE_SKILLS:
        path = root / skill_id / "SKILL.md"
        assert path.exists(), f"missing {path}"
        text = path.read_text(encoding="utf-8")
        assert len(text.splitlines()) >= 40, f"{path} is unexpectedly thin"


def test_companion_skills_exist_and_are_nontrivial() -> None:
    root = repo_root() / "src" / "skills"
    for skill_id in EXPECTED_COMPANION_SKILLS:
        path = root / skill_id / "SKILL.md"
        assert path.exists(), f"missing {path}"
        text = path.read_text(encoding="utf-8")
        assert len(text.splitlines()) >= 30, f"{path} is unexpectedly thin"


def test_skill_discovery_prefers_src_skills() -> None:
    bundles = discover_skill_bundles(repo_root())
    discovered = {bundle.skill_id for bundle in bundles}
    assert EXPECTED_STAGE_SKILLS.issubset(discovered)
    assert EXPECTED_COMPANION_SKILLS.issubset(discovered)
    for bundle in bundles:
        if bundle.skill_id in EXPECTED_STAGE_SKILLS:
            assert Path(bundle.skill_md).is_relative_to(repo_root() / "src" / "skills")

    paper_plot = next(bundle for bundle in bundles if bundle.skill_id == "paper-plot")
    assert paper_plot.role == "companion"
    assert paper_plot.openai_yaml is not None


def test_new_companion_skill_reference_files_exist() -> None:
    root = repo_root() / "src" / "skills"
    assert (root / "paper-plot" / "references" / "bar_grouped_hatch.md").exists()
    assert (root / "paper-plot" / "references" / "line_confidence_band.md").exists()
    assert (root / "paper-plot" / "references" / "scatter_tsne_cluster.md").exists()
    assert (root / "paper-plot" / "scripts" / "bar_spice.py").exists()
    assert (root / "paper-plot" / "scripts" / "line_selfdistill.py").exists()
    assert (root / "paper-plot" / "scripts" / "scatter_tsne.py").exists()
    assert (root / "intake-audit" / "references" / "state-audit-template.md").exists()
    assert (root / "review" / "references" / "review-report-template.md").exists()
    assert (root / "review" / "references" / "revision-log-template.md").exists()
    assert (root / "review" / "references" / "experiment-todo-template.md").exists()
    assert (root / "rebuttal" / "references" / "action-plan-template.md").exists()
    assert (root / "rebuttal" / "references" / "evidence-update-template.md").exists()
    assert (root / "rebuttal" / "references" / "review-matrix-template.md").exists()
    assert (root / "rebuttal" / "references" / "response-letter-template.md").exists()


def test_stage_plan_and_checklist_templates_exist() -> None:
    root = repo_root() / "src" / "skills"
    assert (root / "baseline" / "references" / "baseline-plan-template.md").exists()
    assert (root / "baseline" / "references" / "baseline-checklist-template.md").exists()
    assert (root / "baseline" / "references" / "artifact-payload-examples.md").exists()
    assert (root / "experiment" / "references" / "main-experiment-plan-template.md").exists()
    assert (root / "experiment" / "references" / "main-experiment-checklist-template.md").exists()
    assert (root / "analysis-campaign" / "references" / "campaign-plan-template.md").exists()
    assert (root / "analysis-campaign" / "references" / "campaign-checklist-template.md").exists()


def test_write_skill_venue_templates_exist_and_sync(temp_home: Path) -> None:
    root = repo_root() / "src" / "skills" / "write" / "templates"
    assert (root / "README.md").exists()
    assert (root / "DEEPSCIENTIST_NOTES.md").exists()
    assert (root / "UPSTREAM_LICENSE.txt").exists()
    assert (root / "iclr2026" / "iclr2026_conference.tex").exists()
    assert (root / "icml2026" / "example_paper.tex").exists()
    assert (root / "neurips2025" / "main.tex").exists()
    assert (root / "acl" / "acl_latex.tex").exists()

    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    quest = QuestService(temp_home, skill_installer=SkillInstaller(repo_root(), temp_home)).create("write template sync quest")
    quest_root = Path(quest["quest_root"])

    synced_root = quest_root / ".codex" / "skills" / "deepscientist-write" / "templates"
    assert (synced_root / "DEEPSCIENTIST_NOTES.md").exists()
    assert (synced_root / "iclr2026" / "iclr2026_conference.tex").exists()
    assert (synced_root / "acl" / "acl_latex.tex").exists()


def test_global_skill_sync_is_disabled(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    installer = SkillInstaller(repo_root(), temp_home)

    result = installer.sync_global()

    assert result["codex"] == []
    assert result["claude"] == []
    assert result["notes"]


def test_quest_creation_syncs_all_stage_skills(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    quest = QuestService(temp_home, skill_installer=SkillInstaller(repo_root(), temp_home)).create("skill sync quest")
    quest_root = Path(quest["quest_root"])

    codex_skills = sorted((quest_root / ".codex" / "skills").glob("deepscientist-*"))
    claude_skills = sorted((quest_root / ".claude" / "agents").glob("deepscientist-*.md"))

    synced_codex = {path.name.removeprefix("deepscientist-") for path in codex_skills}
    synced_claude = {path.stem.removeprefix("deepscientist-") for path in claude_skills}

    assert EXPECTED_STAGE_SKILLS.issubset(synced_codex)
    assert EXPECTED_STAGE_SKILLS.issubset(synced_claude)
    assert EXPECTED_COMPANION_SKILLS.issubset(synced_codex)
    assert EXPECTED_COMPANION_SKILLS.issubset(synced_claude)
    assert (quest_root / ".codex" / "prompts" / "system.md").exists()
    assert (quest_root / ".codex" / "prompts" / "contracts" / "shared_interaction.md").exists()
    assert (quest_root / ".codex" / "prompts" / "connectors" / "qq.md").exists()


def test_sync_quest_keeps_stage_skills_available_in_quest_and_worktree_without_global_install(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    installer = SkillInstaller(repo_root(), temp_home)
    quest = QuestService(temp_home, skill_installer=installer).create("paper workspace skill availability")
    quest_root = Path(quest["quest_root"])
    worktree_root = quest_root / ".ds" / "worktrees" / "paper-main"
    worktree_root.mkdir(parents=True)

    result = installer.sync_quest(quest_root)

    assert result["worktrees"]
    for root in (quest_root, worktree_root):
        for skill_id in EXPECTED_STAGE_SKILLS:
            assert (root / ".codex" / "skills" / f"deepscientist-{skill_id}" / "SKILL.md").exists()
            assert (root / ".claude" / "agents" / f"deepscientist-{skill_id}.md").exists()
        assert (root / ".codex" / "prompts" / "system.md").exists()
        assert (root / ".codex" / "prompts" / "contracts" / "shared_interaction.md").exists()

    assert not (temp_home / ".codex" / "skills").exists()
    assert not (temp_home / ".claude" / "agents").exists()


def test_skill_resync_repairs_frontmatter_and_removes_stale_files(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    installer = SkillInstaller(repo_root(), temp_home)
    quest = QuestService(temp_home, skill_installer=installer).create("skill resync quest")
    quest_root = Path(quest["quest_root"])

    installed_skill = quest_root / ".codex" / "skills" / "deepscientist-idea" / "SKILL.md"
    stale_file = quest_root / ".codex" / "skills" / "deepscientist-idea" / "stale.tmp"
    stale_removed_codex = quest_root / ".codex" / "skills" / "deepscientist-alpharxiv-paper-loopup"
    stale_removed_claude = quest_root / ".claude" / "agents" / "deepscientist-alpharxiv-paper-loopup.md"

    installed_skill.write_text("broken skill body\n", encoding="utf-8")
    stale_file.write_text("remove me\n", encoding="utf-8")
    stale_removed_codex.mkdir(parents=True)
    (stale_removed_codex / "SKILL.md").write_text("legacy skill\n", encoding="utf-8")
    stale_removed_claude.write_text("legacy claude skill\n", encoding="utf-8")

    installer.sync_quest(quest_root)

    repaired = installed_skill.read_text(encoding="utf-8")
    assert repaired.startswith("---\n")
    assert "name:" in repaired
    assert not stale_file.exists()
    assert not stale_removed_codex.exists()
    assert not stale_removed_claude.exists()


def test_skill_resync_refreshes_existing_worktree_skill_copies(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    installer = SkillInstaller(repo_root(), temp_home)
    quest = QuestService(temp_home, skill_installer=installer).create("worktree skill resync quest")
    quest_root = Path(quest["quest_root"])

    worktree_root = quest_root / ".ds" / "worktrees" / "paper-main"
    figure_skill = worktree_root / ".codex" / "skills" / "deepscientist-figure-polish" / "SKILL.md"
    figure_skill.parent.mkdir(parents=True, exist_ok=True)
    figure_skill.write_text("AutoFigure-Edit\nsrc/skills/write/SKILL.md\n", encoding="utf-8")

    installer.sync_quest(quest_root)

    repaired = figure_skill.read_text(encoding="utf-8")
    assert "AutoFigure-Edit" not in repaired
    assert "src/skills/" not in repaired


def test_legacy_alpharxiv_skill_is_removed() -> None:
    root = repo_root() / "src" / "skills"

    assert not (root / "alpharxiv-paper-loopup" / "SKILL.md").exists()


def test_write_skill_keeps_medical_preflight_reference_assets_available() -> None:
    root = repo_root() / "src" / "skills" / "write"

    reference = root / "references" / "medical-journal-prose.md"
    assert reference.exists()


def test_checkpoint_memory_reference_files_exist() -> None:
    root = repo_root() / "src" / "skills"

    assert (root / "decision" / "references" / "checkpoint-memory-template.md").exists()
    assert (root / "finalize" / "references" / "checkpoint-memory-template.md").exists()
    assert (root / "finalize" / "references" / "resume-packet-template.md").exists()


def test_prompt_builder_skill_paths_only_reference_existing_files(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    quest = QuestService(temp_home, skill_installer=SkillInstaller(repo_root(), temp_home)).create("skill prompt quest")
    builder = PromptBuilder(repo_root(), temp_home)

    prompt = builder.build(
        quest_id=quest["quest_id"],
        skill_id="finalize",
        user_message="Please summarize the quest and stop cleanly.",
        model="gpt-5.4",
    )

    finalize_primary = str((repo_root() / "src" / "skills" / "finalize" / "SKILL.md").resolve())
    assert "Fallback mirrored skills root:" not in prompt
    assert f"- finalize: primary={finalize_primary}" in prompt


def test_write_skill_paper_reference_files_exist() -> None:
    root = repo_root() / "src" / "skills" / "write"

    assert (root / "references" / "paper-experiment-matrix-template.md").exists()
    assert (root / "references" / "reviewer-first-writing.md").exists()
    assert (root / "references" / "section-contracts.md").exists()
    assert (root / "references" / "sentence-level-proofing.md").exists()


def test_experiment_and_analysis_reference_files_exist() -> None:
    root = repo_root() / "src" / "skills"

    assert (root / "experiment" / "references" / "evidence-ladder.md").exists()
    assert (root / "analysis-campaign" / "references" / "campaign-design.md").exists()


def test_figure_polish_skill_requires_render_inspect_revise_workflow_and_style_asset() -> None:
    style_asset = repo_root() / "src" / "skills" / "figure-polish" / "assets" / "deepscientist-academic.mplstyle"

    assert style_asset.exists()


def test_paper_plot_skill_agent_metadata_exists() -> None:
    openai_yaml = (repo_root() / "src" / "skills" / "paper-plot" / "agents" / "openai.yaml").read_text(encoding="utf-8")

    assert 'display_name: "Paper Plot"' in openai_yaml


def test_figure_polish_skill_and_synced_copy_stay_manuscript_safe(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    quest = QuestService(temp_home, skill_installer=SkillInstaller(repo_root(), temp_home)).create("figure polish sync quest")
    quest_root = Path(quest["quest_root"])

    source_text = (repo_root() / "src" / "skills" / "figure-polish" / "SKILL.md").read_text(encoding="utf-8")
    synced_text = (quest_root / ".codex" / "skills" / "deepscientist-figure-polish" / "SKILL.md").read_text(encoding="utf-8")

    for text in (source_text, synced_text):
        assert "AutoFigure-Edit" not in text
        assert "https://deepscientist" not in text
        assert "src/skills/" not in text
        assert "src/prompts/system.md" not in text
