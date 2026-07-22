#!/usr/bin/env python3
"""Promote reviewed Simplified Chinese Divine Pride names into runtime data."""

from __future__ import annotations

import argparse
import csv
import re
from datetime import datetime
from pathlib import Path

from opencc import OpenCC

try:
    from scripts.sync_divine_pride_items import (
        DEFAULT_BATCH_OUTPUT,
        DEFAULT_REVIEW_OUTPUT,
        atomic_write_json,
        load_items_file,
    )
except ModuleNotFoundError:  # Direct execution from the scripts directory.
    from sync_divine_pride_items import (
        DEFAULT_BATCH_OUTPUT,
        DEFAULT_REVIEW_OUTPUT,
        atomic_write_json,
        load_items_file,
    )


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_APPROVED_CSV = (
    ROOT / "reports" / "divine_pride_item_name_approved.csv"
)
APPROVAL_POLICY = "user_approved_simplified_chinese"
VARIANT_ALIAS_POLICY = "user_approved_chinese_variant_alias"
APPROVAL_POLICIES = {APPROVAL_POLICY, VARIANT_ALIAS_POLICY}
HAN_RE = re.compile(r"[\u3400-\u9fff]")
KANA_RE = re.compile(r"[\u3040-\u30ff]")
HANGUL_RE = re.compile(r"[\u1100-\u11ff\uac00-\ud7af]")
HANGUL_SYLLABLE_RE = re.compile(r"[\uac00-\ud7af]")
T2S_CONVERTER = OpenCC("t2s")

# Short Korean strings can survive a cp949 -> GB18030 decoding error without
# enough context for the bigram detector below. These candidates were observed
# in the completed cRO scan and reverse cleanly to Korean item names.
KNOWN_SHORT_MOJIBAKE = {
    "格犁",
    "了荐汗",
    "胶墨捞镐",
    "何侩",
    "桂碱",
    "催脾辫葛惦",
    "催脾辫",
    "内技扼技扼",
    "丢皑",
}

# cRO terminology variants explicitly approved by the project maintainer.
# They remain aliases so the Simplified Chinese display name stays stable.
USER_APPROVED_VARIANT_ALIAS_IDS = {
    "4671",
    "4672",
    "4673",
    "4674",
    "4675",
    "4676",
    "4677",
    "4678",
    "4679",
    "4680",
    "4681",
    "4682",
    "4683",
}


def is_simplified_chinese_name(name: object) -> bool:
    candidate = str(name or "").strip()
    return bool(
        candidate
        and HAN_RE.search(candidate)
        and not KANA_RE.search(candidate)
        and not HANGUL_RE.search(candidate)
        and "\ufffd" not in candidate
        and T2S_CONVERTER.convert(candidate) == candidate
    )


def is_equivalent_chinese_variant(
    local_name: object,
    candidate_name: object,
) -> bool:
    local = str(local_name or "").strip()
    candidate = str(candidate_name or "").strip()
    if (
        not local
        or not candidate
        or KANA_RE.search(candidate)
        or HANGUL_RE.search(candidate)
        or "\ufffd" in candidate
        or T2S_CONVERTER.convert(candidate) == candidate
    ):
        return False
    normalize = lambda value: re.sub(r"\s+", "", value)
    return normalize(T2S_CONVERTER.convert(candidate)) == normalize(local)


def is_approved_variant_alias(
    item_id: object,
    local_name: object,
    candidate_name: object,
) -> bool:
    return (
        str(item_id) in USER_APPROVED_VARIANT_ALIAS_IDS
        or is_equivalent_chinese_variant(local_name, candidate_name)
    )


def build_korean_bigram_set(review_items: dict[str, object]) -> set[str]:
    bigrams: set[str] = set()
    for raw_entry in review_items.values():
        if not isinstance(raw_entry, dict):
            continue
        candidate = str(raw_entry.get("candidate_name", ""))
        syllables = "".join(HANGUL_SYLLABLE_RE.findall(candidate))
        bigrams.update(
            syllables[index:index + 2]
            for index in range(len(syllables) - 1)
        )
    return bigrams


def reverse_korean_mojibake(candidate: str) -> str:
    try:
        recovered = candidate.encode("gb18030").decode("cp949")
    except UnicodeError:
        return ""
    if not HANGUL_SYLLABLE_RE.search(recovered) or HAN_RE.search(recovered):
        return ""
    return recovered


def is_suspected_korean_mojibake(
    candidate_name: object,
    local_name: object,
    korean_bigrams: set[str],
) -> bool:
    candidate = str(candidate_name or "").strip()
    local = str(local_name or "").strip()
    if candidate in KNOWN_SHORT_MOJIBAKE:
        return True
    recovered = reverse_korean_mojibake(candidate)
    if not recovered:
        return False
    syllables = "".join(HANGUL_SYLLABLE_RE.findall(recovered))
    has_known_bigram = any(
        syllables[index:index + 2] in korean_bigrams
        for index in range(len(syllables) - 1)
    )
    shared_han = set(HAN_RE.findall(candidate)) & set(HAN_RE.findall(local))
    return has_known_bigram or (" " in recovered and not shared_han)


def write_approved_csv(verified_path: Path, csv_path: Path) -> int:
    items = load_items_file(verified_path)["items"]
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    approved_count = 0
    with csv_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(
            file,
            lineterminator="\n",
            fieldnames=(
                "item_id",
                "original_name",
                "approved_name",
                "aliases",
                "approval_policy",
                "approved_at",
                "source_url",
            ),
        )
        writer.writeheader()
        for raw_item_id, raw_entry in sorted(
            items.items(),
            key=lambda pair: int(pair[0]),
        ):
            if not isinstance(raw_entry, dict):
                continue
            approval = raw_entry.get("approval", {})
            if (
                not isinstance(approval, dict)
                or approval.get("policy") not in APPROVAL_POLICIES
            ):
                continue
            source = raw_entry.get("source", {})
            source = source if isinstance(source, dict) else {}
            writer.writerow(
                {
                    "item_id": raw_item_id,
                    "original_name": approval.get("original_name", ""),
                    "approved_name": raw_entry.get("name", ""),
                    "aliases": "|".join(
                        str(alias)
                        for alias in raw_entry.get("aliases", [])
                    ) if isinstance(raw_entry.get("aliases"), list) else "",
                    "approval_policy": approval.get("policy", ""),
                    "approved_at": approval.get("approved_at", ""),
                    "source_url": source.get("url", ""),
                }
            )
            approved_count += 1
    return approved_count


def promote_simplified_names(
    *,
    verified_path: Path,
    review_path: Path,
    approved_at: str | None = None,
) -> tuple[int, int, int, int]:
    verified_payload = load_items_file(verified_path)
    review_payload = load_items_file(review_path)
    verified_items = verified_payload["items"]
    review_items = review_payload["items"]
    approved_at = approved_at or datetime.now().astimezone().date().isoformat()
    korean_bigrams = build_korean_bigram_set(review_items)
    promoted = 0
    variant_aliases = 0
    not_simplified = 0
    suspected_mojibake = 0

    for raw_item_id, raw_entry in list(review_items.items()):
        if not isinstance(raw_entry, dict):
            continue
        local_name = str(raw_entry.get("local_name", "")).strip()
        candidate_name = str(raw_entry.get("candidate_name", "")).strip()
        reasons = list(raw_entry.get("reasons", []))
        if is_approved_variant_alias(
            raw_item_id,
            local_name,
            candidate_name,
        ):
            source = raw_entry.get("source", {})
            verified_items[raw_item_id] = {
                "name": local_name,
                "aliases": [candidate_name],
                "source": dict(source) if isinstance(source, dict) else {},
                "approval": {
                    "policy": VARIANT_ALIAS_POLICY,
                    "approved_at": approved_at,
                    "original_name": local_name,
                    "candidate_name": candidate_name,
                },
            }
            del review_items[raw_item_id]
            variant_aliases += 1
            continue
        if not is_simplified_chinese_name(candidate_name):
            raw_entry["reasons"] = list(
                dict.fromkeys([*reasons, "not_simplified_chinese"])
            )
            not_simplified += 1
            continue
        if is_suspected_korean_mojibake(
            candidate_name,
            local_name,
            korean_bigrams,
        ):
            raw_entry["reasons"] = list(
                dict.fromkeys([*reasons, "suspected_korean_mojibake"])
            )
            suspected_mojibake += 1
            continue

        source = raw_entry.get("source", {})
        verified_items[raw_item_id] = {
            "name": candidate_name,
            "source": dict(source) if isinstance(source, dict) else {},
            "approval": {
                "policy": APPROVAL_POLICY,
                "approved_at": approved_at,
                "original_name": local_name,
            },
        }
        del review_items[raw_item_id]
        promoted += 1

    verified_meta = verified_payload.setdefault("_meta", {})
    if isinstance(verified_meta, dict):
        verified_meta["verified_item_count"] = len(verified_items)
        verified_meta["approved_simplified_item_count"] = sum(
            isinstance(entry, dict)
            and isinstance(entry.get("approval"), dict)
            and entry["approval"].get("policy") == APPROVAL_POLICY
            for entry in verified_items.values()
        )
        verified_meta["approved_variant_alias_count"] = sum(
            isinstance(entry, dict)
            and isinstance(entry.get("approval"), dict)
            and entry["approval"].get("policy") == VARIANT_ALIAS_POLICY
            for entry in verified_items.values()
        )
    review_meta = review_payload.setdefault("_meta", {})
    if isinstance(review_meta, dict):
        review_meta["review_item_count"] = len(review_items)
        review_meta["purpose"] = (
            "Candidates rejected by the Simplified Chinese approval policy; "
            "runtime keeps the original name."
        )
    atomic_write_json(verified_path, verified_payload)
    atomic_write_json(review_path, review_payload)
    return promoted, variant_aliases, not_simplified, suspected_mojibake


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verified", type=Path, default=DEFAULT_BATCH_OUTPUT)
    parser.add_argument("--review", type=Path, default=DEFAULT_REVIEW_OUTPUT)
    parser.add_argument("--approved-csv", type=Path, default=DEFAULT_APPROVED_CSV)
    args = parser.parse_args()
    (
        promoted,
        variant_aliases,
        not_simplified,
        suspected_mojibake,
    ) = promote_simplified_names(
        verified_path=args.verified,
        review_path=args.review,
    )
    approved_total = write_approved_csv(args.verified, args.approved_csv)
    print(f"本次采用简体名称：{promoted} 条")
    print(f"本次录入中文异体名称别名：{variant_aliases} 条")
    print(f"保留原名（非简体中文）：{not_simplified} 条")
    print(f"保留原名（疑似韩文乱码）：{suspected_mojibake} 条")
    print(f"累计已采用清单：{approved_total} 条，{args.approved_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
