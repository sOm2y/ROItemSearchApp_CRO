"""Item-content localization helpers keyed by stable Ragnarok item IDs.

The upstream Lua files remain the source of truth for item IDs, slots and
resource names.  Locale files only override user-facing names/descriptions, so
refreshing upstream game data does not overwrite translations.
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Iterable, Mapping
from typing import Any

from i18n import LangManager, get_app_base_dir, normalize_language


ITEM_LOCALE_SUBDIR = os.path.join("lang", "items")
_ITEM_ID_PATTERN = re.compile(
    r"(?:^|\s)\(?(?:ID\s*[:：]\s*)?(\d+)\)?(?:$|\s)",
    re.IGNORECASE,
)


def get_item_locale_path(
    language: str | None = None,
    *,
    base_dir: str | None = None,
) -> str:
    language = normalize_language(language or LangManager.current_lang)
    root = base_dir or get_app_base_dir()
    return os.path.join(root, ITEM_LOCALE_SUBDIR, f"{language}.json")


def get_item_override_path(
    language: str | None = None,
    *,
    base_dir: str | None = None,
) -> str:
    language = normalize_language(language or LangManager.current_lang)
    root = base_dir or get_app_base_dir()
    return os.path.join(
        root,
        ITEM_LOCALE_SUBDIR,
        f"{language}_overrides.json",
    )


def get_item_verified_path(
    language: str | None = None,
    *,
    base_dir: str | None = None,
) -> str:
    language = normalize_language(language or LangManager.current_lang)
    root = base_dir or get_app_base_dir()
    return os.path.join(
        root,
        ITEM_LOCALE_SUBDIR,
        f"{language}_divine_pride.json",
    )


def _load_item_locale_file(path: str) -> dict[int, dict[str, Any]]:
    try:
        with open(path, "r", encoding="utf-8") as file:
            payload = json.load(file)
    except FileNotFoundError:
        return {}
    except (OSError, json.JSONDecodeError) as error:
        print(f"物品语言包加载失败：{path}，{error}")
        return {}

    if not isinstance(payload, dict):
        return {}

    records = payload.get("items", payload)
    if not isinstance(records, dict):
        return {}

    translations: dict[int, dict[str, Any]] = {}
    for raw_item_id, raw_entry in records.items():
        try:
            item_id = int(raw_item_id)
        except (TypeError, ValueError):
            continue
        if item_id < 0 or not isinstance(raw_entry, dict):
            continue

        entry: dict[str, Any] = {}
        name = raw_entry.get("name")
        if isinstance(name, str) and name.strip():
            entry["name"] = name.strip()

        description = raw_entry.get("description")
        if isinstance(description, list):
            entry["description"] = [str(line) for line in description]

        aliases = raw_entry.get("aliases")
        if isinstance(aliases, list):
            entry["aliases"] = [
                str(alias).strip()
                for alias in aliases
                if str(alias).strip()
            ]

        if entry:
            translations[item_id] = entry

    return translations


def load_item_translations(
    language: str | None = None,
    *,
    base_dir: str | None = None,
) -> dict[int, dict[str, Any]]:
    """Load and validate one item locale file.

    Supported JSON shapes are either ``{"items": {"123": {...}}}`` or a
    direct ``{"123": {...}}`` mapping. Invalid records are ignored so a
    partially edited translation file cannot prevent the app from starting.
    """

    translations = _load_item_locale_file(
        get_item_locale_path(language, base_dir=base_dir)
    )
    verified = _load_item_locale_file(
        get_item_verified_path(language, base_dir=base_dir)
    )
    overrides = _load_item_locale_file(
        get_item_override_path(language, base_dir=base_dir)
    )
    for overlay in (verified, overrides):
        for item_id, override in overlay.items():
            merged = dict(translations.get(item_id, {}))
            prior_name = merged.get("name")
            prior_aliases = merged.get("aliases", [])
            merged.update(override)
            override_aliases = override.get("aliases", [])
            if override.get("name") and prior_name != override.get("name"):
                merged["aliases"] = _unique_text(
                    [
                        *(
                            prior_aliases
                            if isinstance(prior_aliases, list)
                            else []
                        ),
                        prior_name,
                        *(
                            override_aliases
                            if isinstance(override_aliases, list)
                            else []
                        ),
                    ]
                )
            translations[item_id] = merged
    return translations


def _unique_text(values: Iterable[Any]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        folded = text.casefold()
        if not text or folded in seen:
            continue
        seen.add(folded)
        result.append(text)
    return result


def apply_item_localization(
    items: Mapping[int, Mapping[str, Any]],
    language: str | None = None,
    *,
    base_dir: str | None = None,
    translations: Mapping[int, Mapping[str, Any]] | None = None,
) -> dict[int, dict[str, Any]]:
    """Return a localized copy while retaining all original searchable text."""

    language = normalize_language(language or LangManager.current_lang)
    locale_entries = (
        dict(translations)
        if translations is not None
        else load_item_translations(language, base_dir=base_dir)
    )

    localized_items: dict[int, dict[str, Any]] = {}
    localized_count = 0

    for raw_item_id, raw_info in items.items():
        try:
            item_id = int(raw_item_id)
        except (TypeError, ValueError):
            continue
        if not isinstance(raw_info, Mapping):
            continue

        info = dict(raw_info)
        original_name = str(
            info.get("original_name", info.get("name", ""))
        ).strip()
        original_base_name = str(
            info.get("original_base_name", info.get("base_name", original_name))
        ).strip()
        raw_original_description = info.get(
            "original_description",
            info.get("description", []),
        )
        if isinstance(raw_original_description, (list, tuple)):
            original_description = [str(line) for line in raw_original_description]
        else:
            original_description = [str(raw_original_description)]

        info["original_name"] = original_name
        info["original_base_name"] = original_base_name
        info["original_description"] = original_description

        entry = locale_entries.get(item_id, {})
        localized_base_name = str(
            entry.get("name", original_base_name)
        ).strip() or original_base_name
        slot_count = int(info.get("slot", 0) or 0)
        localized_name = (
            f"{localized_base_name} [{slot_count}]"
            if slot_count > 0
            else localized_base_name
        )

        translated_description = entry.get("description")
        if isinstance(translated_description, list):
            description = [str(line) for line in translated_description]
        else:
            description = list(original_description)

        prior_aliases = info.get("search_aliases", [])
        entry_aliases = entry.get("aliases", [])
        info["base_name"] = localized_base_name
        info["name"] = localized_name
        info["description"] = description
        info["search_aliases"] = _unique_text(
            [
                *(prior_aliases if isinstance(prior_aliases, list) else []),
                original_name,
                original_base_name,
                localized_name,
                localized_base_name,
                info.get("kr_name", ""),
                *(entry_aliases if isinstance(entry_aliases, list) else []),
            ]
        )
        info["localized"] = bool(entry)
        if entry:
            localized_count += 1

        localized_items[item_id] = info

    print(
        f"🌐 物品语言覆盖：{language}，"
        f"已翻译 {localized_count}/{len(localized_items)} 笔"
    )
    return localized_items


def build_item_name_index(
    items: Mapping[int, Mapping[str, Any]],
) -> dict[str, list[int]]:
    """Build a case-insensitive name/alias -> item IDs lookup."""

    index: dict[str, list[int]] = {}
    for raw_item_id, info in items.items():
        try:
            item_id = int(raw_item_id)
        except (TypeError, ValueError):
            continue
        if not isinstance(info, Mapping):
            continue

        aliases = info.get("search_aliases", [])
        candidates = [
            info.get("name", ""),
            info.get("base_name", ""),
            info.get("original_name", ""),
            info.get("original_base_name", ""),
            info.get("kr_name", ""),
            *(aliases if isinstance(aliases, list) else []),
        ]
        for candidate in _unique_text(candidates):
            key = candidate.casefold()
            bucket = index.setdefault(key, [])
            if item_id not in bucket:
                bucket.append(item_id)

    return index


def resolve_item_id(
    name_or_id: Any,
    items: Mapping[int, Mapping[str, Any]],
    *,
    name_index: Mapping[str, list[int]] | None = None,
    preferred_ids: Iterable[int] | None = None,
) -> int | None:
    """Resolve localized/original names and explicit IDs to a stable item ID."""

    text = str(name_or_id or "").strip()
    if not text:
        return None

    if text.isdigit():
        direct_id = int(text)
        if direct_id in items:
            return direct_id

    explicit_match = _ITEM_ID_PATTERN.search(text)
    if explicit_match:
        explicit_id = int(explicit_match.group(1))
        if explicit_id in items:
            return explicit_id

    index = name_index or build_item_name_index(items)
    candidates = list(index.get(text.casefold(), []))
    if preferred_ids is not None:
        preferred = set(preferred_ids)
        candidates = [item_id for item_id in candidates if item_id in preferred]

    return candidates[0] if candidates else None


def build_item_search_text(item_id: int, info: Mapping[str, Any]) -> str:
    """Combine localized and original content for the equipment search box."""

    aliases = info.get("search_aliases", [])
    description = info.get("description", [])
    return " ".join(
        str(value)
        for value in [
            item_id,
            info.get("name", ""),
            info.get("base_name", ""),
            info.get("kr_name", ""),
            *(aliases if isinstance(aliases, list) else []),
            *(description if isinstance(description, list) else [description]),
        ]
        if value is not None
    )
