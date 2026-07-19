
import sys
import os
import re
import html
import random
from PySide6.QtWidgets import (
    QApplication, QWidget, QListWidget, QTableWidget, QVBoxLayout, QHBoxLayout,
    QComboBox, QTableWidgetItem, QLabel, QTabWidget, QMessageBox, QPushButton,
    QGroupBox, QPlainTextEdit
)
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHeaderView
from PySide6.QtWidgets import QToolTip
from PySide6.QtGui import QCursor
from PySide6.QtGui import QFontMetrics
from PySide6.QtCore import QPoint
from i18n import tr, translate_equipment_part
# ---------------------------------------------------------------
# 讀檔：自動嘗試多種編碼
# ---------------------------------------------------------------
def read_text_with_fallback(path):
    encodings = ["utf-8", "utf-8-sig", "cp950", "big5", "cp936", "cp932", "latin1"]
    for enc in encodings:
        try:
            with open(path, "r", encoding=enc) as f:
                data = f.read()
            print(f"[INFO] 使用 {enc} 讀取成功：{path}")
            return data
        except Exception:
            continue

    with open(path, "rb") as f:
        data = f.read().decode("latin1", errors="replace")
    print(f"[WARN] 所有編碼失敗，改用 latin1+replace：{path}")
    return data




# ---------------------------------------------------------------
# 解析 ItemDBNameTbl.lua  => {"DBName": item_id}
# ---------------------------------------------------------------
def parse_itemdb_name_tbl(filename):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        print(f"❌ 找不到檔案：{filename}")
        return {}
    except UnicodeDecodeError:
        with open(filename, "rb") as f:
            content = f.read().decode("latin1", errors="replace")

    # 支援  Name = 123  或  ["Name"] = 123
    pattern = r'(?:\["([^"]+)"\]|([A-Za-z0-9_]+))\s*=\s*(\d+)'
    name_to_id = {}

    for m in re.finditer(pattern, content):
        key1, key2, val = m.groups()
        key = key1 or key2
        if key:
            name_to_id[key] = int(val)

    print(f"[INFO] ItemDBNameTbl 解析完成，共 {len(name_to_id)} 筆")
    return name_to_id


# ---------------------------------------------------------------
# 解析 EnchantList.lua
# parsed 結構：
#   { table_id: {
#       "slot_order": [3,2,1],
#       "target_items": ["N_Avenger_Cape_TW", ...],
#       "slots": {
#          slot_id: {
#             "enchants": [(grade, name, rate), ...],
#             "perfect":  [{"name": n, "rate": r, "materials": [...]}, ...]
#          }
#       }
#   } }
# ---------------------------------------------------------------
def parse_enchant_list(filename):
    if not os.path.exists(filename):
        print("❌ 找不到檔案", filename)
        return {}

    content = read_text_with_fallback(filename)

    # 找出所有 CreateEnchantInfo
    tables = re.split(r"Table\[(\d+)\]\s*=\s*CreateEnchantInfo\(\s*\)", content)
    if len(tables) <= 1:
        print("⚠ 解析不到任何 Table")
        return {}

    parsed = {}

    # 先逐 Table 把 slot_order / target_items / reset 抓出來
    for i in range(1, len(tables), 2):
        tid = int(tables[i])
        body = tables[i + 1]

        parsed[tid] = {
            "slot_order": [],
            "target_items": [],
            "reset": None,
            "slots": {}
        }

        # SetSlotOrder(3, 2, 1)
        sso = re.search(r"SetSlotOrder\((.*?)\)", body)
        if sso:
            nums = [
                int(x.strip()) for x in sso.group(1).split(",")
                if x.strip().isdigit()
            ]
            parsed[tid]["slot_order"] = nums

        # AddTargetItem("xxx")
        targets = re.findall(r'AddTargetItem(?:_Duplicate)?\("([^"]+)"\)', body)
        parsed[tid]["target_items"] = targets

        # SetReset(true, 80000, 0, {"Silvervine", 3})
        rst = re.search(
            r"SetReset\((true|false)\s*,\s*(\d+)\s*,\s*(\d+)(?:\s*,\s*((?:\{.*?\})+))?",
            body,
            re.DOTALL
        )
        if rst:
            enable = rst.group(1) == "true"
            rr = int(rst.group(2))
            er = int(rst.group(3))

            mats = []
            raw = rst.group(4)
            if raw:
                mats = [
                    (a, int(b))
                    for a, b in re.findall(r'\{\s*"([^"]+)"\s*,\s*(\d+)\s*\}', raw)
                ]
            parsed[tid]["reset"] = {
                "enable": enable,
                "reset_rate": rr,
                "enchant_rate": er,
                "materials": mats,
            }

    # --------------------------------------------------
    # 解析 SetRequire (支援多材料)
    # --------------------------------------------------
    all_requires = re.findall(
        r'Table\[(\d+)\]\.Slot\[(\d+)\]\:SetRequire'
        r'\(\s*(\d+)(?:\s*,\s*((?:\{[^}]+\}\s*,?\s*)*))?\s*\)',
        content
    )

    for tid, sid, zeny, mats_raw in all_requires:
        tid = int(tid)
        sid = int(sid)
        zeny = int(zeny)

        if tid not in parsed:
            continue

        parsed[tid]["slots"].setdefault(sid, {
            "enchants": [],
            "perfect": [],
            "upgrade": [],
            "perfect_upgrade": [],
            "random_upgrade": []
        })

        mats_raw = mats_raw or ""
        mats = re.findall(r'\{\s*"([^"]+)"\s*,\s*(\d+)\s*\}', mats_raw)
        materials = [(m_name, int(m_cnt)) for m_name, m_cnt in mats]

        parsed[tid]["slots"][sid]["require"] = {
            "zeny": zeny,
            "materials": materials
        }



    # --------------------------------------------------
    # 全檔掃描 SetEnchant
    # --------------------------------------------------
    all_enchants = re.findall(
        r'Table\[(\d+)\]\.Slot\[(\d+)\]\:SetEnchant\(\s*(\d+)\s*,\s*"([^"]+)"\s*,\s*(\d+)\s*\)',
        content
    )

    for tid, sid, grade, name, rate in all_enchants:
        tid = int(tid)
        sid = int(sid)
        grade = int(grade)
        rate = int(rate)

        if tid not in parsed:
            continue

        if sid not in parsed[tid]["slots"]:
            parsed[tid]["slots"][sid] = {
                "enchants": [],
                "perfect": []
            }

        parsed[tid]["slots"][sid]["enchants"].append((grade, name, rate))

    # --------------------------------------------------
    # 全檔掃描 AddPerfectEnchant
    # --------------------------------------------------
    all_perfects = re.findall(
        r'Table\[(\d+)\]\.Slot\[(\d+)\]\:AddPerfectEnchant'
        r'\(\s*"([^"]+)"\s*,\s*(\d+)\s*,\s*((?:\{.*?\})+)\)',
        content,
        re.DOTALL
    )

    for tid, sid, name, zeny, mats_raw in all_perfects:
        tid = int(tid)
        sid = int(sid)
        zeny = int(zeny)

        if tid not in parsed:
            continue

        if sid not in parsed[tid]["slots"]:
            parsed[tid]["slots"][sid] = {
                "enchants": [],
                "perfect": []
            }

        mats = re.findall(r'\{\s*"([^"]*)"\s*,\s*(\d+)\s*\}', mats_raw)
        materials = [(m_name, int(m_cnt)) for m_name, m_cnt in mats]

        parsed[tid]["slots"][sid]["perfect"].append({
            "name": name,
            "zeny": zeny,
            "materials": materials
        })

    # --------------------------------------------------
    # 全檔掃描 AddUpgradeEnchant
    # --------------------------------------------------
    all_upgrades = re.findall(
        r'Table\[(\d+)\]\.Slot\[(\d+)\]\:AddUpgradeEnchant'
        r'\(\s*"([^"]+)"\s*,\s*"([^"]+)"\s*,\s*(\d+)\s*,\s*((?:\{.*?\})+)\)',
        content,
        re.DOTALL
    )

    for tid, sid, src, dst, zeny, mats_raw in all_upgrades:
        tid = int(tid)
        sid = int(sid)
        zeny = int(zeny)

        if tid not in parsed:
            continue

        if sid not in parsed[tid]["slots"]:
            parsed[tid]["slots"][sid] = {
                "enchants": [],
                "perfect": [],
                "upgrade": []
            }
        else:
            parsed[tid]["slots"][sid].setdefault("upgrade", [])

        # 解析材料
        mats = re.findall(r'\{\s*"([^"]+)"\s*,\s*(\d+)\s*\}', mats_raw)
        materials = [(m_name, int(m_cnt)) for m_name, m_cnt in mats]

        parsed[tid]["slots"][sid]["upgrade"].append({
            "from": src,
            "to": dst,
            "zeny": zeny,
            "materials": materials
        })

    # --------------------------------------------------
    # 完美升階 AddPerfectUpgradeEnchant
    # --------------------------------------------------
    all_perfect_upgrades = re.findall(
        r'Table\[(\d+)\]\.Slot\[(\d+)\]\:AddPerfectUpgradeEnchant'
        r'\(\s*"([^"]+)"\s*,\s*"([^"]+)"\s*,\s*(\d+)\s*,\s*((?:\{.*?\})+)\)',
        content,
        re.DOTALL
    )

    for tid, sid, src, dst, zeny, mats_raw in all_perfect_upgrades:
        tid = int(tid)
        sid = int(sid)
        zeny = int(zeny)

        if tid not in parsed:
            continue

        if sid not in parsed[tid]["slots"]:
            parsed[tid]["slots"][sid] = {
                "enchants": [],
                "perfect": [],
                "upgrade": [],
                "perfect_upgrade": [],
                "random_upgrade": []
            }
        else:
            parsed[tid]["slots"][sid].setdefault("perfect_upgrade", [])

        # 材料
        mats = re.findall(r'\{\s*"([^"]+)"\s*,\s*(\d+)\s*\}', mats_raw)
        materials = [(m_name, int(m_cnt)) for m_name, m_cnt in mats]

        parsed[tid]["slots"][sid]["perfect_upgrade"].append({
            "from": src,
            "to": dst,
            "zeny": zeny,
            "materials": materials
        })
    # --------------------------------------------------
    # 解析 SetRandomUpgradeRequire
    # --------------------------------------------------
    all_random_require = re.findall(
        r'Table\[(\d+)\]\.Slot\[(\d+)\]\:SetRandomUpgradeRequire'
        r'\(\s*"([^"]+)"\s*,\s*(\d+)\s*,\s*((?:\{[^}]+\}\s*,?\s*)+)\)',
        content
    )

    for tid, sid, src, zeny, mats_raw in all_random_require:
        tid = int(tid)
        sid = int(sid)
        zeny = int(zeny)

        if tid not in parsed:
            continue

        parsed[tid]["slots"].setdefault(sid, {
            "enchants": [],
            "perfect": [],
            "upgrade": [],
            "perfect_upgrade": [],
            "random_upgrade": []
        })

        # 多組材料解析
        mats = re.findall(r'\{\s*"([^"]+)"\s*,\s*(\d+)\s*\}', mats_raw)
        materials = [(m_name, int(m_cnt)) for m_name, m_cnt in mats]

        parsed[tid]["slots"][sid].setdefault("random_require", {})

        parsed[tid]["slots"][sid]["random_require"][src] = {
            "zeny": zeny,
            "materials": materials
        }
    # --------------------------------------------------
    # 機率升階 AddRandomUpgradeEnchant
    # --------------------------------------------------
    all_random_upgrades = re.findall(
        r'Table\[(\d+)\]\.Slot\[(\d+)\]\:AddRandomUpgradeEnchant'
        r'\(\s*"([^"]+)"\s*,\s*"([^"]+)"\s*,\s*(\d+)\s*\)',
        content
    )

    for tid, sid, src, dst, rate in all_random_upgrades:
        tid = int(tid)
        sid = int(sid)
        rate = int(rate)

        if tid not in parsed:
            continue

        if sid not in parsed[tid]["slots"]:
            parsed[tid]["slots"][sid] = {
                "enchants": [],
                "perfect": [],
                "upgrade": [],
                "perfect_upgrade": [],
                "random_upgrade": []
            }
        else:
            parsed[tid]["slots"][sid].setdefault("random_upgrade", [])

        parsed[tid]["slots"][sid]["random_upgrade"].append({
            "from": src,
            "to": dst,
            "rate": rate,   # 這個才是真的機率
            "zeny": parsed[tid]["slots"][sid]
                .get("random_require", {})
                .get(src, {})
                .get("zeny", 0),
            "materials": parsed[tid]["slots"][sid]
                .get("random_require", {})
                .get(src, {})
                .get("materials", [])
        })






    print(f"✅ 完成解析，共 {len(parsed)} 組 Table")
    return parsed


# ============================================================
# 附魔目標共用判定
# ============================================================
ENCHANT_CONTENT_KEYS = (
    "enchants",
    "perfect",
    "upgrade",
    "perfect_upgrade",
    "random_upgrade",
)


def enchant_slot_has_content(slot_data):
    """判斷單一洞位是否至少有一筆可顯示／套用的附魔內容。"""
    return (
        isinstance(slot_data, dict)
        and any(slot_data.get(key) for key in ENCHANT_CONTENT_KEYS)
    )


def get_enchant_slot_ids(table_data):
    """回傳 Table 中實際有附魔內容的洞位 ID。"""
    if not isinstance(table_data, dict):
        return set()

    slots = table_data.get("slots", {})
    if not isinstance(slots, dict):
        return set()

    result = set()
    for slot_id, slot_data in slots.items():
        if not enchant_slot_has_content(slot_data):
            continue
        try:
            result.add(int(slot_id))
        except (TypeError, ValueError):
            continue
    return result


def enchant_table_has_content(table_data):
    """判斷附魔 Table 是否至少有一筆可顯示／套用的附魔內容。"""
    return bool(get_enchant_slot_ids(table_data))


def resolve_enchant_target_name(key, item_data, itemdb):
    """將 EnchantList 的 DBName／內部名稱解析為主程式顯示名稱。"""
    item_data = item_data or {}
    itemdb = itemdb or {}

    item_id = itemdb.get(key)
    if item_id is not None:
        item_info = item_data.get(item_id) or item_data.get(str(item_id))
        if isinstance(item_info, dict) and item_info.get("name"):
            return str(item_info["name"])

    key_text = str(key or "").strip()
    for item_info in item_data.values():
        if not isinstance(item_info, dict):
            continue
        if key_text == str(item_info.get("kr_name", "")).strip():
            return str(item_info.get("name") or key_text)

    return key_text


def build_enchant_target_map(enchant_data, item_data, itemdb, require_content=True):
    """建立「顯示裝備名稱 → Enchant Table ID」映射。"""
    target_map = {}

    for table_id, table_data in (enchant_data or {}).items():
        if require_content and not enchant_table_has_content(table_data):
            continue

        for raw_name in table_data.get("target_items", []):
            display_name = resolve_enchant_target_name(raw_name, item_data, itemdb)
            if display_name:
                target_map[display_name] = table_id

    return target_map


# ============================================================
# PySide6 UI
# ============================================================
from PySide6.QtWidgets import (
    QWidget, QListWidget, QTableWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QLabel, QTabWidget, QTableWidgetItem, QHeaderView,
    QGroupBox, QPlainTextEdit
)
from PySide6.QtCore import Qt, Signal, QTimer


def _item_description_to_html(description):
    """將 iteminfo 的說明文字轉成可安全顯示的 HTML，並支援 ^RRGGBB 色碼。"""
    if isinstance(description, str):
        lines = description.splitlines()
    elif isinstance(description, (list, tuple)):
        lines = [str(line) for line in description]
    else:
        lines = []

    if not lines:
        return f"<i>{html.escape(tr('enchant.message.no_item_description'))}</i>"

    html_lines = []
    color_pattern = re.compile(r"\^([0-9a-fA-F]{6})")

    for line in lines:
        parts = []
        cursor = 0
        span_open = False

        for match in color_pattern.finditer(line):
            parts.append(html.escape(line[cursor:match.start()]))
            if span_open:
                parts.append("</span>")
                span_open = False

            color_code = match.group(1)
            # iteminfo 常用 ^000000 表示恢復預設色；不要強制顯示黑色，避免深色主題看不到。
            if color_code.lower() != "000000":
                parts.append(f'<span style="color:#{color_code}">')
                span_open = True
            cursor = match.end()

        parts.append(html.escape(line[cursor:]))
        if span_open:
            parts.append("</span>")
        html_lines.append("".join(parts))

    return "<br>".join(html_lines)



class EnchantTableWidget(QTableWidget):
    """將左右鍵事件分流，並讓右鍵 Tooltip 在放開按鍵後仍保持顯示。"""
    rightCellClicked = Signal(QPoint)

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            pos = event.position().toPoint()
            index = self.indexAt(pos)
            if index.isValid():
                # 按下時只更新目前儲存格；Tooltip 統一在放開後顯示，避免觸發兩次。
                self.setCurrentCell(index.row(), index.column())
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.RightButton:
            pos = event.position().toPoint()
            index = self.indexAt(pos)
            if index.isValid():
                # Qt 可能在 MouseButtonRelease 時自動收起 QToolTip；
                # 等事件處理完後再顯示一次，放開右鍵便不會消失。
                QTimer.singleShot(
                    0,
                    lambda pos=QPoint(pos): self.rightCellClicked.emit(pos)
                )
            event.accept()
            return
        super().mouseReleaseEvent(event)


class EnchantUI(QWidget):
    # 裝備名稱、洞位 ID（0~3）、附魔物品名稱
    enchantApplyRequested = Signal(str, int, str)

    def __init__(
        self,
        enchant_data,
        item_data,
        itemdb,
        initial_equipment_name="",
        target_part_name="",
        initial_slot_id=None,
        initial_slot_enchants=None,
    ):
        super().__init__()

        self.parsed = enchant_data        # EnchantList 解析結果
        self.items = item_data           # iteminfo_new
        self.itemdb = itemdb             # ItemDBNameTbl
        self.target_part_name = target_part_name or ""
        self.initial_equipment_name = initial_equipment_name or ""
        self.initial_slot_id = initial_slot_id
        self.target_slot_enchants = self._normalize_slot_enchants(initial_slot_enchants)

        # 隨機附魔 LOG 只存在於本次工具視窗生命週期，開啟工具時立即顯示。
        # 統計僅保留「使用次數」，不區分成功／失敗。
        self.random_attempt_count = 0
        self._pending_random_attempt = None

        self.setWindowTitle(tr("enchant.window.main"))
        layout = QHBoxLayout(self)

        # ==============================
        # 左區域（搜尋欄 + 裝備列表）
        # ==============================
        left_box = QVBoxLayout()
        layout.addLayout(left_box)

        # ▶ 搜尋欄
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText(
            tr("enchant.placeholder.search_equipment")
        )
        left_box.addWidget(self.search_box)

        # ▶ 裝備列表
        self.list_items = QListWidget()
        left_box.addWidget(self.list_items)

        # ==============================
        # 右：套用目標 + 附魔資訊（Tab）
        # ==============================
        right_box = QVBoxLayout()
        layout.addLayout(right_box, 1)


        self.apply_hint_label = QLabel()
        self.apply_hint_label.setWordWrap(True)
        right_box.addWidget(self.apply_hint_label)

        random_row = QHBoxLayout()
        self.random_enchant_button = QPushButton(
            tr("enchant.button.random_enchant")
        )
        self.random_enchant_button.setToolTip(
            tr("enchant.tooltip.random_enchant")
        )
        self.random_enchant_button.clicked.connect(self.roll_random_enchant)
        random_row.addWidget(self.random_enchant_button)
        #random_row.addStretch(1)
        right_box.addLayout(random_row)
        self.apply_status_label = QLabel("")
        self.apply_status_label.setWordWrap(True)
        right_box.addWidget(self.apply_status_label)

        self.tabs = QTabWidget()
        self.tabs.currentChanged.connect(self._update_random_enchant_button_state)
        right_box.addWidget(self.tabs, 1)

        # ==============================
        # 最右側：隨機附魔 LOG
        # 開啟附魔工具時立即顯示。
        # ==============================
        self.random_log_panel = QGroupBox(tr("enchant.group.random_log"))
        self.random_log_panel.setMinimumWidth(400)
        self.random_log_panel.setMaximumWidth(400)
        log_layout = QVBoxLayout(self.random_log_panel)

        log_header_row = QHBoxLayout()
        self.random_log_summary = QLabel()
        self.random_log_summary.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.random_log_summary.setStyleSheet("font-weight: bold;")
        log_header_row.addWidget(self.random_log_summary)
        log_header_row.addStretch(1)

        self.clear_random_log_button = QPushButton(
            tr("enchant.button.clear_log")
        )
        self.clear_random_log_button.setToolTip(
            tr("enchant.tooltip.clear_log")
        )
        self.clear_random_log_button.clicked.connect(self.clear_random_log)
        log_header_row.addWidget(self.clear_random_log_button)
        log_layout.addLayout(log_header_row)

        self.random_log_view = QPlainTextEdit()
        self.random_log_view.setReadOnly(True)
        self.random_log_view.setPlaceholderText(
            tr("enchant.placeholder.random_log")
        )
        log_layout.addWidget(self.random_log_view, 1)

        layout.addWidget(self.random_log_panel)
        self.random_log_panel.show()
        self._update_random_log_summary()

        # -----------------------------------------------------------
        # 建立：裝備名稱 → 所屬 Enchant Table 映射
        # -----------------------------------------------------------
        self.all_target_items = build_enchant_target_map(
            self.parsed,
            self.items,
            self.itemdb,
            require_content=True,
        )

        # 顯示所有裝備
        #self.full_item_list = sorted(self.all_target_items.keys())
        self.full_item_list = sorted(
        self.all_target_items.keys(),
        key=lambda name: (self.all_target_items[name], name)
    )
        self.refresh_item_list("")
        self.adjust_left_list_width()

        # 綁定搜尋事件
        self.search_box.textChanged.connect(self.refresh_item_list)

        # 點選裝備
        self.list_items.currentTextChanged.connect(self.select_equipment)

        self.set_target_context(
            self.target_part_name,
            self.initial_equipment_name,
            self.target_slot_enchants,
        )
        if self.initial_equipment_name:
            self.select_item_by_name(self.initial_equipment_name)
        if self.initial_slot_id is not None:
            self.select_slot_by_id(self.initial_slot_id)

    @staticmethod
    def _normalize_slot_enchants(slot_enchants):
        """將主畫面四個附魔欄位正規化成固定長度清單。"""
        values = ["", "", "", ""]
        if isinstance(slot_enchants, dict):
            iterator = slot_enchants.items()
        elif isinstance(slot_enchants, (list, tuple)):
            iterator = enumerate(slot_enchants)
        else:
            iterator = []

        for slot_id, value in iterator:
            try:
                slot_id = int(slot_id)
            except (TypeError, ValueError):
                continue
            if 0 <= slot_id < len(values):
                values[slot_id] = str(value or "").strip()
        return values

    def set_target_context(self, part_name="", equipment_name="", slot_enchants=None):
        """更新主畫面目前的紅底裝備欄與四個附魔欄位資訊。"""
        self.target_part_name = part_name or ""
        self.initial_equipment_name = equipment_name or ""
        if slot_enchants is not None:
            self.target_slot_enchants = self._normalize_slot_enchants(slot_enchants)
        elif not self.target_part_name:
            self.target_slot_enchants = ["", "", "", ""]

        if self.target_part_name:
            equip_text = (
                tr(
                    "enchant.label.current_equipment_suffix",
                    equipment=self.initial_equipment_name,
                )
                if self.initial_equipment_name
                else ""
            )
            self.apply_hint_label.setText(
                tr(
                    "enchant.hint.apply_target",
                    part=translate_equipment_part(self.target_part_name),
                    equipment_suffix=equip_text,
                )
            )
        else:
            self.apply_hint_label.setText(
                tr("enchant.hint.no_apply_target")
            )

        self._update_random_enchant_button_state()

    def _update_random_log_summary(self):
        """更新隨機附魔使用次數。"""
        label = getattr(self, "random_log_summary", None)
        if label is None:
            return
        label.setText(
            tr(
                "enchant.label.attempt_count",
                count=self.random_attempt_count,
            )
        )

    def clear_random_log(self, checked=False):
        """清除隨機附魔紀錄與使用次數"""
        self.random_attempt_count = 0
        self._pending_random_attempt = None

        log_view = getattr(self, "random_log_view", None)
        if log_view is not None:
            log_view.clear()

        self._update_random_log_summary()


    def _show_random_log_panel(self):
        """確保最右側的隨機附魔 LOG 維持顯示。"""
        panel = getattr(self, "random_log_panel", None)
        if panel is not None and not panel.isVisible():
            panel.show()

    def _begin_random_attempt(self, context):
        """建立一次隨機附魔嘗試；有效抽選才計入使用次數。"""
        self.random_attempt_count += 1
        self._show_random_log_panel()
        self._pending_random_attempt = {
            "attempt_no": self.random_attempt_count,
            "equipment_name": str(context.get("equipment_name") or ""),
            "slot_id": int(context.get("slot_id", 0)),
            "mode": str(context.get("mode") or ""),
            "current_enchant": str(context.get("current_enchant") or ""),
            "result_text": "",
        }
        self._update_random_log_summary()
        return self._pending_random_attempt

    def _finish_random_attempt(self, success=None, detail=""):
        """完成目前隨機嘗試並寫入右側 LOG；紀錄不標示成功或失敗。"""
        attempt = self._pending_random_attempt
        if not attempt:
            return
        self._pending_random_attempt = None

        equipment_name = (
            attempt.get("equipment_name")
            or tr("enchant.label.unknown_equipment")
        )
        slot_text = tr(
            "enchant.label.slot_number",
            slot=int(attempt.get("slot_id", 0)) + 1,
        )
        result_text = attempt.get("result_text") or str(detail or "").strip()
        if not result_text:
            result_text = tr("enchant.message.no_result")

        log_line = (
            f"#{attempt.get('attempt_no')}｜{equipment_name}｜\n"
            f"{slot_text}｜{result_text}"

        )
        self.random_log_view.appendPlainText(log_line)
        scrollbar = self.random_log_view.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def set_apply_status(self, message, success=False):
        """由主程式回報附魔是否寫入完成；若為隨機抽選，同步完成 LOG 紀錄。"""
        prefix = "✅ " if success else "⚠️ "
        self.apply_status_label.setText(prefix + str(message))
        if self._pending_random_attempt is not None:
            self._finish_random_attempt(bool(success), str(message))

    def select_item_by_name(self, equipment_name):
        """由主畫面的裝備名稱自動定位附魔清單。"""
        equipment_name = str(equipment_name or "").strip()
        if not equipment_name:
            return False

        matches = self.list_items.findItems(equipment_name, Qt.MatchExactly)
        if not matches:
            self.search_box.setText(equipment_name)
            matches = self.list_items.findItems(equipment_name, Qt.MatchExactly)

        if not matches:
            self.set_apply_status(
                tr(
                    "enchant.message.equipment_not_in_list",
                    equipment=equipment_name,
                )
            )
            return False

        self.list_items.setCurrentItem(matches[0])
        self.list_items.scrollToItem(matches[0])
        return True

    def select_slot_by_id(self, slot_id):
        """切換到指定洞位分頁；找不到時維持目前分頁。"""
        try:
            target_slot = int(slot_id)
        except (TypeError, ValueError):
            return False

        for index in range(self.tabs.count()):
            tab = self.tabs.widget(index)
            if tab is not None and tab.property("enchant_slot_id") == target_slot:
                self.tabs.setCurrentIndex(index)
                self._update_random_enchant_button_state()
                return True
        return False

    def _current_slot_context(self):
        """取得目前裝備、Table、洞位與該洞附魔資料。"""
        current_item = self.list_items.currentItem()
        tab = self.tabs.currentWidget()
        if current_item is None or tab is None:
            return None

        equipment_name = current_item.text().strip()
        table_id = self.all_target_items.get(equipment_name)
        if table_id is None:
            return None

        try:
            slot_id = int(tab.property("enchant_slot_id"))
        except (TypeError, ValueError):
            return None

        table_info = self.parsed.get(table_id, {})
        slot_info = table_info.get("slots", {}).get(slot_id, {})
        if not isinstance(slot_info, dict):
            return None

        return equipment_name, table_id, slot_id, slot_info

    def _current_target_enchant(self, slot_id):
        try:
            slot_id = int(slot_id)
        except (TypeError, ValueError):
            return ""
        if 0 <= slot_id < len(self.target_slot_enchants):
            return str(self.target_slot_enchants[slot_id] or "").strip()
        return ""

    @staticmethod
    def _normalize_enchant_name(value):
        return str(value or "").strip().casefold()

    def _enchant_name_matches(self, current_name, raw_name):
        """同時比對顯示名稱與 EnchantList 內部名稱。"""
        current = self._normalize_enchant_name(current_name)
        if not current:
            return False
        return current in {
            self._normalize_enchant_name(raw_name),
            self._normalize_enchant_name(self.resolve_item_name(raw_name)),
        }

    def _random_candidates_for_current_slot(self):
        """優先建立相同來源的機率升階候選，否則建立一般機率附魔候選。"""
        context = self._current_slot_context()
        if context is None:
            return None, []

        equipment_name, table_id, slot_id, slot_info = context
        current_enchant = self._current_target_enchant(slot_id)
        random_upgrades = slot_info.get("random_upgrade", []) or []

        matched_upgrades = []
        if current_enchant:
            for up in random_upgrades:
                if not isinstance(up, dict):
                    continue
                if not self._enchant_name_matches(current_enchant, up.get("from")):
                    continue
                try:
                    rate = max(0, int(up.get("rate", 0)))
                except (TypeError, ValueError):
                    rate = 0
                if rate <= 0 or not up.get("to"):
                    continue
                matched_upgrades.append({
                    "type": "random_upgrade",
                    "from": up.get("from"),
                    "to": up.get("to"),
                    "output_raw": up.get("to"),
                    "output_name": self.resolve_item_name(up.get("to")),
                    "rate": rate,
                })

        if matched_upgrades:
            return {
                "mode": "random_upgrade",
                "equipment_name": equipment_name,
                "table_id": table_id,
                "slot_id": slot_id,
                "current_enchant": current_enchant,
            }, matched_upgrades

        # 同一附魔可能因 Grade 重複出現；輸出相同時合併其機率。
        merged = {}
        for entry in slot_info.get("enchants", []) or []:
            try:
                _grade, raw_name, rate = entry
                rate = max(0, int(rate))
            except (TypeError, ValueError):
                continue
            if not raw_name or rate <= 0:
                continue
            key = str(raw_name)
            if key not in merged:
                merged[key] = {
                    "type": "enchant",
                    "name": raw_name,
                    "output_raw": raw_name,
                    "output_name": self.resolve_item_name(raw_name),
                    "rate": 0,
                }
            merged[key]["rate"] += rate

        return {
            "mode": "enchant",
            "equipment_name": equipment_name,
            "table_id": table_id,
            "slot_id": slot_id,
            "current_enchant": current_enchant,
        }, list(merged.values())

    @staticmethod
    def _effective_candidate_rate_percent(candidate, candidates):
        """回傳與實際抽選一致的顯示機率，範圍固定為 0%～100%。

        EnchantList 通常以 100000 代表 100%。候選總權重未滿 100000 時，
        剩餘權重代表抽選失敗；候選總權重超過 100000 時，抽選會依所有
        候選的相對權重正規化，因此 LOG 也必須顯示正規化後的實際抽中率。
        """
        try:
            selected_weight = max(0, int(candidate.get("rate", 0)))
        except (TypeError, ValueError, AttributeError):
            selected_weight = 0

        total_weight = 0
        for item in candidates or []:
            try:
                total_weight += max(0, int(item.get("rate", 0)))
            except (TypeError, ValueError, AttributeError):
                continue

        if selected_weight <= 0 or total_weight <= 0:
            return 0.0

        denominator = max(100000, total_weight)
        return min(100.0, selected_weight * 100.0 / denominator)

    @staticmethod
    def _format_probability_percent(value):
        """將 0%～100% 機率輸出成精簡且易讀的文字。"""
        try:
            value = max(0.0, min(100.0, float(value)))
        except (TypeError, ValueError):
            value = 0.0
        return f"{value:.3f}".rstrip("0").rstrip(".")

    @staticmethod
    def _pick_weighted_candidate(candidates):
        """依 EnchantList 的十萬分率抽選；總率不足 100% 時保留失敗機率。"""
        weighted = []
        total = 0
        for candidate in candidates:
            try:
                weight = max(0, int(candidate.get("rate", 0)))
            except (TypeError, ValueError):
                weight = 0
            if weight <= 0:
                continue
            weighted.append((candidate, weight))
            total += weight

        if not weighted or total <= 0:
            return None

        # 正常資料以 100000 表示 100%；若資料總和超過 100000，改按相對權重抽選。
        roll_range = max(100000, total)
        roll = random.randrange(roll_range)
        if roll >= total:
            return None

        cumulative = 0
        for candidate, weight in weighted:
            cumulative += weight
            if roll < cumulative:
                return candidate
        return weighted[-1][0]

    def _update_random_enchant_button_state(self, *_):
        button = getattr(self, "random_enchant_button", None)
        if button is None:
            return

        context, candidates = self._random_candidates_for_current_slot()
        enabled = bool(self.target_part_name and context and candidates)
        button.setEnabled(enabled)

        if not self.target_part_name:
            button.setToolTip(tr("enchant.tooltip.select_target_first"))
        elif not context:
            button.setToolTip(tr("enchant.tooltip.no_random_slot"))
        elif context["mode"] == "random_upgrade":
            button.setToolTip(
                tr(
                    "enchant.tooltip.random_upgrade_candidates",
                    enchant=context["current_enchant"],
                    count=len(candidates),
                )
            )
        elif candidates:
            button.setToolTip(tr("enchant.tooltip.random_candidates"))
        else:
            current = (
                context.get("current_enchant")
                or tr("enchant.label.blank")
            )
            button.setToolTip(
                tr(
                    "enchant.tooltip.no_matching_candidates",
                    enchant=current,
                )
            )

    def roll_random_enchant(self, checked=False):
        """依目前洞位資料抽選附魔；機率升階會先按目前附魔自動配對來源。"""
        if not self.target_part_name:
            self.set_apply_status(
                tr("enchant.message.select_target_first")
            )
            return

        context, candidates = self._random_candidates_for_current_slot()
        if not context or not candidates:
            self.set_apply_status(tr("enchant.message.no_random_data"))
            self._update_random_enchant_button_state()
            return

        # 只有真正具備候選、開始抽選時，才顯示 LOG 並計入使用次數。
        attempt = self._begin_random_attempt(context)
        selected = self._pick_weighted_candidate(candidates)
        slot_id = int(context["slot_id"])
        if selected is None:
            failure_text = tr("enchant.message.random_no_result")
            attempt["result_text"] = failure_text
            self.apply_status_label.setText(
                tr(
                    "enchant.status.random_failed",
                    slot=slot_id + 1,
                    reason=failure_text,
                )
            )
            self._finish_random_attempt(False, failure_text)
            return

        output_name = str(selected.get("output_name") or "").strip()
        if not output_name:
            failure_text = tr("enchant.message.random_name_missing")
            attempt["result_text"] = failure_text
            self.apply_status_label.setText(
                tr("enchant.status.warning", message=failure_text)
            )
            self._finish_random_attempt(False, failure_text)
            return

        effective_rate = self._effective_candidate_rate_percent(selected, candidates)
        rate_text = self._format_probability_percent(effective_rate)
        if context["mode"] == "random_upgrade":
            result_text = (
                f"{context['current_enchant']} → {output_name}（{rate_text}%）"
            )
        else:
            result_text = f"{output_name}（{rate_text}%）"

        attempt["result_text"] = result_text
        self.apply_status_label.setText(
            tr(
                "enchant.status.applying_random_result",
                slot=slot_id + 1,
                result=result_text,
            )
        )
        self.enchantApplyRequested.emit(
            context["equipment_name"],
            slot_id,
            output_name,
        )

    def _get_output_enchant_name(self, data):
        """一般附魔回傳自身；升階類型回傳升階後的附魔。"""
        if not data:
            return ""
        raw_name = data.get("to") if data.get("type") in (
            "upgrade", "perfect_upgrade", "random_upgrade"
        ) else data.get("name")
        return self.resolve_item_name(raw_name) if raw_name else ""

    def handle_enchant_click(self, table, sid, row, col):
        """單擊附魔列只顯示材料，不會寫入主畫面裝備欄。"""
        self.show_materials(table, sid, row, col)

    def apply_enchant(self, table, sid, row):
        """按下該列的「套用」按鈕後，才要求主程式寫入對應洞位。"""
        item = table.item(row, 1)
        if not item:
            return

        data = item.data(Qt.UserRole)
        enchant_name = self._get_output_enchant_name(data)
        current_item = self.list_items.currentItem()
        equipment_name = current_item.text() if current_item else ""

        if not equipment_name or not enchant_name:
            self.set_apply_status(
                tr("enchant.message.equipment_or_enchant_missing")
            )
            return

        self.apply_status_label.setText(
            tr(
                "enchant.status.applying",
                equipment=equipment_name,
                slot=int(sid) + 1,
                enchant=enchant_name,
            )
        )
        self.enchantApplyRequested.emit(equipment_name, int(sid), enchant_name)

    def add_apply_button(self, table, sid, row):
        """在指定列建立套用按鈕，並固定綁定該列與洞位。"""
        button = QPushButton(tr("button.apply"))
        button.setToolTip(tr("enchant.tooltip.apply_to_main"))
        button.clicked.connect(
            lambda checked=False, table=table, sid=sid, row=row:
                self.apply_enchant(table, sid, row)
        )
        table.setCellWidget(row, 3, button)

    def _resolve_item_id(self, key):
        """將 DBName、韓文內部名稱或顯示名稱解析成物品 ID。"""
        if not key:
            return None

        item_id = self.itemdb.get(key)
        if item_id is not None and item_id in self.items:
            return int(item_id)

        key_text = str(key).strip()
        for candidate_id, info in self.items.items():
            if not isinstance(info, dict):
                continue
            if key_text in (
                str(info.get("name", "")).strip(),
                str(info.get("kr_name", "")).strip(),
            ):
                try:
                    return int(candidate_id)
                except (TypeError, ValueError):
                    return None
        return None

    def handle_enchant_right_click(self, table, pos):
        """右鍵附魔列：直接在附魔工具內顯示該物品內容。"""
        index = table.indexAt(pos)
        if not index.isValid():
            return

        item = table.item(index.row(), 1)
        if not item:
            return

        data = item.data(Qt.UserRole) or {}
        raw_name = (
            data.get("to")
            if data.get("type") in ("upgrade", "perfect_upgrade", "random_upgrade")
            else data.get("name")
        )
        item_id = self._resolve_item_id(raw_name)
        if item_id is None:
            self.set_apply_status(
                tr(
                    "enchant.message.item_content_not_found",
                    item=self.resolve_item_name(raw_name),
                )
            )
            return


        item_info = self.items.get(item_id)
        if not isinstance(item_info, dict):
            self.set_apply_status(
                tr(
                    "enchant.message.item_data_missing",
                    item=self.resolve_item_name(raw_name),
                )
            )
            return

        display_name = str(item_info.get("name") or self.resolve_item_name(raw_name))
        resource_name = str(
            item_info.get("kr_name")
            or tr("enchant.label.no_data")
        )
        slot_count = item_info.get("slot", 0)
        description_html = _item_description_to_html(item_info.get("description", []))

        # 與左鍵材料顯示相同：直接在滑鼠旁以 Tooltip 顯示，不開新視窗。
        tooltip_html = (
            '<table width="520" cellspacing="0" cellpadding="2">'
            f'<tr><td colspan="2"><b>{html.escape(display_name)}</b></td></tr>'
            #f'<tr><td width="85">物品 ID：</td><td>{html.escape(str(item_id))}</td></tr>'
            #f'<tr><td>內部名稱：</td><td>{html.escape(resource_name)}</td></tr>'
            #f'<tr><td>洞數：</td><td>{html.escape(str(slot_count))}</td></tr>'
            '<tr><td colspan="2"><hr></td></tr>'
            f'<tr><td colspan="2">{description_html}</td></tr>'
            '</table>'
        )

        self.apply_status_label.setText(
            tr("enchant.status.showing_item", item=display_name)
        )
        pos = QCursor.pos() + QPoint(10, -10)
        cell_rect = table.visualRect(index)
        QToolTip.hideText()
        QToolTip.showText(
            pos,
            tooltip_html,
            table.viewport(),
            cell_rect,
            60000,
        )

    def show_materials(self, table, sid, row, col):
        """顯示所點附魔的材料；sid 直接由分頁建立時傳入，避免隱藏空分頁後洞位錯置。"""
        if not table:
            return

        item = table.item(row, 1)
        if not item:
            return

        data = item.data(Qt.UserRole)
        if not data:
            return

        # ---------------------------------------------------------
        # 裝備名稱
        # ---------------------------------------------------------
        current_item = self.list_items.currentItem()
        if not current_item:
            return
        equip_name = current_item.text()

        # ---------------------------------------------------------
        # 附魔類型
        # ---------------------------------------------------------
        type_map = {
            "enchant": tr("enchant.type.random"),
            "perfect": tr("enchant.type.guaranteed"),
            "upgrade": tr("enchant.type.guaranteed_upgrade"),
            "perfect_upgrade": tr("enchant.type.guaranteed_upgrade"),
            "random_upgrade": tr("enchant.type.random_upgrade"),
        }
        type_text = type_map.get(data["type"], tr("button.enchant"))

        # ---------------------------------------------------------
        # 附魔名稱
        # ---------------------------------------------------------
        if data["type"] in ("upgrade", "perfect_upgrade", "random_upgrade"):
            # 升階：from → to
            src = self.resolve_item_name(data["from"])
            dst = self.resolve_item_name(data["to"])
            enchant_name = f"{src} → {dst}"
        else:
            enchant_name = self.resolve_item_name(item.text())

        # ---------------------------------------------------------
        # 機率（沒有 rate = 100%）
        # ---------------------------------------------------------
        if "rate" in data:
            value = data["rate"] / 1000
            rate_text = f"{value:.3f}".rstrip("0").rstrip(".")
            rate_str = f"{rate_text}%"
        else:
            rate_str = "100%"

        # ---------------------------------------------------------
        # 收集材料
        # ---------------------------------------------------------
        mlist = []

        tid = self.all_target_items[equip_name]
        info = self.parsed[tid]
        slot_info = info["slots"].get(sid)

        # 只有機率附魔才加 SetRequire
        if data["type"] == "enchant" and slot_info and "require" in slot_info:
            req = slot_info["require"]

            if req.get("zeny", 0) > 0:
                mlist.append(("Zeny", req["zeny"]))

            for name, cnt in req.get("materials", []):
                mlist.append((self.resolve_item_name(name), cnt))

        # 各類附魔 / 升階自己的金額
        if data.get("zeny", 0) > 0:
            mlist.append(("Zeny", data["zeny"]))

        # 加上自身材料
        for name, cnt in data.get("materials", []):
            mlist.append((self.resolve_item_name(name), cnt))

        # ---------------------------------------------------------
        # 組 Tooltip 文字（符合你要的格式）
        # ---------------------------------------------------------
        msg = tr(
            "enchant.materials.summary",
            equipment=equip_name,
            type=type_text,
            enchant=enchant_name,
            rate=rate_str,
        )

        if not mlist:
            msg += tr("enchant.materials.none")
        else:
            msg += tr("enchant.materials.heading")
            for name, cnt in mlist:
                if name == "Zeny":
                    msg += f"● {name}: {cnt:,}\n"
                else:
                    msg += f"● {name} × {cnt}\n"

        msg = msg.rstrip()

        # ---------------------------------------------------------
        # 顯示 Tooltip
        # ---------------------------------------------------------
        pos = QCursor.pos() + QPoint(10, -10)
        QToolTip.hideText()
        QToolTip.showText(pos, msg, table)




    def adjust_left_list_width(self):
        fm = QFontMetrics(self.list_items.font())
        max_width = 0

        for name in self.full_item_list:
            w = fm.horizontalAdvance(name)
            if w > max_width:
                max_width = w

        # 加上捲軸、邊框的空間（大約）
        max_width += 40

        self.list_items.setMinimumWidth(max_width)
        self.list_items.setMaximumWidth(max_width)
        self.search_box.setMinimumWidth(max_width)
        self.search_box.setMaximumWidth(max_width)
        

    # ==============================
    # 裝備名稱解析（DBName -> id -> 顯示名）
    # ==============================
    def resolve_item_name(self, key: str) -> str:
        display = key

        # ① DBName → item_id → 中文名
        item_id = self.itemdb.get(key)
        if item_id is not None:
            item_info = self.items.get(item_id)
            if item_info:
                return item_info["name"]

        # ② kr_name
        for info in self.items.values():
            if info["kr_name"] == key:
                return info["name"]

        return display

    # ==============================
    # 搜尋 + 重新填入列表
    # ==============================
    def refresh_item_list(self, text):
        text = text.strip().lower()
        self.list_items.clear()

        for name in self.full_item_list:
            if text in name.lower():  # 部分比對
                self.list_items.addItem(name)

    # ==============================
    # 選擇裝備
    # ==============================
    def select_equipment(self, equip_name: str):
        if not equip_name:
            return

        tid = self.all_target_items.get(equip_name)
        if tid is None:
            return

        self.load_all_slots_tabs(tid)
        self._update_random_enchant_button_state()

    # ==============================
    # 顯示該 table 所有 Slots 附魔
    # ==============================
    def load_all_slots_tabs(self, tid):
        self.tabs.clear()

        info = self.parsed.get(tid)
        if not info:
            return

        slot_name_map = {
            0: tr("enchant.slot.first"),
            1: tr("enchant.slot.second"),
            2: tr("enchant.slot.third"),
            3: tr("enchant.slot.fourth"),
        }

        for sid in reversed(info["slot_order"]):
            slot_info = info.get("slots", {}).get(sid)
            if not slot_info:
                continue

            enchants = slot_info.get("enchants", [])
            perfects = slot_info.get("perfect", [])
            upgrades = slot_info.get("upgrade", [])
            perfect_upgrades = slot_info.get("perfect_upgrade", [])
            random_upgrades = slot_info.get("random_upgrade", [])

            total_rows = (
                len(enchants) +
                len(perfects) +
                len(upgrades) +
                len(perfect_upgrades) +
                len(random_upgrades)
            )

            # 該洞沒有任何附魔／升階資料時，不建立分頁。
            if total_rows == 0:
                continue

            tab = QWidget()
            v = QVBoxLayout(tab)

            table = EnchantTableWidget()
            table.setColumnCount(4)
            table.setHorizontalHeaderLabels([
                tr("enchant.column.type"),
                tr("enchant.column.enchant"),
                tr("enchant.column.probability"),
                tr("enchant.column.action"),
            ])
            table.verticalHeader().setVisible(False)
            table.cellClicked.connect(
                lambda row, col, table=table, sid=sid: self.handle_enchant_click(
                    table, sid, row, col
                )
            )
            table.rightCellClicked.connect(
                lambda pos, table=table: self.handle_enchant_right_click(table, pos)
            )

            header = table.horizontalHeader()
            header.setSectionResizeMode(0, QHeaderView.Fixed)
            header.setSectionResizeMode(2, QHeaderView.Fixed)
            header.setSectionResizeMode(3, QHeaderView.Fixed)
            header.resizeSection(0, 80)
            header.resizeSection(2, 80)
            header.resizeSection(3, 72)
            header.setSectionResizeMode(1, QHeaderView.Stretch)

            table.setRowCount(total_rows)
            v.addWidget(table)

            title = slot_name_map.get(
                sid,
                tr("enchant.label.slot_number", slot=sid),
            )
            tab.setProperty("enchant_slot_id", int(sid))
            self.tabs.addTab(tab, title)

            row = 0

            # --------------------------------------------------
            # 合併一般附魔：只看名稱 + 機率，不看 Grade
            # --------------------------------------------------
            merged = {}  # key = (name, rate) → value = True

            for grade, name, rate in enchants:
            #     key = (name, rate)
            #     merged[key] = True  # 重複會自動覆蓋

            # # 寫入表格
            # for (name, rate) in merged.keys():
                table.setItem(
                    row,
                    0,
                    QTableWidgetItem(tr("enchant.type.random")),
                )
                item = QTableWidgetItem(self.resolve_item_name(name))
                item.setData(Qt.UserRole, {
                    "type": "enchant",
                    "name": name,
                    "rate": rate 
                })
                table.setItem(row, 1, item)
                table.setItem(row, 2, QTableWidgetItem(f"{rate/1000:.3f}"))
                value = rate / 1000
                text = f"{value:.3f}".rstrip('0').rstrip('.')
                table.setItem(row, 2, QTableWidgetItem(f"{text}%"))
                self.add_apply_button(table, sid, row)
                row += 1


            # 完美附魔
            for p in perfects:
                table.setItem(
                    row,
                    0,
                    QTableWidgetItem(tr("enchant.type.guaranteed")),
                )
                item = QTableWidgetItem(self.resolve_item_name(p["name"]))
                item.setData(Qt.UserRole, {
                    "type": "perfect",
                    "name": p["name"],
                    "zeny": p.get("zeny", 0),
                    "materials": p["materials"],
                })
                table.setItem(row, 1, item)

                table.setItem(row, 2, QTableWidgetItem("100%"))
                self.add_apply_button(table, sid, row)
                row += 1

            # 升階 目前沒有物品會附魔失敗，都先寫100%
            for up in upgrades:
                src = self.resolve_item_name(up["from"])
                dst = self.resolve_item_name(up["to"])
                table.setItem(
                    row,
                    0,
                    QTableWidgetItem(tr("enchant.type.guaranteed_upgrade")),
                )
                item = QTableWidgetItem(f"{src} → {dst}")
                item.setData(Qt.UserRole, {
                    "type": "upgrade",
                    "from": up["from"],
                    "to": up["to"],
                    "zeny": up.get("zeny", 0),
                    "materials": up["materials"],
                })
                table.setItem(row, 1, item)

                table.setItem(row, 2, QTableWidgetItem("100%"))#(f"{up['rate']/1000:.3f}"))

                self.add_apply_button(table, sid, row)
                row += 1

            # 完美升階
            for up in perfect_upgrades:
                src = self.resolve_item_name(up["from"])
                dst = self.resolve_item_name(up["to"])
                table.setItem(
                    row,
                    0,
                    QTableWidgetItem(tr("enchant.type.guaranteed_upgrade")),
                )
                item = QTableWidgetItem(f"{src} → {dst}")
                item.setData(Qt.UserRole, {
                    "type": "perfect_upgrade",
                    "from": up["from"],
                    "to": up["to"],
                    "zeny": up.get("zeny", 0),
                    "materials": up.get("materials", [])
                })
                table.setItem(row, 1, item)
                table.setItem(row, 2, QTableWidgetItem("100%"))
                self.add_apply_button(table, sid, row)
                row += 1

            # 機率升階
            for up in random_upgrades:
                src = self.resolve_item_name(up["from"])
                dst = self.resolve_item_name(up["to"])
                table.setItem(
                    row,
                    0,
                    QTableWidgetItem(tr("enchant.type.random_upgrade")),
                )
                item = QTableWidgetItem(f"{src} → {dst}")
                item.setData(Qt.UserRole, {
                    "type": "random_upgrade",
                    "from": up["from"],
                    "to": up["to"],
                    "rate": up["rate"],
                    "zeny": up.get("zeny", 0),
                    "materials": up.get("materials", [])
                })
                table.setItem(row, 1, item)

                #table.setItem(row, 2, QTableWidgetItem(f"{up['rate']/1000:.3f}"))
                value = up['rate'] / 1000
                text = f"{value:.3f}".rstrip('0').rstrip('.')
                table.setItem(row, 2, QTableWidgetItem(f"{text}%"))
                self.add_apply_button(table, sid, row)
                row += 1

        self._update_random_enchant_button_state()


# ---------------------------------------------------------------
# Main
# ---------------------------------------------------------------
def main():
    app = QApplication(sys.argv)

    # base_dir = os.path.dirname(os.path.abspath(__file__))
    # item_path = os.path.join(base_dir, "data", "iteminfo_new.lua")
    # enchant_path = os.path.join(base_dir, "data", "EnchantList.lua")
    # itemdb_path = os.path.join(base_dir, "data", "ItemDBNameTbl.lua")

    # iteminfo = parse_lub_file(item_path)
    # enchant = parse_enchant_list(enchant_path)
    # itemdb = parse_itemdb_name_tbl(itemdb_path)

    # ui = EnchantUI(enchant, iteminfo, itemdb)
    # ui.resize(900, 600)
    # ui.show()
    # sys.exit(app.exec())


if __name__ == "__main__":
    main()
