from __future__ import annotations

import re


def format_route_label(value: object) -> str | None:
    normalized = str(value or "").strip().replace("_", " ").replace("-", " ")
    if not normalized:
        return None
    return " ".join(part.capitalize() for part in normalized.split())


def notification_text(value: object) -> str | None:
    text = str(value or "")
    if not text.strip():
        return None
    normalized_lines: list[str] = []
    for raw_line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        cleaned = re.sub(r"[ \t]+", " ", raw_line).strip()
        if not cleaned:
            if normalized_lines and normalized_lines[-1] != "":
                normalized_lines.append("")
            continue
        normalized_lines.append(cleaned)
    while normalized_lines and normalized_lines[-1] == "":
        normalized_lines.pop()
    rendered = "\n".join(normalized_lines).strip()
    return rendered or None


def notification_block(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, dict):
        lines: list[str] = []
        for key, item in value.items():
            label = format_route_label(key) or str(key).strip()
            block = notification_block(item)
            if not label or not block:
                continue
            block_lines = block.splitlines()
            if len(block_lines) == 1:
                lines.append(f"- {label}: {block_lines[0]}")
                continue
            lines.append(f"- {label}:")
            lines.extend(f"  {line}" if line else "" for line in block_lines)
        return "\n".join(lines).strip() or None
    if isinstance(value, (list, tuple, set)):
        lines = []
        for item in value:
            block = notification_block(item)
            if not block:
                continue
            block_lines = block.splitlines()
            if not block_lines:
                continue
            lines.append(f"- {block_lines[0]}")
            lines.extend(f"  {line}" if line else "" for line in block_lines[1:])
        return "\n".join(lines).strip() or None
    return notification_text(value)


def append_notification_section(lines: list[str], label: str, value: object) -> None:
    block = notification_block(value)
    if not block:
        return
    lines.extend(["", f"{label}:", block])


def append_notification_file_section(lines: list[str], entries: list[tuple[str, str | None]]) -> None:
    normalized = [
        (label, str(path).strip())
        for label, path in entries
        if str(path or "").strip()
    ]
    if not normalized:
        return
    lines.extend(["", "Files:"])
    for label, path in normalized:
        lines.append(f"- {label}: `{path}`")
