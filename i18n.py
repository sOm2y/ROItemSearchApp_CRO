"""Shared JSON-based localization helpers.

UI modules should import ``tr`` from this module instead of importing the main
window. The selected language is read once during import, before any Qt widgets
are created.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any


DEFAULT_LANGUAGE = "zh_CN"
FALLBACK_LANGUAGE = "zh_TW"
SUPPORTED_LANGUAGES = {
    "zh_CN": "简体中文",
    "zh_TW": "繁體中文",
    "en_US": "English",
}


def get_app_base_dir() -> str:
    """Return the source directory or the directory containing the frozen app."""
    # The main application launches a temporary copy of update.exe so the
    # installed updater can also be replaced. Keep translations/config rooted
    # in the actual installation directory while that temporary copy runs.
    override = os.environ.get("ROITEMSEARCHAPP_BASE_DIR", "").strip()
    if override:
        return os.path.abspath(override)
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def get_config_path() -> str:
    return os.path.join(get_app_base_dir(), "data", "config.json")


def normalize_language(language: Any, default: str = DEFAULT_LANGUAGE) -> str:
    code = str(language or "").strip()
    if code in SUPPORTED_LANGUAGES:
        return code
    return default if default in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE


def load_language_from_config(default: str = DEFAULT_LANGUAGE) -> str:
    try:
        with open(get_config_path(), "r", encoding="utf-8") as file:
            config = json.load(file)
        if isinstance(config, dict):
            return normalize_language(config.get("language"), default)
    except (OSError, json.JSONDecodeError, TypeError):
        pass
    return normalize_language(default)


class LangManager:
    current_lang = DEFAULT_LANGUAGE
    fallback_lang = FALLBACK_LANGUAGE
    translations: dict[str, str] = {}
    fallback_translations: dict[str, str] = {}

    @classmethod
    def _read_lang_file(cls, lang_code: str) -> dict[str, str]:
        path = os.path.join(get_app_base_dir(), "lang", f"{lang_code}.json")
        try:
            with open(path, "r", encoding="utf-8") as file:
                data = json.load(file)
            return data if isinstance(data, dict) else {}
        except (OSError, json.JSONDecodeError) as error:
            print(f"语言包加载失败：{path}，{error}")
            return {}

    @classmethod
    def load(cls, lang_code: str | None = None) -> str:
        cls.current_lang = normalize_language(lang_code)
        cls.fallback_translations = cls._read_lang_file(cls.fallback_lang)
        cls.translations = cls._read_lang_file(cls.current_lang)
        return cls.current_lang

    @classmethod
    def tr(cls, key: str, default: str | None = None, **kwargs: Any) -> str:
        text = cls.translations.get(
            key,
            cls.fallback_translations.get(
                key,
                default if default is not None else key,
            ),
        )
        if not isinstance(text, str):
            text = str(text)
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            return text


def tr(key: str, default: str | None = None, **kwargs: Any) -> str:
    return LangManager.tr(key, default, **kwargs)


EQUIPMENT_PART_TRANSLATION_KEYS = {
    "頭上": "equipment_part.head_top",
    "頭中": "equipment_part.head_middle",
    "頭下": "equipment_part.head_lower",
    "鎧甲": "equipment_part.armor",
    "右手(武器)": "equipment_part.right_hand_weapon",
    "投擲物品": "equipment_part.throwable",
    "左手(盾牌)": "equipment_part.left_hand_shield",
    "披肩": "equipment_part.garment",
    "鞋子": "equipment_part.shoes",
    "飾品右": "equipment_part.accessory_right",
    "飾品左": "equipment_part.accessory_left",
    "影子鎧甲": "equipment_part.shadow_armor",
    "影子手套": "equipment_part.shadow_glove",
    "影子盾牌": "equipment_part.shadow_shield",
    "影子鞋子": "equipment_part.shadow_shoes",
    "影子耳環右": "equipment_part.shadow_earring_right",
    "影子墬子左": "equipment_part.shadow_pendant_left",
    "服飾頭上": "equipment_part.costume_head_top",
    "服飾頭中": "equipment_part.costume_head_middle",
    "服飾頭下": "equipment_part.costume_head_lower",
    "服飾斗篷": "equipment_part.costume_garment",
    "符文石碑": "equipment_part.rune_tablet",
    "寵物蛋": "equipment_part.pet_egg",
    "技能": "equipment_part.skill",
}


def translate_equipment_part(part_name: Any) -> str:
    """Translate a stable equipment-part key without changing stored data."""
    key = EQUIPMENT_PART_TRANSLATION_KEYS.get(part_name)
    return tr(key, str(part_name)) if key else str(part_name)


LangManager.load(load_language_from_config())
