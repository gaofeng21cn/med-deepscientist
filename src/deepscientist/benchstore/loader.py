from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ..shared import read_yaml, slugify


_ENTRY_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def _normalize_catalog_locale(value: str | None) -> str:
    normalized = str(value or "en").strip().lower()
    return "zh" if normalized.startswith("zh") else "en"


def _optional_str(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _optional_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    raise ValueError(f"Expected boolean, got {value!r}.")


def _optional_number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise ValueError(f"Expected number, got {value!r}.")
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        return float(value.strip())
    raise ValueError(f"Expected number, got {value!r}.")


def _normalize_string_list(value: Any, *, field_name: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"`{field_name}` must be a list of strings.")
    items: list[str] = []
    for raw in value:
        normalized = _optional_str(raw)
        if normalized:
            items.append(normalized)
    return items


def _normalize_resource_spec(value: Any, *, field_name: str) -> dict[str, float]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"`{field_name}` must be an object.")
    normalized: dict[str, float] = {}
    for key in ("cpu_cores", "ram_gb", "disk_gb", "gpu_count", "gpu_vram_gb"):
        number = _optional_number(value.get(key))
        if number is not None:
            normalized[key] = number
    return normalized


def _normalize_environment_spec(value: Any) -> dict[str, Any]:
    if value is None:
        return {
            "python": None,
            "cuda": None,
            "pytorch": None,
            "flash_attn": None,
            "key_packages": [],
            "notes": [],
        }
    if not isinstance(value, dict):
        raise ValueError("`environment` must be an object.")
    return {
        "python": _optional_str(value.get("python")),
        "cuda": _optional_str(value.get("cuda")),
        "pytorch": _optional_str(value.get("pytorch")),
        "flash_attn": _optional_str(value.get("flash_attn")),
        "key_packages": _normalize_string_list(value.get("key_packages"), field_name="environment.key_packages"),
        "notes": _normalize_string_list(value.get("notes"), field_name="environment.notes"),
    }


def _normalize_dataset_sources(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("`dataset_download.sources` must be a list.")
    sources: list[dict[str, Any]] = []
    for index, raw in enumerate(value):
        if isinstance(raw, dict):
            sources.append(
                {
                    "kind": _optional_str(raw.get("kind")),
                    "url": _optional_str(raw.get("url")),
                    "access": _optional_str(raw.get("access")),
                    "note": _optional_str(raw.get("note")),
                }
            )
            continue
        normalized = _optional_str(raw)
        if normalized:
            sources.append(
                {
                    "kind": None,
                    "url": normalized,
                    "access": None,
                    "note": None,
                }
            )
            continue
        raise ValueError(f"`dataset_download.sources[{index}]` must be an object or string.")
    return sources


def _normalize_dataset_download_spec(value: Any) -> dict[str, Any]:
    if value is None:
        return {
            "primary_method": None,
            "sources": [],
            "notes": [],
        }
    if not isinstance(value, dict):
        raise ValueError("`dataset_download` must be an object.")
    return {
        "primary_method": _optional_str(value.get("primary_method")),
        "sources": _normalize_dataset_sources(value.get("sources")),
        "notes": _normalize_string_list(value.get("notes"), field_name="dataset_download.notes"),
    }


def _normalize_credential_requirements_spec(value: Any) -> dict[str, Any]:
    if value is None:
        return {
            "mode": None,
            "items": [],
            "notes": [],
        }
    if not isinstance(value, dict):
        raise ValueError("`credential_requirements` must be an object.")
    return {
        "mode": _optional_str(value.get("mode")),
        "items": _normalize_string_list(value.get("items"), field_name="credential_requirements.items"),
        "notes": _normalize_string_list(value.get("notes"), field_name="credential_requirements.notes"),
    }


def _sanitize_catalog_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, list):
        return [_sanitize_catalog_value(item) for item in value]
    if isinstance(value, dict):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            normalized[str(key)] = _sanitize_catalog_value(item)
        return normalized
    return str(value)


def _collect_search_values(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, bool):
        return ["true" if value else "false"]
    if isinstance(value, (str, int, float)):
        normalized = str(value).strip()
        return [normalized] if normalized else []
    if isinstance(value, list):
        items: list[str] = []
        for item in value:
            items.extend(_collect_search_values(item))
        return items
    if isinstance(value, dict):
        items: list[str] = []
        for key, item in value.items():
            key_text = str(key).strip()
            if key_text:
                items.append(key_text)
            items.extend(_collect_search_values(item))
        return items
    normalized = str(value).strip()
    return [normalized] if normalized else []


def time_band_upper_hours(value: str | None) -> float | None:
    text = str(value or "").strip().lower()
    if not text:
        return None
    if text.endswith("m") and text[:-1].strip().isdigit():
        return int(text[:-1].strip()) / 60.0
    if text.endswith("h") and text[:-1].strip().isdigit():
        return float(text[:-1].strip())
    if text.endswith("d") and text[:-1].strip().isdigit():
        return float(text[:-1].strip()) * 24.0
    band_match = re.match(r"^\s*(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*([mhd])\s*$", text)
    if band_match:
        upper = float(band_match.group(2))
        unit = band_match.group(3)
        if unit == "m":
            return upper / 60.0
        if unit == "d":
            return upper * 24.0
        return upper
    plus_match = re.match(r"^\s*(\d+(?:\.\d+)?)\s*([mhd])\s*\+\s*$", text)
    if plus_match:
        upper = float(plus_match.group(1))
        unit = plus_match.group(2)
        if unit == "m":
            return upper / 60.0
        if unit == "d":
            return upper * 24.0
        return upper
    return None


class BenchStoreCatalogLoader:
    def __init__(self, *, repo_root: Path, catalog_root: Path | None = None) -> None:
        self.repo_root = repo_root.resolve()
        self.catalog_root = (catalog_root or (self.repo_root / "AISB" / "catalog")).resolve()

    def list_entry_paths(self, *, locale: str = "en") -> list[Path]:
        normalized_locale = _normalize_catalog_locale(locale)
        base_paths = sorted(
            path
            for path in self.catalog_root.rglob("*.yaml")
            if not path.name.endswith(".zh.yaml")
        )
        resolved: list[Path] = []
        for path in base_paths:
            if normalized_locale == "zh":
                zh_path = path.with_name(f"{path.stem}.zh.yaml")
                if zh_path.exists():
                    resolved.append(zh_path)
                    continue
            resolved.append(path)
        return resolved

    def scan_catalog(self, *, locale: str = "en") -> dict[str, Any]:
        items: list[dict[str, Any]] = []
        invalid_entries: list[dict[str, str]] = []
        seen_ids: set[str] = set()

        if self.catalog_root.exists():
            for path in self.list_entry_paths(locale=locale):
                try:
                    entry = self.load_entry_file(path)
                except ValueError as exc:
                    invalid_entries.append(
                        {
                            "source_file": path.relative_to(self.repo_root).as_posix(),
                            "message": str(exc),
                        }
                    )
                    continue
                if entry["id"] in seen_ids:
                    invalid_entries.append(
                        {
                            "source_file": path.relative_to(self.repo_root).as_posix(),
                            "message": f"Duplicate benchmark id `{entry['id']}`.",
                        }
                    )
                    continue
                seen_ids.add(entry["id"])
                items.append(entry)

        items.sort(key=self._entry_sort_key)
        return {
            "items": items,
            "invalid_entries": invalid_entries,
        }

    def load_entry_file(self, path: Path, *, include_raw_payload: bool = False) -> dict[str, Any]:
        payload = read_yaml(path, {})
        if not isinstance(payload, dict):
            raise ValueError("BenchStore entry must be a YAML object.")

        name = _optional_str(payload.get("name"))
        if not name:
            raise ValueError("BenchStore entry requires non-empty `name`.")

        entry_id = self._normalize_identifier(payload.get("id"), fallback=path.stem)
        if not entry_id:
            raise ValueError("BenchStore entry id could not be derived.")

        paper_raw = payload.get("paper") if isinstance(payload.get("paper"), dict) else {}
        download_raw = payload.get("download") if isinstance(payload.get("download"), dict) else {}
        dataset_download_raw = (
            payload.get("dataset_download")
            if isinstance(payload.get("dataset_download"), dict)
            else payload.get("dataset_download")
        )
        credential_requirements_raw = (
            payload.get("credential_requirements")
            if isinstance(payload.get("credential_requirements"), dict)
            else payload.get("credential_requirements")
        )
        resources_raw = payload.get("resources") if isinstance(payload.get("resources"), dict) else {}
        environment_raw = payload.get("environment") if isinstance(payload.get("environment"), dict) else payload.get("environment")

        entry = {
            "schema_version": int(_optional_number(payload.get("schema_version")) or 1),
            "id": entry_id,
            "name": name,
            "version": _optional_str(payload.get("version")),
            "one_line": _optional_str(payload.get("one_line")),
            "task_description": _optional_str(payload.get("task_description")),
            "capability_tags": _normalize_string_list(payload.get("capability_tags"), field_name="capability_tags"),
            "track_fit": _normalize_string_list(payload.get("track_fit"), field_name="track_fit"),
            "task_mode": _optional_str(payload.get("task_mode")),
            "requires_execution": _optional_bool(payload.get("requires_execution")),
            "requires_paper": _optional_bool(payload.get("requires_paper")),
            "cost_band": _optional_str(payload.get("cost_band")),
            "time_band": _optional_str(payload.get("time_band")),
            "difficulty": _optional_str(payload.get("difficulty")),
            "data_access": _optional_str(payload.get("data_access")),
            "primary_outputs": _normalize_string_list(payload.get("primary_outputs"), field_name="primary_outputs"),
            "paper": {
                "title": _optional_str(paper_raw.get("title")),
                "venue": _optional_str(paper_raw.get("venue")),
                "year": int(_optional_number(paper_raw.get("year"))) if _optional_number(paper_raw.get("year")) is not None else None,
                "url": _optional_str(paper_raw.get("url")),
            },
            "download": {
                "url": _optional_str(download_raw.get("url")),
                "archive_type": _optional_str(download_raw.get("archive_type")),
                "local_dir_name": _optional_str(download_raw.get("local_dir_name")),
                "sha256": _optional_str(download_raw.get("sha256")),
                "size_bytes": int(_optional_number(download_raw.get("size_bytes"))) if _optional_number(download_raw.get("size_bytes")) is not None else None,
            },
            "dataset_download": _normalize_dataset_download_spec(dataset_download_raw),
            "credential_requirements": _normalize_credential_requirements_spec(credential_requirements_raw),
            "resources": {
                "minimum": _normalize_resource_spec(resources_raw.get("minimum"), field_name="resources.minimum"),
                "recommended": _normalize_resource_spec(resources_raw.get("recommended"), field_name="resources.recommended"),
            },
            "environment": _normalize_environment_spec(environment_raw),
            "source_file": path.relative_to(self.repo_root).as_posix(),
        }
        if include_raw_payload:
            entry["raw_payload"] = _sanitize_catalog_value(payload)
        entry["search_text"] = self._search_text(entry, raw_payload=payload)
        return entry

    @staticmethod
    def _normalize_identifier(value: Any, *, fallback: str) -> str:
        candidate = _optional_str(value) or _optional_str(fallback) or slugify(fallback or "bench")
        normalized = str(candidate).strip()
        if not normalized:
            return ""
        if _ENTRY_ID_PATTERN.match(normalized):
            return normalized
        return slugify(normalized, default="bench").replace("-", "_")

    @staticmethod
    def _entry_sort_key(entry: dict[str, Any]) -> tuple[str, str]:
        return (str(entry.get("id") or "").lower(), str(entry.get("name") or "").lower())

    @staticmethod
    def _search_text(entry: dict[str, Any], *, raw_payload: dict[str, Any] | None = None) -> str:
        paper = entry.get("paper") if isinstance(entry.get("paper"), dict) else {}
        environment = entry.get("environment") if isinstance(entry.get("environment"), dict) else {}
        dataset_download = entry.get("dataset_download") if isinstance(entry.get("dataset_download"), dict) else {}
        credential_requirements = entry.get("credential_requirements") if isinstance(entry.get("credential_requirements"), dict) else {}
        parts = [
            entry.get("id"),
            entry.get("name"),
            entry.get("one_line"),
            entry.get("task_description"),
            entry.get("task_mode"),
            entry.get("difficulty"),
            entry.get("time_band"),
            entry.get("cost_band"),
            entry.get("data_access"),
            paper.get("title"),
            paper.get("venue"),
            paper.get("url"),
            environment.get("python"),
            environment.get("cuda"),
            environment.get("pytorch"),
            environment.get("flash_attn"),
            dataset_download.get("primary_method"),
            credential_requirements.get("mode"),
        ]
        parts.extend(entry.get("capability_tags") or [])
        parts.extend(entry.get("track_fit") or [])
        parts.extend(entry.get("primary_outputs") or [])
        parts.extend(environment.get("key_packages") or [])
        parts.extend(environment.get("notes") or [])
        parts.extend(dataset_download.get("notes") or [])
        parts.extend(credential_requirements.get("items") or [])
        parts.extend(credential_requirements.get("notes") or [])
        for source in dataset_download.get("sources") or []:
            if isinstance(source, dict):
                parts.extend([source.get("kind"), source.get("url"), source.get("access"), source.get("note")])
        if isinstance(raw_payload, dict):
            parts.extend(_collect_search_values(raw_payload))
        return " ".join(str(item).strip().lower() for item in parts if str(item or "").strip())
