# recompile_service.py
import os
import sys
from pathlib import Path
from datetime import datetime, timezone

import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from PySide6.QtCore import QObject, QThread, Signal, Slot
class RecompileWorker(QObject):
    finished = Signal(list)          # [(filename, default_checked), ...]
    error = Signal(str)
    progress = Signal(int, int)      # done, total

    def __init__(self, data_folder: str, items: list, owner: str, repo: str, branch: str, parent=None):
        super().__init__(parent)
        self.data_folder = data_folder
        self.items = items
        self.owner = owner
        self.repo = repo
        self.branch = branch
        self._abort = False
        self._thread_local = threading.local()

    def abort(self):
        self._abort = True

    @Slot()
    def run(self):
        try:
            files = self._build_files_to_delete()
            self.finished.emit(files)
        except Exception as e:
            self.error.emit(str(e))

    # ===== implementation details =====
    def _load_env_if_possible(self):
        try:
            from dotenv import load_dotenv
        except ImportError:
            load_dotenv = None
        if load_dotenv is None:
            return

        candidates = [
            Path.cwd() / ".env",
            Path(sys.executable).resolve().parent / ".env",
        ]
        if "__file__" in globals():
            candidates.insert(1, Path(__file__).resolve().parent / ".env")

        for p in candidates:
            if p.is_file():
                load_dotenv(p, override=False)
                break

    def _get_github_pat(self) -> str | None:
        self._load_env_if_possible()
        # The cRO repository is public. A token raises the API rate limit for
        # developers, but end users must be able to check updates without one.
        return os.environ.get("GITHUB_PAT") or None

    def _get_session(self) -> requests.Session:
        if not hasattr(self._thread_local, "session"):
            self._thread_local.session = requests.Session()
        return self._thread_local.session

    def _github_file_last_commit_dt(self, session: requests.Session, path: str, token: str | None, timeout=(3.05, 8)):
        url = f"https://api.github.com/repos/{self.owner}/{self.repo}/commits"
        params = {"path": path, "sha": self.branch, "per_page": 1}
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "ROItemSearchApp-CRO",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"

        r = session.get(url, params=params, headers=headers, timeout=timeout)
        if r.status_code != 200:
            return None
        data = r.json()
        if not data:
            return None
        iso = data[0]["commit"]["committer"]["date"]  # "...Z"
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc)

    def _local_file_mtime_dt(self, full_path: str):
        if not os.path.exists(full_path):
            return None
        ts = os.path.getmtime(full_path)
        return datetime.fromtimestamp(ts, tz=timezone.utc)

    def _should_check_by_remote_newer(self, local_dt, remote_dt):
        if remote_dt is None:
            return False
        if local_dt is None:
            return True
        return remote_dt > local_dt

    def _build_files_to_delete(self):
        token = self._get_github_pat()
        total = len(self.items)
        out = [None] * total
        done = 0

        def check_one(idx: int, filename: str, github_path: str):
            if self._abort:
                return idx, (filename, False)

            local_path = os.path.join(self.data_folder, filename)
            local_dt = self._local_file_mtime_dt(local_path)

            # 本機沒有檔案時，原本邏輯本來就會勾選，直接略過 GitHub 查詢
            if local_dt is None:
                return idx, (filename, True)

            remote_dt = self._github_file_last_commit_dt(
                self._get_session(),
                github_path,
                token=token,
            )
            default_checked = self._should_check_by_remote_newer(local_dt, remote_dt)
            return idx, (filename, default_checked)

        max_workers = min(6, max(1, total))

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(check_one, idx, filename, github_path)
                for idx, (filename, github_path) in enumerate(self.items)
            ]

            for future in as_completed(futures):
                if self._abort:
                    executor.shutdown(wait=False, cancel_futures=True)
                    return []

                idx, result = future.result()
                out[idx] = result
                done += 1
                self.progress.emit(done, total)

        return out


class RecompileService(QObject):
    """
    可重用的非同步服務：
    - start() 之後會在背景抓 GitHub 資訊
    - 完成 emit finished(list)
    - 出錯 emit error(str)
    - 進度 emit progress(done, total)
    """
    finished = Signal(list)
    error = Signal(str)
    progress = Signal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._thread: QThread | None = None
        self._worker: RecompileWorker | None = None

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.isRunning()

    def cancel(self):
        if self._worker is not None:
            self._worker.abort()

    def start(self, *, data_folder: str, items: list, owner: str, repo: str, branch: str = "main"):
        if self.is_running():
            return  # 或 raise，隨你

        self._thread = QThread()
        self._worker = RecompileWorker(data_folder, items, owner, repo, branch)
        self._worker.moveToThread(self._thread)

        # pipe signals
        self._worker.progress.connect(self.progress)
        self._worker.finished.connect(self.finished)
        self._worker.error.connect(self.error)

        # cleanup
        self._worker.finished.connect(self._cleanup)
        self._worker.error.connect(self._cleanup)

        self._thread.started.connect(self._worker.run)
        self._thread.start()

    @Slot()
    def _cleanup(self):
        # 這個 slot 會在主執行緒被呼叫
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait()

        if self._worker is not None:
            self._worker.deleteLater()
        if self._thread is not None:
            self._thread.deleteLater()

        self._worker = None
        self._thread = None
