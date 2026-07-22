#!/usr/bin/env python3
"""Generate the Simplified Chinese monster overlay from local ID sources."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from opencc import OpenCC
except ImportError as error:  # pragma: no cover - developer dependency
    raise SystemExit(
        "缺少开发期依赖 opencc-python-reimplemented；"
        "请先安装后再运行本脚本。"
    ) from error

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from monster_localization import load_monster_catalog


def generate_overlay(source_root: Path, output: Path) -> int:
    converter = OpenCC("t2s")
    catalog = load_monster_catalog(str(source_root.resolve()))
    monsters = {
        str(monster_id): {"name": converter.convert(str(info["name"]))}
        for monster_id, info in sorted(catalog.items())
        if str(info.get("name", "")).strip()
    }
    payload = {
        "_meta": {
            "language": "zh_CN",
            "sources": ["data/monsters.json", "data/monster/*.json"],
            "generator": "scripts/generate_monster_zh_cn.py",
            "conversion": "OpenCC t2s; requires CRO terminology review",
            "translated_monster_count": len(monsters),
        },
        "monsters": monsters,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return len(monsters)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, default=Path("."))
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("lang/monsters/zh_CN.json"),
    )
    args = parser.parse_args()
    count = generate_overlay(args.source_root, args.output)
    print(f"已生成 {count} 条简体怪物名称：{args.output}")


if __name__ == "__main__":
    main()
