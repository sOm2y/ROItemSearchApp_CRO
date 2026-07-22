"""Pure helpers shared by the application and the Windows updater."""

from __future__ import annotations

import os
import stat
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any


RELEASE_ASSET_NAME = "ROItemSearchApp.zip"
PACKAGE_DIR_NAME = "ROItemSearchApp"


def select_release_asset(
    release_data: dict[str, Any],
    asset_name: str = RELEASE_ASSET_NAME,
) -> tuple[str, str]:
    """Return ``(tag_name, browser_download_url)`` for the expected asset."""
    tag_name = str(release_data.get("tag_name") or "").strip()
    if not tag_name:
        raise RuntimeError("GitHub Release 缺少 tag_name。")

    expected = asset_name.casefold()
    for asset in release_data.get("assets") or []:
        if str(asset.get("name") or "").casefold() != expected:
            continue
        download_url = str(asset.get("browser_download_url") or "").strip()
        if download_url:
            return tag_name, download_url

    raise RuntimeError(f"GitHub Release 缺少更新文件：{asset_name}")


def safe_extract_zip(zip_path: str | os.PathLike[str], destination: str | os.PathLike[str]) -> None:
    """Extract a trusted release ZIP while rejecting traversal and symlinks."""
    destination_path = Path(destination).resolve()
    destination_path.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path) as archive:
        for member in archive.infolist():
            normalized_name = member.filename.replace("\\", "/")
            relative_path = PurePosixPath(normalized_name)
            has_windows_drive = bool(
                relative_path.parts and ":" in relative_path.parts[0]
            )
            if (
                relative_path.is_absolute()
                or has_windows_drive
                or ".." in relative_path.parts
            ):
                raise RuntimeError(f"更新包包含不安全路径：{member.filename}")

            unix_mode = (member.external_attr >> 16) & 0o170000
            if stat.S_ISLNK(unix_mode):
                raise RuntimeError(f"更新包包含不支持的符号链接：{member.filename}")

            target_path = (destination_path / Path(*relative_path.parts)).resolve()
            try:
                target_path.relative_to(destination_path)
            except ValueError as error:
                raise RuntimeError(f"更新包包含不安全路径：{member.filename}") from error

        archive.extractall(destination_path)


def find_package_root(
    extracted_dir: str | os.PathLike[str],
    target_executable: str,
    preferred_dir_name: str = PACKAGE_DIR_NAME,
) -> Path:
    """Locate the directory containing the application executable."""
    extracted_path = Path(extracted_dir).resolve()
    target_name = Path(target_executable).name.casefold()

    preferred = extracted_path / preferred_dir_name
    for candidate in (preferred, extracted_path):
        if candidate.is_dir() and any(
            child.is_file() and child.name.casefold() == target_name
            for child in candidate.iterdir()
        ):
            return candidate

    matches: list[Path] = []
    for root, _, files in os.walk(extracted_path):
        if any(filename.casefold() == target_name for filename in files):
            matches.append(Path(root).resolve())

    if not matches:
        raise RuntimeError(f"更新包中找不到主程序：{Path(target_executable).name}")
    if len(matches) > 1:
        raise RuntimeError(f"更新包中存在多个主程序：{Path(target_executable).name}")
    return matches[0]
