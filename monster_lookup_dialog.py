# monster_lookup_dialog.py
import json
from pathlib import Path
import requests

from PySide6.QtCore import QObject, Signal, QThread
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QPushButton, QLabel, QMessageBox
)
from PySide6.QtWidgets import QComboBox 
# ================= monster =================
MONSTERS_FILE = Path("data","monsters.json")

def load_presets() -> list[dict]:
    """
    回傳格式: [{"name": str, "id": int}, ...]
    檔案不存在/壞掉 -> 回傳空清單
    """
    if not MONSTERS_FILE.exists():
        return []
    try:
        with MONSTERS_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            return []
        out = []
        for row in data:
            if not isinstance(row, dict):
                continue
            name = str(row.get("name", "")).strip()
            mid = row.get("id", None)
            try:
                mid = int(mid)
            except Exception:
                continue
            if name and mid > 0:
                out.append({"name": name, "id": mid})
        return out
    except Exception:
        return []

# ================= config =================
CONFIG_FILE = Path("data","config.json")

def load_api_key_from_config() -> str:
    if not CONFIG_FILE.exists():
        return ""
    try:
        with CONFIG_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return str(data.get("api_key", "")).strip()
    except Exception:
        return ""


# ================= element decode =================
def decode_element(element_code: int):
    if element_code is None:
        return 0, 1

    lv_a = element_code // 20
    rem = element_code % 20
    if rem in (0, 5, 10, 15) and 1 <= lv_a <= 4:
        return rem // 5, lv_a

    lv_b = element_code // 20
    id_b = element_code % 20
    if 1 <= lv_b <= 4:
        return id_b, lv_b

    return 0, max(1, lv_a if lv_a > 0 else 1)


# ================= worker =================
class MonsterFetchWorker(QObject):
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, monster_id: int, api_key: str, language="zh-TW"):
        super().__init__()
        self.monster_id = monster_id
        self.api_key = api_key
        self.language = language

    def run(self):
        try:
            url = f"https://www.divine-pride.net/api/database/Monster/{self.monster_id}?apiKey={self.api_key}"
            headers = {"Accept-Language": self.language}
            r = requests.get(url, headers=headers, timeout=10)
            r.raise_for_status()
            self.finished.emit(r.json())
        except Exception as e:
            self.error.emit(str(e))


# ================= dialog =================
class MonsterLookupDialog(QDialog):
    """
    使用方式（在主程式）：
        from monster_lookup_dialog import MonsterLookupDialog
        dlg = MonsterLookupDialog(self)
        dlg.monsterSelected.connect(self.apply_monster_to_main_ui)
        dlg.exec()
    """
    monsterSelected = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("怪物查詢")
        self.setModal(True)

        self._last_data = None

        # -------- UI --------
        self.id_input = QLineEdit()
        self.id_input.setPlaceholderText("怪物ID")

        self.key_input = QLineEdit()
        self.key_input.setText(load_api_key_from_config())
        self.key_input.setPlaceholderText("API Key")

        self.btn_query = QPushButton("查詢")
        self.btn_query.clicked.connect(self.on_query)

        self.btn_apply = QPushButton("套用")
        self.btn_apply.setEnabled(False)
        self.btn_apply.clicked.connect(self.on_apply)

        self.status = QLabel("請輸入怪物ID")

        self.name_preview = QLineEdit()
        self.name_preview.setReadOnly(True)
        self.preset_box = QComboBox()
        self.preset_box.addItem("（選擇預設怪物）", None)

        for m in load_presets():
            # 顯示名稱，data 存 id
            self.preset_box.addItem(m["name"], m["id"])

        self.preset_box.currentIndexChanged.connect(self.on_preset_changed)
        form = QFormLayout()
        form.addRow("預設怪物", self.preset_box)
        form.addRow("怪物 ID", self.id_input)
        #form.addRow("API Key", self.key_input)
        form.addRow("名稱預覽", self.name_preview)

        btn_row = QHBoxLayout()
        btn_row.addWidget(self.btn_query)
        btn_row.addWidget(self.btn_apply)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.status)
        layout.addLayout(btn_row)

    def on_preset_changed(self, _index: int):
        monster_id = self.preset_box.currentData()
        if monster_id is None:
            return
        self.id_input.setText(str(monster_id))

    # -------- logic --------
    def on_query(self):
        try:
            monster_id = int(self.id_input.text())
        except ValueError:
            QMessageBox.warning(self, "錯誤", "怪物ID 必須是數字")
            return

        api_key = self.key_input.text().strip()
        if not api_key:
            QMessageBox.warning(self, "錯誤", "API Key 不可為空")
            return

        self.status.setText("查詢中...")
        self.btn_query.setEnabled(False)
        self.btn_apply.setEnabled(False)

        self.thread = QThread(self)
        self.worker = MonsterFetchWorker(monster_id, api_key)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self.worker.finished.connect(self.on_fetched)
        self.worker.error.connect(self.on_error)

        self.thread.start()

    def on_error(self, msg: str):
        self.btn_query.setEnabled(True)
        self.status.setText("查詢失敗")
        QMessageBox.critical(self, "API 錯誤", msg)

    def on_fetched(self, data: dict):
        self.btn_query.setEnabled(True)

        parsed = self.parse_monster(data)
        self._last_data = parsed

        self.name_preview.setText(parsed["name"])
        self.status.setText("查詢完成")
        self.btn_apply.setEnabled(True)

    def on_apply(self):
        if self._last_data:
            self.monsterSelected.emit(self._last_data)
            self.accept()

    # -------- parse --------
    def parse_monster(self, data: dict) -> dict:
        stats = data.get("stats", {})

        name = data.get("name") or data.get("dbname", "")
        level = int(stats.get("level", 0))
        vit = int(stats.get("vit") or 0)
        inte = int(stats.get("int") or 0)

        def_after = int(stats.get("defense", 0))
        mdef_after = int(stats.get("magicDefense", 0))

        def_before = int((level + vit) / 2)
        mdef_before = int(int(level / 4) + int(vit / 10) + int(inte / 5))

        element_id, element_lv = decode_element(stats.get("element", 0))

        return {
            "name": name,
            "element_id": element_id,
            "element_lv": element_lv,
            "size_id": int(stats.get("scale", 0)),
            "race_id": int(stats.get("race", 0)),
            "class_id": int(stats.get("class", 0)),
            "def_before": def_before,
            "mdef_before": mdef_before,
            "def_after": def_after,
            "mdef_after": mdef_after,
            "res": int(stats.get("res", 0)),
            "mres": int(stats.get("mres", 0)),
        }
