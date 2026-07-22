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

    def test_screenshot_damage_and_buff_text_is_simplified(self):
        source_lines = [
            "================角色防禦================",
            "受到體型物理傷害: 0%",
            "後段物理減免後傷害: 90% (數字越少傷害越低。)",
            "物理種族: 98%",
            "無視階級防禦: 70%",
            "技能增傷(裝備段): 61%",
            "技能 天使之賜福",
            "技能 加速術",
            "技能 堅毅信念",
            "技能 真誠信念",
            "料理 靈巧料理",
            "料理 幸運料理",
            "料理 萬能年糕",
            "料理 活力激發劑",
            "料理 力量棒棒條",
        ]

        localized = localize_effect_lines(source_lines, "zh_CN")

        self.assertEqual(
            localized,
            [
                "================角色防御================",
                "受到体型物理伤害: 0%",
                "后段物理减免后伤害: 90% (数字越少伤害越低。)",
                "物理种族: 98%",
                "无视阶级防御: 70%",
                "技能增伤(装备段): 61%",
                "技能 天使之赐福",
                "技能 加速术",
                "技能 坚毅信念",
                "技能 真诚信念",
                "料理 灵巧料理",
                "料理 幸运料理",
                "料理 万能年糕",
                "料理 活力激发剂",
                "料理 力量棒棒条",
            ],
        )


if __name__ == "__main__":
    unittest.main()
