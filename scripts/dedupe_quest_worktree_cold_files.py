#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from deepscientist.runtime_storage import dedupe_worktree_files


def main() -> None:
    parser = argparse.ArgumentParser(description="Hardlink-dedupe duplicated large cold files under quest worktrees.")
    parser.add_argument("quest_root", help="Absolute quest root path")
    parser.add_argument("--older-than-hours", type=int, default=6, help="Only dedupe files older than this many hours")
    parser.add_argument("--min-mb", type=int, default=16, help="Only dedupe files at or above this size")
    args = parser.parse_args()

    quest_root = Path(args.quest_root).expanduser().resolve()
    result = dedupe_worktree_files(
        quest_root,
        older_than_seconds=max(1, args.older_than_hours) * 3600,
        min_bytes=max(1, args.min_mb) * 1024 * 1024,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
