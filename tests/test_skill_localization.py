import json
import tempfile
import unittest
from pathlib import Path

from skill_localization import (
    build_localized_skill_map,
    build_skill_name_index,
    build_skill_search_text,
    get_localized_skill_name,
    load_skill_translations,
    localize_skill_references,
    resolve_skill_id,
)


class SkillLocalizationTests(unittest.TestCase):
    def setUp(self):
        self.skills = {
            5: {"Name": "狂擊", "Code": "SM_BASH"},
            28: {"Name": "治癒術", "Code": "AL_HEAL"},
        }

    def test_loads_overlay_and_manual_override(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            locale_dir = Path(temp_dir, "lang", "skills")
            locale_dir.mkdir(parents=True)
            Path(locale_dir, "zh_CN.json").write_text(
                json.dumps(
                    {"skills": {"5": {"name": "狂击"}, "28": {"name": "治愈术"}}},
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            Path(locale_dir, "zh_CN_overrides.json").write_text(
                json.dumps(
                    {"skills": {"28": {"name": "治疗术", "aliases": ["恢复术"]}}},
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            translations = load_skill_translations(
                "zh_CN",
                base_dir=temp_dir,
            )

        self.assertEqual(translations[5]["name"], "狂击")
        self.assertEqual(translations[28]["name"], "治疗术")
        self.assertIn("治愈术", translations[28]["aliases"])
        self.assertIn("恢复术", translations[28]["aliases"])

    def test_localized_map_does_not_mutate_source(self):
        localized = build_localized_skill_map(
            {5: "狂擊", 28: "治癒術"},
            self.skills,
            "zh_CN",
        )

        self.assertEqual(localized[5], "狂击")
        self.assertEqual(self.skills[5]["Name"], "狂擊")

    def test_resolves_id_code_and_names_across_languages(self):
        index = build_skill_name_index(self.skills)
        self.assertEqual(resolve_skill_id(5, self.skills, name_index=index), 5)
        self.assertEqual(resolve_skill_id("ID:5", self.skills, name_index=index), 5)
        self.assertEqual(resolve_skill_id("SM_BASH", self.skills, name_index=index), 5)
        self.assertEqual(resolve_skill_id("狂擊", self.skills, name_index=index), 5)
        self.assertEqual(resolve_skill_id("狂击", self.skills, name_index=index), 5)

    def test_search_text_contains_id_code_and_both_chinese_names(self):
        text = build_skill_search_text(5, self.skills[5])
        self.assertIn("5", text)
        self.assertIn("sm_bash", text)
        self.assertIn("狂擊", text)
        self.assertIn("狂击", text)

    def test_other_language_falls_back_to_source(self):
        self.assertEqual(
            get_localized_skill_name(5, self.skills[5], "zh_TW"),
            "狂擊",
        )

    def test_localizes_parser_skill_references(self):
        self.assertEqual(
            localize_skill_references(
                "技能【狂擊】傷害 +10% ← 技能：治癒術 Lv.10",
                "zh_CN",
            ),
            "技能【狂击】傷害 +10% ← 技能：治愈术 Lv.10",
        )


if __name__ == "__main__":
    unittest.main()
