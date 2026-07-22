import json
import tempfile
import unittest
from pathlib import Path

from item_localization import (
    apply_item_localization,
    build_item_name_index,
    build_item_search_text,
    load_item_translations,
    resolve_item_id,
)


class ItemLocalizationTests(unittest.TestCase):
    def setUp(self):
        self.items = {
            100: {
                "name": "青蘋果頭飾 [1]",
                "base_name": "青蘋果頭飾",
                "kr_name": "Apple_Of_Archer",
                "description": ["遠距離物理傷害+5%。", "^FF0000測試^000000"],
                "slot": 1,
            },
            101: {
                "name": "測試裝備",
                "base_name": "測試裝備",
                "kr_name": "Test_Item",
                "description": [],
                "slot": 0,
            },
        }

    def test_load_and_apply_overlay(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            locale_dir = Path(temp_dir, "lang", "items")
            locale_dir.mkdir(parents=True)
            Path(locale_dir, "zh_CN.json").write_text(
                json.dumps(
                    {
                        "items": {
                            "100": {
                                "name": "青苹果头饰",
                                "description": [
                                    "远距离物理伤害+5%。",
                                    "^FF0000测试^000000",
                                ],
                            }
                        }
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            Path(locale_dir, "zh_CN_overrides.json").write_text(
                json.dumps(
                    {
                        "items": {
                            "100": {
                                "name": "CRO青苹果头饰",
                                "aliases": ["官方苹果头饰"],
                            }
                        }
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            Path(locale_dir, "zh_CN_divine_pride.json").write_text(
                json.dumps(
                    {
                        "items": {
                            "100": {
                                "name": "Divine苹果头饰",
                            }
                        }
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            translations = load_item_translations("zh_CN", base_dir=temp_dir)
            localized = apply_item_localization(
                self.items,
                "zh_CN",
                base_dir=temp_dir,
            )

        self.assertEqual(translations[100]["name"], "CRO青苹果头饰")
        self.assertIn("青苹果头饰", translations[100]["aliases"])
        self.assertIn("Divine苹果头饰", translations[100]["aliases"])
        self.assertEqual(localized[100]["name"], "CRO青苹果头饰 [1]")
        self.assertEqual(localized[100]["original_name"], "青蘋果頭飾 [1]")
        self.assertIn("青蘋果頭飾", localized[100]["search_aliases"])
        self.assertIn("官方苹果头饰", localized[100]["search_aliases"])
        self.assertEqual(
            localized[100]["description"][1],
            "^FF0000测试^000000",
        )
        self.assertEqual(localized[101]["name"], "測試裝備")

    def test_name_index_resolves_localized_original_resource_and_id(self):
        localized = apply_item_localization(
            self.items,
            "zh_CN",
            translations={
                100: {
                    "name": "青苹果头饰",
                    "description": ["远距离物理伤害+5%。"],
                }
            },
        )
        index = build_item_name_index(localized)

        self.assertEqual(resolve_item_id("青苹果头饰 [1]", localized, name_index=index), 100)
        self.assertEqual(resolve_item_id("青蘋果頭飾 [1]", localized, name_index=index), 100)
        self.assertEqual(resolve_item_id("Apple_Of_Archer", localized, name_index=index), 100)
        self.assertEqual(resolve_item_id("ID:100", localized, name_index=index), 100)

    def test_search_text_contains_both_languages(self):
        localized = apply_item_localization(
            self.items,
            "zh_CN",
            translations={
                100: {
                    "name": "青苹果头饰",
                    "description": ["远距离物理伤害+5%。"],
                }
            },
        )
        search_text = build_item_search_text(100, localized[100])
        self.assertIn("青苹果头饰", search_text)
        self.assertIn("青蘋果頭飾", search_text)
        self.assertIn("远距离物理伤害", search_text)


if __name__ == "__main__":
    unittest.main()
