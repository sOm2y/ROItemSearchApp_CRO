# update_helper_pyside6.py
import os
import shutil
import subprocess
import sys
import tempfile
import time

import psutil
import requests
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMessageBox,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from i18n import tr
from updater_core import find_package_root, safe_extract_zip


class UpdateWorker(QThread):
    stage = Signal(str)
    detail = Signal(str)
    progress = Signal(int)
    done = Signal()
    failed = Signal(str)

    def __init__(self, zip_url: str, target_exe: str, install_dir: str, parent=None):
        super().__init__(parent)
        self.zip_url = zip_url
        self.install_dir = os.path.abspath(install_dir)
        self.target_path = (
            os.path.abspath(target_exe)
            if os.path.isabs(target_exe)
            else os.path.join(self.install_dir, target_exe)
        )
        self.target_exe = os.path.basename(self.target_path)

    def run(self):
        archive_path = None
        try:
            archive_path = self.download_with_progress()
            self.wait_or_kill_process()
            self.extract_and_replace(archive_path)

            self.stage.emit(tr("updater.stage.complete"))
            self.detail.emit("")
            self.progress.emit(100)

            subprocess.Popen([self.target_path], cwd=self.install_dir)
            time.sleep(1.0)
            self.done.emit()
        except Exception as error:
            self.failed.emit(str(error))
        finally:
            if archive_path:
                try:
                    os.remove(archive_path)
                except OSError:
                    pass

    def download_with_progress(self) -> str:
        self.stage.emit(tr("updater.stage.downloading"))
        self.detail.emit("")
        self.progress.emit(0)

        temp_file = tempfile.NamedTemporaryFile(
            prefix="ROItemSearchApp-CRO-",
            suffix=".zip",
            delete=False,
        )
        archive_path = temp_file.name
        temp_file.close()

        try:
            with requests.get(
                self.zip_url,
                headers={"User-Agent": "ROItemSearchApp-CRO-Updater"},
                stream=True,
                timeout=(10, 120),
            ) as response:
                response.raise_for_status()
                total = int(response.headers.get("content-length", 0))
                downloaded = 0
                last_percent = -1

                with open(archive_path, "wb") as output:
                    for chunk in response.iter_content(chunk_size=256 * 1024):
                        if not chunk:
                            continue
                        output.write(chunk)
                        downloaded += len(chunk)

                        if total > 0:
                            percent = int(downloaded * 100 / total)
                            if percent == last_percent:
                                continue
                            last_percent = percent

                        self.stage.emit(tr("updater.stage.download_progress"))
                        if total > 0:
                            self.detail.emit(
                                f"{downloaded // 1024} KB / {total // 1024} KB"
                            )
                            self.progress.emit(max(0, min(100, last_percent)))
                        else:
                            self.detail.emit(f"{downloaded // 1024} KB")

            self.stage.emit(tr("updater.stage.download_complete"))
            self.detail.emit("")
            self.progress.emit(100)
            return archive_path
        except Exception:
            try:
                os.remove(archive_path)
            except OSError:
                pass
            raise

    def _matching_processes(self):
        target_path = os.path.normcase(os.path.abspath(self.target_path))
        target_name = self.target_exe.casefold()
        matches = []
        for process in psutil.process_iter(["pid", "name", "exe"]):
            if process.pid == os.getpid():
                continue
            name = str(process.info.get("name") or "").casefold()
            executable = process.info.get("exe")
            if executable:
                if os.path.normcase(os.path.abspath(executable)) == target_path:
                    matches.append(process)
            elif name == target_name:
                matches.append(process)
        return matches

    def wait_or_kill_process(self):
        self.stage.emit(
            tr("updater.stage.waiting_for_close", executable=self.target_exe)
        )
        self.detail.emit("")
        self.progress.emit(0)

        start = time.time()
        while time.time() - start < 30:
            if not self._matching_processes():
                return
            time.sleep(0.5)

        self.stage.emit(tr("updater.stage.force_closing"))
        self.detail.emit("")
        for process in self._matching_processes():
            try:
                process.kill()
            except (psutil.Error, OSError):
                pass
        time.sleep(1)

    @staticmethod
    def _copy_with_retry(src_path: str, dst_path: str, attempts: int = 6):
        staging_path = f"{dst_path}.update_tmp"
        last_error = None
        for attempt in range(attempts):
            try:
                os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                shutil.copy2(src_path, staging_path)
                os.replace(staging_path, dst_path)
                return
            except OSError as error:
                last_error = error
                try:
                    os.remove(staging_path)
                except OSError:
                    pass
                if attempt + 1 < attempts:
                    time.sleep(0.5)
        raise last_error or RuntimeError(f"无法覆盖文件：{dst_path}")

    def extract_and_replace(self, archive_path: str):
        temp_dir = tempfile.mkdtemp(prefix="ROItemSearchApp-CRO-extract-")
        try:
            self.stage.emit(tr("updater.stage.extracting"))
            self.detail.emit("")
            self.progress.emit(0)

            safe_extract_zip(archive_path, temp_dir)
            base_dir = find_package_root(temp_dir, self.target_exe)
            file_paths = [path for path in base_dir.rglob("*") if path.is_file()]
            total_files = max(1, len(file_paths))
            current_updater = os.path.normcase(
                os.path.abspath(
                    sys.executable if getattr(sys, "frozen", False) else sys.argv[0]
                )
            )

            self.stage.emit(tr("updater.stage.copying_files"))
            for copied, src_path in enumerate(file_paths, start=1):
                rel_path = src_path.relative_to(base_dir)
                dst_path = os.path.abspath(os.path.join(self.install_dir, rel_path))

                # A directly launched installed updater cannot overwrite itself.
                # Stage that file for the main app to install after restart.
                if os.path.normcase(dst_path) == current_updater:
                    dst_path = os.path.join(self.install_dir, "update.next.exe")

                self._copy_with_retry(str(src_path), dst_path)

                percent = int(copied * 100 / total_files)
                self.stage.emit(tr("updater.stage.copy_progress"))
                self.detail.emit(f"{copied} / {total_files}")
                self.progress.emit(max(0, min(100, percent)))

            if not os.path.isfile(self.target_path):
                raise RuntimeError(f"更新后找不到主程序：{self.target_exe}")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class UpdaterWindow(QWidget):
    def __init__(self, zip_url: str, target_exe: str, install_dir: str):
        super().__init__()
        self.setWindowTitle(tr("updater.window.title"))
        self.setFixedSize(420, 120)

        self.label_stage = QLabel(tr("updater.stage.preparing"))
        self.label_stage.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)

        self.label_detail = QLabel("")
        self.label_detail.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.label_detail.setStyleSheet("color: gray;")

        layout = QVBoxLayout()
        layout.addWidget(self.label_stage)
        layout.addWidget(self.progress)
        layout.addWidget(self.label_detail)
        self.setLayout(layout)

        self.worker = UpdateWorker(zip_url, target_exe, install_dir)
        self.worker.stage.connect(self.label_stage.setText)
        self.worker.detail.connect(self.label_detail.setText)
        self.worker.progress.connect(self.progress.setValue)
        self.worker.done.connect(self.on_done)
        self.worker.failed.connect(self.on_failed)
        self.worker.start()

    def on_done(self):
        self.close()

    def on_failed(self, message: str):
        self.label_stage.setText(tr("updater.stage.error"))
        self.label_detail.setText(message)
        self.progress.setValue(0)
        QMessageBox.critical(self, tr("updater.error.title"), message)


def main():
    if len(sys.argv) < 3:
        app = QApplication(sys.argv)
        QMessageBox.critical(
            None,
            tr("common.error"),
            tr("updater.error.arguments_required"),
        )
        sys.exit(1)

    zip_url = sys.argv[1]
    exe_to_restart = sys.argv[2]
    if len(sys.argv) >= 4:
        install_dir = os.path.abspath(sys.argv[3])
    elif os.path.isabs(exe_to_restart):
        install_dir = os.path.dirname(exe_to_restart)
    elif getattr(sys, "frozen", False):
        install_dir = os.path.dirname(sys.executable)
    else:
        install_dir = os.getcwd()

    app = QApplication(sys.argv)
    window = UpdaterWindow(zip_url, exe_to_restart, install_dir)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
