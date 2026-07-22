"""Skill-name localization keyed by stable Ragnarok Skill IDs."""

from __future__ import annotations

import csv
import json
import os
import re
from collections.abc import Mapping
from functools import lru_cache
from typing import Any

from i18n import (
    LangManager,
    SUPPORTED_LANGUAGES,
    get_app_base_dir,
    normalize_language,
)


SKILL_LOCALE_SUBDIR = os.path.join("lang", "skills")


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


def _load_skill_locale_file(path: str) -> dict[int, dict[str, Any]]:
    try:
        with open(path, "r", encoding="utf-8") as file:
            payload = json.load(file)
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return {}

    if not isinstance(payload, dict):
        return {}
    records = payload.get("skills", payload)
    if not isinstance(records, dict):
        return {}

    translations: dict[int, dict[str, Any]] = {}
    for raw_skill_id, raw_entry in records.items():
        try:
            skill_id = int(raw_skill_id)
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
            translations[skill_id] = entry
    return translations


@lru_cache(maxsize=None)
def _load_skill_translations_cached(
    language: str,
    base_dir: str,
) -> dict[int, dict[str, Any]]:
    locale_path = os.path.join(
        base_dir,
        SKILL_LOCALE_SUBDIR,
        f"{language}.json",
    )
    override_path = os.path.join(
        base_dir,
        SKILL_LOCALE_SUBDIR,
        f"{language}_overrides.json",
    )
    translations = _load_skill_locale_file(locale_path)
    for skill_id, override in _load_skill_locale_file(override_path).items():
        merged = dict(translations.get(skill_id, {}))
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
        translations[skill_id] = merged
    return translations


def load_skill_translations(
    language: str | None = None,
    *,
    base_dir: str | None = None,
) -> dict[int, dict[str, Any]]:
    language = normalize_language(language or LangManager.current_lang)
    root = os.path.abspath(base_dir or get_app_base_dir())
    return _load_skill_translations_cached(language, root)


def get_localized_skill_name(
    skill_id: object,
    skill_info: Mapping[str, Any] | None = None,
    language: str | None = None,
    *,
    base_dir: str | None = None,
    default: object = "",
) -> str:
    try:
        normalized_skill_id = int(skill_id)
    except (TypeError, ValueError):
        normalized_skill_id = None
    entry = load_skill_translations(language, base_dir=base_dir).get(
        normalized_skill_id,
        {},
    )
    localized_name = str(entry.get("name", "")).strip()
    if localized_name:
        return localized_name
    return str((skill_info or {}).get("Name", default)).strip()


def build_localized_skill_map(
    skills: Mapping[int, object],
    skill_details: Mapping[int, Mapping[str, Any]] | None = None,
    language: str | None = None,
    *,
    base_dir: str | None = None,
) -> dict[int, str]:
    result: dict[int, str] = {}
    details = skill_details or {}
    for raw_skill_id, raw_name in skills.items():
        try:
            skill_id = int(raw_skill_id)
        except (TypeError, ValueError):
            continue
        result[skill_id] = get_localized_skill_name(
            skill_id,
            details.get(skill_id),
            language,
            base_dir=base_dir,
            default=raw_name,
        )
    return result


def build_skill_name_index(
    skills: Mapping[int, Mapping[str, Any]],
    *,
    base_dir: str | None = None,
) -> dict[str, int]:
    """Index source names, localized names, codes and numeric IDs."""

    root = os.path.abspath(base_dir or get_app_base_dir())
    locale_records = {
        language: load_skill_translations(language, base_dir=root)
        for language in SUPPORTED_LANGUAGES
    }
    index: dict[str, int] = {}
    for raw_skill_id, skill_info in skills.items():
        try:
            skill_id = int(raw_skill_id)
        except (TypeError, ValueError):
            continue

        names: list[Any] = [
            skill_id,
            f"ID:{skill_id}",
            skill_info.get("Name"),
            skill_info.get("Code"),
        ]
        for records in locale_records.values():
            entry = records.get(skill_id, {})
            names.append(entry.get("name"))
            aliases = entry.get("aliases", [])
            if isinstance(aliases, list):
                names.extend(aliases)
        for name in _unique_text(names):
            index.setdefault(name.casefold(), skill_id)
    return index


def resolve_skill_id(
    value: object,
    skills: Mapping[int, Mapping[str, Any]],
    *,
    name_index: Mapping[str, int] | None = None,
    base_dir: str | None = None,
) -> int | None:
    try:
        numeric_id = int(value)
    except (TypeError, ValueError):
        numeric_id = None
    if numeric_id in skills:
        return numeric_id

    text = str(value or "").strip()
    if not text:
        return None
    index = (
        dict(name_index)
        if name_index is not None
        else build_skill_name_index(skills, base_dir=base_dir)
    )
    return index.get(text.casefold())


def build_skill_search_text(
    skill_id: int,
    skill_info: Mapping[str, Any],
    *,
    base_dir: str | None = None,
) -> str:
    values: list[Any] = [
        skill_id,
        f"ID:{skill_id}",
        skill_info.get("Name"),
        skill_info.get("Code"),
    ]
    root = os.path.abspath(base_dir or get_app_base_dir())
    for language in SUPPORTED_LANGUAGES:
        entry = load_skill_translations(language, base_dir=root).get(skill_id, {})
        values.append(entry.get("name"))
        aliases = entry.get("aliases", [])
        if isinstance(aliases, list):
            values.extend(aliases)
    return " ".join(_unique_text(values)).casefold()


@lru_cache(maxsize=None)
def _load_source_skill_details(base_dir: str) -> dict[int, dict[str, Any]]:
    path = os.path.join(base_dir, "data", "skillneme.csv")
    details: dict[int, dict[str, Any]] = {}
    try:
        with open(path, "r", encoding="utf-8-sig", newline="") as file:
            for row in csv.DictReader(file):
                try:
                    skill_id = int(row.get("ID", ""))
                except (TypeError, ValueError):
                    continue
                details[skill_id] = {
                    "Name": str(row.get("Name", "")).strip(),
                    "Code": str(row.get("Code", "")).strip(),
                }
    except OSError:
        return {}
    return details


@lru_cache(maxsize=None)
def _skill_reference_name_map(
    language: str,
    base_dir: str,
) -> dict[str, str]:
    replacements: dict[str, str] = {}
    for skill_id, skill_info in _load_source_skill_details(base_dir).items():
        source_name = str(skill_info.get("Name", "")).strip()
        localized_name = get_localized_skill_name(
            skill_id,
            skill_info,
            language,
            base_dir=base_dir,
        )
        if source_name and localized_name and source_name != localized_name:
            replacements[source_name] = localized_name
    return replacements


def localize_skill_references(
    text: object,
    language: str | None = None,
    *,
    base_dir: str | None = None,
) -> str:
    """Localize skill names in parser brackets and skill source labels."""

    result = str(text)
    language = normalize_language(language or LangManager.current_lang)
    root = os.path.abspath(base_dir or get_app_base_dir())
    replacements = _skill_reference_name_map(
        language,
        root,
    )
    if not replacements:
        return result

    result = re.sub(
        r"【([^】]+)】",
        lambda match: f"【{replacements.get(match.group(1), match.group(1))}】",
        result,
    )
    return re.sub(
        r"技能：(.+?)(?=\s+Lv\.\d+|\s+←|$)",
        lambda match: f"技能：{replacements.get(match.group(1), match.group(1))}",
        result,
    )
