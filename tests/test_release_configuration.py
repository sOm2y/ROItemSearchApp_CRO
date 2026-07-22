import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RELEASE_VERSION = "v0.3.21-260722"


class ReleaseConfigurationTests(unittest.TestCase):
    def test_application_and_data_versions_match_release_tag(self):
        app_source = (ROOT / "ItemSearchApp.py").read_text(encoding="utf-8")
        match = re.search(r'^Version = "([^"]+)"', app_source, re.MULTILINE)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), RELEASE_VERSION)
        self.assertEqual(
            (ROOT / "data" / "version.txt").read_text(encoding="utf-8").strip(),
            RELEASE_VERSION,
        )

    def test_updater_uses_cro_repository(self):
        app_source = (ROOT / "ItemSearchApp.py").read_text(encoding="utf-8")
        self.assertIn('GITHUB_OWNER = "sOm2y"', app_source)
        self.assertIn('GITHUB_REPO = "ROItemSearchApp_CRO"', app_source)
        self.assertIn("raw.githubusercontent.com/", app_source)
        self.assertIn('f"{GITHUB_OWNER}/{GITHUB_REPO}/main/data"', app_source)
        self.assertIn("read_remote_release_github", app_source)
        self.assertIn('child_env["ROITEMSEARCHAPP_BASE_DIR"] = app_dir', app_source)

    def test_updater_uses_install_directory_instead_of_working_directory(self):
        updater_source = (ROOT / "update.py").read_text(encoding="utf-8")
        self.assertIn("self.install_dir = os.path.abspath(install_dir)", updater_source)
        self.assertIn("cwd=self.install_dir", updater_source)
        self.assertNotIn('temp_dir = "update_temp"', updater_source)

    def test_release_workflow_builds_on_version_tags(self):
        workflow = (ROOT / ".github" / "workflows" / "windows-release.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn('- "v*"', workflow)
        self.assertIn("Create GitHub Release", workflow)
        self.assertIn("release/ROItemSearchApp.zip", workflow)


if __name__ == "__main__":
    unittest.main()
