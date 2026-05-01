#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from deepscientist.runtime_storage import maintain_quest_runtime_storage


def main() -> None:
    parser = argparse.ArgumentParser(description="Compact oversized quest runtime storage and prune stale runtime tempfiles.")
    parser.add_argument("quest_root", help="Absolute quest root path")
    parser.add_argument("--no-worktrees", action="store_true", help="Only maintain the quest root itself")
    parser.add_argument("--no-slim-oversized-jsonl", action="store_true", help="Skip quest-local backup + placeholder compaction for oversized JSONL entries")
    parser.add_argument("--no-dedupe-worktrees", action="store_true", help="Skip hardlink dedupe for duplicated cold files under .ds/worktrees")
    parser.add_argument("--no-prune-expanded-worktrees", action="store_true", help="Keep cold expanded .ds/worktrees checkouts even when they have no runtime payloads")
    parser.add_argument("--older-than-hours", type=int, default=6, help="Only compact finished runtime files older than this many hours")
    parser.add_argument("--jsonl-max-mb", type=int, default=64, help="Compact completed JSONL logs at or above this size")
    parser.add_argument("--text-max-mb", type=int, default=16, help="Compact completed text logs at or above this size")
    parser.add_argument("--event-segment-max-mb", type=int, default=64, help="Rotate .ds/events.jsonl into segmented archives at or above this size")
    parser.add_argument("--slim-jsonl-threshold-mb", type=int, default=8, help="Compact individual JSONL lines larger than this many MB into quest-local backups")
    parser.add_argument("--dedupe-worktree-min-mb", type=int, default=16, help="Hardlink-dedupe duplicated cold worktree files at or above this many MB")
    parser.add_argument("--head-lines", type=int, default=200, help="Retain this many lines from the start of compacted logs")
    parser.add_argument("--tail-lines", type=int, default=200, help="Retain this many lines from the end of compacted logs")
    args = parser.parse_args()

    result = maintain_quest_runtime_storage(
        Path(args.quest_root).expanduser().resolve(),
        include_worktrees=not args.no_worktrees,
        older_than_seconds=max(1, args.older_than_hours) * 3600,
        jsonl_max_mb=max(1, args.jsonl_max_mb),
        text_max_mb=max(1, args.text_max_mb),
        event_segment_max_mb=max(1, args.event_segment_max_mb),
        slim_jsonl_threshold_mb=None if args.no_slim_oversized_jsonl else max(1, args.slim_jsonl_threshold_mb),
        dedupe_worktree_min_mb=None if args.no_dedupe_worktrees else max(1, args.dedupe_worktree_min_mb),
        prune_expanded_worktrees=not args.no_prune_expanded_worktrees,
        head_lines=max(1, args.head_lines),
        tail_lines=max(1, args.tail_lines),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
