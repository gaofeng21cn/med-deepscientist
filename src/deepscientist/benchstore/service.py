from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .loader import BenchStoreCatalogLoader, _optional_bool, _optional_str, time_band_upper_hours


class BenchStoreRegistryService:
    def __init__(self, *, repo_root: Path, catalog_root: Path | None = None) -> None:
        self.repo_root = repo_root.resolve()
        self.loader = BenchStoreCatalogLoader(repo_root=self.repo_root, catalog_root=catalog_root)
        self.catalog_root = self.loader.catalog_root

    def list_entries(self, *, locale: str = "en") -> dict[str, Any]:
        catalog = self.loader.scan_catalog(locale=locale)
        items = list(catalog["items"])
        return {
            "ok": True,
            "catalog_root": str(self.catalog_root),
            "invalid_entries": catalog["invalid_entries"],
            "filter_options": self._filter_options(items),
            "items": items,
            "total": len(items),
        }

    def query_entries(self, *, filters: dict[str, Any] | None = None, locale: str = "en") -> dict[str, Any]:
        catalog = self.loader.scan_catalog(locale=locale)
        normalized_filters = self._normalize_filters(filters)
        items = [item for item in catalog["items"] if self._matches_filters(item, normalized_filters)]
        return {
            "ok": True,
            "catalog_root": str(self.catalog_root),
            "invalid_entries": catalog["invalid_entries"],
            "filter_options": self._filter_options(catalog["items"]),
            "items": items,
            "total": len(items),
            "applied_filters": normalized_filters,
        }

    def get_entry(self, entry_id: str, *, locale: str = "en") -> dict[str, Any]:
        normalized_id = str(entry_id or "").strip()
        if not normalized_id:
            raise FileNotFoundError("Benchmark id is required.")
        catalog = self.loader.scan_catalog(locale=locale)
        for item in catalog["items"]:
            if str(item.get("id") or "") == normalized_id:
                return {
                    "ok": True,
                    "entry": item,
                }
        raise FileNotFoundError(f"Unknown BenchStore entry `{normalized_id}`.")

    def build_setup_packet(self, entry_id: str, *, locale: str = "en") -> dict[str, Any]:
        entry = self._load_entry_with_raw(entry_id, locale=locale)
        benchmark_context = dict(entry)
        benchmark_context["entry_id"] = str(entry.get("id") or "").strip()
        benchmark_context["entry_name"] = str(entry.get("name") or "").strip()
        benchmark_goal = self._build_benchmark_goal(entry)
        constraints = self._build_constraints(entry)
        objectives = self._build_objectives(entry)
        suggested_form = {
            "title": str(entry.get("name") or "").strip(),
            "goal": benchmark_goal,
            "baseline_urls": self._join_lines(self._reference_lines(entry, field_name="baseline")),
            "paper_urls": self._join_lines(self._reference_lines(entry, field_name="paper")),
            "runtime_constraints": self._join_lines(constraints),
            "objectives": self._join_lines(objectives),
            "custom_brief": self._build_custom_brief(entry),
            "need_research_paper": bool(entry.get("requires_paper") is not False),
        }
        startup_instruction = "\n".join(
            line
            for line in [
                f"Please help prepare the autonomous start-research form for `{entry.get('name')}`.",
                benchmark_goal,
                "Use the injected benchmark context as the main source of truth.",
                "If material information is still missing, ask only the shortest practical follow-up questions.",
            ]
            if line
        ).strip()
        startup_contract = {
            "benchstore_context": benchmark_context,
            "start_setup_session": {
                "source": "benchstore",
                "locale": locale,
                "benchmark_context": benchmark_context,
                "suggested_form": suggested_form,
            },
        }
        return {
            "entry_id": str(entry.get("id") or "").strip(),
            "assistant_label": "SetupAgent",
            "project_title": str(entry.get("name") or "").strip(),
            "benchmark_local_path": None,
            "local_dataset_paths": [],
            "latex_markdown_path": None,
            "device_summary": None,
            "device_fit": "catalog_only",
            "requires_paper": bool(entry.get("requires_paper") is not False),
            "benchmark_goal": benchmark_goal,
            "constraints": constraints,
            "suggested_form": suggested_form,
            "startup_instruction": startup_instruction,
            "launch_payload": {
                "title": str(entry.get("name") or "").strip(),
                "goal": benchmark_goal,
                "initial_message": startup_instruction,
                "startup_contract": startup_contract,
            },
        }

    def _load_entry_with_raw(self, entry_id: str, *, locale: str = "en") -> dict[str, Any]:
        normalized_id = str(entry_id or "").strip()
        if not normalized_id:
            raise FileNotFoundError("Benchmark id is required.")
        for path in self.loader.list_entry_paths(locale=locale):
            try:
                entry = self.loader.load_entry_file(path, include_raw_payload=True)
            except ValueError:
                continue
            if str(entry.get("id") or "").strip() == normalized_id:
                return entry
        raise FileNotFoundError(f"Unknown BenchStore entry `{normalized_id}`.")

    @staticmethod
    def _build_benchmark_goal(entry: dict[str, Any]) -> str:
        name = str(entry.get("name") or entry.get("id") or "benchmark").strip()
        one_line = str(entry.get("one_line") or "").strip()
        task_description = str(entry.get("task_description") or "").strip()
        parts = [f"Prepare a faithful start-research launch for `{name}`."]
        if one_line:
            parts.append(one_line)
        if task_description:
            parts.append(task_description)
        return " ".join(parts).strip()

    @staticmethod
    def _reference_lines(entry: dict[str, Any], *, field_name: str) -> list[str]:
        lines: list[str] = []
        paper = entry.get("paper") if isinstance(entry.get("paper"), dict) else {}
        download = entry.get("download") if isinstance(entry.get("download"), dict) else {}
        dataset_download = entry.get("dataset_download") if isinstance(entry.get("dataset_download"), dict) else {}
        if field_name == "paper":
            url = str(paper.get("url") or "").strip()
            if url:
                lines.append(url)
            title = str(paper.get("title") or "").strip()
            if title:
                lines.append(title)
            return lines
        download_url = str(download.get("url") or "").strip()
        if download_url:
            lines.append(download_url)
        for source in dataset_download.get("sources") or []:
            if isinstance(source, dict):
                url = str(source.get("url") or "").strip()
                if url:
                    lines.append(url)
        return lines

    @staticmethod
    def _build_constraints(entry: dict[str, Any]) -> list[str]:
        constraints: list[str] = []
        time_band = str(entry.get("time_band") or "").strip()
        cost_band = str(entry.get("cost_band") or "").strip()
        data_access = str(entry.get("data_access") or "").strip()
        requires_execution = entry.get("requires_execution")
        resources = entry.get("resources") if isinstance(entry.get("resources"), dict) else {}
        recommended = resources.get("recommended") if isinstance(resources.get("recommended"), dict) else {}
        minimum = resources.get("minimum") if isinstance(resources.get("minimum"), dict) else {}
        if time_band:
            constraints.append(f"- Time expectation: {time_band}")
        if cost_band:
            constraints.append(f"- Cost band: {cost_band}")
        if isinstance(requires_execution, bool):
            constraints.append(
                "- Requires execution on the local/runtime environment."
                if requires_execution
                else "- Catalog entry can be prepared without a heavy local execution step."
            )
        if data_access:
            constraints.append(f"- Data access: {data_access}")
        if recommended:
            constraints.append(f"- Recommended resources: {json.dumps(recommended, ensure_ascii=False, sort_keys=True)}")
        elif minimum:
            constraints.append(f"- Minimum resources: {json.dumps(minimum, ensure_ascii=False, sort_keys=True)}")
        return constraints

    @staticmethod
    def _build_objectives(entry: dict[str, Any]) -> list[str]:
        objectives = [
            "- Preserve the benchmark scope faithfully in the startup form.",
            "- Make the first run bounded and reproducible.",
        ]
        if entry.get("requires_paper") is True:
            objectives.append("- Keep paper-facing deliverables in scope for the first research cycle.")
        if entry.get("requires_execution") is True:
            objectives.append("- Verify the runtime and dataset prerequisites before heavy execution starts.")
        return objectives

    @staticmethod
    def _build_custom_brief(entry: dict[str, Any]) -> str:
        track_fit = ", ".join(str(item).strip() for item in (entry.get("track_fit") or []) if str(item).strip())
        tags = ", ".join(str(item).strip() for item in (entry.get("capability_tags") or []) if str(item).strip())
        parts = [
            "Stay within the benchmark-defined task shape during setup.",
            f"Preferred tracks: {track_fit}." if track_fit else "",
            f"Capability tags: {tags}." if tags else "",
        ]
        return " ".join(part for part in parts if part).strip()

    @staticmethod
    def _join_lines(lines: list[str]) -> str:
        return "\n".join(line for line in lines if str(line or "").strip())

    @staticmethod
    def _filter_options(items: list[dict[str, Any]]) -> dict[str, list[str]]:
        def collect_scalar(key: str) -> list[str]:
            values = sorted(
                {
                    str(item.get(key) or "").strip()
                    for item in items
                    if str(item.get(key) or "").strip()
                }
            )
            return values

        def collect_list(key: str) -> list[str]:
            return sorted(
                {
                    str(value).strip()
                    for item in items
                    for value in (item.get(key) or [])
                    if str(value).strip()
                }
            )

        return {
            "capability_tags": collect_list("capability_tags"),
            "track_fit": collect_list("track_fit"),
            "cost_band": collect_scalar("cost_band"),
            "time_band": collect_scalar("time_band"),
            "task_mode": collect_scalar("task_mode"),
            "requires_execution": sorted(
                {
                    "true" if bool(item.get("requires_execution")) else "false"
                    for item in items
                    if item.get("requires_execution") is not None
                }
            ),
            "requires_paper": sorted(
                {
                    "true" if bool(item.get("requires_paper")) else "false"
                    for item in items
                    if item.get("requires_paper") is not None
                }
            ),
        }

    @staticmethod
    def _normalize_filters(filters: dict[str, Any] | None) -> dict[str, Any]:
        if not isinstance(filters, dict):
            return {}

        normalized: dict[str, Any] = {}

        tags_raw = filters.get("tags", filters.get("capability_tags"))
        tags = BenchStoreRegistryService._normalize_str_list(tags_raw)
        if tags:
            normalized["tags"] = tags

        cost_band = BenchStoreRegistryService._normalize_str_list(filters.get("cost_band"))
        if cost_band:
            normalized["cost_band"] = cost_band

        time_band = BenchStoreRegistryService._normalize_str_list(filters.get("time_band"))
        if time_band:
            normalized["time_band"] = time_band

        requires_paper = filters.get("requires_paper")
        if requires_paper is not None:
            normalized["requires_paper"] = _optional_bool(requires_paper)

        requires_execution = filters.get("requires_execution")
        if requires_execution is not None:
            normalized["requires_execution"] = _optional_bool(requires_execution)

        search = _optional_str(filters.get("search"))
        if search:
            normalized["search"] = search.lower()

        max_time_hours = filters.get("max_time_hours")
        if max_time_hours is not None:
            normalized["max_time_hours"] = float(max_time_hours)

        return normalized

    @staticmethod
    def _normalize_str_list(value: Any) -> list[str]:
        if value is None:
            return []
        values = value if isinstance(value, list) else [value]
        normalized: list[str] = []
        seen: set[str] = set()
        for raw in values:
            text = str(raw or "").strip().lower()
            if not text or text in seen:
                continue
            seen.add(text)
            normalized.append(text)
        return normalized

    @staticmethod
    def _matches_filters(entry: dict[str, Any], filters: dict[str, Any]) -> bool:
        if not filters:
            return True

        tags = filters.get("tags")
        if tags:
            entry_tags = {
                str(tag).strip().lower()
                for tag in (entry.get("capability_tags") or [])
                if str(tag).strip()
            }
            if entry_tags.isdisjoint(tags):
                return False

        cost_band = filters.get("cost_band")
        if cost_band and str(entry.get("cost_band") or "").strip().lower() not in set(cost_band):
            return False

        time_band = filters.get("time_band")
        if time_band and str(entry.get("time_band") or "").strip().lower() not in set(time_band):
            return False

        if "requires_paper" in filters and entry.get("requires_paper") is not filters["requires_paper"]:
            return False

        if "requires_execution" in filters and entry.get("requires_execution") is not filters["requires_execution"]:
            return False

        search = filters.get("search")
        if search and search not in str(entry.get("search_text") or "").lower():
            return False

        if "max_time_hours" in filters:
            upper = time_band_upper_hours(str(entry.get("time_band") or ""))
            if upper is None or upper > float(filters["max_time_hours"]):
                return False

        return True
