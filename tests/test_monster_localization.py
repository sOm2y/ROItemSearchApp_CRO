import json
import tempfile
import unittest
from pathlib import Path

from monster_localization import (
    build_monster_name_index,
    build_monster_search_text,
    get_localized_monster_name,
    load_monster_catalog,
    load_monster_translations,
    localize_monster_name,
    resolve_monster_id,
)
from i18n import LangManager
from monster_lookup_dialog import MonsterLookupDialog, load_presets


class MonsterLocalizationTests(unittest.TestCase):
    def test_catalog_prefers_curated_name_and_keeps_cache_aliases(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            Path(root, "data", "monster").mkdir(parents=True)
            Path(root, "data", "monster", "21531.json").write_text(
                json.dumps(
                    {
                        "id": 21531,
                        "name": "Aquila",
                        "dbname": "EP19_MD_AQUILA",
                    }
                ),
                encoding="utf-8",
            )
            Path(root, "data", "monsters.json").write_text(
                json.dumps(
                    [{"id": 21531, "name": "阿奎亞"}],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            catalog = load_monster_catalog(temp_dir)

        self.assertEqual(catalog[21531]["name"], "阿奎亞")
        self.assertIn("Aquila", catalog[21531]["aliases"])
        self.assertEqual(catalog[21531]["dbname"], "EP19_MD_AQUILA")

    def test_override_preserves_generated_name_as_alias(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            locale_dir = Path(temp_dir, "lang", "monsters")
            locale_dir.mkdir(parents=True)
            Path(locale_dir, "zh_CN.json").write_text(
                json.dumps(
                    {"monsters": {"22260": {"name": "심연의 살라만다"}}},
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            Path(locale_dir, "zh_CN_overrides.json").write_text(
                json.dumps(
                    {"monsters": {"22260": {"name": "深渊火蜥蜴"}}},
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            translations = load_monster_translations(
                "zh_CN",
                base_dir=temp_dir,
            )

        self.assertEqual(translations[22260]["name"], "深渊火蜥蜴")
        self.assertIn("심연의 살라만다", translations[22260]["aliases"])

    def test_resolves_all_known_name_forms(self):
        catalog = load_monster_catalog()
        index = build_monster_name_index(catalog)
        for value in (
            21531,
            "ID:21531",
            "阿奎亞",
            "阿奎亚",
            "Aquila",
            "EP19_MD_AQUILA",
        ):
            self.assertEqual(
                resolve_monster_id(value, catalog, name_index=index),
                21531,
            )

    def test_localizes_cached_name_and_searches_all_aliases(self):
        catalog = load_monster_catalog()
        self.assertEqual(localize_monster_name("Aquila", "zh_CN"), "阿奎亚")
        self.assertEqual(
            get_localized_monster_name(21531, catalog[21531], "zh_TW"),
            "阿奎亞",
        )
        search_text = build_monster_search_text(21531, catalog[21531])
        for text in ("21531", "ep19_md_aquila", "aquila", "阿奎亞", "阿奎亚"):
            self.assertIn(text, search_text)

    def test_lookup_presets_and_cached_payload_use_localized_name(self):
        original_language = LangManager.current_lang
        try:
            LangManager.load("zh_CN")
            presets = {row["id"]: row["name"] for row in load_presets()}
            self.assertEqual(presets[21531], "阿奎亚")

            cache_path = Path("data", "monster", "21531.json")
            payload = json.loads(cache_path.read_text(encoding="utf-8"))
            parsed = MonsterLookupDialog.parse_monster(None, payload)
            self.assertEqual(parsed["id"], 21531)
            self.assertEqual(parsed["name"], "阿奎亚")
        finally:
            LangManager.load(original_language)


if __name__ == "__main__":
    unittest.main()
