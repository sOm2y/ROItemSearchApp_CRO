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
from i18n import LangManager, tr

# ================= monster =================
MONSTERS_FILE = Path("data","monsters.json")
MONSTER_CACHE_DIR = Path("data", "monster")
API_LANGUAGE_MAP = {
    "zh_CN": "zh-CN",
    "zh_TW": "zh-TW",
    "en_US": "en-US",
}
def cache_path(monster_id: int) -> Path:
    # data/monster/1002.json
    return MONSTER_CACHE_DIR / f"{int(monster_id)}.json"

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
        return rem , lv_a

    lv_b = element_code // 20
    id_b = element_code % 20
    if 1 <= lv_b <= 4:
        return id_b, lv_b

    return 0, max(1, lv_a if lv_a > 0 else 1)


# ================= worker =================
class MonsterFetchWorker(QObject):
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, monster_id: int, api_key: str, language=None):
        super().__init__()
        self.monster_id = monster_id
        self.api_key = api_key
        self.language = language or API_LANGUAGE_MAP.get(
            LangManager.current_lang,
            "zh-TW",
        )

    def run(self):
        try:
            # 1) 先讀快取
            MONSTER_CACHE_DIR.mkdir(parents=True, exist_ok=True)
            cpath = cache_path(self.monster_id)

            if cpath.exists():
                with cpath.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    data["_from_cache"] = True
                self.finished.emit(data)
                return

            # 2) 沒快取才打 API
            if not self.api_key:
                raise Exception(tr("message.monster_cache_and_api_key_missing"))

            url = f"https://www.divine-pride.net/api/database/Monster/{self.monster_id}?apiKey={self.api_key}"
            headers = {"Accept-Language": self.language}
            r = requests.get(url, headers=headers, timeout=10)
            r.raise_for_status()
            data = r.json()

            # 3) 存快取（存原始 JSON）
            try:
                with cpath.open("w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            except Exception:
                # 快取寫入失敗不阻擋主要流程
                pass

            self.finished.emit(data)

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
        self.setWindowTitle(tr("window.monster_lookup"))
        self.setModal(True)

        self._last_data = None

        # -------- UI --------
        self.id_input = QLineEdit()
        self.id_input.setPlaceholderText(tr("placeholder.monster_id"))

        self.key_input = QLineEdit()
        self.key_input.setText(load_api_key_from_config())
        self.key_input.setPlaceholderText("API Key")

        self.btn_query = QPushButton(tr("button.query"))
        self.btn_query.clicked.connect(self.on_query)

        self.btn_apply = QPushButton(tr("button.apply"))
        self.btn_apply.setEnabled(False)
        self.btn_apply.clicked.connect(self.on_apply)

        self.status = QLabel(tr("status.enter_monster_id"))

        self.name_preview = QLineEdit()
        self.name_preview.setReadOnly(True)
        self.preset_box = QComboBox()
        self.preset_box.addItem(tr("placeholder.select_preset_monster"), None)

        for m in load_presets():
            # 顯示名稱，data 存 id
            self.preset_box.addItem(m["name"], m["id"])

        self.preset_box.currentIndexChanged.connect(self.on_preset_changed)
        form = QFormLayout()
        form.addRow(tr("label.preset_monster"), self.preset_box)
        form.addRow(tr("label.monster_id"), self.id_input)
        #form.addRow("API Key", self.key_input)
        form.addRow(tr("label.name_preview"), self.name_preview)

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
            QMessageBox.warning(
                self,
                tr("message.title.error"),
                tr("message.monster_id_must_be_numeric"),
            )
            return

        api_key = self.key_input.text().strip()

        self.status.setText(tr("status.querying"))
        self.btn_query.setEnabled(False)
        self.btn_apply.setEnabled(False)

        self.thread = QThread(self)
        self.worker = MonsterFetchWorker(monster_id, api_key)
        self.thread.started.connect(self.worker.run)

        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)

        # ✅ 這三行是關鍵：錯誤也要結束 thread，不然按「套用」關窗就會爆
        self.worker.error.connect(self.thread.quit)
        self.worker.error.connect(self.worker.deleteLater)
        self.worker.error.connect(self.thread.quit)  #（重複也沒關係，但建議保留一次即可）

        self.thread.finished.connect(self.thread.deleteLater)

        self.worker.finished.connect(self.on_fetched)
        self.worker.error.connect(self.on_error)


        self.thread.start()

    def on_error(self, msg: str):
        self.btn_query.setEnabled(True)
        self.btn_apply.setEnabled(False)   # <<< 重要：錯誤就不允許套用
        self._last_data = None             # <<< 重要：清掉上一次成功資料，避免誤套用
        self.name_preview.clear()
        self.status.setText(tr("status.query_failed"))
        QMessageBox.critical(self, tr("message.title.api_error"), msg)



    def on_fetched(self, data: dict):
        self.btn_query.setEnabled(True)

        parsed = self.parse_monster(data)
        self._last_data = parsed

        self.name_preview.setText(parsed["name"])
        src = (
            tr("source.cache")
            if data.get("_from_cache")
            else tr("source.api")
        )
        self.status.setText(tr("status.query_complete", source=src))
        self.btn_apply.setEnabled(True)

    def on_apply(self):
        if self._last_data:
            self.monsterSelected.emit(self._last_data)
            self.accept()

    # -------- parse --------
    def parse_monster(self, data: dict) -> dict:
        stats = data.get("stats", {})
        attack_data = stats.get("attack") or {}
        mattack_data = stats.get("magicAttack") or {}
        name = data.get("name") or data.get("dbname", "")
        level = int(stats.get("level", 0))
        s_tr = int(stats.get("str") or 0)
        vit = int(stats.get("vit") or 0)
        inte = int(stats.get("int") or 0)

        def_after = int(stats.get("defense", 0))
        mdef_after = int(stats.get("magicDefense", 0))

        def_before = int((level + vit) / 2)
        mdef_before = int(int(level / 4) + int(vit / 10) + int(inte / 5))

        element_id, element_lv = decode_element(stats.get("element", 0))

        f_atk = int(level + s_tr)
        c_atk = int(attack_data.get("maximum") or 0)
        f_matk = int(level + inte)
        c_matk = int(mattack_data.get("maximum") or 0)
        #print(f"==================前atk{f_atk}後atk{c_atk}前MATK{f_matk}後MATK{c_matk}")

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
            "monster_f_atk": f_atk,
            "monster_c_atk": c_atk,
            "monster_f_matk": f_matk,
            "monster_c_matk": c_matk,
        }
