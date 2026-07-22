#!/usr/bin/env python3
"""Validate Monster ID localization coverage against local source data."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from monster_localization import load_monster_catalog, load_monster_translations


def main() -> int:
    catalog = load_monster_catalog(str(ROOT))
    translations = load_monster_translations("zh_CN", base_dir=str(ROOT))
    source_ids = set(catalog)
    translated_ids = set(translations)
    missing = source_ids - translated_ids
    extra = translated_ids - source_ids
    problems: list[str] = []
    if missing:
        problems.append(f"missing translations: {sorted(missing)}")
    if extra:
        problems.append(f"unknown translated IDs: {sorted(extra)}")
    if problems:
        print("monster localization FAILED")
        for problem in problems:
            print(f"- {problem}")
        return 1
    print(
        "monster localization OK: "
        f"{len(source_ids)} source IDs, {len(translated_ids)} translations"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
