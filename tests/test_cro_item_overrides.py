import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def equipment_block(item_id: int) -> str:
    content = (ROOT / "data" / "User_EquipmentProperties.lua").read_text(encoding="utf-8")
    match = re.search(rf"\[{item_id}\]\s*=\s*{{", content)
    if not match:
        raise AssertionError(f"missing equipment override for {item_id}")
    next_match = re.search(r"\n\s*\[\d+\]\s*=\s*{", content[match.end():])
    end = match.end() + next_match.start() if next_match else len(content)
    return content[match.start():end]


class CroItemOverrideTests(unittest.TestCase):
    def test_month_charms_are_available_as_custom_items(self):
        content = (ROOT / "data" / "User_iteminfo_new.lua").read_text(encoding="utf-8")
        self.assertIn('[490384] = {', content)
        self.assertIn('identifiedDisplayName = "月之护符"', content)
        self.assertIn('identifiedDisplayName = "月之护符-LT"', content)
        self.assertIn('"[A阶级]对全属性对象的物理/魔法伤害+15%。"', content)
        self.assertIn('slotCount = 1', content)

    def test_month_charm_effects_cover_refine_and_grade_rules(self):
        normal = equipment_block(490384)
        self.assertIn("AddExtParam(0, 41, 50)", normal)
        self.assertIn("AddExtParam(0, 200, 50)", normal)
        self.assertIn("RaceAddDamage(9999, 10)", normal)
        self.assertIn("AddMdamage_Race(9999, 10)", normal)

        lt = equipment_block(491073)
        self.assertIn("temp2 = math.floor(temp / 4)", lt)
        self.assertIn("AddMeleeAttackDamage(1, temp2 * 5)", lt)
        self.assertIn("if 11 < temp then", lt)
        self.assertIn("AddDamage_SKID(1, 2449, 30)", lt)
        self.assertIn("if 2 < tempGrade and 199 < get(11) then", lt)
        self.assertIn("AddDamage_SKID(1, 5328, 30)", lt)
        self.assertIn("AddDamage_SKID(1, 5409, 25)", lt)
        self.assertIn("SubSpellDelay(5)", lt)
        self.assertIn("AddDamage_Property(1, 10, 15)", lt)
        self.assertIn("AddMDamage_Property(1, 10, 15)", lt)

    def test_magic_star_uses_cro_attribute_scaling(self):
        block = equipment_block(19393)
        self.assertIn("SubSpellCastTime(5)", block)
        expected = {
            0: "temp1",
            4: "temp2",
            1: "temp4",
            3: "temp3",
            2: "temp5",
            6: "temp6",
        }
        for element, variable in expected.items():
            self.assertIn(
                f"AddSkillMDamage({element}, math.floor({variable} / 12) * 2)",
                block,
            )

    def test_simplified_chinese_overrides_include_cro_descriptions(self):
        payload = json.loads(
            (ROOT / "lang" / "items" / "zh_CN_overrides.json").read_text(encoding="utf-8")
        )
        items = payload["items"]
        self.assertEqual(items["490384"]["name"], "月之护符")
        self.assertEqual(items["491073"]["name"], "月之护符-LT")
        self.assertIn("ATK+50，MATK+50。", items["490384"]["description"])
        self.assertTrue(any("BaseLv200以上" in line for line in items["491073"]["description"]))
        self.assertTrue(any("净STR每+12时" in line for line in items["19393"]["description"]))
        for item_id in ("19393", "490384", "491073"):
            self.assertEqual(items[item_id]["source"]["server"], "cRO")
            self.assertIn("description", items[item_id]["source"]["fields"])


if __name__ == "__main__":
    unittest.main()
