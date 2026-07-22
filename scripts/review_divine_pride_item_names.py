#!/usr/bin/env python3
"""Restore unapproved Divine Pride name changes and export a review list."""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path

from sync_divine_pride_items import (
    DEFAULT_BASE_LOCALE,
    DEFAULT_BATCH_OUTPUT,
    DEFAULT_REVIEW_OUTPUT,
    DivinePrideItem,
    atomic_write_json,
    classify_candidate_name,
    load_items_file,
    update_review_payload,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV_OUTPUT = (
    ROOT / "reports" / "divine_pride_item_name_review.csv"
)
REASON_LABELS_ZH_CN = {
    "missing_local_name": "本地名称缺失",
    "different_from_local": "与当前本地名称不同",
    "contains_japanese_kana": "包含日文假名",
    "contains_hangul": "包含韩文",
    "replaced_chinese_with_non_chinese": "中文名称被非中文替换",
    "contains_replacement_character": "包含乱码替换符",
    "contains_traditional_characters": "包含繁体字形",
    "not_simplified_chinese": "不是简体中文名称",
    "suspected_korean_mojibake": "疑似韩文错误解码乱码",
}


def migrate_candidates(
    *,
    base_path: Path,
    verified_path: Path,
    review_path: Path,
) -> tuple[int, Counter[str]]:
    base_payload = load_items_file(base_path)
    verified_payload = load_items_file(verified_path)
    review_payload = load_items_file(review_path)
    base_items = base_payload["items"]
    verified_items = verified_payload["items"]
    if not isinstance(base_items, dict):
        raise ValueError("基础语言包 items 必须是 JSON 对象")
    if not isinstance(verified_items, dict):
        raise ValueError("校对层 items 必须是 JSON 对象")

    moved = 0
    reason_counts: Counter[str] = Counter()
    for raw_item_id, raw_entry in list(verified_items.items()):
        if not isinstance(raw_entry, dict):
            continue
        approval = raw_entry.get("approval", {})
        if (
            isinstance(approval, dict)
            and str(approval.get("policy", "")).startswith("user_approved_")
        ):
            continue
        base_entry = base_items.get(raw_item_id, {})
        local_name = (
            str(base_entry.get("name", "")).strip()
            if isinstance(base_entry, dict)
            else ""
        )
        candidate_name = str(raw_entry.get("name", "")).strip()
        reasons = classify_candidate_name(local_name, candidate_name)
        if not reasons:
            continue
        source = raw_entry.get("source", {})
        source = source if isinstance(source, dict) else {}
        item = DivinePrideItem(
            item_id=int(raw_item_id),
            name=candidate_name,
            description=[],
            url=str(source.get("url", "")),
            server=str(source.get("server", "cRO")),
        )
        update_review_payload(
            review_payload,
            item,
            local_name=local_name,
            reasons=reasons,
            checked_at=str(source.get("checked_at", "")) or None,
        )
        del verified_items[raw_item_id]
        moved += 1
        reason_counts.update(reasons)

    verified_meta = verified_payload.setdefault("_meta", {})
    if isinstance(verified_meta, dict):
        verified_meta["verified_item_count"] = len(verified_items)
    review_items = review_payload.get("items", {})
    if isinstance(review_items, dict):
        for raw_entry in review_items.values():
            if not isinstance(raw_entry, dict):
                continue
            normalized_reasons = classify_candidate_name(
                raw_entry.get("local_name", ""),
                raw_entry.get("candidate_name", ""),
            )
            existing_reasons = raw_entry.get("reasons", [])
            if isinstance(existing_reasons, list):
                normalized_reasons.extend(
                    reason
                    for reason in existing_reasons
                    if reason in {
                        "not_simplified_chinese",
                        "suspected_korean_mojibake",
                    }
                )
            if normalized_reasons:
                raw_entry["reasons"] = list(dict.fromkeys(normalized_reasons))
    review_meta = review_payload.setdefault("_meta", {})
    if isinstance(review_meta, dict):
        review_meta.update(
            {
                "language": "zh_CN",
                "provider": "Divine Pride",
                "server": "cRO",
                "review_item_count": (
                    len(review_items)
                    if isinstance(review_items, dict)
                    else 0
                ),
                "purpose": (
                    "Name candidates excluded from runtime localization "
                    "pending manual approval."
                ),
            }
        )
    atomic_write_json(verified_path, verified_payload)
    atomic_write_json(review_path, review_payload)
    return moved, reason_counts


def write_review_csv(review_path: Path, csv_path: Path) -> int:
    payload = load_items_file(review_path)
    items = payload.get("items", {})
    if not isinstance(items, dict):
        raise ValueError("审核文件 items 必须是 JSON 对象")
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(
            file,
            lineterminator="\n",
            fieldnames=(
                "item_id",
                "local_name",
                "candidate_name",
                "reasons",
                "reason_zh_cn",
                "source_url",
                "checked_at",
            ),
        )
        writer.writeheader()
        for raw_item_id, raw_entry in sorted(
            items.items(),
            key=lambda pair: int(pair[0]),
        ):
            entry = raw_entry if isinstance(raw_entry, dict) else {}
            source = entry.get("source", {})
            source = source if isinstance(source, dict) else {}
            reasons = entry.get("reasons", [])
            writer.writerow(
                {
                    "item_id": raw_item_id,
                    "local_name": entry.get("local_name", ""),
                    "candidate_name": entry.get("candidate_name", ""),
                    "reasons": "|".join(
                        str(reason)
                        for reason in reasons
                    ) if isinstance(reasons, list) else "",
                    "reason_zh_cn": "|".join(
                        REASON_LABELS_ZH_CN.get(
                            str(reason),
                            str(reason),
                        )
                        for reason in reasons
                    ) if isinstance(reasons, list) else "",
                    "source_url": source.get("url", ""),
                    "checked_at": source.get("checked_at", ""),
                }
            )
    return len(items)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", type=Path, default=DEFAULT_BASE_LOCALE)
    parser.add_argument(
        "--verified",
        type=Path,
        default=DEFAULT_BATCH_OUTPUT,
    )
    parser.add_argument(
        "--review",
        type=Path,
        default=DEFAULT_REVIEW_OUTPUT,
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=DEFAULT_CSV_OUTPUT,
    )
    args = parser.parse_args()
    moved, reason_counts = migrate_candidates(
        base_path=args.base,
        verified_path=args.verified,
        review_path=args.review,
    )
    total = write_review_csv(args.review, args.csv)
    print(f"已恢复 {moved} 条未批准名称，审核列表共 {total} 条。")
    for reason, count in sorted(reason_counts.items()):
        print(f"- {reason}: {count}")
    print(f"CSV: {args.csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
