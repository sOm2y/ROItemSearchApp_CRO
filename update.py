# update_helper_pyside6.py
import os
import sys
import time
import io
import zipfile
import shutil
import subprocess

import requests
import psutil

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QProgressBar, QVBoxLayout, QMessageBox
)


class UpdateWorker(QThread):
    stage = Signal(str)          # 大標題
    detail = Signal(str)         # 細節文字
    progress = Signal(int)       # 0~100
    done = Signal()
    failed = Signal(str)

    def __init__(self, zip_url: str, target_exe: str, parent=None):
        super().__init__(parent)
        self.zip_url = zip_url
        self.target_exe = target_exe

    def run(self):
        try:
            data = self.download_with_progress()
            self.wait_or_kill_process()
            self.extract_and_replace(data)

            self.stage.emit("✅ 更新完成，啟動主程式...")
            self.detail.emit("")
            self.progress.emit(100)

            # 重啟主程式
            subprocess.Popen([self.target_exe], shell=True)
            time.sleep(1.0)

            self.done.emit()
        except Exception as e:
            self.failed.emit(str(e))

    def download_with_progress(self) -> bytes:
        self.stage.emit("📥 正在下載更新檔...")
        self.detail.emit("")
        self.progress.emit(0)

        response = requests.get(self.zip_url, stream=True, timeout=60)
        response.raise_for_status()

        total = int(response.headers.get("content-length", 0))
        downloaded = 0
        data = io.BytesIO()
        last_percent = -1

        for chunk in response.iter_content(chunk_size=8192):
            if not chunk:
                continue
            data.write(chunk)
            downloaded += len(chunk)

            if total > 0:
                percent = int(downloaded * 100 / total)
                if percent != last_percent:
                    self.stage.emit("📥 下載中...")
                    self.detail.emit(f"{downloaded // 1024} KB / {total // 1024} KB")
                    self.progress.emit(max(0, min(100, percent)))
                    last_percent = percent
            else:
                # 沒有 content-length 時，只能顯示已下載
                self.stage.emit("📥 下載中...")
                self.detail.emit(f"{downloaded // 1024} KB")
                # 不亂跳：維持 0，等完成再設 100

        self.stage.emit("✅ 下載完成")
        self.detail.emit("")
        self.progress.emit(100)
        return data.getvalue()

    def wait_or_kill_process(self):
        self.stage.emit(f"⏳ 等待手動 {self.target_exe} 關閉中...")
        self.detail.emit("")
        self.progress.emit(0)

        start = time.time()
        while time.time() - start < 30:
            running = [
                p for p in psutil.process_iter(["name"])
                if (p.info.get("name") or "").lower() == self.target_exe.lower()
            ]
            if not running:
                return
            time.sleep(0.5)

        self.stage.emit("💀 強制關閉主程式")
        self.detail.emit("")
        for proc in psutil.process_iter(["name"]):
            name = (proc.info.get("name") or "").lower()
            if name == self.target_exe.lower():
                try:
                    proc.kill()
                except Exception:
                    pass
        time.sleep(1)

    def extract_and_replace(self, data: bytes):
        temp_dir = "update_temp"
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)

        self.stage.emit("📂 正在解壓縮更新...")
        self.detail.emit("")
        self.progress.emit(0)

        with zipfile.ZipFile(io.BytesIO(data)) as z:
            z.extractall(temp_dir)

        # ===== 關鍵設定 =====

        OUTER_DIR = "ROItemSearchApp"   # zip 最外層資料夾名稱

        current_updater_name = os.path.basename(sys.argv[0]).lower()
        exclude_names = {
            current_updater_name,
            "updater.exe",
        }

        # ===== 收集要複製的檔案 =====
        file_paths = []

        base_dir = os.path.join(temp_dir, OUTER_DIR)
        if not os.path.isdir(base_dir):
            raise RuntimeError(f"更新包缺少資料夾：{OUTER_DIR}")

        for root, _, files in os.walk(base_dir):
            for fn in files:
                if fn.lower() in exclude_names:
                    continue
                file_paths.append(os.path.join(root, fn))

        total_files = max(1, len(file_paths))

        self.stage.emit("📂 正在覆蓋檔案...")
        copied = 0

        # ===== 開始覆蓋 =====
        for src_path in file_paths:
            # 這裡 rel 是「相對於 ItemSearchApp」的路徑
            rel = os.path.relpath(src_path, base_dir)
            dst_path = os.path.join(os.getcwd(), rel)

            os.makedirs(os.path.dirname(dst_path), exist_ok=True)
            shutil.copy2(src_path, dst_path)

            copied += 1
            percent = int(copied * 100 / total_files)
            self.stage.emit("📂 覆蓋檔案中")
            self.detail.emit(f"{copied} / {total_files}")
            self.progress.emit(max(0, min(100, percent)))

        shutil.rmtree(temp_dir, ignore_errors=True)




class UpdaterWindow(QWidget):
    def __init__(self, zip_url: str, target_exe: str):
        super().__init__()
        self.zip_url = zip_url
        self.target_exe = target_exe

        self.setWindowTitle("自動更新中...")
        self.setFixedSize(420, 120)

        self.label_stage = QLabel("準備中...")
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

        #self.move_to_bottom_right()

        self.worker = UpdateWorker(zip_url, target_exe)
        self.worker.stage.connect(self.label_stage.setText)
        self.worker.detail.connect(self.label_detail.setText)
        self.worker.progress.connect(self.progress.setValue)
        self.worker.done.connect(self.on_done)
        self.worker.failed.connect(self.on_failed)

        # 開窗後立刻開始
        self.worker.start()

    def move_to_bottom_right(self):
        screen = QApplication.primaryScreen()
        if not screen:
            return
        geo = screen.availableGeometry()
        x = geo.x() + geo.width() - self.width() - 20
        y = geo.y() + geo.height() - self.height() - 60
        self.move(x, y)

    def on_done(self):
        self.close()

    def on_failed(self, msg: str):
        self.label_stage.setText("❌ 更新錯誤")
        self.label_detail.setText(msg)
        self.progress.setValue(0)
        QMessageBox.critical(self, "更新失敗", msg)


def main():
    if len(sys.argv) < 3:
        # 你原本 Tkinter 這段其實少 import messagebox；這裡改用 Qt 的 MessageBox
        app = QApplication(sys.argv)
        QMessageBox.critical(None, "錯誤", "請提供 zip 下載網址 與 EXE 名稱")
        sys.exit(1)

    zip_url = sys.argv[1]
    exe_to_restart = sys.argv[2]

    app = QApplication(sys.argv)
    w = UpdaterWindow(zip_url, exe_to_restart)
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
