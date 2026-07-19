#!/usr/bin/env python3
"""Validate language-pack coverage and formatting placeholders."""

from __future__ import annotations

import ast
import json
import string
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LANG_DIR = ROOT / "lang"
REQUIRED_LANGUAGES = ("zh_CN", "zh_TW", "en_US")


def load_json_with_duplicate_check(path: Path) -> tuple[dict[str, str], list[str]]:
    duplicates: list[str] = []

    def object_pairs_hook(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                duplicates.append(key)
            result[key] = value
        return result

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file, object_pairs_hook=object_pairs_hook)
    if not isinstance(data, dict):
        raise ValueError("language pack root must be a JSON object")
    return data, duplicates


def collect_used_keys() -> set[str]:
    keys: set[str] = set()
    for path in ROOT.rglob("*.py"):
        if any(
            part in {
                ".git",
                ".venv",
                "venv",
                "env",
                "__pycache__",
                "data",
            }
            for part in path.parts
        ):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                value = node.value
                is_translation_map = any(
                    isinstance(target, ast.Name)
                    and target.id.endswith("_TRANSLATION_KEYS")
                    for target in targets
                )
                if is_translation_map and isinstance(value, ast.Dict):
                    keys.update(
                        item.value
                        for item in value.values
                        if isinstance(item, ast.Constant)
                        and isinstance(item.value, str)
                    )
                continue
            if not isinstance(node, ast.Call) or not node.args:
                continue
            func_name = ""
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                func_name = node.func.attr
            if func_name != "tr":
                continue
            first_arg = node.args[0]
            if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                keys.add(first_arg.value)
    return keys


def placeholders(value: str) -> set[str]:
    names = set()
    for _, field_name, _, _ in string.Formatter().parse(value):
        if field_name:
            names.add(field_name.split(".", 1)[0].split("[", 1)[0])
    return names


def main() -> int:
    errors: list[str] = []
    packs: dict[str, dict[str, str]] = {}

    for language in REQUIRED_LANGUAGES:
        path = LANG_DIR / f"{language}.json"
        if not path.exists():
            errors.append(f"missing language pack: {path.relative_to(ROOT)}")
            continue
        try:
            pack, duplicates = load_json_with_duplicate_check(path)
        except (OSError, json.JSONDecodeError, ValueError) as error:
            errors.append(f"{path.relative_to(ROOT)}: {error}")
            continue
        packs[language] = pack
        if duplicates:
            errors.append(
                f"{path.relative_to(ROOT)} has duplicate keys: "
                + ", ".join(sorted(set(duplicates)))
            )
        invalid_values = sorted(
            key for key, value in pack.items() if not isinstance(value, str)
        )
        if invalid_values:
            errors.append(
                f"{path.relative_to(ROOT)} has non-string values: "
                + ", ".join(invalid_values)
            )

    if not packs:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    reference_language = "zh_CN" if "zh_CN" in packs else next(iter(packs))
    reference_keys = set(packs[reference_language])
    for language, pack in packs.items():
        keys = set(pack)
        missing = sorted(reference_keys - keys)
        extra = sorted(keys - reference_keys)
        if missing:
            errors.append(f"{language} missing keys: {', '.join(missing)}")
        if extra:
            errors.append(f"{language} has extra keys: {', '.join(extra)}")

    used_keys = collect_used_keys()
    for language, pack in packs.items():
        missing_used = sorted(used_keys - set(pack))
        if missing_used:
            errors.append(
                f"{language} missing keys used by Python: {', '.join(missing_used)}"
            )

    for key in sorted(reference_keys):
        expected = placeholders(packs[reference_language][key])
        for language, pack in packs.items():
            if key not in pack:
                continue
            actual = placeholders(pack[key])
            if actual != expected:
                errors.append(
                    f"{language}:{key} placeholders {sorted(actual)} "
                    f"do not match {reference_language} {sorted(expected)}"
                )

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print(
        f"i18n OK: {len(reference_keys)} keys, "
        f"{len(used_keys)} keys referenced by Python, "
        f"{len(packs)} language packs"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
