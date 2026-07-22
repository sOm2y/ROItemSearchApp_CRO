import json
import tempfile
import unittest
from pathlib import Path

from job_localization import (
    build_job_name_index,
    get_localized_job_name,
    load_job_translations,
    resolve_job_id,
)
from data.job_dict import job_dict


class JobLocalizationTests(unittest.TestCase):
    def setUp(self):
        self.jobs = {
            4252: {
                "name": "盧恩龍爵",
                "id_jobneme": "Dragon_Knight",
            },
            4260: {
                "name": "深淵追跡者",
                "id_jobneme": "Abyss_Chaser",
            },
        }

    def test_loads_locale_by_stable_job_id(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            locale_dir = Path(temp_dir, "lang", "jobs")
            locale_dir.mkdir(parents=True)
            Path(locale_dir, "zh_CN.json").write_text(
                json.dumps(
                    {
                        "jobs": {
                            "4252": {
                                "name": "卢恩龙爵",
                                "aliases": ["龙爵"],
                            }
                        }
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            translations = load_job_translations(
                "zh_CN",
                base_dir=temp_dir,
            )
            name = get_localized_job_name(
                4252,
                self.jobs[4252],
                "zh_CN",
                base_dir=temp_dir,
            )

        self.assertEqual(translations[4252]["name"], "卢恩龙爵")
        self.assertEqual(name, "卢恩龙爵")
        self.assertEqual(self.jobs[4252]["name"], "盧恩龍爵")

    def test_resolves_source_simplified_english_resource_and_id(self):
        index = build_job_name_index(self.jobs)

        self.assertEqual(resolve_job_id("盧恩龍爵", self.jobs, name_index=index), 4252)
        self.assertEqual(resolve_job_id("卢恩龙爵", self.jobs, name_index=index), 4252)
        self.assertEqual(resolve_job_id("Dragon Knight", self.jobs, name_index=index), 4252)
        self.assertEqual(resolve_job_id("Dragon_Knight", self.jobs, name_index=index), 4252)
        self.assertEqual(resolve_job_id("ID:4252", self.jobs, name_index=index), 4252)
        self.assertEqual(resolve_job_id(4252, self.jobs, name_index=index), 4252)

    def test_missing_locale_falls_back_to_source_name(self):
        self.assertEqual(
            get_localized_job_name(4252, self.jobs[4252], "zh_TW"),
            "盧恩龍爵",
        )

    def test_project_job_locales_cover_every_selectable_job(self):
        expected_ids = set(job_dict) - {0}
        for language in ("zh_CN", "en_US"):
            translations = load_job_translations(language)
            self.assertEqual(set(translations), expected_ids)
            names = [entry["name"] for entry in translations.values()]
            self.assertEqual(len(names), len(set(names)))


if __name__ == "__main__":
    unittest.main()
