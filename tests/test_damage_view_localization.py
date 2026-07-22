import unittest

from PySide6.QtCore import Qt

from Damage_view import (
    DAMAGE_STEP_TRANSLATION_KEYS,
    Step,
    StepModel,
    apply_round,
    localize_damage_step_name,
)
from i18n import LangManager


class DamageViewLocalizationTests(unittest.TestCase):
    def setUp(self):
        self.original_language = LangManager.current_lang

    def tearDown(self):
        LangManager.load(self.original_language)

    def test_every_damage_step_key_exists_in_all_language_packs(self):
        for language in ("zh_CN", "zh_TW", "en_US"):
            LangManager.load(language)
            missing = set(DAMAGE_STEP_TRANSLATION_KEYS.values()) - set(
                LangManager.translations
            )
            self.assertEqual(missing, set(), language)

    def test_step_display_changes_without_mutating_stable_name(self):
        step = Step("體型%", 25)
        model = StepModel([step])

        LangManager.load("zh_CN")
        self.assertEqual(localize_damage_step_name(step.name), "体型%")
        self.assertEqual(
            model.data(model.index(0, 0), Qt.DisplayRole)[0],
            "體型%",
        )

        LangManager.load("en_US")
        self.assertEqual(localize_damage_step_name(step.name), "Size damage%")
        self.assertEqual(step.name, "體型%")

    def test_unknown_step_name_is_preserved(self):
        LangManager.load("zh_CN")
        self.assertEqual(localize_damage_step_name("自定义步骤"), "自定义步骤")

    def test_calculation_still_uses_stable_step_keys(self):
        self.assertEqual(apply_round(1000, 25, "INT", "MDEF減算"), 975)
        self.assertEqual(apply_round(1000, 50, "INT", "ATK%"), 1050)
        self.assertEqual(apply_round(1000, 250, "INT", "總傷害"), 2500)


if __name__ == "__main__":
    unittest.main()
