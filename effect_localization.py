"""Display-only localization for parsed equipment effect text.

The parser and calculator intentionally continue using their original stable
keys. Only strings about to be shown in the UI pass through this module.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Iterable

from i18n import LangManager, get_app_base_dir, normalize_language
from skill_localization import localize_skill_references


EFFECT_LOCALE_SUBDIR = os.path.join("lang", "effects")


@lru_cache(maxsize=None)
def _load_effect_locale(
    language: str,
    base_dir: str,
) -> tuple[tuple[tuple[str, str], ...], dict[int, str]]:
    path = os.path.join(
        base_dir,
        EFFECT_LOCALE_SUBDIR,
        f"{language}.json",
    )
    try:
        with open(path, "r", encoding="utf-8") as file:
            payload = json.load(file)
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return (), {}

    if not isinstance(payload, dict):
        return (), {}

    raw_phrases = payload.get("phrases", {})
    phrases: list[tuple[str, str]] = []
    if isinstance(raw_phrases, dict):
        phrases = [
            (str(source), str(target))
            for source, target in raw_phrases.items()
            if str(source) and str(source) != str(target)
        ]
        phrases.sort(key=lambda pair: len(pair[0]), reverse=True)

    raw_characters = payload.get("characters", {})
    characters = {}
    if isinstance(raw_characters, dict):
        characters = {
            ord(str(source)): str(target)
            for source, target in raw_characters.items()
            if len(str(source)) == 1 and str(source) != str(target)
        }

    return tuple(phrases), characters


def localize_effect_text(
    text: object,
    language: str | None = None,
    *,
    base_dir: str | None = None,
) -> str:
    """Localize one parsed-effect display line without changing its raw value."""

    result = localize_skill_references(
        text,
        language,
        base_dir=base_dir,
    )
    language = normalize_language(language or LangManager.current_lang)
    root = os.path.abspath(base_dir or get_app_base_dir())
    phrases, characters = _load_effect_locale(language, root)

    for source, target in phrases:
        result = result.replace(source, target)
    if characters:
        result = result.translate(characters)
    return result


def localize_effect_lines(
    lines: Iterable[object],
    language: str | None = None,
    *,
    base_dir: str | None = None,
) -> list[str]:
    return [
        localize_effect_text(line, language, base_dir=base_dir)
        for line in lines
    ]
