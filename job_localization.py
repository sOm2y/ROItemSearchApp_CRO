"""Job-name localization keyed by stable Ragnarok Job IDs."""

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


JOB_LOCALE_SUBDIR = os.path.join("lang", "jobs")


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
def _load_job_translations_cached(
    language: str,
    base_dir: str,
) -> dict[int, dict[str, Any]]:
    path = os.path.join(
        base_dir,
        JOB_LOCALE_SUBDIR,
        f"{language}.json",
    )
    try:
        with open(path, "r", encoding="utf-8") as file:
            payload = json.load(file)
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return {}

    if not isinstance(payload, dict):
        return {}
    records = payload.get("jobs", payload)
    if not isinstance(records, dict):
        return {}

    translations: dict[int, dict[str, Any]] = {}
    for raw_job_id, raw_entry in records.items():
        try:
            job_id = int(raw_job_id)
        except (TypeError, ValueError):
            continue
        if not isinstance(raw_entry, dict):
            continue

        name = raw_entry.get("name")
        aliases = raw_entry.get("aliases", [])
        entry: dict[str, Any] = {}
        if isinstance(name, str) and name.strip():
            entry["name"] = name.strip()
        if isinstance(aliases, list):
            entry["aliases"] = _unique_text(aliases)
        if entry:
            translations[job_id] = entry
    return translations


def load_job_translations(
    language: str | None = None,
    *,
    base_dir: str | None = None,
) -> dict[int, dict[str, Any]]:
    language = normalize_language(language or LangManager.current_lang)
    root = os.path.abspath(base_dir or get_app_base_dir())
    return _load_job_translations_cached(language, root)


def get_localized_job_name(
    job_id: object,
    job_info: Mapping[str, Any] | None = None,
    language: str | None = None,
    *,
    base_dir: str | None = None,
) -> str:
    try:
        normalized_job_id = int(job_id)
    except (TypeError, ValueError):
        normalized_job_id = None
    entry = load_job_translations(language, base_dir=base_dir).get(
        normalized_job_id,
        {},
    )
    localized_name = str(entry.get("name", "")).strip()
    if localized_name:
        return localized_name
    return str((job_info or {}).get("name", "")).strip()


def build_job_name_index(
    jobs: Mapping[int, Mapping[str, Any]],
    *,
    base_dir: str | None = None,
) -> dict[str, int]:
    """Build an index accepting IDs, source names and every installed locale."""

    root = os.path.abspath(base_dir or get_app_base_dir())
    locale_records = {
        language: load_job_translations(language, base_dir=root)
        for language in SUPPORTED_LANGUAGES
    }
    index: dict[str, int] = {}

    for raw_job_id, job_info in jobs.items():
        try:
            job_id = int(raw_job_id)
        except (TypeError, ValueError):
            continue
        names: list[Any] = [
            job_id,
            f"ID:{job_id}",
            job_info.get("name"),
            job_info.get("id_jobneme"),
        ]
        for records in locale_records.values():
            entry = records.get(job_id, {})
            names.append(entry.get("name"))
            aliases = entry.get("aliases", [])
            if isinstance(aliases, list):
                names.extend(aliases)

        for name in _unique_text(names):
            index.setdefault(name.casefold(), job_id)
    return index


def resolve_job_id(
    value: object,
    jobs: Mapping[int, Mapping[str, Any]],
    *,
    name_index: Mapping[str, int] | None = None,
    base_dir: str | None = None,
) -> int | None:
    try:
        numeric_id = int(value)
    except (TypeError, ValueError):
        numeric_id = None
    if numeric_id in jobs:
        return numeric_id

    text = str(value or "").strip()
    if not text:
        return None
    index = (
        dict(name_index)
        if name_index is not None
        else build_job_name_index(jobs, base_dir=base_dir)
    )
    return index.get(text.casefold())
