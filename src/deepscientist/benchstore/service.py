from __future__ import annotations

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
