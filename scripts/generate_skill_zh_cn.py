#!/usr/bin/env python3
"""Generate the Simplified Chinese skill-name overlay from skillneme.csv."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

try:
    from opencc import OpenCC
except ImportError as error:  # pragma: no cover - developer dependency
    raise SystemExit(
        "缺少开发期依赖 opencc-python-reimplemented；"
        "请先安装后再运行本脚本。"
    ) from error


def generate_overlay(source: Path, output: Path) -> int:
    converter = OpenCC("t2s")
    skills: dict[str, dict[str, str]] = {}
    with source.open("r", encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            try:
                skill_id = int(row.get("ID", ""))
            except (TypeError, ValueError):
                continue
            name = str(row.get("Name", "")).strip()
            if not name:
                continue
            skills[str(skill_id)] = {"name": converter.convert(name)}

    payload = {
        "_meta": {
            "language": "zh_CN",
            "source": source.as_posix(),
            "generator": "scripts/generate_skill_zh_cn.py",
            "conversion": "OpenCC t2s; requires CRO terminology review",
            "translated_skill_count": len(skills),
        },
        "skills": skills,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return len(skills)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("data/skillneme.csv"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("lang/skills/zh_CN.json"),
    )
    args = parser.parse_args()
    count = generate_overlay(args.source, args.output)
    print(f"已生成 {count} 条简体技能名称：{args.output}")


if __name__ == "__main__":
    main()
