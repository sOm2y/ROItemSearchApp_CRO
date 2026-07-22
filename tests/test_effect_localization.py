import unittest

from effect_localization import localize_effect_lines, localize_effect_text


class EffectLocalizationTests(unittest.TestCase):
    def test_simplified_chinese_localizes_display_text(self):
        raw = "受到遠距離物理傷害 -5%  ← 〔套裝來源〕"
        localized = localize_effect_text(raw, "zh_CN")

        self.assertEqual(
            localized,
            "受到远距离物理伤害 -5%  ← 〔套装来源〕",
        )
        self.assertEqual(raw, "受到遠距離物理傷害 -5%  ← 〔套裝來源〕")

    def test_parser_identifiers_and_numbers_are_preserved(self):
        raw = "bonus2 bAddRace,RC_DemiHuman,15;"
        self.assertEqual(
            localize_effect_text(raw, "zh_CN"),
            raw,
        )

    def test_other_languages_are_unchanged_without_effect_locale(self):
        raw = "完全迴避 +10"
        self.assertEqual(localize_effect_text(raw, "zh_TW"), raw)
        self.assertEqual(localize_effect_text(raw, "en_US"), raw)

    def test_localizes_multiple_lines(self):
        self.assertEqual(
            localize_effect_lines(
                [
                    "完全迴避 +10",
                    "攻擊後延遲 -5%",
                    "受到物理傷害 -3%",
                ],
                "zh_CN",
            ),
            [
                "完全回避 +10",
                "攻击后延迟 -5%",
                "受到物理伤害 -3%",
            ],
        )


if __name__ == "__main__":
    unittest.main()
