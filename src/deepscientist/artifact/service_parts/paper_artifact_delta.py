from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from ...evidence_packets import payload_sha256
from ...shared import ensure_dir, utc_now, write_json


def _relative_artifact_path(path: Path, *, quest_root: Path, workspace_root: Path) -> str:
    resolved = path.resolve(strict=False)
    for root in (workspace_root, quest_root):
        try:
            return str(resolved.relative_to(root.resolve(strict=False)))
        except ValueError:
            continue
    return str(resolved)


def _file_signature(path: Path, *, quest_root: Path, workspace_root: Path) -> dict[str, Any]:
    resolved = path.resolve(strict=False)
    item: dict[str, Any] = {
        "path": _relative_artifact_path(resolved, quest_root=quest_root, workspace_root=workspace_root),
        "absolute_path": str(resolved),
        "exists": resolved.exists() and resolved.is_file(),
    }
    if not item["exists"]:
        item["sha256"] = None
        item["bytes"] = 0
        return item
    data = resolved.read_bytes()
    item["sha256"] = hashlib.sha256(data).hexdigest()
    item["bytes"] = len(data)
    return item


def build_paper_artifact_delta_marker(
    *,
    quest_root: Path,
    workspace_root: Path,
    artifact_kind: str,
    written_paths: list[Path],
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    seen: set[str] = set()
    path_signatures: list[dict[str, Any]] = []
    for path in written_paths:
        key = str(path.resolve(strict=False))
        if key in seen:
            continue
        seen.add(key)
        path_signatures.append(
            _file_signature(
                path,
                quest_root=quest_root,
                workspace_root=workspace_root,
            )
        )

    payload_fingerprint = payload_sha256(payload or {})
    signature_paths = [
        {key: value for key, value in item.items() if key != "absolute_path"}
        for item in path_signatures
    ]
    source_signature = payload_sha256(
        {
            "artifact_kind": artifact_kind,
            "payload_fingerprint": payload_fingerprint,
            "written_paths": signature_paths,
        }
    )
    sidecar_path = (
        quest_root
        / ".ds"
        / "artifact_deltas"
        / f"{artifact_kind}-{source_signature[:16]}.json"
    )
    marker = {
        "version": 1,
        "marker": "artifact-delta",
        "source_signature_marker": "source-signature",
        "artifact_kind": artifact_kind,
        "source_signature": source_signature,
        "payload_fingerprint": payload_fingerprint,
        "written_paths": path_signatures,
        "sidecar_path": str(sidecar_path),
        "created_at": utc_now(),
    }
    ensure_dir(sidecar_path.parent)
    write_json(sidecar_path, marker)
    return marker
