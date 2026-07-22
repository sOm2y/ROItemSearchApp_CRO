import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from recompile_service import RecompileWorker
from update import UpdateWorker
from updater_core import find_package_root, safe_extract_zip, select_release_asset


class ReleaseAssetTests(unittest.TestCase):
    def test_selects_cro_release_zip_download_url(self):
        version, url = select_release_asset(
            {
                "tag_name": "v0.3.21-260722",
                "assets": [
                    {
                        "name": "ROItemSearchApp.zip",
                        "browser_download_url": "https://github.com/sOm2y/ROItemSearchApp_CRO/releases/download/v0.3.21-260722/ROItemSearchApp.zip",
                    }
                ],
            }
        )
        self.assertEqual(version, "v0.3.21-260722")
        self.assertIn("sOm2y/ROItemSearchApp_CRO", url)

    def test_missing_release_asset_is_an_error(self):
        with self.assertRaisesRegex(RuntimeError, "ROItemSearchApp.zip"):
            select_release_asset({"tag_name": "v1.0.0", "assets": []})


class PackageExtractionTests(unittest.TestCase):
    def test_extracts_and_finds_expected_outer_folder(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            archive_path = Path(temp_dir) / "release.zip"
            extracted_dir = Path(temp_dir) / "extracted"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("ROItemSearchApp/ItemSearchApp.exe", b"exe")
                archive.writestr("ROItemSearchApp/data/version.txt", "v1")

            safe_extract_zip(archive_path, extracted_dir)
            package_root = find_package_root(extracted_dir, "ItemSearchApp.exe")

            self.assertEqual(package_root.name, "ROItemSearchApp")
            self.assertEqual(
                (package_root / "data" / "version.txt").read_text(),
                "v1",
            )

    def test_finds_package_if_outer_folder_name_changes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            package_dir = Path(temp_dir) / "renamed-package"
            package_dir.mkdir()
            (package_dir / "ItemSearchApp.exe").write_bytes(b"exe")
            self.assertEqual(
                find_package_root(temp_dir, "ItemSearchApp.exe"),
                package_dir.resolve(),
            )

    def test_rejects_zip_path_traversal(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            archive_path = Path(temp_dir) / "unsafe.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("../outside.txt", "bad")

            with self.assertRaisesRegex(RuntimeError, "不安全路径"):
                safe_extract_zip(archive_path, Path(temp_dir) / "extracted")
            self.assertFalse((Path(temp_dir) / "outside.txt").exists())

    def test_rejects_windows_drive_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            archive_path = Path(temp_dir) / "unsafe-drive.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("C:/outside.txt", "bad")

            with self.assertRaisesRegex(RuntimeError, "不安全路径"):
                safe_extract_zip(archive_path, Path(temp_dir) / "extracted")


class PublicRepositoryUpdateTests(unittest.TestCase):
    def test_github_token_is_optional_for_public_cro_repo(self):
        worker = RecompileWorker("data", [], "sOm2y", "ROItemSearchApp_CRO", "main")
        with mock.patch.dict(os.environ, {}, clear=True), mock.patch.object(
            worker, "_load_env_if_possible"
        ):
            self.assertIsNone(worker._get_github_pat())


class UpdateWorkerTests(unittest.TestCase):
    def test_replaces_files_in_install_dir_even_when_cwd_is_elsewhere(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            install_dir = temp_path / "installed"
            unrelated_cwd = temp_path / "shortcut-cwd"
            install_dir.mkdir()
            unrelated_cwd.mkdir()
            (install_dir / "ItemSearchApp.exe").write_bytes(b"old")

            archive_path = temp_path / "release.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("ROItemSearchApp/ItemSearchApp.exe", b"new")
                archive.writestr("ROItemSearchApp/data/version.txt", "v-new")

            worker = UpdateWorker(
                "https://example.invalid/release.zip",
                str(install_dir / "ItemSearchApp.exe"),
                str(install_dir),
            )
            original_cwd = os.getcwd()
            try:
                os.chdir(unrelated_cwd)
                worker.extract_and_replace(str(archive_path))
            finally:
                os.chdir(original_cwd)

            self.assertEqual((install_dir / "ItemSearchApp.exe").read_bytes(), b"new")
            self.assertEqual(
                (install_dir / "data" / "version.txt").read_text(),
                "v-new",
            )
            self.assertFalse((unrelated_cwd / "data").exists())


if __name__ == "__main__":
    unittest.main()
