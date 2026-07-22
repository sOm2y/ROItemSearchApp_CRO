#!/usr/bin/env python3
"""Validate the generated Item ID localization overlay."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATHS = (
    ROOT / "data" / "iteminfo_new.lua",
    ROOT / "data" / "User_iteminfo_new.lua",
)
LOCALE_PATH = ROOT / "lang" / "items" / "zh_CN.json"
VERIFIED_PATH = ROOT / "lang" / "items" / "zh_CN_divine_pride.json"
REVIEW_PATH = ROOT / "lang" / "items" / "zh_CN_divine_pride_review.json"
OVERRIDE_PATH = ROOT / "lang" / "items" / "zh_CN_overrides.json"
ITEM_ENTRY_RE = re.compile(
    r"\[(\d+)\]\s*=\s*{(.*?)}(?=,\s*\[\d+\]|\s*\[\d+\]|\s*$)",
    re.DOTALL,
)
NAME_RE = re.compile(r'(?<!un)identifiedDisplayName\s*=\s*"([^"]+)"')
RESOURCE_RE = re.compile(r'(?<!un)identifiedResourceName\s*=\s*"([^"]*)"')
SLOT_RE = re.compile(r"slotCount\s*=\s*(\d+)")
DESCRIPTION_RE = re.compile(
    r"(?<!un)identifiedDescriptionName\s*=\s*{(.*?)}",
    re.DOTALL,
)
QUOTED_TEXT_RE = re.compile(r'"([^"]*)"')
PROTECTED_TOKEN_RE = re.compile(
    r"\^[0-9A-Fa-f]{6}|</?[A-Z][A-Z0-9_]*(?:\s[^>]*)?>|\\[nrt]"
)
INVALID_VERIFIED_NAME_RE = re.compile(
    r"^(?:\(null\)|null|item name|\[ph\]\s*item name)$",
    re.IGNORECASE,
)


def parse_source_items() -> dict[int, dict[str, object]]:
    result: dict[int, dict[str, object]] = {}
    for source_path in SOURCE_PATHS:
        content = source_path.read_text(encoding="utf-8")
        for raw_item_id, body in ITEM_ENTRY_RE.findall(content):
            name_match = NAME_RE.search(body)
            if not name_match or not RESOURCE_RE.search(body) or not SLOT_RE.search(body):
                continue
            description_match = DESCRIPTION_RE.search(body)
            result[int(raw_item_id)] = {
                "name": name_match.group(1).strip(),
                "description": (
                    QUOTED_TEXT_RE.findall(description_match.group(1))
                    if description_match
                    else []
                ),
            }
    return result


def protected_tokens(entry: dict[str, object]) -> list[str]:
    description = entry.get("description", [])
    text = str(entry.get("name", "")) + "\n" + "\n".join(
        str(line)
        for line in description
    )
    return PROTECTED_TOKEN_RE.findall(text)


def main() -> int:
    errors: list[str] = []
    try:
        payload = json.loads(LOCALE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(f"ERROR: {LOCALE_PATH.relative_to(ROOT)}: {error}")
        return 1

    if not isinstance(payload, dict) or not isinstance(payload.get("items"), dict):
        print("ERROR: item locale root must contain an items object")
        return 1

    source_items = parse_source_items()
    locale_items = payload["items"]
    try:
        verified_payload = json.loads(
            VERIFIED_PATH.read_text(encoding="utf-8")
        )
        verified_items = verified_payload.get("items", {})
        if not isinstance(verified_items, dict):
            raise ValueError("items must be an object")
    except (OSError, json.JSONDecodeError, ValueError) as error:
        errors.append(f"{VERIFIED_PATH.relative_to(ROOT)}: {error}")
        verified_items = {}
    try:
        review_payload = json.loads(REVIEW_PATH.read_text(encoding="utf-8"))
        review_items = review_payload.get("items", {})
        if not isinstance(review_items, dict):
            raise ValueError("items must be an object")
    except (OSError, json.JSONDecodeError, ValueError) as error:
        errors.append(f"{REVIEW_PATH.relative_to(ROOT)}: {error}")
        review_items = {}
    try:
        override_payload = json.loads(OVERRIDE_PATH.read_text(encoding="utf-8"))
        override_items = override_payload.get("items", {})
        if not isinstance(override_items, dict):
            raise ValueError("items must be an object")
    except (OSError, json.JSONDecodeError, ValueError) as error:
        errors.append(f"{OVERRIDE_PATH.relative_to(ROOT)}: {error}")
        override_items = {}

    effective_items = {
        str(item_id): dict(entry)
        for item_id, entry in source_items.items()
    }
    for raw_item_id, entry in locale_items.items():
        if not isinstance(entry, dict):
            errors.append(f"item {raw_item_id} translation must be an object")
            continue
        merged = dict(effective_items.get(str(raw_item_id), {}))
        merged.update(entry)
        effective_items[str(raw_item_id)] = merged
    for raw_item_id, verified in verified_items.items():
        if not isinstance(verified, dict):
            errors.append(
                f"verified item {raw_item_id} must be an object"
            )
            continue
        source = verified.get("source", {})
        fields = source.get("fields", []) if isinstance(source, dict) else []
        if (
            not isinstance(source, dict)
            or source.get("provider") != "Divine Pride"
            or str(source.get("server", "")).casefold() != "cro"
            or not isinstance(fields, list)
            or "name" not in fields
        ):
            errors.append(
                f"verified item {raw_item_id} has invalid source metadata"
            )
        verified_name = str(verified.get("name", "")).strip()
        if not verified_name or INVALID_VERIFIED_NAME_RE.fullmatch(
            verified_name
        ):
            errors.append(
                f"verified item {raw_item_id} has invalid placeholder name"
            )
        base_translation = locale_items.get(raw_item_id, {})
        base_name = (
            str(base_translation.get("name", "")).strip()
            if isinstance(base_translation, dict)
            else ""
        )
        approval = verified.get("approval", {})
        is_approved_difference = (
            isinstance(approval, dict)
            and approval.get("policy") in {
                "user_approved_simplified_chinese",
                "user_approved_chinese_variant_alias",
            }
            and bool(str(approval.get("approved_at", "")).strip())
        )
        if base_name and verified_name != base_name and not is_approved_difference:
            errors.append(
                f"verified item {raw_item_id} changes runtime name "
                "without manual approval"
            )
        merged = dict(effective_items.get(str(raw_item_id), {}))
        merged.update(verified)
        effective_items[str(raw_item_id)] = merged
    overlap = set(verified_items) & set(review_items)
    if overlap:
        errors.append(
            f"{len(overlap)} item IDs exist in both verified and review layers"
        )
    for raw_item_id, review in review_items.items():
        if not isinstance(review, dict):
            errors.append(f"review item {raw_item_id} must be an object")
            continue
        try:
            item_id = int(raw_item_id)
        except (TypeError, ValueError):
            errors.append(f"invalid review item ID: {raw_item_id!r}")
            continue
        if item_id not in source_items:
            errors.append(f"review item {item_id} does not exist in source")
        local_name = str(review.get("local_name", "")).strip()
        candidate_name = str(review.get("candidate_name", "")).strip()
        reasons = review.get("reasons", [])
        source = review.get("source", {})
        fields = source.get("fields", []) if isinstance(source, dict) else []
        if not candidate_name:
            errors.append(f"review item {item_id} has an empty candidate name")
        if not isinstance(reasons, list) or not reasons:
            errors.append(f"review item {item_id} has no reasons")
        elif not local_name and "missing_local_name" not in reasons:
            errors.append(
                f"review item {item_id} has an unmarked missing local name"
            )
        if (
            not isinstance(source, dict)
            or source.get("provider") != "Divine Pride"
            or str(source.get("server", "")).casefold() != "cro"
            or not isinstance(fields, list)
            or "name" not in fields
        ):
            errors.append(f"review item {item_id} has invalid source metadata")
    for raw_item_id, override in override_items.items():
        if not isinstance(override, dict):
            errors.append(f"override item {raw_item_id} must be an object")
            continue
        merged = dict(effective_items.get(str(raw_item_id), {}))
        merged.update(override)
        effective_items[str(raw_item_id)] = merged

    for raw_item_id, entry in effective_items.items():
        try:
            item_id = int(raw_item_id)
        except (TypeError, ValueError):
            errors.append(f"invalid item ID: {raw_item_id!r}")
            continue
        if item_id not in source_items:
            errors.append(f"item {item_id} does not exist in source")
            continue
        if not isinstance(entry, dict):
            errors.append(f"item {item_id} translation must be an object")
            continue
        if not isinstance(entry.get("name"), str) or not entry["name"].strip():
            errors.append(f"item {item_id} has invalid name")
        if not isinstance(entry.get("description"), list) or any(
            not isinstance(line, str)
            for line in entry.get("description", [])
        ):
            errors.append(f"item {item_id} has invalid description")
            continue
        if protected_tokens(entry) != protected_tokens(source_items[item_id]):
            errors.append(f"item {item_id} changed protected color/markup tokens")

    meta = payload.get("_meta", {})
    if isinstance(meta, dict):
        expected_source_count = meta.get("source_item_count")
        expected_translated_count = meta.get("translated_item_count")
        if expected_source_count != len(source_items):
            errors.append(
                f"source_item_count is {expected_source_count}, "
                f"expected {len(source_items)}"
            )
        if expected_translated_count != len(locale_items):
            errors.append(
                f"translated_item_count is {expected_translated_count}, "
                f"expected {len(locale_items)}"
            )
    else:
        errors.append("_meta must be an object")

    if errors:
        for error in errors[:100]:
            print(f"ERROR: {error}")
        if len(errors) > 100:
            print(f"ERROR: and {len(errors) - 100} more")
        return 1

    print(
        f"item localization OK: {len(locale_items)} translated records, "
        f"{len(verified_items)} Divine Pride verified records, "
        f"{len(review_items)} name candidates pending review, "
        f"{len(override_items)} manual overrides, "
        f"{len(source_items)} source records"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
