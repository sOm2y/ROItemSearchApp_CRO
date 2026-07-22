#!/usr/bin/env python3
"""Validate Skill ID localization coverage against skillneme.csv."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from skill_localization import load_skill_translations


def main() -> int:
    source_ids: set[int] = set()
    duplicate_ids: set[int] = set()
    with Path(ROOT, "data", "skillneme.csv").open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        for row in csv.DictReader(file):
            try:
                skill_id = int(row.get("ID", ""))
            except (TypeError, ValueError):
                continue
            if skill_id in source_ids:
                duplicate_ids.add(skill_id)
            source_ids.add(skill_id)

    translations = load_skill_translations("zh_CN", base_dir=str(ROOT))
    translated_ids = set(translations)
    missing = source_ids - translated_ids
    extra = translated_ids - source_ids

    problems: list[str] = []
    if duplicate_ids:
        problems.append(f"source duplicate IDs: {sorted(duplicate_ids)[:20]}")
    if missing:
        problems.append(f"missing translations: {sorted(missing)[:20]}")
    if extra:
        problems.append(f"unknown translated IDs: {sorted(extra)[:20]}")
    if problems:
        print("skill localization FAILED")
        for problem in problems:
            print(f"- {problem}")
        return 1

    print(
        "skill localization OK: "
        f"{len(source_ids)} source IDs, {len(translated_ids)} translations"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
