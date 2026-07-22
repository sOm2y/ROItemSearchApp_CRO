#!/usr/bin/env python3
"""Generate the Simplified Chinese item overlay from the upstream Lua file.

This is a development-time tool. Install ``opencc-python-reimplemented`` in
the environment used to run the script; the packaged application does not
need OpenCC because it reads the generated JSON.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

try:
    from opencc import OpenCC
except ImportError as error:  # pragma: no cover - depends on developer env
    raise SystemExit(
        "缺少开发期依赖 opencc-python-reimplemented；"
        "请先安装后再运行本脚本。"
    ) from error


ITEM_ENTRY_RE = re.compile(
    r"\[(\d+)\]\s*=\s*{(.*?)}(?=,\s*\[\d+\]|\s*\[\d+\]|\s*$)",
    re.DOTALL,
)
NAME_RE = re.compile(r'(?<!un)identifiedDisplayName\s*=\s*"([^"]+)"')
RESOURCE_RE = re.compile(r'(?<!un)identifiedResourceName\s*=\s*"([^"]+)"')
SLOT_RE = re.compile(r"slotCount\s*=\s*(\d+)")
DESCRIPTION_RE = re.compile(
    r"(?<!un)identifiedDescriptionName\s*=\s*{(.*?)}",
    re.DOTALL,
)
QUOTED_TEXT_RE = re.compile(r'"([^"]*)"')


def parse_item_text(lua_path: Path) -> dict[int, dict[str, object]]:
    content = lua_path.read_text(encoding="utf-8")
    parsed: dict[int, dict[str, object]] = {}
    for raw_item_id, body in ITEM_ENTRY_RE.findall(content):
        name_match = NAME_RE.search(body)
        if not name_match or not RESOURCE_RE.search(body) or not SLOT_RE.search(body):
            continue
        description_match = DESCRIPTION_RE.search(body)
        description = (
            QUOTED_TEXT_RE.findall(description_match.group(1))
            if description_match
            else []
        )
        parsed[int(raw_item_id)] = {
            "name": name_match.group(1).strip(),
            "description": description,
        }
    return parsed


def generate_overlay(
    sources: list[Path],
    output: Path,
    *,
    include_unchanged: bool = False,
) -> int:
    converter = OpenCC("t2s")
    source_items: dict[int, dict[str, object]] = {}
    for source in sources:
        source_items.update(parse_item_text(source))
    converted_items: dict[str, dict[str, object]] = {}

    for item_id, item in source_items.items():
        original_name = str(item["name"])
        original_description = [str(line) for line in item["description"]]
        converted_name = converter.convert(original_name)
        converted_description = [
            converter.convert(line)
            for line in original_description
        ]
        if (
            not include_unchanged
            and converted_name == original_name
            and converted_description == original_description
        ):
            continue
        converted_items[str(item_id)] = {
            "name": converted_name,
            "description": converted_description,
        }

    payload = {
        "_meta": {
            "language": "zh_CN",
            "sources": [str(source.as_posix()) for source in sources],
            "generator": "scripts/generate_item_zh_cn.py",
            "conversion": "OpenCC t2s; requires CRO terminology review",
            "source_item_count": len(source_items),
            "translated_item_count": len(converted_items),
        },
        "items": converted_items,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return len(converted_items)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source",
        action="append",
        type=Path,
        dest="sources",
        help=(
            "物品 Lua 来源，可重复指定。默认读取 iteminfo_new.lua 和 "
            "User_iteminfo_new.lua。"
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("lang/items/zh_CN.json"),
    )
    parser.add_argument(
        "--include-unchanged",
        action="store_true",
        help="也输出繁简转换后没有变化的物品。",
    )
    args = parser.parse_args()
    sources = args.sources or [
        Path("data/iteminfo_new.lua"),
        Path("data/User_iteminfo_new.lua"),
    ]

    count = generate_overlay(
        sources,
        args.output,
        include_unchanged=args.include_unchanged,
    )
    print(f"已生成 {count} 条简体物品覆盖：{args.output}")


if __name__ == "__main__":
    main()
