import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SimplifiedUiSurfaceTests(unittest.TestCase):
    def test_damage_and_reduction_panels_localize_before_rendering(self):
        source = (ROOT / "ItemSearchApp.py").read_text(encoding="utf-8")
        self.assertIn(
            "self.generate_highlighted_html(localize_effect_lines(result))",
            source,
        )
        self.assertIn(
            "self.generate_highlighted_html(localize_effect_lines(body_results))",
            source,
        )
        self.assertIn(
            "self.generate_highlighted_html(localize_effect_lines(new_output))",
            source,
        )

    def test_buff_checkboxes_use_localized_display_text(self):
        source = (ROOT / "ItemSearchApp.py").read_text(encoding="utf-8")
        self.assertGreaterEqual(
            source.count('localize_effect_text(f"{data[\'type\']} {name}")'),
            2,
        )
        self.assertIn("localize_effect_text(name)", source)


if __name__ == "__main__":
    unittest.main()
