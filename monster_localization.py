"""Monster-name localization keyed by stable Ragnarok Monster IDs."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from functools import lru_cache
from typing import Any

from i18n import (
    LangManager,
    SUPPORTED_LANGUAGES,
    get_app_base_dir,
    normalize_language,
)


MONSTER_LOCALE_SUBDIR = os.path.join("lang", "monsters")


def _unique_text(values: list[Any]) -> list[str]:
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


@lru_cache(maxsize=None)
def load_monster_catalog(base_dir: str | None = None) -> dict[int, dict[str, Any]]:
    """Merge cached API records and curated presets into one ID catalog."""

    root = os.path.abspath(base_dir or get_app_base_dir())
    catalog: dict[int, dict[str, Any]] = {}
    cache_dir = os.path.join(root, "data", "monster")
    try:
        cache_names = sorted(os.listdir(cache_dir))
    except OSError:
        cache_names = []

    for filename in cache_names:
        if not filename.endswith(".json"):
            continue
        path = os.path.join(cache_dir, filename)
        try:
            with open(path, "r", encoding="utf-8") as file:
                payload = json.load(file)
            monster_id = int(payload.get("id", os.path.splitext(filename)[0]))
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            continue
        if not isinstance(payload, dict):
            continue
        name = str(payload.get("name", "")).strip()
        dbname = str(payload.get("dbname", "")).strip()
        catalog[monster_id] = {
            "name": name or dbname,
            "dbname": dbname,
            "aliases": _unique_text([name, dbname]),
        }

    preset_path = os.path.join(root, "data", "monsters.json")
    try:
        with open(preset_path, "r", encoding="utf-8") as file:
            presets = json.load(file)
    except (OSError, json.JSONDecodeError):
        presets = []
    if isinstance(presets, list):
        for row in presets:
            if not isinstance(row, dict):
                continue
            try:
                monster_id = int(row.get("id"))
            except (TypeError, ValueError):
                continue
            preset_name = str(row.get("name", "")).strip()
            if not preset_name:
                continue
            existing = catalog.get(monster_id, {})
            catalog[monster_id] = {
                "name": preset_name,
                "dbname": existing.get("dbname", ""),
                "aliases": _unique_text(
                    [
                        preset_name,
                        existing.get("name"),
                        *(existing.get("aliases", []) or []),
                    ]
                ),
            }
    return catalog


def _load_monster_locale_file(path: str) -> dict[int, dict[str, Any]]:
    try:
        with open(path, "r", encoding="utf-8") as file:
            payload = json.load(file)
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    records = payload.get("monsters", payload)
    if not isinstance(records, dict):
        return {}

    translations: dict[int, dict[str, Any]] = {}
    for raw_monster_id, raw_entry in records.items():
        try:
            monster_id = int(raw_monster_id)
        except (TypeError, ValueError):
            continue
        if not isinstance(raw_entry, dict):
            continue
        entry: dict[str, Any] = {}
        name = raw_entry.get("name")
        aliases = raw_entry.get("aliases", [])
        if isinstance(name, str) and name.strip():
            entry["name"] = name.strip()
        if isinstance(aliases, list):
            entry["aliases"] = _unique_text(aliases)
        if entry:
            translations[monster_id] = entry
    return translations


@lru_cache(maxsize=None)
def _load_monster_translations_cached(
    language: str,
    base_dir: str,
) -> dict[int, dict[str, Any]]:
    locale_path = os.path.join(
        base_dir,
        MONSTER_LOCALE_SUBDIR,
        f"{language}.json",
    )
    override_path = os.path.join(
        base_dir,
        MONSTER_LOCALE_SUBDIR,
        f"{language}_overrides.json",
    )
    translations = _load_monster_locale_file(locale_path)
    for monster_id, override in _load_monster_locale_file(override_path).items():
        merged = dict(translations.get(monster_id, {}))
        generated_name = merged.get("name")
        merged.update(override)
        aliases = _unique_text(
            [
                *(merged.get("aliases", []) or []),
                generated_name
                if generated_name != merged.get("name")
                else None,
            ]
        )
        if aliases:
            merged["aliases"] = aliases
        translations[monster_id] = merged
    return translations


def load_monster_translations(
    language: str | None = None,
    *,
    base_dir: str | None = None,
) -> dict[int, dict[str, Any]]:
    language = normalize_language(language or LangManager.current_lang)
    root = os.path.abspath(base_dir or get_app_base_dir())
    return _load_monster_translations_cached(language, root)


def get_localized_monster_name(
    monster_id: object,
    monster_info: Mapping[str, Any] | None = None,
    language: str | None = None,
    *,
    base_dir: str | None = None,
    default: object = "",
) -> str:
    try:
        normalized_monster_id = int(monster_id)
    except (TypeError, ValueError):
        normalized_monster_id = None
    entry = load_monster_translations(language, base_dir=base_dir).get(
        normalized_monster_id,
        {},
    )
    localized_name = str(entry.get("name", "")).strip()
    if localized_name:
        return localized_name
    info = monster_info or {}
    return str(info.get("name", default)).strip()


def build_monster_name_index(
    catalog: Mapping[int, Mapping[str, Any]] | None = None,
    *,
    base_dir: str | None = None,
) -> dict[str, int]:
    root = os.path.abspath(base_dir or get_app_base_dir())
    monsters = catalog or load_monster_catalog(root)
    locale_records = {
        language: load_monster_translations(language, base_dir=root)
        for language in SUPPORTED_LANGUAGES
    }
    index: dict[str, int] = {}
    for raw_monster_id, monster_info in monsters.items():
        try:
            monster_id = int(raw_monster_id)
        except (TypeError, ValueError):
            continue
        names: list[Any] = [
            monster_id,
            f"ID:{monster_id}",
            monster_info.get("name"),
            monster_info.get("dbname"),
            *(monster_info.get("aliases", []) or []),
        ]
        for records in locale_records.values():
            entry = records.get(monster_id, {})
            names.append(entry.get("name"))
            aliases = entry.get("aliases", [])
            if isinstance(aliases, list):
                names.extend(aliases)
        for name in _unique_text(names):
            index.setdefault(name.casefold(), monster_id)
    return index


def resolve_monster_id(
    value: object,
    catalog: Mapping[int, Mapping[str, Any]] | None = None,
    *,
    name_index: Mapping[str, int] | None = None,
    base_dir: str | None = None,
) -> int | None:
    monsters = catalog or load_monster_catalog(base_dir)
    try:
        numeric_id = int(value)
    except (TypeError, ValueError):
        numeric_id = None
    if numeric_id in monsters:
        return numeric_id

    text = str(value or "").strip()
    if not text:
        return None
    index = (
        dict(name_index)
        if name_index is not None
        else build_monster_name_index(monsters, base_dir=base_dir)
    )
    return index.get(text.casefold())


def localize_monster_name(
    name: object,
    language: str | None = None,
    *,
    base_dir: str | None = None,
) -> str:
    text = str(name or "").strip()
    catalog = load_monster_catalog(base_dir)
    monster_id = resolve_monster_id(text, catalog, base_dir=base_dir)
    if monster_id is None:
        return text
    return get_localized_monster_name(
        monster_id,
        catalog.get(monster_id),
        language,
        base_dir=base_dir,
        default=text,
    )


def build_monster_search_text(
    monster_id: int,
    monster_info: Mapping[str, Any],
    *,
    base_dir: str | None = None,
) -> str:
    root = os.path.abspath(base_dir or get_app_base_dir())
    values: list[Any] = [
        monster_id,
        f"ID:{monster_id}",
        monster_info.get("name"),
        monster_info.get("dbname"),
        *(monster_info.get("aliases", []) or []),
    ]
    for language in SUPPORTED_LANGUAGES:
        entry = load_monster_translations(language, base_dir=root).get(
            monster_id,
            {},
        )
        values.append(entry.get("name"))
        aliases = entry.get("aliases", [])
        if isinstance(aliases, list):
            values.extend(aliases)
    return " ".join(_unique_text(values)).casefold()
