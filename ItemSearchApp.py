#部分資料取自ROCalculator,搜尋 ROCalculator 可以知道哪些有使用
Version = "v0.1.36-260127"

import sys, builtins, time
from PySide6.QtCore import QThread, Signal, Qt, QMetaObject, QTimer
from PySide6.QtWidgets import QApplication, QDialog, QVBoxLayout, QPlainTextEdit, QLabel
import enchant #載入附魔工具
import skill_tree #載入技能樹
import reform_viewer #載入改造工具
from rrf_to_App import run_rrf_main#載入rrf轉換
from monster_lookup_dialog import MonsterLookupDialog#查詢怪物
import requests
class InitWorker(QThread):
    log_signal = Signal(str)
    progress_signal = Signal(str)
    done_signal = Signal(object)
    
    def __init__(self, app_instance=None):
        super().__init__()
        self.app_instance = app_instance  # 接收主程式的物件

    def run(self):
        original_print = builtins.print

        def custom_print(*args, **kwargs):
            msg = " ".join(str(a) for a in args)
            end = kwargs.get("end", "\n")

            if end == "\r":
                self.progress_signal.emit(msg)
            else:
                self.log_signal.emit(msg)

            # ✅ 同時即時印出（不等事件迴圈）
            original_print(*args, **kwargs, flush=True)


        builtins.print = custom_print

        try:
            #print("開始載入資料...")
            data = None
            if self.app_instance:
                mode = "online_only"
                if self.app_instance and hasattr(self.app_instance, "get_update_mode"):
                    mode = self.app_instance.get_update_mode() or "online_only"
                data = self.app_instance.dataloading(mode=mode)

            #print("載入完成！")
            self.done_signal.emit(data) 
        except Exception as e:
            print(f"初始化發生錯誤：{e}")
        finally:
            builtins.print = original_print

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextBrowser
)
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices


class UpdateDialog(QDialog):#顯示更新內容
    def __init__(self, local_ver: str, remote_ver: str, notes_md: str, release_url: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("有新版本")
        self.setModal(True)
        self.resize(640, 520)

        layout = QVBoxLayout(self)

        title = QLabel(f"目前版本：{local_ver}　　最新版本：{remote_ver}")
        title.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(title)

        link = QLabel(f'<a href="{release_url}">前往 Release 頁面</a>')
        link.setOpenExternalLinks(True)
        layout.addWidget(link)

        self.browser = QTextBrowser()
        # 讓 QTextBrowser 顯示 markdown（PySide6 支援 setMarkdown）
        self.browser.setMarkdown(notes_md if notes_md.strip() else "(此版本沒有填寫更新內容)")
        self.browser.setReadOnly(True)

        # 點連結開外部瀏覽器（避免某些情況下內建行為不一致）
        self.browser.setOpenExternalLinks(False)
        self.browser.anchorClicked.connect(lambda url: QDesktopServices.openUrl(QUrl(url.toString())))

        layout.addWidget(self.browser, 1)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)

        self.btn_update = QPushButton("立即更新")
        self.btn_cancel = QPushButton("稍後再說")

        self.btn_update.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)

        btn_row.addWidget(self.btn_update)
        btn_row.addWidget(self.btn_cancel)
        layout.addLayout(btn_row)



class LoadingDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("初始化中…")
        self.resize(500, 200)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

        layout = QVBoxLayout(self)

        self.label = QLabel("正在載入資料，請稍候...")
        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)

        layout.addWidget(self.label)
        layout.addWidget(self.text)

    def append_text(self, msg: str):
        self.text.appendPlainText(msg)

    def update_progress(self, msg: str):
        self.label.setText(msg)



import os
import subprocess

def compile_ui_files(ui_dir="UI"):
    """
    將 ui_dir 資料夾下的所有 .ui 檔案轉換成 .py
    """
    for file in os.listdir(ui_dir):
        if file.endswith(".ui"):
            ui_path = os.path.join(ui_dir, file)
            py_path = os.path.splitext(ui_path)[0] + ".py"

            # 呼叫 pyside6-uic
            cmd = ["pyside6-uic", ui_path, "-o", py_path]
            print(f"[UI] 轉換 {ui_path} → {py_path}")
            try:
                subprocess.run(cmd, check=True, shell=True)
            except Exception as e:
                print(f"[UI] 轉換失敗: {e}")

# === 主程式執行前，先自動轉換 UI ===
compile_ui_files()

import importlib.util
import sys
import re
import subprocess
import os
import json
import math
from collections import defaultdict
import pandas as pd
from PySide6.QtCore import Qt,QThread, Signal ,QTimer, QPoint
from PySide6.QtGui import QFont ,QAction,QIntValidator,QPalette, QColor
from sympy import sympify, symbols, Symbol
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLineEdit, QLabel,QGroupBox, QToolButton,QSizePolicy,
    QComboBox, QTextEdit, QMessageBox, QHBoxLayout, QScrollArea, QCheckBox, QMenuBar, QFileDialog,
    QPushButton, QTabWidget, QFormLayout, QSpinBox  ,QDoubleSpinBox  ,QFrame , QGridLayout,QDialog, QListWidget, QButtonGroup,QSlider,
)

from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime

enabled_skill_levels = {}  # 存放已啟用技能的等級
Use_skill_levels = {}#已啟用的技能id
global_weapon_level_map = {}#武器等級
global_armor_weapon_map = {}#裝備類型(防具武器)
global_armor_level_map = {}#防具等級
global_weapon_type_map = {}#武器類型
global_weapon_atk_map = {}#武器基礎攻擊力
global_weapon_matk_map = {}#武器基礎魔法攻擊力
function_defs = {}#公式變數字典
slot_item_id_map = {}#部位裝備的ID
def register_function(name, desc, args):
    if name in function_defs:
        return  # 已經有了就跳過
    function_defs[name] = {
        "desc": desc,
        "args": args
    }


def load_python_dict(path, var_name):
    """
    從外部 .py 檔載入指定變數。
    
    path: 外部 .py 檔案路徑
    var_name: 要讀取的 dict 變數名稱，例如 'all_skill_entries'
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"外部資料檔不存在: {path}")

    spec = importlib.util.spec_from_file_location("external_module", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if not hasattr(module, var_name):
        raise AttributeError(f"{path} 裡找不到變數: {var_name}")

    return getattr(module, var_name)


class DataRegistry:
    """
    用於統一管理所有外部 py 資料來源。
    key = 資料名稱（如：skill, job）
    value = {
        "path": 本地路徑,
        "var_name": py 裡的變數名稱,
        "default": 預設 fallback dict,
        "on_reload": 重新載入後要執行的 callback（例如 UI 更新）
    }
    """
    sources = {}

    loaded_data = {}   # 儲存已載入的資料，如：loaded_data["skill"] = {...}
    window = None   # 🔥 讓 UI 建好後再塞進來
    @classmethod
    def register(cls, key, path, var_name, default, on_reload=None):
        cls.sources[key] = {
            "path": path,
            "var_name": var_name,
            "default": default,
            "on_reload": on_reload,
        }

    @classmethod
    def load(cls, key):
        info = cls.sources[key]
        path = info["path"]
        var_name = info["var_name"]

        try:
            data = load_python_dict(path, var_name)
            cls.loaded_data[key] = data
            print(f"✓ 載入 {key} 成功")
        except Exception as e:
            print(f"⚠️ 載入 {key} 失敗，使用預設值：{e}")
            cls.loaded_data[key] = info["default"]

        return cls.loaded_data[key]

    @classmethod
    def reload_all(cls):
        print("=== 重新載入所有資料來源 ===")

        for key, info in cls.sources.items():
            cls.load(key)

            cb = info["on_reload"]
            if cb and cls.window:
                cb(cls.window)   # 把 window 實體傳進 callback



 # 註冊 all_skill_entries
DataRegistry.register(
    key="skills",
    path="data/all_skill_entries.py",
    var_name="all_skill_entries",
    default={},
    on_reload=lambda win: win.rebuild_skill_tab()  # UI 更新
)

# 註冊 job_dict
DataRegistry.register(
    key="jobs",
    path="data/job_dict.py",
    var_name="job_dict",
    default={
    0: {"id": "","id_jobneme": "","id_jobneme_OL": "","selectskill": "", "name": "沒有資料", "TJobMaxPoint": [0,0,0,0,0,0,0,0,0,0,0,0],"point":"0"}}, 
    on_reload=lambda win: win.reload_job_list()  # 若職業列表要更新
)

DataRegistry.register(
    key="jobHPSP",
    path="data/job_dict.py",
    var_name="job_4th_hpsp",
    default={},
    on_reload=lambda win: win.reload_job_list()  # 若職業列表要更新
)

DataRegistry.register(
    key="ASPD",
    path="data/job_dict.py",
    var_name="WPASPDdata",
    default={
    0: {0:144}},
    on_reload=lambda win: win.reload_job_list()  # 若職業列表要更新
)
# 外部py載入清單
DataRegistry.reload_all()#先讀取所有外部py並設定預設
all_skill_entries = DataRegistry.loaded_data["skills"]# 載入技能效果資料
job_dict  = DataRegistry.loaded_data["jobs"]#職業job_id
job_4th_hpsp = DataRegistry.loaded_data["jobHPSP"]#HPSP
WPASPDdata = DataRegistry.loaded_data["ASPD"]#攻速資料


effect_map = {
    41: "ATK", 45: "DEF", 47: "MDEF", 49: "HIT", 50: "FLEE", 51: "完全迴避", 52: "CRI", 54: "ASPD",
    103: "STR", 104: "AGI", 105: "VIT", 106: "INT", 107: "DEX", 108: "LUK",
    109: "MHP", 110: "MSP", 111: "MHP%", 112: "MSP%", 113: "HP自然恢復%", 114: "SP自然恢復%",
    140: "MATK%", 167: "攻擊後延遲", 200: "MATK", 207: "ATK%",
    234: "POW", 235: "STA", 236: "WIS", 237: "SPL", 238: "CON", 239: "CRT",
    242: "P.ATK", 243: "S.MATK", 244: "RES", 245: "MRES",
    253: "C.RATE", 254: "H.PLUS",
    #非官方編碼 用於二轉以下的技能跟集中覺醒波色克藥水
    301: "(2轉以下)攻擊後延遲",302: "(2轉以下)ASPD"
}
element_map = {
    0: "無屬性",
    1: "水屬性",
    2: "地屬性",
    3: "火屬性",
    4: "風屬性",
    5: "毒屬性",
    6: "聖屬性",
    7: "暗屬性",
    8: "念屬性",
    9: "不死屬性",
    10: "全屬性",
    999: "（不使用）"
}

size_map = {
    0: "小型",
    1: "中型",
    2: "大型"
}

race_map = {
    0: "無形",
    1: "不死",
    2: "動物",
    3: "植物",
    4: "昆蟲",
    5: "魚貝",
    6: "惡魔",
    7: "人形",
    8: "天使",
    9: "龍族",
    10: "玩家（人類）",
    11: "玩家（貓族）",
    9999: "全種族"
}

unit_map = {
    0: "玩家",
    1: "魔物"
}

class_map = {
    0: "一般",
    1: "首領",
    2: "監護人"
    #2: "玩家"
}




stat_name_sets  = {#裝備基礎編碼
    "armor": [
        "DEF", "STR", "AGI", "VIT", "INT", "DEX", "LUK", "未知7", "未知8",
        "MDEF", "防具等級", "POW", "SPL", "STA", "WIS", "CON", "CRT"
    ],
    "Mweapon": [
        "武器屬性", "武器類型", "武器ATK", "武器MATK", "STR", "INT", "VIT", "DEX", "AGI",
        "LUK", "武器等級", "POW", "SPL", "STA", "WIS", "CON", "CRT"
    ],
    "Rweapon": [
        "武器類型", "武器ATK", "STR", "INT", "VIT", "DEX", "AGI", "LUK", "武器等級",
         "POW", "SPL", "STA", "WIS", "CON", "CRT"
    ],
    "ammo": [
        "屬性", "箭矢/彈藥ATK"
    ]
}


weapon_type_map = {
    0: "空手",1: "短劍", 2: "單手劍", 3: "雙手劍", 4: "單手矛", 5: "雙手矛",
    6: "單手斧", 7: "雙手斧", 8: "鈍器", 10: "單手仗", 12: "拳套",
    13: "樂器", 14: "鞭子", 15: "書", 16: "拳刃", 23: "雙手仗",
    11: "弓", 17: "左輪手槍", 18: "來福槍", 19: "格林機關槍",
    20: "霰彈槍", 21: "榴彈槍", 22: "風魔飛鏢"
}

weapon_class_codes = {#輸出用
    0: "Empty",# 空手
    1: "Daggers",  # 短劍
    2: "OneHandedSwords",  # 單手劍
    3: "TwoHandedSword",  # 雙手劍
    4: "Spears",  # 單手矛
    5: "Spears",  # 雙手矛
    6: "Axes",  # 單手斧
    7: "Axes",  # 雙手斧
    8: "Maces",  # 鈍器
    10: "Rods",  # 單手仗
    11: "Bows",  # 弓
    12: "Knuckles",  # 拳套
    13: "Instruments",  # 樂器
    14: "Whips",  # 鞭子
    15: "Books",  # 書
    16: "Katars",  # 拳刃
    17: "Guns",  # 左輪手槍
    18: "Guns",  # 來福槍
    19: "Guns",  # 格林機關槍
    20: "Guns",  # 霰彈槍
    21: "Guns",  # 榴彈槍
    22: "Shuriken",  # 風魔飛鏢
    23: "Rods",  # 雙手仗
}
#weapon_class
weapon_type_size_penalty = {#物體武器體型修正
    0: [100, 100, 100],# 空手
    1: [100, 75, 50],  # 短劍
    2: [75, 100, 75],  # 單手劍
    3: [75, 75, 100],  # 雙手劍
    4: [75, 75, 100],  # 單手矛
    5: [75, 75, 100],  # 雙手矛
    6: [50, 75, 100],  # 單手斧
    7: [50, 75, 100],  # 雙手斧
    8: [75, 100, 100],  # 鈍器
    10: [100, 100, 100],  # 單手仗
    11: [100, 100, 75],  # 弓
    12: [100, 100, 75],  # 拳套
    13: [75, 100, 75],  # 樂器
    14: [75, 100, 50],  # 鞭子
    15: [100, 100, 50],  # 書
    16: [75, 100, 75],  # 拳刃
    17: [100, 100, 100],  # 左輪手槍
    18: [100, 100, 100],  # 來福槍
    19: [100, 100, 100],  # 格林機關槍
    20: [100, 100, 100],  # 霰彈槍
    21: [100, 100, 100],  # 榴彈槍
    22: [75, 75, 100],  # 風魔飛鏢
    23: [100, 100, 100],  # 雙手仗

}




excluded_stat_names = {#過濾不顯示到效果
    "防具等級","武器等級","武器類型"
    }

# 定義多組排序規則
custom_sort_orders = {
    "增傷詞條": [
        "ATK",
        "MATK",
        "P.ATK",
        "S.MATK",
        "屬性 的",
        "小型",
        "中型",
        "大型",
        "全種族",
        "型怪",
        "全屬性",
        "對象",
        "階級",
        "距離",
        "防禦",
        "技能",
        "詠唱",
    ],
    "ROCalculator輸入": [
        "STR",
        "AGI",
        "VIT",
        "INT",
        "DEX",
        "LUK",
        "POW",
        "STA",
        "WIS",
        "SPL",
        "CON",
        "CRT",
        "技能",
        "CRI",
        "P.ATK",
        "S.MATK",
        "ATK",
        "全種族",
        "型怪",
        "小型",
        "中型",
        "大型",
        "階級",
        "全屬性",
        "對象",
        "魔法傷害",
        "爆擊傷害",
        "C.RATE",
        "距離",
    ],
}

def get_custom_sort_value(key, sort_mode):
    """依照指定 sort_mode 的順序表來決定排序位置"""
    order_list = custom_sort_orders.get(sort_mode, [])
    for idx, keyword in enumerate(order_list):
        if keyword in key:
            return idx
    return len(order_list)  # 沒找到的放最後


# 屬性倍率表（level, attacker, defender）

# Lv1 ~ Lv4 相剋表（依 element_map 順序）
damage_tables = {
    1: [ #無   水   地    火   風   毒    聖    暗   念  不死
        [100, 100, 100, 100, 100, 100, 100, 100,  90, 100],
        [100,  25, 100, 150,  90, 150, 100, 100, 100, 100],
        [100, 100,  25,  90, 150, 150, 100, 100, 100, 100],
        [100,  90, 150,  25, 100, 150, 100, 100, 100, 125],
        [100, 150,  90, 100,  25, 150, 100, 100, 100, 100],
        [100, 150, 150, 150, 150,   0,  75,  75,  75,  75],
        [100, 100, 100, 100, 100,  75,   0, 125, 100, 125],
        [100, 100, 100, 100, 100,  75, 125,   0, 100,   0],
        [ 90, 100, 100, 100, 100,  75,  90,  90, 125, 100],
        [100,  90, 100, 100, 100,  75, 125,   0, 100,   0],
    ],
    2: [ #無   水   地    火   風   毒    聖    暗   念  不死
        [100, 100, 100, 100, 100, 100, 100, 100,  70, 100],
        [100,   0, 100, 175,  80, 150, 100, 100, 100, 100],
        [100, 100,   0,  80, 175, 150, 100, 100, 100, 100],
        [100,  80, 175,   0, 100, 150, 100, 100, 100, 150],
        [100, 175,  80, 100,   0, 150, 100, 100, 100, 100],
        [100, 150, 150, 150, 150,   0,  75,  75,  75,  50],
        [100, 100, 100, 100, 100,  75,   0, 150, 100, 150],
        [100, 100, 100, 100, 100,  75, 150,   0, 100,   0],
        [ 70, 100, 100, 100, 100,  75,  80,  80, 150, 125],
        [100,  80, 100, 100, 100,  50, 150,   0, 125,   0],
    ],
    3: [ #無   水   地    火   風   毒    聖    暗   念  不死
        [100, 100, 100, 100, 100, 100, 100, 100,  50, 100],
        [100,   0, 100, 200,  70, 125, 100, 100, 100, 100],
        [100, 100,   0,  70, 200, 125, 100, 100, 100, 100],
        [100,  70, 200,   0, 100, 125, 100, 100, 100, 175],
        [100, 200,  70, 100,   0, 125, 100, 100, 100, 100],
        [100, 125, 125, 125, 125,   0,  50,  50,  50,  25],
        [100, 100, 100, 100, 100,  50,   0, 175, 100, 175],
        [100, 100, 100, 100, 100,  50, 175,   0, 100,   0],
        [ 50, 100, 100, 100, 100,  50,  70,  70, 175, 150],
        [100,  70, 100, 100, 100,  25, 175,   0, 150,   0],
    ],
    4: [ #無   水   地    火   風   毒    聖    暗   念  不死
        [100, 100, 100, 100, 100, 100, 100, 100,   0, 100],
        [100,   0, 100, 200,  60, 125, 100, 100, 100, 100],
        [100, 100,   0,  60, 200, 125, 100, 100, 100, 100],
        [100,  60, 200,   0, 100, 125, 100, 100, 100, 200],
        [100, 200,  60, 100,   0, 125, 100, 100, 100, 100],
        [100, 125, 125, 125, 125,   0,  50,  50,  50,   0],
        [100, 100, 100, 100, 100,  50,   0, 200, 100, 200],
        [100, 100, 100, 100, 100,  50, 200,   0, 100,   0],
        [  0, 100, 100, 100, 100,  50,  60,  60, 200, 175],
        [100,  60, 100, 100, 100,   0, 200,   0, 175,   0],
    ]
}


equipid_mapping = {#主程式equip to ROCalculator 轉換
    "equip_STR": "STR",
    "equip_AGI": "AGI",
    "equip_VIT": "VIT",
    "equip_INT": "INT",
    "equip_DEX": "DEX",
    "equip_LUK": "LUK",
    "equip_POW": "POW",
    "equip_STA": "STA",
    "equip_WIS": "WIS",
    "equip_SPL": "SPL",
    "equip_CON": "CON",
    "equip_CRT": "CRT",
    "Use_Skills": "SkillDamagePercent",
    "HP":"HP",
    "HPPercent":"HPPercent",
    "SP":"SP",
    "SPPercent":"SPPercent",
    "HPRegenPercent":"HPRegenPercent",
    "SPRegenPercent":"SPRegenPercent",

    #魔法
    "SMATK": "SMATK",
    "MATK_armor": "Matk",
    "MATK_percent": "MatkPercent",
    "RaceMatkPercent": "RaceMatkPercent",
    "SizeMatkPercent": "SizeMatkPercent",
    "LevelMatkPercent": "LevelMatkPercent",
    "ElementalMatkPercent": "ElementalMatkPercent",
    "ElementalMagicPercent": "ElementalMagicPercent",
    "target_monsterMDamage": "MonsterMatkPercent",

    #物理
    "PATK": "PATK",
    "CRATE":"CRIDR",
    "ATK_armor": "Atk",
    "ATK_percent": "AtkPercent",
    "RaceAtkPercent": "RaceAtkPercent",
    "SizeAtkPercent": "SizeAtkPercent",
    "LevelAtkPercent": "LevelAtkPercent",
    "ElementalAtkPercent": "ElementalAtkPercent",
    "Damage_CRI": "CriDamagePercent",
    "MeleeAttackDamage": "MeleeDamagePercent",
    "RangeAttackDamage": "RangedDamagePercent",
    "target_monsterDamage": "MonsterAtkPercent",
    "Damage_HIT": "HitAtkDamagePercent",
}

status_mapping = {#主程式status to ROCalculator 轉換
    "BaseLv": "Level",
    "JobLv": "JOBLevel",
    "job_idcore": "classid",
    "base_STR": "STR",
    "base_AGI": "AGI",
    "base_VIT": "VIT",
    "base_INT": "INT",
    "base_DEX": "DEX",
    "base_LUK": "LUK",
    "base_POW": "POW",
    "base_STA": "STA",
    "base_WIS": "WIS",
    "base_SPL": "SPL",
    "base_CON": "CON",
    "base_CRT": "CRT",
}

weapon_mapping = {#主程式weapon to ROCalculator 轉換
    "weapon_codes": ("type", "id"),
    "weapon_weapon_size0": ("type", "sizefix", "small"),
    "weapon_weapon_size1": ("type", "sizefix", "middle"),
    "weapon_weapon_size2": ("type", "sizefix", "large"),
    "weaponR_Level": ("level", "id"),
    "weaponGradeR": ("grade", "id"),
    "ATK_Mweapon": "ATK",
    "MATK_Mweapon": "MATK",
    "weaponRefineR": "refinelevel",
    "ammoATK": "ArrowATK"
}

SubWeapon_mapping = {#主程式Subweapon to ROCalculator 轉換
    "Subweapon_codes": ("type", "id"),
    "weaponL_Level": ("level", "id"),
    "weaponGradeL": ("grade", "id"),
    "MATK_MweaponL": "MATK",
    "weaponRefineL": "refinelevel"
}


TSTATUS_POINT_COSTS = [#取自ROCalculator(特性數值點術 
    7,10,13,16,19,26,29,32,35,38,
    45,48,51,54,57,64,67,70,73,76,
    83,86,89,92,95,102,105,108,111,114,
    121,124,127,130,133,140,143,146,149,152,
    159,162,165,168,171,178,181,184,187,190,
    197,200,203,206,209,216,219,222,225,228,
    235,238,241,244,247,254,257,260,263,266,
    273,276,279,282,285,292
]


from PySide6.QtCore import Qt, QElapsedTimer, QTimer
from PySide6.QtWidgets import QWidget
from PySide6 import QtGui

class CastBarWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        # durations
        self._cast_ms = 1
        self._gcd_ms = 0
        self._cd_ms = 0

        # timers
        self._cast_elapsed = QElapsedTimer()
        self._gcd_elapsed = QElapsedTimer()
        self._cd_elapsed = QElapsedTimer()

        # progress
        self._cast_progress = 0.0
        self._gcd_progress = 0.0
        self._cd_progress = 0.0

        # state
        self._state = "idle"  # idle | cast | post

        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self.update)

        self.setFixedHeight(10)

    def start(self, cast_ms: int, gcd_ms: int = 0, cooldown_ms: int = 0):
        self._cast_ms = max(1, int(cast_ms))
        self._gcd_ms = max(0, int(gcd_ms))
        self._cd_ms = max(0, int(cooldown_ms))

        self._cast_elapsed.restart()
        self._cast_progress = 0.0

        self._gcd_progress = 0.0
        self._cd_progress = 0.0

        self._state = "cast"
        self._timer.start()
        self.update()

    def stop(self):
        self._timer.stop()
        self._state = "idle"
        self._cast_progress = 0.0
        self._gcd_progress = 0.0
        self._cd_progress = 0.0
        self.update()

    def _enter_post(self):
        """詠唱結束後：綠色滿格，開始跑 GCD / CD（覆蓋都要留下）"""
        self._state = "post"
        self._cast_progress = 1.0  # 綠色滿格保留

        # GCD：沒有時間也要直接蓋滿（照你「沒有就直接蓋上」的規則）
        if self._gcd_ms > 0:
            self._gcd_elapsed.restart()
            self._gcd_progress = 0.0
        else:
            self._gcd_progress = 1.0  # 直接 100% 淺藍覆蓋

        # CD：沒有時間也直接蓋滿
        if self._cd_ms > 0:
            self._cd_elapsed.restart()
            self._cd_progress = 0.0
        else:
            self._cd_progress = 1.0  # 直接 100% 灰色覆蓋

    def paintEvent(self, event):
        # ---------- update ----------
        if self._timer.isActive():
            if self._state == "cast":
                t = self._cast_elapsed.elapsed()
                self._cast_progress = min(1.0, t / self._cast_ms)
                if self._cast_progress >= 1.0:
                    self._enter_post()

            elif self._state == "post":
                # GCD progress
                if self._gcd_ms > 0 and self._gcd_progress < 1.0:
                    t = self._gcd_elapsed.elapsed()
                    self._gcd_progress = min(1.0, t / self._gcd_ms)
                    if self._gcd_progress >= 1.0:
                        self._gcd_progress = 1.0  # 跑完也留下

                # CD progress
                if self._cd_ms > 0 and self._cd_progress < 1.0:
                    t = self._cd_elapsed.elapsed()
                    self._cd_progress = min(1.0, t / self._cd_ms)
                    if self._cd_progress >= 1.0:
                        self._cd_progress = 1.0  # 跑完也留下

                # 都不動了就停 timer（覆蓋留著也不需要一直刷新）
                animating = (
                    (self._gcd_ms > 0 and self._gcd_progress < 1.0) or
                    (self._cd_ms > 0 and self._cd_progress < 1.0)
                )
                if not animating:
                    self._timer.stop()

        # ---------- paint ----------
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing, False)

        rect = self.rect().adjusted(0, 0, -1, -1)

        # border
        p.setPen(QtGui.QPen(QtGui.QColor(120, 120, 120)))
        p.setBrush(Qt.NoBrush)
        p.drawRect(rect)

        # green: cast grows, post stays full
        if self._state == "cast":
            green_ratio = self._cast_progress
        elif self._state == "post":
            green_ratio = 1.0
        else:
            green_ratio = 0.0

        green_w = int(rect.width() * green_ratio)
        if green_w > 0:
            green_rect = rect.adjusted(1, 1, -(rect.width() - green_w) - 1, -1)
            p.setPen(Qt.NoPen)
            p.setBrush(QtGui.QColor(0, 200, 0))
            p.drawRect(green_rect)

        # GCD overlay: light-blue, LEFT -> RIGHT, stays when finished
        if self._state == "post" and self._gcd_progress > 0.0:
            w = int(rect.width() * self._gcd_progress)
            if w > 0:
                r = rect.adjusted(1, 1, -(rect.width() - w) - 1, -1)
                p.setPen(Qt.NoPen)
                p.setBrush(QtGui.QColor(0, 255, 255, 255))  # 淺藍半透明
                p.drawRect(r)

        # CD overlay: gray, LEFT -> RIGHT, stays when finished
        if self._state == "post" and self._cd_progress > 0.0:
            w = int(rect.width() * self._cd_progress)
            if w > 0:
                r = rect.adjusted(1, 1, -(rect.width() - w) - 1, -1)
                p.setPen(Qt.NoPen)
                p.setBrush(QtGui.QColor(0, 0, 0, 100))  # 灰色半透明
                p.drawRect(r)

        p.end()






from PySide6.QtWidgets import QDialog
from UI.ui_savemanager import Ui_SaveManagerDialog

class SaveManagerDialog(QDialog, Ui_SaveManagerDialog):#儲存裝被選則
    def __init__(self, part_name, save_list, on_delete, parent=None):
        super().__init__(parent)
        self.setupUi(self)   # 這裡載入 Designer 畫的 UI

        self.setWindowTitle(f"{part_name} 的裝備清單")
        self.part_name = part_name
        self.save_list = save_list
        self.selected_save = None
        self.on_delete = on_delete

        self.listWidget.addItems(self.save_list)
        self.loadButton.clicked.connect(self.load_selected)
        self.deleteButton.clicked.connect(self.delete_selected)
        self.cancelButton.clicked.connect(self.reject)
        self.listWidget.itemDoubleClicked.connect(self.load_selected)


    def load_selected(self, item=None):
        if item:  # 如果是雙擊傳進來的 item
            self.selected_save = item.text()
            self.accept()
        else:  # 如果是按下按鈕呼叫
            current_item = self.listWidget.currentItem()
            if current_item:
                self.selected_save = current_item.text()
                self.accept()

    def delete_selected(self):
        current_item = self.listWidget.currentItem()
        if current_item:
            save_name = current_item.text()
            confirm = QMessageBox.question(
                self,
                "確認刪除",
                f"確定要刪除存檔「{save_name}」嗎？",
                QMessageBox.Yes | QMessageBox.No
            )
            if confirm == QMessageBox.Yes:
                # 👇 呼叫主程式的刪除邏輯
                self.on_delete(self.part_name, save_name)

                # 從清單移掉
                self.save_list.remove(save_name)
                self.listWidget.takeItem(self.listWidget.row(current_item))




#取自ROCalculator特性數值點數計算
def get_total_tstat_points(level: int) -> int:
    index = level - 200
    if index < 0:
        return 0
    if index >= len(TSTATUS_POINT_COSTS):
        return TSTATUS_POINT_COSTS[-1]
    return TSTATUS_POINT_COSTS[index]




skill_df = pd.DataFrame(columns=[#檔案不在使用硬編碼以防跳錯
    "ID","Code","Name","attack_type","Rangedamage","Special_WPRange","Slv","Calculation","element","hits",
    "Critical_hit","combo","combo_element","combo_hits","Special_Calculation","combo_Special_Calculation",
    "monster_race","skill_buff","decay_hits","bonus_add","bonus_step"
])

# 初始化技能映射變數
skill_map = {}
skill_map_all = {}

def load_skill_map(filepath=None):
    global skill_map, skill_map_all, skill_df
    import skill_tree
    import pandas as pd
    import os

    # 若 filepath 沒指定 → 不做任何事
    if filepath is None:
        print("未指定路徑，使用預設空白技能列表。")
        return

    if not os.path.exists(filepath):
        print(f"{filepath} 找不到，保留空白技能列表。")
        return

    skill_df = pd.read_csv(filepath)

    # === ItemSearchApp 用 ===
    skill_map = dict(zip(skill_df["ID"], skill_df["Name"]))
    skill_map_all = skill_df.set_index("ID").to_dict(orient="index")

    # === skill_tree 用 ===
    skill_tree.skill_id_to_name = dict(zip(skill_df["ID"], skill_df["Name"]))
    skill_tree.skill_code_to_id = dict(zip(skill_df["Code"], skill_df["ID"]))
    skill_tree.skill_code_to_name = dict(zip(skill_df["Code"], skill_df["Name"]))


    print("技能列表載入成功")


load_skill_map() #讀取SKILL列表

import re

def update_skill_delay_labels(#技能延遲標籤更新
    skill_name: str,
    skill_map_all: dict,
    lua_text: str,
    fix_label,
    delay_label,
    cast_bar,
    skill_level,
    Equipfixed,
    Equipfixed_2,
    basestat,
    Equipstat,
    Equipgpost,
    Equipspost,
    selected_Equipspost
):
    """
    skill_name   : skill_box.currentText()
    skill_map_all: 技能資料字典（含 Name -> Code）
    lua_text     : skilldelaylist.lua 內容（字串）
    fix_label    : QLabel（固定 / 變動詠唱）
    delay_label  : QLabel（共延 / 冷卻）
    cast_bar     : CastBarWidget（詠唱條）
    skill_level  : 技能等級（可選）
    Equipfixed   : 固定詠唱（回傳用）
    Equipfixed_2 : 固定詠唱百分比（回傳用）
    stat         : 素質變動詠唱（回傳用）
    Equipstat    : 裝備變動詠唱（回傳用）
    Equipgpost   : 共延（回傳用）
    Equipspost   : 冷卻（回傳用）
    selected_Equipspost : 選擇的裝備冷卻（回傳用）
    """

    # ---------- Name -> Code ----------
    skill_code = None
    for _, row in skill_map_all.items():
        if row.get("Name") == skill_name:
            skill_code = (
                row.get("Code")
                or row.get("SkillCode")
                or row.get("SkillNameCode")
            )
            break

    if not skill_code:
        fix_label.setText("找不到技能 Code")
        delay_label.setText("")
        return

    # ---------- 找到 [SKID.CODE] 區塊 ----------
    start_pat = re.compile(
        rf"\[\s*SKID\.{re.escape(skill_code)}\s*\]\s*=\s*\{{",
        re.MULTILINE
    )
    m = start_pat.search(lua_text)
    if not m:
        fix_label.setText(f"lua 找不到 [SKID.{skill_code}]")
        delay_label.setText("")
        return

    i = m.end() - 1
    depth = 0
    block = None
    for j in range(i, len(lua_text)):
        if lua_text[j] == "{":
            depth += 1
        elif lua_text[j] == "}":
            depth -= 1
            if depth == 0:
                block = lua_text[i:j + 1]
                break

    if not block:
        fix_label.setText("技能資料解析失敗")
        delay_label.setText("")
        return

    # ---------- 解析延遲欄位 ----------
    def parse_array(field: str):
        mm = re.search(rf"{field}\s*=\s*\{{([^}}]*)\}}", block, re.MULTILINE)
        if not mm:
            return [0]          # ❗ 沒資料 → [0]

        nums = re.findall(r"-?\d+", mm.group(1))
        return [int(x) for x in nums] if nums else [0]

    fixed_raw = parse_array("SkillCastFixedDelay")
    stat_raw  = parse_array("SkillCastStatDelay")
    gpost_raw = parse_array("SkillGlobalPostDelay")
    spost_raw = parse_array("SkillSinglePostDelay")


    
    # -- 變詠固詠計算 --    
    basestat = math.sqrt(basestat / 265) * 100#素質轉換變詠%       
    stat = [max(0,(x + selected_Equipspost) * ((100 - basestat)/100) * ((100 + Equipstat)/100))  for x in stat_raw]#(變詠秒數+選擇技能變詠秒數)*素質變詠*裝備變詠
    #print(f"素質{basestat}，*裝備變詠：{Equipstat}")
    fixed = [max(0, (x + Equipfixed) * ((100 + Equipfixed_2)/100)) for x in fixed_raw]#固詠毫秒秒數-裝備固詠毫秒*裝備or技能固詠%(取最大值)
    gpost= [max(0, x * ((100 + Equipgpost)/100)) for x in gpost_raw]#共延秒數*裝備共延%
    spost= [max(0, x + Equipspost) for x in spost_raw]#冷卻秒數-裝備冷卻秒數
    

    # ---------- 依技能等級取值 ----------
    def pick(arr):
        if arr is None or len(arr) == 0:
            return "無"

        def ms_to_s(ms):
            return f"{ms / 1000:.3f}".rstrip("0").rstrip(".")

        if skill_level is None:
            return "/".join(ms_to_s(x) for x in arr)

        idx = max(skill_level - 1, 0)
        ms = arr[idx] if idx < len(arr) else arr[-1]
        return f"{ms_to_s(ms)}"


    # ---------- 更新 QLabel ----------
    fix_label.setText(
        f"固詠: {pick(fixed)}秒({pick(fixed_raw)}秒) "
        f"變詠: {pick(stat)}秒({pick(stat_raw)}秒)"
    )

    delay_label.setText(
        f"共延: {pick(gpost)}秒({pick(gpost_raw)}秒) "
        f"冷卻: {pick(spost)}秒({pick(spost_raw)}秒)"
    )
    # fix_label.setText(
    #     f"固詠: {pick(fixed)}秒 "
    #     f"變詠: {pick(stat)}秒"
    # )

    # delay_label.setText(
    #     f"共延: {pick(gpost)}秒 "
    #     f"冷卻: {pick(spost)}秒"
    # )
    stat_value = stat[skill_level] if skill_level < len(stat) else stat[-1]
    fixed_value = fixed[skill_level] if skill_level < len(fixed) else fixed[-1]
    spost_value = spost[skill_level] if skill_level < len(spost) else spost[-1]
    gcdtotal_value = max(0.0, gpost[skill_level] if skill_level < len(gpost) else gpost[-1])
    gcdtotal_raw_value = max(0.0, gpost_raw[skill_level] if skill_level < len(gpost_raw) else gpost_raw[-1])

    total_s = max(0.0, fixed_value + stat_value)
    cdtotal_s = max(0.0, spost_value)
    gcdtotal_s = max(0.0, gcdtotal_value)
    gcdtotal_raw_s = max(0.0, gcdtotal_raw_value)


    cast_bar.start(int(total_s),int(gcdtotal_s),int(cdtotal_s))  # 轉 ms
    return gcdtotal_raw_s/1000

#動態下拉式選單
import re
from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QComboBox

class MultiComboField(QWidget):
    def __init__(self, options, parent=None):
        """
        options: list[(label, data)]
                 例如 [("無形",0),("不死",1),...,("龍族",9)]
                 可包含 ("", None) 作為空白選項
        """
        super().__init__(parent)
        self.options = options
        self.combos: list[QComboBox] = []

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)

        self.box_layout = QHBoxLayout()
        self.box_layout.setContentsMargins(0, 0, 0, 0)
        self.box_layout.setSpacing(6)
        root.addLayout(self.box_layout)

        self.add_btn = QPushButton("+")
        self.add_btn.setFixedWidth(28)
        self.add_btn.clicked.connect(self.add_combo)
        root.addWidget(self.add_btn)

        # 預設先放一個下拉
        self.add_combo()

    def _make_combo(self) -> QComboBox:
        cb = QComboBox()
        for label, data in self.options:
            cb.addItem(label, data)
        return cb

    def add_combo(self, preset_data=None):
        cb = self._make_combo()
        if preset_data is not None:
            idx = cb.findData(preset_data)
            if idx < 0 and isinstance(preset_data, str):
                idx = cb.findText(preset_data)
            if idx >= 0:
                cb.setCurrentIndex(idx)
        self.box_layout.addWidget(cb)
        self.combos.append(cb)
        return cb

    def set_values(self, values):
        """values: 例如 [0,5,9] 或 ['無形','不死'] 或混合"""
        for cb in self.combos:
            cb.deleteLater()
        self.combos.clear()

        if not values:
            self.add_combo()
            return

        for v in values:
            self.add_combo(v)

    def get_values(self):
        """回傳去重後的 userData 陣列（忽略空白/None）"""
        vals = []
        for cb in self.combos:
            data = cb.currentData()
            if data is None or str(data) == "":
                continue
            vals.append(data)

        uniq, seen = [], set()
        for v in vals:
            if v not in seen:
                seen.add(v)
                uniq.append(v)
        return uniq

import requests

REMOTE_VERSION_URL = "https://z2911902.github.io/ROItemSearchApp/data/version.txt" 
UPDATER_EXE = "update.exe"
TARGET_EXE = "ItemSearchApp.exe"

# 你指定的 zip 下載 URL 格式
ZIP_URL_TEMPLATE = "https://github.com/z2911902/ROItemSearchApp/releases/download/{ver}/ROItemSearchApp.zip"


def read_local_version(app_dir: str) -> str:
    path = os.path.join(app_dir,"data","version.txt")
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()


def read_remote_version(url: str) -> str:
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    return r.text.strip()


def normalize_version(v: str) -> tuple[tuple[int, ...], int]:
    """
    'v0.1.22-260110' -> ((0, 1, 22), 260110)
    'v0.1.22'        -> ((0, 1, 22), 0)
    """
    v = v.strip().lstrip("vV")

    # 拆版本與日期（日期可有可無）
    if "-" in v:
        ver_part, date_part = v.split("-", 1)
    else:
        ver_part, date_part = v, "0"

    # 版本段：0.1.22
    ver_nums = tuple(int(x) for x in ver_part.split(".") if x.isdigit())

    # 日期段：只取前面的數字（避免後面夾字）
    m = re.match(r"(\d+)", date_part.strip())
    date_num = int(m.group(1)) if m else 0

    return ver_nums, date_num


def compare_versions(a: str, b: str) -> int:
    """
    回傳:
      1  表示 a > b
      0  表示 a == b
     -1  表示 a < b

    規則：
      先比主版本 (0,1,22)
      若相同再比日期 260110
    """
    (va, da) = normalize_version(a)
    (vb, db) = normalize_version(b)

    n = max(len(va), len(vb))
    va = va + (0,) * (n - len(va))
    vb = vb + (0,) * (n - len(vb))

    if va != vb:
        return (va > vb) - (va < vb)

    return (da > db) - (da < db)



import sys
import csv
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QComboBox,
    QFormLayout, QLineEdit, QPushButton, QMessageBox, QHBoxLayout
)
from PySide6.QtCore import Qt
skill_editor = None
class CSVEditor(QMainWindow):
    def center_to_parent(self):
        if self.parent():
            parent_geometry = self.parent().frameGeometry()
            parent_center = parent_geometry.center()
            this_geometry = self.frameGeometry()
            this_geometry.moveCenter(parent_center)
            self.move(this_geometry.topLeft())
        else:
            # 若沒有父視窗，就置中到螢幕中央
            screen = QApplication.primaryScreen().geometry()
            x = (screen.width() - self.width()) // 2
            y = (screen.height() - self.height()) // 2
            self.move(x, y)

    def __init__(self, file_path, parent=None):
        super().__init__(parent)  # ✅ 把 parent 傳給 QMainWindow
        self.file_path = file_path
        self.setWindowTitle("技能設定編輯器")
        self.resize(600, 600)
        self.center_to_parent()
        self.file_path = file_path

        # 主容器
        widget = QWidget()
        self.setCentralWidget(widget)
        main_layout = QVBoxLayout(widget)

        # === 搜尋 + 選擇 技能（同一行） ===
        search_name_layout = QHBoxLayout()

        search_label = QLabel("搜尋 技能：")
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("輸入名稱關鍵字...")
        self.search_box.textChanged.connect(self.filter_names)

        # 🔹 清空按鈕
        self.clear_search_button = QPushButton("清空")
        self.clear_search_button.setFixedWidth(50)
        self.clear_search_button.setToolTip("清除搜尋文字")
        self.clear_search_button.clicked.connect(self.search_box.clear)

        name_label = QLabel("選擇 技能：")
        self.name_combo = QComboBox()
        self.name_combo.setMinimumWidth(200)

        # 加入到同一行
        search_name_layout.addWidget(search_label)
        search_name_layout.addWidget(self.search_box)
        search_name_layout.addWidget(self.clear_search_button)
        search_name_layout.addSpacing(20)
        search_name_layout.addWidget(name_label)
        search_name_layout.addWidget(self.name_combo)
        search_name_layout.addStretch()

        main_layout.addLayout(search_name_layout)



        # === 欄位編輯區 ===
        self.form = QFormLayout()
        main_layout.addLayout(self.form)
        # 建立一個橫向排版
        button_layout = QHBoxLayout()

        # 儲存但不關閉
        self.save_only_button = QPushButton("📝 只儲存變更")
        self.save_only_button.clicked.connect(lambda: self.save_changes(close_after=False))
        button_layout.addWidget(self.save_only_button)

        # 儲存並關閉
        self.save_button = QPushButton("💾 儲存變更並關閉")
        self.save_button.clicked.connect(lambda: self.save_changes(close_after=True))
        button_layout.addWidget(self.save_button)

        # 加到主layout（假設main_layout是垂直排版 QVBoxLayout）
        main_layout.addLayout(button_layout)

        # === 初始化資料 ===
        self.all_rows = []     # 存所有行
        self.filtered_rows = []  # 搜尋後顯示的行
        self.field_edits = {}

        # === 載入 CSV ===
        self.load_csv(file_path)
        self.name_combo.currentIndexChanged.connect(self.update_fields)

    def load_csv(self, file_path):
        """讀取 CSV 並初始化資料"""
        with open(file_path, newline='', encoding='utf-8-sig') as csvfile:
            reader = csv.reader(csvfile)
            rows = list(reader)

        if not rows:
            QMessageBox.warning(self, "錯誤", "CSV 檔案是空的！")
            return

        self.headers = rows[0]
        self.data = rows[1:]

        # 找出 Name 欄位索引
        try:
            self.name_index = next(i for i, h in enumerate(self.headers) if h.lower() in ["name", "skillname"])
        except StopIteration:
            QMessageBox.warning(self, "錯誤", "找不到 'Name' 欄位！")
            return

        # 將所有行資料加入
        self.all_rows = [row for row in self.data if len(row) > self.name_index]
        self.filtered_rows = self.all_rows.copy()

        # 填入所有 Name（允許重複）
        self.name_combo.clear()
        self.name_combo.addItems([row[self.name_index].strip() for row in self.filtered_rows])


        # === 欄位資訊（名稱 + 提示文字） ===
        header_info = {
            "ID": {
                "label": "技能 ID",
                "tooltip": "技能在資料表中的唯一識別碼，通常不可修改。"
            },
            "Code": {
                "label": "程式代碼",
                "tooltip": "內部使用的技能代碼，用於程式判斷。"
            },
            "attack_type": {
                "label": "攻擊類型",
                "tooltip": "選擇攻擊類型：magic 為魔法攻擊，physical 為物理攻擊。"
            },
            "Slv": {
                "label": "技能等級",
                "tooltip": "此欄可填入技能等級對應數值。(不輸入時不顯示在下拉式選單)"
            },
            "Calculation": {
                "label": "計算公式",
                "tooltip": "技能傷害或效果的計算公式，可使用 BaseLv、Sklv 等變數。"
            },
            "element": {
                "label": "攻擊屬性",
                "tooltip": "屬性(無=0,水=1,地=2,火=3,風=4,毒=5,聖=6,暗=7,念=8,不死=9)"
            },
            "hits": {
                "label": "打擊次數",
                "tooltip": "技能打擊次數。(負值為總傷害/次數)"
            },
            "Critical_hit": {
                "label": "技能爆擊/命中增傷判定",
                "tooltip": "設定爆擊倍率，例如 0.5 代表半爆擊；設定命中增傷設定0；負數代表兩者不啟用。"
            },
            "combo": {
                "label": "連段技能公式",
                "tooltip": "此技能觸發的下一個公式。"
            },
            "combo_element": {
                "label": "連段技能攻擊屬性",
                "tooltip": "連段技能的屬性。"
            },
            "combo_hits": {
                "label": "連段次數",
                "tooltip": "連段技能的打擊次數。(負值為總傷害/次數)"
            },
            "combo_Special_Calculation": {
                "label": "特殊連段計算公式",
                "tooltip": "觸發特殊條件下的技能公式，會覆蓋連段公式。"
            },
            "Special_Calculation": {
                "label": "特殊計算公式",
                "tooltip": "觸發特殊條件下的技能公式，會覆蓋一般公式。"
            },
            "monster_race": {
                "label": "觸發特殊計算種族",
                "tooltip": "怪物種族觸發特別公式。"
            },
            "skill_buff": {
                "label": "觸發特殊計算技能(ID)",
                "tooltip": "目前技能觸發的特殊技能 ID（例如狀態技能）。"
            },
            "decay_hits": {
                "label": "遞增/減段數",
                "tooltip": "設定每段的遞增或遞減次數，例如 4 代表 4 段。"
            },
            "bonus_add": {
                "label": "遞增/減原始數字",
                "tooltip": "起始加成（或乘數），可輸入 +800 或 *1。"
            },
            "bonus_step": {
                "label": "遞增/減數字",
                "tooltip": "每段遞增/減的變化量，例如 -100 或 +0.1。"
            },
            "Rangedamage": {
                "label": "技能遠距傷害",
                "tooltip": "技能套用遠距傷害計算。"
            },
            "special_wprange": {
                "label": "裝備武器套用遠距計算",
                "tooltip": "裝備該類型的武器自動轉換遠傷。"
            },
            "skill_SpecialATK": {
                "label": "技能特殊段加算傷害",
                "tooltip": "綠光減傷前加算。"
            }

        }


        # 建立欄位編輯器
        for header in self.headers:
            if header.lower() == "name":
                continue

            # 取得中文名稱與提示文字
            info = header_info.get(header, {})
            display_name = info.get("label", header)
            tooltip_text = info.get("tooltip", "")

            label_title = QLabel(f"{display_name}：")

            # 有提示文字就加上 tooltip
            if tooltip_text:
                label_title.setToolTip(tooltip_text)

            # 建立編輯欄位（例：QLineEdit 或 QComboBox）
            if header.lower() == "attack_type":
                edit_field = QComboBox()                
                edit_field.addItem("物理", "physical")
                edit_field.addItem("魔法", "magic")
                edit_field.addItem("龍息", "d_b")
            elif header.lower() in ("element","combo_element"):
                edit_field = QComboBox()
                element_options = [
                    ("", None),
                    ("無", 0), ("水", 1), ("地", 2), ("火", 3), ("風", 4),
                    ("毒", 5), ("聖", 6), ("暗", 7), ("念", 8), ("不死", 9),
                ]
                for label, code in element_options:
                    edit_field.addItem(label, code)
            
            elif header.lower() == "monster_race":
                race_options = [
                    ("", None),  # 空白
                    ("無形", 0), ("不死", 1), ("動物", 2), ("植物", 3), ("昆蟲", 4),
                    ("魚貝", 5), ("惡魔", 6), ("人形", 7), ("天使", 8), ("龍族", 9),
                ]
                edit_field = MultiComboField(race_options)

            elif header.lower() == "special_wprange":
                WPClass_options = [
                    ("", None),  # 空白
                    ("短劍", 1), ("單手劍", 2), ("雙手劍", 3), ("單手矛", 4),("雙手矛", 5),
                    ("單手斧", 6), ("雙手斧", 7), ("鈍器", 8), ("單手仗", 10), ("拳套", 12),
                    ("樂器", 13), ("鞭子", 14), ("書", 15),("拳刃", 16), ("雙手仗", 23),
                    ("弓", 11), ("左輪手槍", 17), ("來福槍", 18), ("格林機關槍", 19), ("霰彈槍", 20), ("榴彈槍", 21), ("風魔飛鏢", 22),
                ]
                edit_field = MultiComboField(WPClass_options)

            # ★★★ 新增：Rangedamage 用勾選框 ★★★
            elif header.lower() == "rangedamage":
                edit_field = QCheckBox()
            else:
                edit_field = QLineEdit()
                if header.lower() in ["id", "code"]:
                    edit_field.setReadOnly(True)
                    edit_field.setStyleSheet("background-color: #f0f0f0; color: #666;")

            self.field_edits[header] = edit_field
            self.form.addRow(label_title, edit_field)

        if self.filtered_rows:
            self.update_fields(0)

    def filter_names(self, text):
        """模糊搜尋 Name"""
        self.filtered_rows = [row for row in self.all_rows if text.lower() in row[self.name_index].lower()]
        self.name_combo.clear()
        self.name_combo.addItems([row[self.name_index].strip() for row in self.filtered_rows])
        if self.filtered_rows:
            self.update_fields(0)
        else:
            for widget in self.field_edits.values():
                if isinstance(widget, QLineEdit):
                    widget.setText("")
                elif isinstance(widget, QComboBox):
                    widget.setCurrentIndex(-1)  # 清空選擇（沒有選項）


    def update_fields(self, index):
        if index < 0 or index >= len(self.filtered_rows):
            return
        row = self.filtered_rows[index]
        for i, header in enumerate(self.headers):
            key = header.strip().lower()
            if key == "name":
                continue
            if header in self.field_edits:
                value = row[i] if i < len(row) else ""
                widget = self.field_edits[header]

                # monster_race（MultiComboField，多值）
                #if isinstance(widget, MultiComboField) and key == "monster_race":
                if isinstance(widget, MultiComboField) and key in ("monster_race","special_wprange"):
                    txt = str(value).strip()
                    if not txt:
                        widget.set_values([])  # 顯示 1 個空白下拉
                    else:
                        import re
                        parts = re.split(r'[,\|;/\s]+', txt)
                        vals = []
                        for p in parts:
                            if not p:
                                continue
                            try:
                                vals.append(int(float(p)))   # 數字優先
                            except:
                                vals.append(p)               # 兼容舊中文
                        widget.set_values(vals)
                    continue

                # element（單值 QComboBox）
                if isinstance(widget, QComboBox) and key in ("element","combo_element"):
                    txt = str(value).strip()
                    if txt == "":
                        idx = widget.findData(None)  # 空白
                    else:
                        try:
                            num = int(float(txt))
                            idx = widget.findData(num)
                        except:
                            # 舊資料若是中文
                            idx = widget.findText(txt)
                    widget.setCurrentIndex(idx if idx >= 0 else widget.findData(None))
                    continue

                if isinstance(widget, QComboBox) and key == "attack_type":
                    txt = ("" if value is None else str(value)).strip()
                    if txt == "":
                        # 若下拉有空白選項
                        idx = widget.findData(None)
                        if idx < 0:
                            idx = widget.findText("")
                    else:
                        # 先找英文 userData（magic/physical）
                        idx = widget.findData(txt.lower())
                        if idx < 0:
                            # 舊資料可能是中文 → 映射到英文再找
                            zh2en = {"魔法": "magic", "物理": "physical", "龍息":"d_b"}
                            mapped = zh2en.get(txt)
                            if mapped:
                                idx = widget.findData(mapped)
                        if idx < 0:
                            # 最後相容：用顯示文字找
                            idx = widget.findText(txt)
                    widget.setCurrentIndex(idx if idx >= 0 else 0)
                    continue

                if isinstance(widget, QCheckBox) and key == "rangedamage":
                    widget.setChecked(str(value).strip() in ("1", "true", "True"))
                    continue



                # 其它欄位照舊
                if isinstance(widget, QComboBox):
                    idx = widget.findText(str(value))
                    widget.setCurrentIndex(idx if idx >= 0 else 0)
                else:
                    widget.setText(str(value))





    def save_changes(self, close_after=True):
        index = self.name_combo.currentIndex()
        if index < 0 or index >= len(self.filtered_rows):
            QMessageBox.warning(self, "錯誤", "請先選擇一個 Name")
            return

        row = self.filtered_rows[index]
        for i, header in enumerate(self.headers):
            key = header.strip().lower()
            if key == "name":
                continue
            if header in self.field_edits:
                widget = self.field_edits[header]

                # 只讀跳過
                from PySide6.QtWidgets import QLineEdit, QComboBox
                if isinstance(widget, QLineEdit) and widget.isReadOnly():
                    continue

                # ✅ 強制規格：element / monster_race 只寫數字；沒選就空白
                if key in ("element","combo_element") and isinstance(widget, QComboBox):
                    data = widget.currentData()
                    new_value = "" if (data is None or str(data) == "") else str(int(data))

                elif key in ("monster_race","special_wprange") and hasattr(widget, "get_values"):
                    vals = widget.get_values()  # e.g. [0,5,9] 或 []
                    # 過濾成純數字字串
                    nums = []
                    for v in vals:
                        if v is None or str(v).strip() == "":
                            continue
                        try:
                            nums.append(str(int(v)))
                        except:
                            # 若意外拿到中文，直接忽略以避免寫中文
                            continue
                    new_value = ",".join(nums) if nums else ""

                # 其他欄位照舊；attack_type 依你規格存英文
                elif isinstance(widget, QComboBox) and key == "attack_type":
                    new_value = widget.currentData()  # "magic"/"physical"
                elif isinstance(widget, QComboBox):
                    new_value = widget.currentText()
                elif isinstance(widget, QCheckBox) and key == "rangedamage":
                    new_value = "1" if widget.isChecked() else "0"

                else:
                    new_value = widget.text()

                if i < len(row):
                    row[i] = new_value
                else:
                    row.append(new_value)


        # 這裡很重要：要把這筆 row 寫回 self.data 對應的那一筆
        id_index = self.headers.index("ID")
        row_id = row[id_index]
        for i, drow in enumerate(self.data):
            if drow[id_index] == row_id:
                self.data[i] = row[:]  # 或用 copy()
                break

        # 這裡才進行存檔，寫 self.data
        try:
            with open(self.file_path, "w", newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(self.headers)
                writer.writerows(self.data)
            load_skill_map("data/skillneme.csv")   # 重新載入技能列表
            if close_after:
                self.close()
        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"儲存失敗：{e}")
        # 讓主畫面即時看到變更，並選到當前編輯的技能
        self._refresh_and_select_in_main()


    def closeEvent(self, event):
        try:
            self._refresh_and_select_in_main()
        except Exception as e:
            print(f"[CSVEditor.closeEvent] 刷新/選取失敗：{e}")

        # 重新計算
        try:
            app = getattr(self, "app_instance", None)
            if app and hasattr(app, "replace_custom_calc_content"):
                setattr(app, "_last_calc_state", None)
                app.replace_custom_calc_content()
        except Exception as e:
            print(f"[CSVEditor.closeEvent] 重新計算失敗：{e}")

        super().closeEvent(event)


    def _refresh_and_select_in_main(self):
        """重建主畫面 skill_box，並用目前編輯列的 ID 精準選取。"""
        try:
            # 取出編輯器目前指到的那筆資料 ID
            idx_in_editor = self.name_combo.currentIndex()
            row_id = None
            if 0 <= idx_in_editor < len(self.filtered_rows):
                id_index = self.headers.index("ID")
                row = self.filtered_rows[idx_in_editor]
                if id_index < len(row):
                    row_id = row[id_index]

            app = getattr(self, "app_instance", None)
            if not app or not hasattr(app, "skill_box"):
                print("[CSVEditor] 找不到 app_instance 或 skill_box")
                return

            # 清除主畫面舊的關鍵字，避免被過濾掉
            if hasattr(app, "skill_filter_input"):
                app.skill_filter_input.blockSignals(True)
                app.skill_filter_input.clear()
                app.skill_filter_input.blockSignals(False)

            # 重建技能清單（需先把主畫面 filter_skills 掛到 self，前面你已做）
            if hasattr(app, "filter_skills"):
                app.filter_skills()

            # 用 ID（userData）精準選取；型別不一致時會嘗試轉型
            if row_id is not None:
                skill_box = app.skill_box
                idx = skill_box.findData(row_id)

                if idx == -1:
                    # 嘗試轉型再找
                    try_ids = []
                    try:
                        try_ids.append(int(row_id))
                    except:
                        pass
                    try_ids.append(str(row_id))
                    for cand in try_ids:
                        idx = skill_box.findData(cand)
                        if idx != -1:
                            break

                if idx != -1:
                    skill_box.setCurrentIndex(idx)
                else:
                    # 退而求其次，用名稱比對
                    name_txt = self.name_combo.currentText().strip()
                    name_idx = skill_box.findText(name_txt)
                    if name_idx != -1:
                        skill_box.setCurrentIndex(name_idx)
                    else:
                        print(f"[CSVEditor] skill_box 找不到 ID={row_id} 或名稱='{name_txt}'")

        except Exception as e:
            print(f"[CSVEditor] _refresh_and_select_in_main 失敗：{e}")



def open_skill_editor(app_instance=None):
    global skill_editor  
    if skill_editor is None or not skill_editor.isVisible():
        skill_editor = CSVEditor(r"data\skillneme.csv", parent=app_instance)
        skill_editor.app_instance = app_instance
        skill_editor.show()
    else:
        skill_editor.raise_()
        skill_editor.activateWindow()

    # === 設定編輯器的 name_combo 下拉式 ===
    if app_instance and hasattr(app_instance, "skill_box"):
        try:
            skill_name = app_instance.skill_box.currentText().strip()
            if skill_name:
                idx = skill_editor.name_combo.findText(skill_name)
                if idx != -1:
                    skill_editor.name_combo.setCurrentIndex(idx)
                else:
                    print(f"[open_skill_editor] 編輯器內找不到技能：{skill_name}")
        except Exception as e:
            print(f"[open_skill_editor] 設定編輯器下拉式失敗：{e}")



class FileSelectionDialog(QDialog):#刪除清單
    """
    彈出多選檔案清單：
    files: [(檔名, 預設是否勾選)]
    base_path: 檔案所在資料夾
    """
    def __init__(self, files, base_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("選擇要刪除的檔案")
        self.resize(480, 400)

        self.base_path = base_path
        self.checkboxes = []

        layout = QVBoxLayout(self)
        # === 說明輸入框（新增） ===
        desc_label = QLabel(
            "每週更新預設只取得物品名稱、物品能力、附魔工具，\n"
            "除非你需要更新技能、技能被動效果、技能樹相關資料。"
        )
        desc_label.setWordWrap(True)
        #self.description_edit = QLineEdit()
        #self.description_edit.setPlaceholderText("輸入此次刪除動作的說明...")
        layout.addWidget(desc_label)
        #layout.addWidget(self.description_edit)
        # === scroll area ===
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        vbox = QVBoxLayout(content)

        for filename, default_checked in files:
            full_path = os.path.join(base_path, filename)
            if os.path.exists(full_path):
                mtime = datetime.fromtimestamp(os.path.getmtime(full_path))
                date_str = mtime.strftime("%Y-%m-%d %H:%M")
            else:
                date_str = "（不存在）"

            cb = QCheckBox(f"{filename}    ({date_str})")
            cb.setChecked(default_checked)
            vbox.addWidget(cb)
            self.checkboxes.append((filename, cb))

        content.setLayout(vbox)
        scroll.setWidget(content)
        layout.addWidget(scroll)

        # === bottom buttons ===
        btn_box = QHBoxLayout()
        ok_btn = QPushButton("刪除")
        cancel_btn = QPushButton("取消")

        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)

        btn_box.addWidget(ok_btn)
        btn_box.addWidget(cancel_btn)
        layout.addLayout(btn_box)

    def get_selected_files(self):
        """回傳使用者勾選的檔案名稱 list"""
        return [
            filename
            for filename, cb in self.checkboxes
            if cb.isChecked()
        ]






def parse_lua_effects_with_variables(
    block_text,
    refine_inputs,
    get_values,
    grade,
    unit_map,
    size_map,
    effect_map,
    hide_unrecognized=False,
    hide_physical=False,
    hide_magical=False,
    current_location_slot=None
):
    lines = block_text.splitlines()
    variables = {}
    sfct_handled = False  # ✅ 控制是否已處理過 SubSFCTEquipAmount
    skill_delay_accum = {}
    results = []
    condition_met = True
    indent_stack = []
    weapon_level_map = variables.setdefault("__weapon_level_map__", {})

    block_stack = []  # 用來追蹤 if-elseif-else 區塊狀態
    safe_globals = {"__builtins__": None}
    safe_locals = {"math": __import__("math")}
    def safe_eval_expr(expr, variables, get_values, refine_inputs, grade):
        expr = re.sub(r"get\((\d+)\)", lambda m: str(get_values.get(int(m.group(1)), 0)), expr)
        expr = re.sub(r"GetRefineLevel\((\d+)\)", lambda m: str(refine_inputs.get(int(m.group(1)), 0)), expr)
        expr = re.sub(r"GetEquipGradeLevel\((\d+)\)", lambda m: str(grade), expr)
        expr = re.sub(r"GetEquipArmorLv\((\d+)\)",lambda m: str(global_armor_level_map.get(int(m.group(1)), 0)),expr) # 防具等級GetEquipArmorLv(數字部位)
        expr = re.sub(r"GetEquipWeaponLv\((\d+)\)",lambda m: str(global_weapon_level_map.get(int(m.group(1)), 0)),expr) # 武器等級GetEquipWeaponLv(數字部位)

        # 將變數名稱替換成實際數值
        for v in sorted(variables.keys(), key=lambda x: -len(x)):
            expr = re.sub(rf'\b{re.escape(v)}\b', str(variables[v]), expr)

        # 補括號
        if expr.count("(") > expr.count(")"):
            expr += ")" * (expr.count("(") - expr.count(")"))

        try:
            # 把 math 跟 temp 等變數放進 local 環境
            safe_locals = {"math": __import__("math")}
            safe_locals.update(variables)
            return int(eval(expr, {"__builtins__": None}, safe_locals))
        except Exception as e:
            return f"{expr}（無法解析）"

    
    
    
        
    
    

    for line in lines:
        original_line = line.strip()
        line = original_line.split("--")[0].strip()
        # 把 GetRefineLevel(GetLocation()) 轉為當前部位的 slot ID
        if current_location_slot is not None:
            refine_value = refine_inputs.get(current_location_slot, 0)
            line = re.sub(
                r"GetRefineLevel\s*\(\s*GetLocation\s*\(\s*\)\s*\)",
                str(refine_value),
                line
            )
            # 從全域變數中抓出該部位的武器等級
            if current_location_slot not in global_weapon_level_map:
                global_weapon_level_map[current_location_slot] = 0
            weapon_level = global_weapon_level_map.get(current_location_slot, 0)

            line = re.sub(
                r"GetEquipWeaponLv\s*\(\s*GetLocation\s*\(\s*\)\s*\)",
                str(weapon_level),
                line
            )
            # 從全域變數中抓出該部位的防具等級
            if current_location_slot not in global_armor_level_map:
                global_armor_level_map[current_location_slot] = 0
            armor_level = global_armor_level_map.get(current_location_slot, 0)
            line = re.sub(
                r"GetEquipArmorLv\s*\(\s*GetLocation\s*\(\s*\)\s*\)",
                str(armor_level),
                line
            )
            #從全域變數抓出技能等級
            line = re.sub(
                r"GetSkillLevel\((\d+)\)",
                lambda m: str(enabled_skill_levels.get(int(m.group(1)), 0)),
                line
            )
            # 從全域變數抓出該部位的武器類型（代碼）
            if current_location_slot not in global_weapon_type_map:
                global_weapon_type_map[current_location_slot] = 0
            weapon_class = global_weapon_type_map.get(current_location_slot, 0)

            line = re.sub(
                r"GetWeaponClass\s*\(\s*GetLocation\s*\(\s*\)\s*\)",
                str(weapon_class),
                line
            )

        if not line:
            continue
            
        # === 特殊判斷：若為 P.S = XXX 則直接顯示後面的文字 ===
        if line.startswith("P.S ="):
            comment = line.split("=", 1)[1].strip()
            results.append(f"📌P.S：{comment}")
            continue
        # 🔽  GetPetRelationship() 替換為傳入的裝備階級
        line = re.sub(r"GetPetRelationship\s*\(\s*\)", str(grade), line)

        # 將 GetEquipGradeLevel(GetLocation()) 替換為傳入的裝備階級
        line = re.sub(r"GetEquipGradeLevel\s*\(\s*GetLocation\s*\(\s*\)\s*\)", str(grade), line)
        # 補充解析 Type 與 Stat 同行的情況（裝備類別與屬性）
        type_stat_match = re.match(r'Type\s*=\s*"(.*?)"\s*,\s*Stat\s*=\s*\{(.*?)\}', line)
        if type_stat_match:
            eq_type = type_stat_match.group(1)
            stat_str = type_stat_match.group(2)
            stat_values = [int(x.strip()) for x in stat_str.split(",")]
            stat_names_list = stat_name_sets.get(eq_type, stat_name_sets["armor"])

            results.append(f"🛠️ 類型：{eq_type}")
            for idx, val in enumerate(stat_values):
                if val != 0:
                    name = stat_names_list[idx] if idx < len(stat_names_list) else f"未知{idx}"
                    results.append(f"{name} +{val}")
            continue




        # 處理單行 Stat = {...}
        stat_match = re.search(r'Stat\s*=\s*\{([^\}]+)\}', line)
        if stat_match:
            stat_values = [int(x.strip()) for x in stat_match.group(1).split(",") if x.strip().isdigit()]

            # 嘗試在整體文本中找到 Type
            type_match = re.search(r'Type\s*=\s*"(\w+)"', block_text)
            equip_type = type_match.group(1) if type_match else "armor"
            stat_names = stat_name_sets.get(equip_type, stat_name_sets["armor"])
            
            for idx, val in enumerate(stat_values):
                if val != 0:
                    stat_name = stat_names[idx] if idx < len(stat_names) else f"未知{idx}"
                    # ✅ 儲存武器或防具類型
                    global_armor_weapon_map[current_location_slot] = equip_type
                    # 儲存武器或防具等級
                    if stat_name == "武器等級":
                        global_weapon_level_map[current_location_slot] = val                    
                    elif stat_name == "防具等級":
                        global_armor_level_map[current_location_slot] = val
                    elif stat_name == "武器ATK":
                        global_weapon_atk_map[current_location_slot] = val
                        #print(f"設定武器ATK: 部位{current_location_slot} = {val}")
                    elif stat_name == "武器MATK":
                        global_weapon_matk_map[current_location_slot] = val
                        #print(f"設定武器MATK: 部位{current_location_slot} = {val}")

                        
                    # ✅ 處理武器類型（使用 map 轉換中文名稱）
                    if stat_name == "武器類型":
                        global_weapon_type_map[current_location_slot] = val
                        weapon_type_name = weapon_type_map.get(val, f"未知武器類型({val})")
                        #results.append(f"武器類型：{weapon_type_name}")
                        continue  # 若你不想再輸出 "武器類型 +x" 可跳過

                    # 過濾排除屬性
                    if stat_name in excluded_stat_names:
                        continue

                    results.append(f"{stat_name} +{val}")



            
         # 處理 if 條件
        if_match = re.match(r"if\s+(.+?)\s+then", line)
        if if_match:
            # 檢查父層是否成立
            parent_active = all(block['active'] for block in block_stack)
            if not parent_active:
                block_stack.append({"active": False, "branch_taken": False})
                continue

            expr = if_match.group(1)
            expr = re.sub(r"get\((\d+)\)", lambda m: str(get_values.get(int(m.group(1)), 0)), expr)
            expr = re.sub(r"GetRefineLevel\((\d+)\)", lambda m: str(refine_inputs.get(int(m.group(1)), 0)), expr)
            expr = re.sub(r"GetEquipGradeLevel\((\d+)\)", lambda m: str(grade), expr)
            expr = re.sub(r"GetItemIDLocation\((\d+)\)", lambda m: str(slot_item_id_map.get(int(m.group(1)), 0)), expr)
            
            for v in sorted(variables.keys(), key=lambda x: -len(x)):
                expr = re.sub(rf'\b{re.escape(v)}\b', str(variables[v]), expr)

            expr = expr.replace("~=", "!=")
            expr = expr.replace(" and ", " and ")
            expr = expr.replace(" or ", " or ")
            expr = expr.replace(" not ", " not ")

            try:
                result = eval(expr, safe_globals, safe_locals)
                condition_met = bool(result)
                results.append(f"{'✅ if 條件成立' if condition_met else '❌ if 條件不成立'} : {if_match.group(1)}")
            except Exception as e:
                condition_met = False
                results.append(f"⚠️ 無法解析條件: {if_match.group(1)}，錯誤: {e}")

            block_stack.append({"active": condition_met, "branch_taken": condition_met})
            continue

        # elseif 判斷
        elseif_match = re.match(r"elseif\s+(.+?)\s+then", line)
        if elseif_match:
            if not block_stack:
                raise Exception("elseif without if")
            # 先移除上一個分支
            last = block_stack.pop()
            parent_active = all(block['active'] for block in block_stack)
            if not parent_active or last["branch_taken"]:
                # 父層不成立 或 已有分支成立
                block_stack.append({"active": False, "branch_taken": True})
                continue

            expr = elseif_match.group(1)
            expr = re.sub(r"get\((\d+)\)", lambda m: str(get_values.get(int(m.group(1)), 0)), expr)
            expr = re.sub(r"GetRefineLevel\((\d+)\)", lambda m: str(refine_inputs.get(int(m.group(1)), 0)), expr)
            expr = re.sub(r"GetEquipGradeLevel\((\d+)\)", lambda m: str(grade), expr)
            expr = re.sub(r"GetItemIDLocation\((\d+)\)", lambda m: str(slot_item_id_map.get(int(m.group(1)), 0)), expr)
            
            for v in sorted(variables.keys(), key=lambda x: -len(x)):
                expr = re.sub(rf'\b{re.escape(v)}\b', str(variables[v]), expr)
            expr = expr.replace("~=", "!=")
            expr = expr.replace(" and ", " and ")
            expr = expr.replace(" or ", " or ")
            expr = expr.replace(" not ", " not ")

            try:
                result = eval(expr, safe_globals, safe_locals)
                condition_met = bool(result)
                results.append(f"{'✅ elseif 條件成立' if condition_met else '❌ elseif 條件不成立'} : {expr}")
            except Exception as e:
                condition_met = False
                results.append(f"⚠️ 無法解析條件: {expr}，錯誤: {e}")

            
            block_stack.append({"active": condition_met, "branch_taken": condition_met})
            condition_met = all(block['active'] for block in block_stack)
            continue

        # else 判斷
        else_match = re.match(r"\s*else\b", line)
        if else_match:
            if not block_stack:
                raise Exception("else without if")
            last = block_stack.pop()
            parent_active = all(block['active'] for block in block_stack)
            
            if not parent_active or last["branch_taken"]:
                block_stack.append({"active": False, "branch_taken": True})
            else:
                block_stack.append({"active": True, "branch_taken": True})

            condition_met = all(block['active'] for block in block_stack)
            continue

        # end 判斷
        end_match = re.match(r"\s*end\b", line)
        if end_match:
            if block_stack:
                block_stack.pop()

            # --- 🔧 重置 condition_met 並回到父層狀態 ---
            # 若目前仍在某些區塊內，就依照父層 active 狀態決定
            if block_stack:
                condition_met = all(block['active'] for block in block_stack)
            else:
                # 已經完全跳出 if/elseif/else 區塊，重置為 True
                condition_met = True

            continue

        # 一般語句判斷
        if block_stack and not all(block['active'] for block in block_stack):
            continue


        # 支援多個 GetRefineLevel 連加 (先處理多段再處理單段)
        multi_refine_assign = re.match(
            r"(\w+)\s*=\s*GetRefineLevel\((\d+)\)((?:\s*\+\s*GetRefineLevel\((\d+)\))+)", line)
        if multi_refine_assign:
            var = multi_refine_assign.group(1)
            slots = re.findall(r"GetRefineLevel\((\d+)\)", line)
            try:
                value = sum([refine_inputs.get(int(slot), 0) for slot in slots])
                variables[var] = value
                results.append(f"📌 `{var}` = {value}（GetRefineLevel({'+'.join(slots)})）")
            except Exception as e:
                results.append(f"⚠️ 無法計算 `{var}` = GetRefineLevel({' + '.join(slots)})，錯誤：{e}")
            continue

        # 新增對 temp = GetRefineLevel(...) 的處理邏輯
        refine_assign = re.match(r"(\w+)\s*=\s*GetRefineLevel\((\d+)\)", line)
        if refine_assign:
            var, slot = refine_assign.groups()
            try:
                value = refine_inputs.get(int(slot), 0)
                variables[var] = value
                results.append(f"📌 `{var}` = {value}（GetRefineLevel({slot})）")
            except:
                results.append(f"⚠️ 無法計算 `{var}` = GetRefineLevel({slot})")
            continue
            


        # 新增對 temp = GetEquipGradeLevel(...) 的處理邏輯
        grade_assign = re.match(r"(\w+)\s*=\s*GetEquipGradeLevel\((\d+)\)", line)
        if grade_assign:
            var, slot = grade_assign.groups()
            try:
                # 如果 grade 是 dict，取對應部位；否則直接用整數
                value = grade.get(int(slot), 0) if isinstance(grade, dict) else grade
                #print(f"[DEBUG] slot {slot} 的 grade 值: {value} 來源: {original_line.strip()}")
                
                variables[var] = value
                results.append(f"📌 `{var}` = {value}（GetEquipGradeLevel({slot})）")
            except:
                results.append(f"⚠️ 無法計算 `{var}` = GetEquipGradeLevel({slot})")
            continue

        # 新增對 temp = GetEquipArmorLv(...) 的處理邏輯
        armor_assign = re.match(r"(\w+)\s*=\s*GetEquipArmorLv\((\d+)\)", line)
        if armor_assign:
            var, slot = armor_assign.groups()
            try:
                slot_i = int(slot)
                # 從全域表拿該部位的「防具等級」；沒設定就預設 0
                value = global_armor_level_map.get(slot_i, 0)
                variables[var] = value
                results.append(f"📌 `{var}` = {value}（GetEquipArmorLv({slot})）")
            except:
                results.append(f"⚠️ 無法計算 `{var}` = GetEquipArmorLv({slot})")
            continue

        # 新增對 temp = GetWeaponClass(...) 的處理邏輯
        weapon_type_name = re.match(r"(\w+)\s*=\s*GetWeaponClass\((\d+)\)", line)
        if weapon_type_name:
            var, slot = weapon_type_name.groups()
            try:
                slot_i = int(slot)
                # 從全域表取得該武器的位置類別，沒有設定則預設 0
                value = global_weapon_type_map.get(slot_i, 0)
                variables[var] = value
                results.append(f"📌 `{var}` = {value}（GetWeaponClass({slot})）")
            except:
                results.append(f"⚠️ 無法計算 `{var}` = GetWeaponClass({slot})")
            continue

        # 新增對 temp = GetEquipWeaponLv(...) 的處理邏輯
        weapon_Lv_name = re.match(r"(\w+)\s*=\s*GetEquipWeaponLv\((\d+)\)", line)
        if weapon_Lv_name:
            var, slot = weapon_Lv_name.groups()
            try:
                slot_i = int(slot)
                # 從全域表取得該武器的位置類別，沒有設定則預設 0
                value = global_weapon_level_map.get(slot_i, 0)
                variables[var] = value
                results.append(f"📌 `{var}` = {value}（GetEquipWeaponLv({slot})）")
            except:
                results.append(f"⚠️ 無法計算 `{var}` = GetEquipWeaponLv({slot})")
            continue
        
        # math.floor(...) 指定變數
        var_math = re.match(r"(\w+)\s*=\s*math\.floor\((.+)\)", line)
        if var_math:
            var, expr = var_math.groups()
            expr = re.sub(r"get\((\d+)\)", lambda m: str(get_values.get(int(m.group(1)), 0)), expr)
            expr = re.sub(r"GetRefineLevel\((\d+)\)", lambda m: str(refine_inputs.get(int(m.group(1)), 0)), expr)
            expr = re.sub(r"GetEquipGradeLevel\((\d+)\)", lambda m: str(grade), expr)
            
            for v in sorted(variables.keys(), key=lambda x: -len(x)):
                expr = re.sub(rf'\b{re.escape(v)}\b', str(variables[v]), expr)
            try:
                value = int(eval(f"math.floor({expr})", safe_globals, safe_locals))
                variables[var] = value
                results.append(f"📌 `{var}` = {value}（floor({expr})）")
            except Exception as e:
                results.append(f"⚠️ 無法計算 `{var}` = floor({expr})，錯誤：{e}")
            continue

        # 一般變數指定
        var_assign = re.match(r"(\w+)\s*=\s*(.+)", line)
        if var_assign and not var_math:
            if not condition_met:
                results.append(f"⛔ 已跳過（條件不成立）: {original_line}")
                continue  # 不執行此行
            var, expr = var_assign.groups()
            if '"' in expr or "'" in expr or "{" in expr or "function" in expr:
                results.append(f"🟡一般變數 無法辨識: {original_line}")
                continue

            # 替換函數式的數值
            expr = re.sub(r"get\((\d+)\)", lambda m: str(get_values.get(int(m.group(1)), 0)), expr)
            expr = re.sub(r"GetRefineLevel\((\d+)\)", lambda m: str(refine_inputs.get(int(m.group(1)), 0)), expr)
            expr = re.sub(r"GetEquipGradeLevel\((\d+)\)", lambda m: str(grade), expr)
            expr = re.sub(
                r"GetSkillLevel\((\d+)\)",
                lambda m: str(enabled_skill_levels.get(int(m.group(1)), 0)),
                expr
            )
            
            variables.update({#給心神凝聚處理的
                "skill_focus_AGI": skill_focus_AGI,
                "skill_focus_DEX": skill_focus_DEX,
            })

            # ✅ 改用 eval + variables 做上下文，不再手動替換
            try:
                value = int(eval(expr, {"__builtins__": None}, variables))
                variables[var] = value
                results.append(f"📌 `{var}` = {value}")
            except Exception as e:
                results.append(f"⚠️ 無法計算 `{var}` = {expr}，錯誤：{e}")
            continue
            

        # 1. EnableSkill(skill_id, level)
        register_function("EnableSkill", "可使用技能", [
            {"name": "技能", "map": "skill_map"},
            {"name": "等級", "type": "value"}
        ])
        enable_skill = re.match(r"EnableSkill\((\d+),\s*(\d+)\)", line)
        if enable_skill and condition_met:
            skill_id, level = enable_skill.groups()
            skill_id = int(skill_id)
            level = int(level)
            skill_name = skill_map.get(skill_id, f"技能ID {skill_id}")
            results.append(f"可使用【{skill_name}】Lv.{level}")
            # ➕ 記錄技能等級
            enabled_skill_levels[skill_id] = level
            continue

        # UseSkill(skill_id)

        use_skill = re.match(r"UseSkill\(\s*(\d+)\s*\)", line)

        if use_skill and condition_met:
            skill_id = int(use_skill.group(1))
            skill_name = skill_map.get(skill_id, f"技能ID {skill_id}")
            results.append(f"使用【{skill_name}】")  # 這裡不帶 Lv，也不紀錄等級
            #紀錄使用
            Use_skill_levels[skill_id] = True 
            continue


        # AddExtParam(...)
        register_function("AddExtParam", "增加基礎能力", [{"name": "無意義", "map": "1"},{"name": "能力", "map": "effect_map"},{"name": "數值", "type": "value"}])
        register_function("SubExtParam", "減少基礎能力", [{"name": "無意義", "map": "1"},{"name": "能力", "map": "effect_map"},{"name": "數值", "type": "value"}])

        # AddExtParam / SubExtParam 合併處理
        ext = re.match(r"(Add|Sub)ExtParam\((\d+),\s*(\d+),\s*(.+)\)", line)
        if ext and condition_met:
            op, unit, param_id, val_expr = ext.groups()
            val = safe_eval_expr(val_expr, variables, get_values, refine_inputs, grade)

            unit_str = unit_map.get(int(unit), f"單位{unit}")
            effect_str = effect_map.get(int(param_id), f"參數{param_id}")

            # 解析失敗保護
            if not isinstance(val, int):
                results.append(f"{effect_str} ({val})（無法解析）")
                continue

            # 預設：Add=+、Sub=-
            def sign_for(op_: str, invert: bool = False) -> str:
                # invert=True 會反轉（給「攻擊後延遲」用）
                return "+" if ((op_ == "Add") != invert) else "-"

            # 特例 1：CRI、完全迴避（每 10 = 1）
            if effect_str in ("CRI", "完全迴避"):
                v = val // 10
                results.append(f"{effect_str} {sign_for(op)}{v}")
                continue

            # 特例 2：攻擊後延遲（Add=減少、Sub=增加）+ 一定加 %
            if effect_str in ("攻擊後延遲","(2轉以下)攻擊後延遲"):
                results.append(f"{effect_str} {sign_for(op, invert=True)}{val}%")
                continue

            # 一般情況：若名稱本身以 % 結尾（如 MATK% / ATK%），就帶 %
            percent_suffix = "%" if str(effect_str).endswith("%") else ""
            results.append(f"{effect_str} {sign_for(op)}{val}{percent_suffix}")
            continue

            
        # AddSpellDelay / SubSpellDelay 合併處理（技能後延遲 %）
        register_function("AddSpellDelay", "增加技能後延遲", [{"name": "數值%", "type": "value"}])
        register_function("SubSpellDelay", "減少技能後延遲", [{"name": "數值%", "type": "value"}])

        delay = re.match(r"(Add|Sub)SpellDelay\(\s*(.+)\s*\)\s*$", line)
        if delay and condition_met:
            op, expr = delay.groups()
            val = safe_eval_expr(expr, variables, get_values, refine_inputs, grade)

            if isinstance(val, int):
                sign = "+" if op == "Add" else "-"
                results.append(f"技能後延遲 {sign}{val}%")
            else:
                # 保留原本的「無法解析」提示
                sign = "+" if op == "Add" else "-"
                results.append(f"技能後延遲 {sign}({val})%（無法解析）")
            continue



        # AddSFCTEquipAmount / SubSFCTEquipAmount（固定詠唱時間，第一參數是物品ID，第二參數是 ms 表達式，第三參數是數字）
        register_function("SubSFCTEquipAmount", "減少固定詠唱時間", [
            {"name": "無意義", "map": "0"},#物品名稱
            {"name": "數值ms", "type": "value"},
            {"name": "無意義", "map": "0"}
        ])
        register_function("AddSFCTEquipAmount", "增加固定詠唱時間", [
            {"name": "無意義", "map": "0"},#物品名稱
            {"name": "數值ms", "type": "value"},
            {"name": "無意義", "map": "0"}
        ])

        sfct = re.match(
            r"(Add|Sub)SFCTEquipAmount\(\s*(?:(\d+)\s*,\s*)?(.+?)\s*,\s*(\d+)\s*\)\s*$",
            line
        )
        if sfct and condition_met and not sfct_handled:
            op, item_id, expr, dummy = sfct.groups()

            # expr 是第二個參數，才是真正的 ms
            val_ms = safe_eval_expr(expr, variables, get_values, refine_inputs, grade)

            sign = "+" if op == "Add" else "-"
            if isinstance(val_ms, int):
                results.append(f"固定詠唱時間 {sign}{val_ms / 1000:.2f} 秒")
            else:
                results.append(f"固定詠唱時間 {sign}({val_ms}) 秒（無法解析）")

            sfct_handled = True
            continue

        sfct_2 = re.match(
            r"(Add|Sub)SFCTEquipPermill\(\s*(?:(\d+)\s*,\s*)?(.+?)\s*,\s*(\d+)\s*\)\s*$",
            line
        )
        if sfct_2 and condition_met and not sfct_handled:
            op, item_id, expr, dummy = sfct_2.groups()

            # expr 是第二個參數，才是真正的 ms
            val = safe_eval_expr(expr, variables, get_values, refine_inputs, grade)
            val = val // 10  # 轉為百分比
            sign = "+" if op == "Add" else "-"
            if isinstance(val, int):
                sign = "+" if op == "Add" else "-"
                results.append(f"固定詠唱時間 {sign}{val}%")
            else:
                # 保留原本的「無法解析」提示
                sign = "+" if op == "Add" else "-"
                results.append(f"固定詠唱時間 {sign}({val})%（無法解析）")
            continue

        # 增減「指定技能傷害(裝備段)」合併處理
        register_function("AddDamage_SKID", "增加技能傷害(裝備段)", [
            {"name": "目標", "map": "unit_map"},
            {"name": "技能", "map": "skill_map"},
            {"name": "數值%", "type": "value"}
        ])
        register_function("SubDamage_SKID", "減少技能傷害(裝備段)", [
            {"name": "目標", "map": "unit_map"},
            {"name": "技能", "map": "skill_map"},
            {"name": "數值%", "type": "value"}
        ])

        add_sub_dmg_skid = re.match(r"(Add|Sub)Damage_SKID\(\s*1\s*,\s*(\d+)\s*,\s*(.+)\s*\)\s*$", line)
        if add_sub_dmg_skid and condition_met:
            op, skill_id, value_expr = add_sub_dmg_skid.groups()
            skill_name = skill_map.get(int(skill_id), f"技能ID {skill_id}")
            val = safe_eval_expr(value_expr, variables, get_values, refine_inputs, grade)

            if isinstance(val, int):
                sign = "+" if op == "Add" else "-"
                results.append(f"技能【{skill_name}】傷害(裝備段) {sign}{val}%")
            else:
                sign = "+" if op == "Add" else "-"
                results.append(f"技能【{skill_name}】傷害(裝備段) {sign}({val})%（無法解析）")
            continue

            
        # 增減「指定技能傷害(技能段)」合併處理
        register_function("AddDamage_passive_SKID", "增加技能傷害(技能段)", [
            {"name": "目標", "map": "unit_map"},
            {"name": "技能", "map": "skill_map"},
            {"name": "數值%", "type": "value"}
        ])
        register_function("SubDamage_passive_SKID", "減少技能傷害(技能段)", [
            {"name": "目標", "map": "unit_map"},
            {"name": "技能", "map": "skill_map"},
            {"name": "數值%", "type": "value"}
        ])

        add_sub_dmg_passive = re.match(
            r"(Add|Sub)Damage_passive_SKID\(\s*1\s*,\s*(\d+)\s*,\s*(.+)\s*\)\s*$",
            line
        )
        if add_sub_dmg_passive and condition_met:
            op, skill_id, value_expr = add_sub_dmg_passive.groups()
            skill_name = skill_map.get(int(skill_id), f"技能ID {skill_id}")
            val = safe_eval_expr(value_expr, variables, get_values, refine_inputs, grade)

            sign = "+" if op == "Add" else "-"
            if isinstance(val, int):
                results.append(f"技能【{skill_name}】傷害(技能段) {sign}{val}%")
            else:
                results.append(f"技能【{skill_name}】傷害(技能段) {sign}({val})%（無法解析）")
            continue

            
        # 指定技能冷卻時間（毫秒）增加/減少 合併處理
        skill_delay = re.match(r"(Add|Sub)SkillDelay\(\s*(\d+)\s*,\s*(.+)\s*\)", line)
        if skill_delay and condition_met:
            op, skill_id, delay_expr = skill_delay.groups()
            skill_name = skill_map.get(int(skill_id), f"技能ID {skill_id}")
            val_ms = safe_eval_expr(delay_expr, variables, get_values, refine_inputs, grade)

            if isinstance(val_ms, int):
                delta = val_ms if op == "Add" else -val_ms
                skill_delay_accum[skill_name] = skill_delay_accum.get(skill_name, 0) + delta
            else:
                # 保留原本的無法解析提示
                results.append(f"技能【{skill_name}】冷卻時間變化 ({val_ms}) 毫秒（無法解析）")
            continue
            
        # 增減 變動詠唱時間（%）合併處理
        register_function("SubSpellCastTime", "減少變動詠唱時間", [{"name": "數值%", "type": "value"}])
        register_function("AddSpellCastTime", "增加變動詠唱時間", [{"name": "數值%", "type": "value"}])

        cast_time = re.match(r"(Add|Sub)SpellCastTime\(\s*(.+)\s*\)", line)
        if cast_time and condition_met:
            op, value_expr = cast_time.groups()
            val = safe_eval_expr(value_expr, variables, get_values, refine_inputs, grade)

            sign = "+" if op == "Add" else "-"
            try:
                results.append(f"變動詠唱時間 {sign}{val}%")
            except Exception:
                results.append(f"變動詠唱時間 {sign}({value_expr})%（無法解析）")
            continue


        # Add/Sub SpecificSpellCastTime（指定技能變動詠唱時間 %）
        specific_cast = re.match(r"(Add|Sub)SpecificSpellCastTime\(\s*(\d+)\s*,\s*(.+)\s*\)", line)
        if specific_cast and condition_met:
            op, skill_id, value_expr = specific_cast.groups()
            skill_name = skill_map.get(int(skill_id), f"技能ID {skill_id}")
            val = safe_eval_expr(value_expr, variables, get_values, refine_inputs, grade)

            sign = "+" if op == "Add" else "-"
            if isinstance(val, int):
                results.append(f"技能【{skill_name}】變動詠唱時間 {sign}{val}%")
            else:
                results.append(f"技能【{skill_name}】變動詠唱時間 {sign}({val})%（無法解析）")
            continue
        # Add/Sub EXPPercent_KillRace (從擊殺魔物獲得的經驗%)
        exp_race = re.match(r"(Add|Sub)EXPPercent_KillRace\(\s*(\d+)\s*,\s*(.+)\s*\)", line)
        if exp_race and condition_met:
            op, race_id, value_expr = exp_race.groups()
            race_name = race_map.get(int(race_id), f"種族{race_id}")
            val = safe_eval_expr(value_expr, variables, get_values, refine_inputs, grade)
            sign = "+" if op == "Add" else "-"
            results.append(f"從 {race_name} 型怪的經驗值 {sign}{val}%")
            continue


        register_function("就說通用了你還產生！", "----以上通用分隔線----", [])
        register_function("就說以下魔法了你還產生！", "--以下魔法增減分隔線--", [])
#==========以上通用變數
#==========以下魔法判斷        
        # Add/Sub MDamage_Size（體型魔法）
        register_function("AddMDamage_Size", "增加體型魔法傷害", [
            {"name": "目標", "map": "unit_map"},
            {"name": "體型", "map": "size_map"},
            {"name": "數值%", "type": "value"}
        ])
        register_function("SubMDamage_Size", "減少體型魔法傷害", [
            {"name": "目標", "map": "unit_map"},
            {"name": "體型", "map": "size_map"},
            {"name": "數值%", "type": "value"}
        ])

        mdamage_size = re.match(r"(Add|Sub)MDamage_Size\(\s*1\s*,\s*(\d+)\s*,\s*(.+)\s*\)", line)
        if mdamage_size and condition_met:
            op, size_id, value_expr = mdamage_size.groups()
            size_name = size_map.get(int(size_id), f"尺寸{size_id}")
            val = safe_eval_expr(value_expr, variables, get_values, refine_inputs, grade)
            sign = "+" if op == "Add" else "-"
            results.append(f"對 {size_name} 敵人的魔法傷害 {sign}{val}%")
            continue


        # Add/Sub SkillMDamage（屬性魔法傷害）
        register_function("AddSkillMDamage", "增加屬性魔法傷害", [
            {"name": "屬性", "map": "element_map"},
            {"name": "數值%", "type": "value"}
        ])
        register_function("SubSkillMDamage", "減少屬性魔法傷害", [
            {"name": "屬性", "map": "element_map"},
            {"name": "數值%", "type": "value"}
        ])

        skill_mdamage = re.match(r"(Add|Sub)SkillMDamage\(\s*(\d+)\s*,\s*(.+)\s*\)", line)
        if skill_mdamage and condition_met:
            op, elem_id, value_expr = skill_mdamage.groups()
            element = element_map.get(int(elem_id), f"屬性{elem_id}")
            val = safe_eval_expr(value_expr, variables, get_values, refine_inputs, grade)
            sign = "+" if op == "Add" else "-"
            results.append(f"{element} 的魔法傷害 {sign}{val}%")
            continue


        # Add/Sub MDamage_Property（對指定種族與屬性）
        register_function("AddMDamage_Property", "增加屬性對象魔法傷害", [
            {"name": "目標", "map": "unit_map"},
            {"name": "屬性", "map": "element_map"},
            {"name": "數值%", "type": "value"}
        ])
        register_function("SubMDamage_Property", "減少屬性對象魔法傷害", [
            {"name": "目標", "map": "unit_map"},
            {"name": "屬性", "map": "element_map"},
            {"name": "數值%", "type": "value"}
        ])

        add_mdamage_prop = re.match(r"(Add|Sub)MDamage_Property\(\s*1\s*,\s*(\d+)\s*,\s*(.+)\s*\)", line)
        if add_mdamage_prop and condition_met:
            op, elem_id, value_expr = add_mdamage_prop.groups()
            elem_name = element_map.get(int(elem_id), f"屬性{elem_id}")
            val = safe_eval_expr(value_expr, variables, get_values, refine_inputs, grade)
            sign = "+" if op == "Add" else "-"
            results.append(f"對 {elem_name} 對象的魔法傷害 {sign}{val}%")
            continue


        # Add/Sub Mdamage_Race（對種族魔法傷害）
        register_function("AddMdamage_Race", "增加種族魔法傷害", [
            {"name": "種族", "map": "race_map"},
            {"name": "數值%", "type": "value"}
        ])
        register_function("SubMdamage_Race", "減少種族魔法傷害", [
            {"name": "種族", "map": "race_map"},
            {"name": "數值%", "type": "value"}
        ])

        mdamage_race = re.match(r"(Add|Sub)Mdamage_Race\(\s*(\d+)\s*,\s*(.+)\s*\)", line)
        if mdamage_race and condition_met:
            op, race_id, value_expr = mdamage_race.groups()
            race_name = race_map.get(int(race_id), f"種族{race_id}")
            val = safe_eval_expr(value_expr, variables, get_values, refine_inputs, grade)
            sign = "+" if op == "Add" else "-"
            results.append(f"對 {race_name} 型怪的魔法傷害 {sign}{val}%")
            continue


        # AddMdamage_Class（對階級魔法傷害）
        
        register_function("AddMdamage_Class", "增加階級魔法傷害", [
            {"name": "階級", "map": "class_map"},
            {"name": "數值%", "type": "value"}
        ])
        register_function("SubMdamage_Class", "減少階級魔法傷害", [
            {"name": "階級", "map": "class_map"},
            {"name": "數值%", "type": "value"}
        ])

        # AddMdamage_Class / SubMdamage_Class 合併處理
        mdamage_class = re.match(r"(Add|Sub)Mdamage_Class\(\s*(\d+)\s*,\s*(.+?)\s*\)", line)
        if mdamage_class and condition_met:
            op, class_id, value_expr = mdamage_class.groups()
            class_name = class_map.get(int(class_id), f"階級{class_id}")
            val = safe_eval_expr(value_expr, variables, get_values, refine_inputs, grade)

            sign = "+" if op == "Add" else "-"
            results.append(f"對 {class_name} 階級的魔法傷害 {sign}{val}%")
            continue

        # SetIgnoreMdefClass（無視階級魔防）
        
        register_function("SetIgnoreMdefClass", "無視階級魔法防禦", [
            {"name": "階級", "map": "class_map"},
            {"name": "數值%", "type": "value"}
        ])
        ignore_mdef = re.match(r"SetIgnoreMdefClass\((\d+),\s*(.+?)\)", line)
        if ignore_mdef and condition_met:
            class_id, value_expr = ignore_mdef.groups()
            class_name = class_map.get(int(class_id), f"階級{class_id}")
            val = safe_eval_expr(value_expr, variables, get_values, refine_inputs, grade)
            results.append(f"無視 {class_name} 階級的魔法防禦 {val}%")
            continue

        # AddIgnore_MRES_RacePercent（無視種族魔抗）
        
        register_function("AddIgnore_MRES_RacePercent", "無視種族魔法抗性", [
            {"name": "種族", "map": "race_map"},
            {"name": "數值%", "type": "value"}
        ])
        ignore_mres_race = re.match(r"AddIgnore_MRES_RacePercent\((\d+),\s*(.+?)\)", line)
        if ignore_mres_race and condition_met:
            race_id, value_expr = ignore_mres_race.groups()
            race_name = race_map.get(int(race_id), f"種族{race_id}")
            val = safe_eval_expr(value_expr, variables, get_values, refine_inputs, grade)
            results.append(f"無視 {race_name} 型怪的魔法抗性 {val}%")
            continue
            
        # SetIgnoreMdefClass（無視種族魔防）
        
        register_function("SetIgnoreMdefRace", "無視種族魔法防禦", [
            {"name": "種族", "map": "race_map"},
            {"name": "數值%", "type": "value"}
        ])
        ignore_mdef_race = re.match(r"SetIgnoreMdefRace\((\d+),\s*(.+?)\)", line)
        if ignore_mdef_race and condition_met:
            race_id, value_expr = ignore_mdef_race.groups()
            race_name = race_map.get(int(race_id), f"種族{race_id}")
            val = safe_eval_expr(value_expr, variables, get_values, refine_inputs, grade)
            results.append(f"無視 {race_name} 型怪的魔法防禦 {val}%")
            continue
            
        # 特定魔物魔法增傷MonsterMAtkPercent(value)
        register_function("MonsterMAtkPercent", "增加特定魔物魔法傷害", [
            {"name": "數值%", "type": "value"}
        ])
        mon_m_atk = re.match(r"MonsterMAtkPercent\(\s*(.+)\s*\)", line)
        if mon_m_atk and condition_met:
            value_expr = mon_m_atk.group(1)
            value_expr = safe_eval_expr(value_expr, variables, get_values, refine_inputs, grade)
            results.append(f"特定魔物魔法增傷 +{value_expr}%")
            continue
        # 特定魔物魔法增傷MonsterMAtkPercent(value)
        register_function("SubMonsterMAtkPercent", "減少特定魔物魔法傷害", [
            {"name": "數值%", "type": "value"}
        ])
        mon_m_atk = re.match(r"SubMonsterMAtkPercent\(\s*(.+)\s*\)", line)
        if mon_m_atk and condition_met:
            value_expr = mon_m_atk.group(1)
            value_expr = safe_eval_expr(value_expr, variables, get_values, refine_inputs, grade)
            results.append(f"特定魔物魔法增傷 -{value_expr}%")
            continue
            
#===========以上魔法判斷
#===========以下物理判斷
        register_function("就說以上魔法了你還產生！", "--以上魔法增減分隔線--", [])
        register_function("就說以下物理了你還產生！", "--以下物理增減分隔線--", [])
        #修煉ATK WeaponMasteryATK(value)
        MasteryATK_dmg = re.match(r"WeaponMasteryATK\(\s*(.+?)\)", line)
        if MasteryATK_dmg and condition_met:
            value_expr = MasteryATK_dmg.group(1)
            value_expr = safe_eval_expr(value_expr, variables, get_values, refine_inputs, grade)
            results.append(f"修煉ATK +{value_expr}")
            continue

        #誘導攻擊機率AddGuideAttack(value)
        guide_attack = re.match(r"AddGuideAttack\(\s*(.+?)\s*\)", line)
        if guide_attack and condition_met:
            value_expr = guide_attack.group(1)
            value_expr = safe_eval_expr(value_expr, variables, get_values, refine_inputs, grade)
            results.append(f"誘導攻擊機率 +{value_expr}%")
            continue

        # AddDamage_HIT(1, value)
        
        register_function("AddDamage_HIT", "物理命中傷害", [
            {"name": "目標", "map": "unit_map"},
            {"name": "數值%", "type": "value"}
        ])
        melee_hit = re.match(r"AddDamage_HIT\(\s*1\s*,\s*(.+)\)", line)
        if melee_hit and condition_met:
            value_expr = melee_hit.group(1)
            value_expr = safe_eval_expr(value_expr, variables, get_values, refine_inputs, grade)
            results.append(f"物理命中傷害 +{value_expr}%")
            continue

        # AddMeleeAttackDamage(1, value)
        
        register_function("AddMeleeAttackDamage", "增加近距離物理傷害", [
            {"name": "目標", "map": "unit_map"},
            {"name": "數值%", "type": "value"}
        ])
        register_function("SubMeleeAttackDamage", "減少近距離物理傷害", [
            {"name": "目標", "map": "unit_map"},
            {"name": "數值%", "type": "value"}
        ])
        melee_dmg = re.match(r"(Add|Sub)MeleeAttackDamage\(\s*1\s*,\s*(.+)\)", line)
        if melee_dmg and condition_met:
            op, value_expr = melee_dmg.group(1,2)
            value_expr = safe_eval_expr(value_expr, variables, get_values, refine_inputs, grade)
            sign = "+" if op == "Add" else "-"
            results.append(f"近距離物理傷害 {sign}{value_expr}%")
            continue

        # AddRangeAttackDamage(1, value)
        
        register_function("AddRangeAttackDamage", "增加遠距離物理傷害", [
            {"name": "目標", "map": "unit_map"},
            {"name": "數值%", "type": "value"}
        ])
        register_function("SubRangeAttackDamage", "減少遠距離物理傷害", [
            {"name": "目標", "map": "unit_map"},
            {"name": "數值%", "type": "value"}
        ])
        range_dmg = re.match(r"(Add|Sub)RangeAttackDamage\(\s*1\s*,\s*(.+)\)", line)

        if range_dmg and condition_met:
            op, value_expr = range_dmg.group(1,2)
            value_expr = safe_eval_expr(value_expr, variables, get_values, refine_inputs, grade)
            sign = "+" if op == "Add" else "-"
            results.append(f"遠距離物理傷害 {sign}{value_expr}%")
            continue
            
        # AddBowAttackDamage(1, value)#弓攻擊力
        range_dmg = re.match(r"AddBowAttackDamage\(\s*1\s*,\s*(.+)\)", line)
        
        if range_dmg and condition_met:
            value_expr = range_dmg.group(1)
            value_expr = safe_eval_expr(value_expr, variables, get_values, refine_inputs, grade)
            #results.append(f"遠距離物理傷害 +{value_expr}%")
            results.append(f"弓攻擊力 +{value_expr}%")
            continue

        # AddDamage_CRI(1, value)
        
        register_function("AddDamage_CRI", "增加爆擊傷害", [
            {"name": "目標", "map": "unit_map"},
            {"name": "數值%", "type": "value"}
        ])
        register_function("SubDamage_CRI", "減少爆擊傷害", [
            {"name": "目標", "map": "unit_map"},
            {"name": "數值%", "type": "value"}
        ])
        cri_dmg = re.match(r"(Add|Sub)Damage_CRI\(\s*1\s*,\s*(.+)\)", line)
        if cri_dmg and condition_met:
            op, value_expr = cri_dmg.group(1,2)
            value_expr = safe_eval_expr(value_expr, variables, get_values, refine_inputs, grade)
            sign = "+" if op == "Add" else "-"
            results.append(f"爆擊傷害 {sign}{value_expr}%")
            continue


        # AddDamage_Size(1, size_id, value)
        
        register_function("AddDamage_Size", "增加體型物理傷害", [
            {"name": "目標", "map": "unit_map"},
            {"name": "體型", "map": "size_map"},
            {"name": "數值%", "type": "value"}
        ])
        register_function("SubDamage_Size", "減少體型物理傷害", [
            {"name": "目標", "map": "unit_map"},
            {"name": "體型", "map": "size_map"},
            {"name": "數值%", "type": "value"}
        ])
        size_dmg = re.match(r"(Add|Sub)Damage_Size\(\s*1\s*,\s*(\d+)\s*,\s*(.+)\s*\)", line)
        if size_dmg and condition_met:
            
            op, size_id, value_expr = size_dmg.groups()
            size_str = size_map.get(int(size_id), f"體型{size_id}")
            value_expr = safe_eval_expr(value_expr, variables, get_values, refine_inputs, grade)
            sign = "+" if op == "Add" else "-"
            results.append(f"對 {size_str} 敵人的物理傷害 {sign}{value_expr}%")
            continue

        # AddDamage_Property（對指定種族與屬性）
        
        register_function("AddDamage_Property", "增加屬性敵人物理傷害", [
            {"name": "目標", "map": "unit_map"},
            {"name": "屬性", "map": "element_map"},
            {"name": "數值%", "type": "value"}
        ])
        register_function("SubDamage_Property", "減少屬性敵人物理傷害", [
            {"name": "目標", "map": "unit_map"},
            {"name": "屬性", "map": "element_map"},
            {"name": "數值%", "type": "value"}
        ])
        add_damage_prop = re.match(r"(Add|Sub)Damage_Property\(\s*1\s*,\s*(\d+)\s*,\s*(.+)\s*\)", line)
        if add_damage_prop and condition_met:
            op, elem_id, value_expr = add_damage_prop.groups()
            elem_name = element_map.get(int(elem_id), f"屬性{elem_id}")
            val = safe_eval_expr(value_expr, variables, get_values, refine_inputs, grade)
            sign = "+" if op == "Add" else "-"
            results.append(f"對 {elem_name} 對象的物理傷害 {sign}{val}%")
            continue

        # SetIgnoreDEFRace(race_id)
        ignore_race = re.match(r"SetIgnoreDEFRace\((\d+)\)", line)
        if ignore_race and condition_met:
            race_name = race_map.get(int(ignore_race.group(1)), f"種族{ignore_race.group(1)}")
            results.append(f"無視 {race_name} 型怪的物理防禦 +100%")
            continue

        # SetIgnoreDefRace_Percent(race_id, value)
        
        register_function("SetIgnoreDefRace_Percent", "無視種族物理防禦", [
            {"name": "種族", "map": "race_map"},
            {"name": "數值%", "type": "value"}
        ])
        ignore_race_pct = re.match(r"SetIgnoreDefRace_Percent\((\d+),\s*(.+?)\)", line)
        if ignore_race_pct and condition_met:
            race_id, value_expr = ignore_race_pct.groups()
            race_name = race_map.get(int(race_id), f"種族{race_id}")
            val = safe_eval_expr(value_expr, variables, get_values, refine_inputs, grade)
            results.append(f"無視 {race_name} 型怪的物理防禦 {val}%")
            continue

        # SetIgnoreDEFClass(class_id)
        ignore_class = re.match(r"SetIgnoreDEFClass\((\d+)\)", line)
        if ignore_class and condition_met:
            class_name = class_map.get(int(ignore_class.group(1)), f"階級{ignore_class.group(1)}")
            results.append(f"無視 {class_name} 階級的物理防禦")
            continue
            
        # PerfectDamage(1)
        perfect_damage = re.match(r"^PerfectDamage\(1\)$", line.strip())
        if perfect_damage and condition_met:
            results.append(f"武器體型修正 100%")
            continue

        # SetIgnoreDefClass_Percent(class_id, value)
        
        register_function("SetIgnoreDefClass_Percent", "無視階級物理防禦", [
            {"name": "階級", "map": "class_map"},
            {"name": "數值%", "type": "value"}
        ])
        ignore_class_pct = re.match(r"SetIgnoreDefClass_Percent\((\d+),\s*(\d+)\)", line)
        if ignore_class_pct and condition_met:
            class_id, value = ignore_class_pct.groups()
            class_name = class_map.get(int(class_id), f"階級{class_id}")
            results.append(f"無視 {class_name} 階級的物理防禦 {value}%")
            continue

        # RaceAddDamage(race_id, value)
        
        register_function("RaceAddDamage", "增加種族物理傷害", [
            {"name": "種族", "map": "race_map"},
            {"name": "數值%", "type": "value"}
        ])
        register_function("RaceSubDamage", "減少種族物理傷害", [
            {"name": "種族", "map": "race_map"},
            {"name": "數值%", "type": "value"}
        ])
        race_dmg = re.match(r"Race(Add|Sub)Damage\((\d+),\s*(.+?)\)", line)
        if race_dmg and condition_met:
            op, race_id, value_expr = race_dmg.groups()
            race_name = race_map.get(int(race_id), f"種族{race_id}")
            value_expr = safe_eval_expr(value_expr, variables, get_values, refine_inputs, grade)
            sign = "+" if op == "Add" else "-"
            results.append(f"對 {race_name} 型怪的物理傷害 {sign}{value_expr}%")
            continue
                
        # AddIgnore_RES_RacePercent(race_id, value)
        
        register_function("AddIgnore_RES_RacePercent", "無視種族物理抗性", [
            {"name": "種族", "map": "race_map"},
            {"name": "數值%", "type": "value"}
        ])
        ignore_res_race = re.match(r"AddIgnore_RES_RacePercent\((\d+),\s*(.+?)\)", line)
        if ignore_res_race and condition_met:
            race_id, value_expr = ignore_res_race.groups()
            race_name = race_map.get(int(race_id), f"種族{race_id}")
            value_expr = safe_eval_expr(value_expr, variables, get_values, refine_inputs, grade)
            results.append(f"無視 {race_name} 型怪的物理抗性 {value_expr}%")
            continue
            
        # 階級物理傷害加成：ClassAddDamage(1, class_id, value)

        register_function("ClassAddDamage", "增加階級的物理傷害", [
            {"name": "階級", "map": "class_map"},
            {"name": "目標", "map": "unit_map"},
            {"name": "數值%", "type": "value"}
        ])
        register_function("ClassSubDamage", "減少階級的物理傷害", [
            {"name": "階級", "map": "class_map"},
            {"name": "目標", "map": "unit_map"},
            {"name": "數值%", "type": "value"}
        ])
        class_dmg = re.match(r"Class(Add|Sub)Damage\(\s*(\d+)\s*,\s*1\s*,\s*(.+?)\s*\)", line)
        if class_dmg and condition_met:
            op, class_id, expr_src = class_dmg.groups()
            class_name = class_map.get(int(class_id), f"階級{class_id}")
            val = safe_eval_expr(expr_src, variables, get_values, refine_inputs, grade)
            sign = "+" if op == "Add" else "-"
            results.append(f"對 {class_name} 階級的物理傷害 {sign}{val}%")
            continue

        WP_INVESTIGATE_dmg = re.match(r"SetInvestigate()", line)
        if WP_INVESTIGATE_dmg and condition_met:
            results.append(f"武器浸透勁效果")
            results.append(f"無視 全種族 型怪的物理防禦 +100%")
            #Use_skill_levels[266] = True #會跟目前裝備衝突 改到計算內處理
            continue


        # 特定魔物物理增傷MonsterAtkPercent(value)
        register_function("MonsterAtkPercent", "增加特定魔物物理傷害", [
            {"name": "數值%", "type": "value"}
        ])       
        mon_atk = re.match(r"MonsterAtkPercent\(\s*(.+)\s*\)", line)
        if mon_atk and condition_met:
            value_expr = mon_atk.group(1)
            value_expr = safe_eval_expr(value_expr, variables, get_values, refine_inputs, grade)
            results.append(f"特定魔物物理增傷 +{value_expr}%")
            continue
        # 特定魔物物理減傷MonsterAtkPercent(value)
        register_function("SubMonsterAtkPercent", "減少特定魔物物理傷害", [
            {"name": "數值%", "type": "value"}
        ])       
        mon_atk = re.match(r"SubMonsterAtkPercent\(\s*(.+)\s*\)", line)
        if mon_atk and condition_met:
            value_expr = mon_atk.group(1)
            value_expr = safe_eval_expr(value_expr, variables, get_values, refine_inputs, grade)
            results.append(f"特定魔物物理增傷 -{value_expr}%")
            continue
#==============以上物理判斷

#待處理判斷
#通用(恢復效果、SP消耗
#自身(對某種族減傷、對某種族抗性、
#物理(物理反射%、對屬性減少傷害、對某種族的CRI+%
#魔法(魔法反射
#================以下判斷失敗或不成立區塊
        if not hide_unrecognized:
            stripped = original_line.strip()
            if stripped and not stripped.startswith("--"):  # 排除空白行和註解
                if not condition_met:
                    results.append(f"⛔ 已跳過（條件不成立）: {original_line}")
                else:
                    results.append(f"🟡line解析 無法辨識: {original_line}")


    for skill_name, total_ms in skill_delay_accum.items():
        sec = abs(total_ms) / 1000
        if total_ms < 0:
            results.append(f"技能【{skill_name}】冷卻時間 -{sec:.2f} 秒")
        else:
            results.append(f"技能【{skill_name}】冷卻時間 +{sec:.2f} 秒")

        # 所有邏輯都未匹配時：顯示無法辨識語句

    def combine_effects(results):
        combined = defaultdict(int)
        final_lines = []
        
        for line in results:
            # 支援加總格式：「效果說明 +數值」或「效果說明 -數值」
            match = re.match(r"(.+?) ([+-]\d+)([%]?)$", line)
            if match:
                key = match.group(1).strip()
                value = int(match.group(2))
                suffix = match.group(3)  # % 結尾
                combined[(key, suffix)] += value
            else:
                final_lines.append(line)

        for (key, suffix), total in combined.items():
            final_lines.append(f"{key} {total:+d}{suffix}")

        return final_lines

        results.append(f"🟡 無法辨識: {original_line}")

   
    if hide_unrecognized:
        return combine_effects(results)
        
    else:
        return results

def convert_description_to_html(description_lines):#視覺化說明欄
    html_lines = []
    color_stack = []

    for line in description_lines:
        result = ""
        i = 0
        while i < len(line):
            if line[i] == "^" and i + 6 < len(line):
                color_code = line[i+1:i+7]
                if re.fullmatch(r"[0-9a-fA-F]{6}", color_code):
                    result += f'<span style="color:#{color_code}">'
                    color_stack.append("</span>")
                    i += 7
                    continue
            result += line[i]
            i += 1

        # 關閉所有尚未關閉的 <span>
        while color_stack:
            result += color_stack.pop()
        html_lines.append(result)

    return "<br>".join(html_lines)

def decompile_lub(lub_path, output_path):
    """使用 luadec.exe 反編譯 LUB → LUA"""
    if not os.path.exists(lub_path):
        QMessageBox.critical(None, "錯誤", f"找不到 LUB 檔案：\n{lub_path}")
        return False

    try:
        with open(output_path, "w", encoding="utf-8") as out_file:
            subprocess.run(
                [r"APP\luadec.exe", lub_path],
                stdout=out_file,
                stderr=subprocess.PIPE,
                check=True
            )
        print(f"✨ LUB 已反編譯 -> {output_path}")
        return True

    except subprocess.CalledProcessError as e:
        QMessageBox.critical(None, "反編譯失敗", e.stderr.decode("utf-8", errors="ignore"))
        return False

    except FileNotFoundError:
        QMessageBox.critical(None, "錯誤", "找不到 luadec.exe，請確認它放在 APP 資料夾。")
        return False


def parse_lub_file(filename):#字典化物品列表


    try:
        with open(filename, "r", encoding="utf-8") as file:
            content = file.read()
    except FileNotFoundError:
        QMessageBox.critical(None, "錯誤", f"找不到檔案：{filename}")
        return {}

    item_entries = re.findall(
        r"\[(\d+)\]\s*=\s*{(.*?)}(?=,\s*\[\d+\]|\s*\[\d+\]|\s*$)",
        content,
        re.DOTALL
    )

    parsed_items = {}
    total = len(item_entries)
    print(f"📦 開始讀取 {os.path.basename(filename)}，共 {total} 筆物品資料。")
    
    
    
    #for item_id, body in item_entries:
    for index, (item_id, body) in enumerate(item_entries, start=1):
        
        try:
            
            print(f"  → 正在讀取第 {index}/{total} 筆", end="\r")
            item_id = int(item_id)
            identified_name = re.search(r'(?<!un)identifiedDisplayName\s*=\s*"([^"]+)"', body)

            kr_name = re.search(r'(?<!un)identifiedResourceName\s*=\s*"([^"]+)"', body)
            slot = re.search(r'slotCount\s*=\s*(\d+)', body)

            desc_match = re.search(r'(?<!un)identifiedDescriptionName\s*=\s*{(.*?)}', body, re.DOTALL)
            if desc_match:
                desc_body = desc_match.group(1)
                desc_lines_raw = re.findall(r'"([^"]*)"', desc_body)
                desc_lines = []
                for line in desc_lines_raw:
                    cleaned = line.strip()
                    # 控制碼行過濾，但保留真正空白行
                    if re.fullmatch(r"\^?[a-fA-F0-9]+", cleaned):
                        continue
                    elif cleaned == "":
                        desc_lines.append("")  # 保留空白行
                    else:
                        desc_lines.append(cleaned)


            else:
                desc_lines = []
            
            if identified_name and kr_name and slot:
                base_name = identified_name.group(1).strip()
                slot_count = int(slot.group(1))

                # ✅ 名稱加上孔數
                if slot_count > 0:
                    display_name = f"{base_name} [{slot_count}]"
                else:
                    display_name = base_name

                parsed_items[item_id] = {
                    "name": display_name,           # 已經含孔數
                    "base_name": base_name,         # 如果以後要用純名稱，可以保留
                    "kr_name": kr_name.group(1).strip(),
                    "description": desc_lines,
                    "slot": slot_count
                }

        except Exception:
            continue
    return parsed_items

def load_skill_delay_lua(filename) -> str:
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print("讀取 skilldelaylist.lua 失敗:", e)
        return ""


def resolve_name_conflicts(parsed_items, equipment_blocks):
    """
    parsed_items: parse_lub_file() 的結果
    equipment_blocks: parse_equipment_blocks() 的結果
    只對有能力區塊的 itemID 執行名稱重複處理
    """

    # 只取出「有能力」的物品
    affected_items = {
        item_id: parsed_items[item_id]
        for item_id in equipment_blocks.keys()
        if item_id in parsed_items
    }

    # 統計名稱出現次數
    name_count = {}
    for item_id, info in affected_items.items():
        name = info["name"]
        name_count[name] = name_count.get(name, 0) + 1

    # 只有重複名稱需要加 itemID
    for item_id, info in affected_items.items():
        name = info["name"]
        if name_count[name] > 1:
            #print(f"{name}")
            info["name"] = f"{name} (ID:{item_id})"

    # 注意：parsed_items 本身也會被更新（因為 dict 是參考）
    return parsed_items



#素質點計算#取自ROCalculator
def calculate_stat_points(level: int, job_id: int) -> int:
    # 4302 ~ 4308 = 0，其餘 = 100
    if 4302 <= job_id <= 4308:
        pt = 48
    else:
        pt = 100

    for i in range(1, level):
        if i < 100:
            pt += i // 5 + 3
        elif i <= 150:
            pt += i // 10 + 13
        elif i <= 185:
            pt += 28 + (i - 150) // 7
        elif i < 200:
            pt += 33 + (i - 185) // 7
    return pt



#素質消耗計算#取自ROCalculator
def raising_stats(stat_str: str) -> int:
    try:
        val = int(stat_str.split('+')[0])
    except Exception:
        return 0

    pt = 0
    for i in range(1, val):
        if i < 100:
            pt += (i - 1) // 10 + 2
        else:
            pt += 4 * ((i - 100) // 5) + 16
    return pt


import json, os
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton

class PreferencesDialog(QDialog):
    def __init__(self, current_mode: str, current_api_key: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("偏好設定")
        self.resize(260, 180)  # 高度加一點

        layout = QVBoxLayout(self)

        # 模式選單
        hl = QHBoxLayout()
        hl.addWidget(QLabel("自動更新模式："))
        self.mode_combo = QComboBox()
        options = [
            ("線上來源", "online_only"),
            ("本機來源", "local_only"),
        ]
        for text, val in options:
            self.mode_combo.addItem(text, userData=val)

        idx = self.mode_combo.findData(current_mode or "online_only")
        self.mode_combo.setCurrentIndex(idx if idx >= 0 else 0)

        hl.addWidget(self.mode_combo)
        layout.addLayout(hl)
        # 說明
        tip = QLabel("建議使用線上模式，設為本機需要環境有Python跟java環境才可編譯。")
        tip.setWordWrap(True)
        layout.addWidget(tip)
        # ✅ 新增：API Key
        ak = QHBoxLayout()
        ak.addWidget(QLabel("API Key："))
        self.api_edit = QLineEdit()
        self.api_edit.setPlaceholderText("輸入 API Key")
        self.api_edit.setText(current_api_key or "")
        self.api_edit.setEchoMode(QLineEdit.EchoMode.Password)  # 預設隱藏
        ak.addWidget(self.api_edit)
        layout.addLayout(ak)

        self.show_key_cb = QCheckBox("顯示")
        self.show_key_cb.toggled.connect(self._toggle_api_visible)
        layout.addWidget(self.show_key_cb)
        # 說明
        keytip = QLabel("此key用於divine-pride內的魔物查詢api，用來取得魔物資訊。")
        keytip.setWordWrap(True)
        layout.addWidget(keytip)


        # 按鈕
        btns = QHBoxLayout()
        ok_btn = QPushButton("確定")
        cancel_btn = QPushButton("取消")
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        btns.addStretch(1)
        btns.addWidget(ok_btn)
        btns.addWidget(cancel_btn)
        layout.addLayout(btns)

    def _toggle_api_visible(self, checked: bool):
        self.api_edit.setEchoMode(
            QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
        )

    def selected_mode(self) -> str:
        return self.mode_combo.currentData()

    def api_key(self) -> str:
        return self.api_edit.text().strip()



class ItemSearchApp(QWidget):
    def open_enchant_tool(self):#附魔工具
        # 載入所需資料
        item_data = self.parsed_items
        itemdb = enchant.parse_itemdb_name_tbl("data/ItemDBNameTbl.lua")
        enchant_data = enchant.parse_enchant_list("data/EnchantList.lua")

        # 建立 UI
        self.enchant_window = enchant.EnchantUI(enchant_data, item_data, itemdb)
        self.enchant_window.setWindowTitle("附魔查詢工具")
        self.enchant_window.resize(900, 600)
        self.enchant_window.show()

    def open_reform_tool(self):#改造工具
        # 載入所需資料
        item_data = self.parsed_items
        reform = reform_viewer.parse_reform_info("data/ItemReformSystem.lua")
        reform_item_list = reform_viewer.parse_reform_item_list("data/ItemReformSystem.lua")
        itemdb = reform_viewer.parse_itemdb_name_tbl("data/ItemDBNameTbl.lua")

        # 建立 UI
        self.reform_viewer_window = reform_viewer.ReformUI(reform, item_data, itemdb, reform_item_list)
        self.reform_viewer_window.setWindowTitle("改造查詢工具")
        self.reform_viewer_window.resize(700, 600)
        self.reform_viewer_window.show()

    def _set_combo_by_key(self, combo, key: int):
        idx = combo.findData(key)
        if idx >= 0:
            combo.setCurrentIndex(idx)

    def apply_monster_to_main_ui(self, m: dict):
        self._set_combo_by_key(self.size_box, m["size_id"])
        self._set_combo_by_key(self.element_box, m["element_id"])
        self.element_lv_input.setText(str(m["element_lv"]))
        self._set_combo_by_key(self.race_box, m["race_id"])
        self._set_combo_by_key(self.class_box, m["class_id"])

        self.defc_input.setText(f'{m["def_before"]}')
        self.mdefc_input.setText(f'{m["mdef_before"]}')
        self.def_input.setText(str(m["def_after"]))
        self.mdef_input.setText(str(m["mdef_after"]))

        self.res_input.setText(str(m["res"]))
        self.mres_input.setText(str(m["mres"]))

    def open_monster_lookup(self):
        dlg = MonsterLookupDialog(self)
        dlg.monsterSelected.connect(self.apply_monster_to_main_ui)
        dlg.monsterSelected.connect(lambda: (setattr(self, "_last_calc_state", None), self.trigger_total_effect_update()))
        dlg.exec()



    def open_skill_tree(self):

        skill_tree.job_dict = job_dict
        skill_tree.load_skill_tree("data/skill_tree.yml")
        skill_tree.load_skill_treeview("data/skilltreeview.lub")

        self.skill_tree_window = skill_tree.SkillTreeWindow()

        # ★ 新增：把主視窗傳給技能樹視窗（這一行是關鍵）
        self.skill_tree_window.attach_main_window(self)

        job_id = self.input_fields["JOB"].currentData()
        job_key = job_dict[job_id]["id_jobneme"]

        # ★ 設定 callback
        self.skill_tree_window.on_close_callback = self.receive_skill_tree_result

        # ★ 設定職業（這會觸發 on_job_changed，但需要等 event-loop）
        idx = self.skill_tree_window.job_combo.findData(job_key)
        self.skill_tree_window.job_combo.setCurrentIndex(idx)

        # ---------------------------------------------------
        # ★ 在下一輪事件（Qt）再執行 restore → 此時 on_job_changed 已初始化完成
        # ---------------------------------------------------
        def do_restore():
            self.restore_skill_tree_levels()

            # ★ 套用技能等級
            self.skill_tree_window.tree_widget.refresh_levels(
                self.skill_tree_window.current_skill_map_job,
                self.skill_tree_window.current_levels
            )

            # ★ 重算點數
            self.skill_tree_window.recalc_region_used()
            self.skill_tree_window.update_points_label()

        QTimer.singleShot(0, do_restore)
        self.input_fields["JOB"].setEnabled(False)
        self.skill_btn.setEnabled(False)
        self.skill_tree_window.show()




    def receive_skill_tree_result(self, text):
        # ★ 將 SkillTree 回傳結果寫入 技能 note 欄位
        self.refine_inputs_ui["技能"]["note"].setPlainText(text)
        #self.refine_inputs_ui["技能"]["note_ui"].setPlainText(text)
        self.input_fields["JOB"].setEnabled(True)
        self.skill_btn.setEnabled(True)
        self.trigger_total_effect_update()



    def restore_skill_tree_levels(self):
        import re
        from skill_tree import skill_code_to_id

        note_widget = self.refine_inputs_ui["技能"]["note"]
        note = note_widget.toPlainText().strip()
        if not note:
            return

        matches = re.findall(r"EnableSkill\((\d+),\s*(\d+)\)", note)
        if not matches:
            return

        restored = {}

        # skill_code_to_id = { "SKIDNAME" : 1234 }
        for code, sid in skill_code_to_id.items():
            for sid2, lv in matches:
                if sid == int(sid2):
                    restored[code] = int(lv)

        if hasattr(self, "skill_tree_window"):
            self.skill_tree_window.current_levels = restored



    def update_window_title(self):
        filename = os.path.basename(self.current_file) if self.current_file else "未命名"
        self.setWindowTitle(f"RO物品查詢計算工具 {Version} - {filename} ")
    
    def replace_custom_calc_content(self):
        # 特殊 CheckBox 狀態
        special_state = "|".join(
            f"{key}:{checkbox.isChecked()}"
            for key, checkbox in self.special_checkboxes.items()
        )
                        #轉成全域變數
        def get_effect_multiplier(category, index):
            return getattr(self, f"{category}_{index}", 0)
        
        result = []
        stat_names = ["STR", "AGI", "VIT", "INT", "DEX", "LUK",
                      "POW", "STA", "WIS", "SPL", "CON", "CRT"]

        # === 從 UI 中取 BaseLv 與 JobLv ===
        try:
            base_lv = int(self.input_fields["BaseLv"].text())
        except:
            base_lv = 0

        try:
            job_lv = int(self.input_fields["JobLv"].text())
        except:
            job_lv = 0

        globals()["BaseLv"] = base_lv
        globals()["JobLv"] = job_lv

        # === 從 UI 輸入 + 職業 + 裝備效果取各項能力加成 ===
        job_id = self.input_fields["JOB"].currentData()
        job_bonus = job_dict.get(job_id, {}).get("TJobMaxPoint", [])
        globals()["job_idcore"] = job_dict[job_id]["id"]#取得職業ID代號
        raw_effects = getattr(self, "effect_dict_raw", {})
        base_raw_effects = getattr(self, "base_effect_dict_raw", {})

        for i, stat in enumerate(stat_names):
            try:
                base = int(self.input_fields[stat].text())
            except:
                base = 0
            job = job_bonus[i] if i < len(job_bonus) else 0
            equip = sum(val for val, _ in raw_effects.get((stat, ""), []))
            base_equip = sum(val for val, _ in base_raw_effects.get((stat, ""), []))
            total = base + job + equip

            # 🔧 自動產生變數：base_STR, job_STR, equip_STR, total_STR
            globals()[f"base_{stat}"] = base
            globals()[f"job_{stat}"] = job
            globals()[f"equip_{stat}"] = equip
            globals()[f"base_equip_{stat}"] = base_equip
            globals()[f"total_{stat}"] = total

            
            #print(f"base_equip_{stat} : {base_equip}")

        #current_text = self.custom_calc_box.toPlainText()
        skill_key = self.skill_box.currentData()
        skill_lv = int(self.skill_LV_input.text())
        
        # ✅ 裝備狀態（你可以根據實際來源換成 combo_effect_text.text() 之類的）
        equip_state = self.total_effect_text.toPlainText()
        # 目標設定選項
        size_key = self.size_box.currentData()
        element_key = self.element_box.currentData()
        race_key = self.race_box.currentData()
        class_key = self.class_box.currentData()
        element_lv_key = self.element_lv_input.text() or 1
        user_element_key = self.attack_element_box.currentData()

        #monsterDamage_key = self.monsterDamage_input.text() or "0"#指定魔物增傷UI
        # 整數輸入值（注意空字串要預設為 0）
        d_ef = self.def_input.text() or "0"
        defc = self.defc_input.text() or "0"
        res = self.res_input.text() or "0"
        mdef = self.mdef_input.text() or "0"
        mdefc = self.mdefc_input.text() or "0"
        mres = self.mres_input.text() or "0"
        skill_formula = self.skill_formula_input.text()
        # 組合新的 state_key
        state_key = f"{Use_skill_levels}|{skill_formula}|{skill_key}|{skill_lv}|{equip_state}|{special_state}|{size_key}|{element_key}|{race_key}|{class_key}|{d_ef}|{defc}|{res}|{mdef}|{mdefc}|{mres}|{element_lv_key}|{user_element_key}|{total_STR}|{total_AGI}|{total_VIT}|{total_INT}|{total_DEX}|{total_LUK}|{total_POW}|{total_STA}|{total_WIS}|{total_SPL}|{total_CON}|{total_CRT}"


        if getattr(self, "_last_calc_state", None) == state_key:
            print("【⛔ 裝備效果沒有更動，跳過運算。】")
            return  # ⛔ 跳過重複運算

        self._last_calc_state = state_key  # ✅ 更新狀態紀錄

        print("【🧠 執行 replace_custom_calc_content()】")
        # 原本你的公式解析邏輯

        #心神凝聚計算
        globals()["skill_focus_AGI"] = base_equip_AGI + base_AGI + job_AGI
        globals()["skill_focus_DEX"] = base_equip_DEX + base_DEX + job_DEX
        #======================取所有增傷資料到變數區=====================
        effect_dict = getattr(self, "effect_dict_raw", {})
        globals()["HP"] = sum(val for val, _ in effect_dict.get(("MHP", ""), []))
        globals()["HPPercent"] = sum(val for val, _ in effect_dict.get(("MHP%", "%"), []))
        globals()["SP"] = sum(val for val, _ in effect_dict.get(("MSP", ""), []))
        globals()["SPPercent"] = sum(val for val, _ in effect_dict.get(("MSP%", "%"), []))
        globals()["HPRegenPercent"] = sum(val for val, _ in effect_dict.get(("HP自然恢復%", "%"), []))
        globals()["SPRegenPercent"] = sum(val for val, _ in effect_dict.get(("SP自然恢復%", "%"), []))




        #print(f"hp:{HP} hp%:{HPPercent}sp:{SP} sp%:{SPPercent} h恢復{HPRegenPercent}s恢復 {SPRegenPercent}")
        #呼叫處理物理,魔法增傷,無視防禦 例:(對"小型"敵人的魔法傷害 +5%)
        self.apply_all_damage_effects(effect_dict)
        #主手武器類型(數字)
        weapon_class = global_weapon_type_map.get(4, 0)
        #副手武器類型(數字)
        Subweapon_class = global_weapon_type_map.get(3, 0)        
        #主手武器類型(代號)
        globals()["weapon_codes"] = weapon_class_codes.get(weapon_class, "?")
        #副手武器類型(數字)
        globals()["Subweapon_codes"] = 0 if Subweapon_class == 0 else 2
        #print(f"副手武器類型代號 {Subweapon_codes}")
        #裝備ATK(不含武器)
        globals()["ATK_armor"] = sum(val for val, _ in effect_dict.get(("ATK", ""), []))
        #修煉ATK
        WeaponMasteryATK = sum(val for val, _ in effect_dict.get(("修煉ATK", ""), []))
        #裝備MATK(不含武器)
        globals()["MATK_armor"] = sum(val for val, _ in effect_dict.get(("MATK", ""), []))
        #裝備ATK%
        globals()["ATK_percent"] = sum(val for val, _ in effect_dict.get(("ATK%", "%"), []))
        #裝備MATK%
        globals()["MATK_percent"] = sum(val for val, _ in effect_dict.get(("MATK%", "%"), []))
        #武器ATK
        #globals()["ATK_Mweapon"] = sum(val for val, _ in effect_dict.get(("武器ATK", ""), []))#捨棄ui資料，改成map資料
        globals()["ATK_Mweapon"] = global_weapon_atk_map.get(4, 0)#主手
        globals()["ATK_MweaponL"] = global_weapon_atk_map.get(3, 0)#副手
        #武器MATK
        #globals()["MATK_Mweapon"] = sum(val for val, _ in effect_dict.get(("武器MATK", ""), []))#捨棄ui資料，改成map資料
        globals()["MATK_Mweapon"] = global_weapon_matk_map.get(4, 0)#主手
        globals()["MATK_MweaponL"] = global_weapon_matk_map.get(3, 0)#副手
        #武器等級
        #globals()["weapon_Level"] = sum(val for val, _ in effect_dict.get(("武器等級", ""), []))#捨棄ui資料，改成map資料
        globals()["weaponR_Level"] = global_weapon_level_map.get(4, 0)#主手
        globals()["weaponL_Level"] = global_weapon_level_map.get(3, 0)#副手
        #print(f"武器等級R{weaponR_Level} L{weaponL_Level}")
        #箭矢彈藥ATK
        globals()["ammoATK"] = sum(val for val, _ in effect_dict.get(("箭矢/彈藥ATK", ""), []))
        #武器精煉R右L左
        globals()["weaponRefineR"] = int(self.refine_inputs_ui["右手(武器)"]["refine"].text())
        globals()["weaponRefineL"] = int(self.refine_inputs_ui["左手(盾牌)"]["refine"].text())
        #武器階級R右L左
        globals()["weaponGradeR"] = int(self.refine_inputs_ui["右手(武器)"]["grade"].currentIndex())
        globals()["weaponGradeL"] = int(self.refine_inputs_ui["左手(盾牌)"]["grade"].currentIndex())
        #print(f"{weaponRefineR} {weaponRefineL} {weaponGradeR} {weaponGradeL}")
        globals()["PATK"] = sum(val for val, _ in effect_dict.get(("P.ATK", ""), []))
        globals()["SMATK"] = sum(val for val, _ in effect_dict.get(("S.MATK", ""), []))
        #print(f"S.MATK{SMATK}")
        #公式用
        
        SKILL_ASC_KATAR = (enabled_skill_levels.get(376,0) * 2) + 10 if weapon_class == 16 else 0#高階拳刃修煉
        #print(f"高階拳刃修煉 {SKILL_ASC_KATAR}")


        # 從下拉選單與欄位取得目標資訊
        target_size    = self.size_box.currentData()
        target_element = self.element_box.currentData()
        target_race    = self.race_box.currentData()
        target_class   = self.class_box.currentData()
        User_attack_element = self.attack_element_box.currentData()

        #輸出ROCalculator全域變數區 globals()[""] = 
        globals()["RaceMatkPercent"] = get_effect_multiplier('MD_Race', target_race) + get_effect_multiplier('MD_Race', 9999)#魔法種族
        globals()["SizeMatkPercent"] = get_effect_multiplier('MD_size', target_size)#魔法體型
        globals()["LevelMatkPercent"] = get_effect_multiplier('MD_class', target_class)#魔法階級
        globals()["ElementalMatkPercent"] = get_effect_multiplier('MD_element', target_element) + get_effect_multiplier('MD_element', 10)#魔法屬性敵人
        globals()["ElementalMagicPercent"] = get_effect_multiplier('MD_Damage', User_attack_element) + get_effect_multiplier('MD_Damage', 10)#屬性魔法
        globals()["RaceAtkPercent"] = get_effect_multiplier('D_Race', target_race) + get_effect_multiplier('D_Race', 9999)#物理種族
        globals()["SizeAtkPercent"] = get_effect_multiplier('D_size', target_size)#物理體型
        globals()["LevelAtkPercent"] = get_effect_multiplier('D_class', target_class)#物理階級
        globals()["ElementalAtkPercent"] = get_effect_multiplier('D_element', target_element) + get_effect_multiplier('D_element', 10)#物理屬性敵人
        globals()["target_monsterDamage"] = sum(val for val, _ in effect_dict.get((f"特定魔物物理增傷", "%"), []))
        globals()["target_monsterMDamage"] = sum(val for val, _ in effect_dict.get((f"特定魔物魔法增傷", "%"), []))

        
        #========================以上魔法增傷===================
        

        try:
            target_element_lv = int(self.element_lv_input.text() or 1)#目標屬性等級
        except ValueError:
            target_element_lv = 1
        try:
            target_def = int(self.def_input.text() or 0)
        except ValueError:
            target_def = 0
        try:
            target_defc = int(self.defc_input.text() or 0)
        except ValueError:
            target_defc = 0
        try:
            target_res = int(self.res_input.text() or 0)
        except ValueError:
            target_res = 0
        try:
            target_mdef = int(self.mdef_input.text() or 0)
        except ValueError:
            target_mdef = 0
        try:
            target_mdefc = int(self.mdefc_input.text() or 0)
        except ValueError:
            target_mdefc = 0
        try:
            target_mres = int(self.mres_input.text() or 0)
        except ValueError:
            target_mres = 0

        #=======取得目前有的技能等級如果沒有回傳0        
        def GSklv(skill_id):
            return enabled_skill_levels.get(skill_id, 0)  # 若沒有這個技能，預設回傳 0
        def GUSklv(skill_id):
            v = Use_skill_levels.get(skill_id, 0)  # 沒有就 0
            if isinstance(v, bool):
                return int(v)  # True->1, False->0
            return v

        #處理公式中的動態變數
        def replace_gsklv_calls(formula: str) -> str:
            pattern = r'GSklv\((\d+)\)'  # 找出 GSklv(數字)
            return re.sub(pattern, lambda m: str(GSklv(int(m.group(1)))), formula)
        def replace_gusklv_calls(formula: str) -> str:
            pattern = r'GUSklv\((\d+)\)'  # 找出 GUSklv(數字)
            return re.sub(pattern, lambda m: str(GUSklv(int(m.group(1)))), formula)

        def replace_custom_calls(formula):#例如超自然波 書跟杖打擊
            import re
    
            # 如果不是字串，直接回傳，不處理
            if not isinstance(formula, str):
                return formula

            # 處理 WPon(x|y|...)a:b
            def replace_wpon_expr(match):
                global global_weapon_type_map
        
                types_str = match.group(1)
                if_true = match.group(2)
                if_false = match.group(3)

                target_types = set(int(x) for x in types_str.split("|"))
                weapon_class = global_weapon_type_map.get(4, 0)  # 主手武器類型

                return if_true if weapon_class in target_types else if_false

            return re.sub(
                r'WPon\(([\d|]+)\)([^:]+):([^:\)\s\+\-\*/]+)',
                replace_wpon_expr,
                formula
            )
        

        def eval_formula_with_vars(formula: str, allowed_vars: dict):
            """
            回傳：
            - expanded_formula：變數已展開的公式字串
            - result：計算結果（失敗為 None）
            """

            allowed_funcs = {
                "floor": math.floor,
                "ceil":  math.ceil,
                "trunc": math.trunc,
            }

            # 變數替換
            expanded_formula = formula
            for var, value in allowed_vars.items():
                expanded_formula = re.sub(
                    rf'\b{re.escape(var)}\b',
                    str(value),
                    expanded_formula
                )

            # 計算
            try:
                result = eval(
                    expanded_formula,
                    {"__builtins__": None},
                    allowed_funcs
                )
            except (SyntaxError, NameError, ZeroDivisionError, TypeError):
                return expanded_formula, None

            return expanded_formula, result


        #=================== 特殊增傷ui取得/處理區===================
        #萬紫/震裂4
        skill_wanzih4_buff = 100/100 if self.special_checkboxes["wanzih_checkbox"].isChecked() and 2 <= User_attack_element <= 3 else 0
        #毒耐性弱化
        skill_poison_weak_buff = 50/100 if self.special_checkboxes["poison_weak_checkbox"].isChecked() and User_attack_element == 5 else 0
        #魔力中毒
        magic_poison_buff = 50/100 if self.special_checkboxes["magic_poison_checkbox"].isChecked() else 0
        #屬性紋章
        attribute_seal_buff = 1+50/100 if self.special_checkboxes["attribute_seal_checkbox"].isChecked() and 1 <= User_attack_element <= 4 else 1
        #潛擊
        is_sneak_checked = self.special_checkboxes["sneak_attack_checkbox"].isChecked()
        sneak_attack_buff = 1+30/100 if is_sneak_checked and target_class == 0 else 1+15/100 if is_sneak_checked else 0
        sneak_MDattack_buff = 30/100 if is_sneak_checked and target_class == 0 else 15/100 if is_sneak_checked else 0
        #致命塗毒
        EDP_attack = 300 if int(GUSklv(378)) == 1 else 0 #378
        #爪痕
        is_DARKCROW_checked = self.special_checkboxes["DARKCROW_attack_checkbox"].isChecked()
        DARKCROW_attack_buff = 1+150/100 if is_DARKCROW_checked and target_class == 0 else 1+75/100 if is_DARKCROW_checked else 0
        #撼動
        RUSH_attack_buff = 1+50/100 if self.special_checkboxes["RUSH_attack_checkbox"].isChecked() else 0
        #孢子
        SPORE_attack_buff = 1+5/100 if self.special_checkboxes["SPORE_attack_checkbox"].isChecked() else 0
        #聖油
        OLEUM_attack_buff = 1+20/100 if self.special_checkboxes["OLEUM_attack_checkbox"].isChecked() else 0
        #魔力增幅
        SKILL_HW_MAGICPOWER = 10 if int(GUSklv(366)) == 1 else 0  # 366

        
        """
        target_size       # 來自 體型 的數值
        C    # 屬性編號
        target_element_lv # 目標屬性等級
        target_race       # 種族代碼C
        target_class      # 階級代碼
        target_mdef       # 數字輸入 MDEF前
        target_mdefc      # 數字輸入 MDEF後
        target_mres       # 數字輸入 MRES
        User_attack_element #施展屬性
        """
        #=============參考動態變數自動抓技能%=(裝備段)==============
        # 從 skill_box 取得目前選中的技能名稱（顯示文字）
        selected_skill_name = self.skill_box.currentText()
        globals()["Use_Skills"] = sum(val for val, _ in effect_dict.get((f"技能【{selected_skill_name}】傷害(裝備段)", "%"), []))
        #=============參考動態變數自動抓技能%=(技能段)==============      
        passive_skill_buff = sum(val for val, _ in effect_dict.get((f"技能【{selected_skill_name}】傷害(技能段)", "%"), []))
        #=====================其他物理增傷========================
        globals()["MeleeAttackDamage"] = sum(val for val, _ in effect_dict.get((f"近距離物理傷害", "%"), []))
        globals()["RangeAttackDamage"] = sum(val for val, _ in effect_dict.get((f"遠距離物理傷害", "%"), []))
        globals()["Damage_CRI"] = sum(val for val, _ in effect_dict.get((f"爆擊傷害", "%"), []))
        globals()["Damage_HIT"] = sum(val for val, _ in effect_dict.get((f"物理命中傷害", "%"), []))
        globals()["BowAtk"] = sum(val for val, _ in effect_dict.get((f"弓攻擊力", "%"), []))
        globals()["CRATE"] = sum(val for val, _ in effect_dict.get((f"C.RATE", ""), []))   
        Ignore_size = sum(val for val, _ in effect_dict.get((f"武器體型修正", "%"), []))   
        if any("武器浸透勁效果" in key for (key, unit) in effect_dict.keys()):
            print("有武器浸透勁效果")
            Use_skill_levels[266] = True
        #== 固定詠唱取得 ==
        fixed_cast = sum(val for val, _ in effect_dict.get(("固定詠唱時間", "秒"), []))
        #== 固定詠唱%取得 ==
        fixed_cast_percent = min((val for val, _ in effect_dict.get(("固定詠唱時間", "%"), [])),default=0)
        #== 變動詠唱取得 ==
        variable_cast_percent = sum(val for val, _ in effect_dict.get(("變動詠唱時間", "%"), []))
        #== 技能後延遲取得 ==
        skill_delay_percent = sum(val for val, _ in effect_dict.get(("技能後延遲", "%"), []))
        #== 技能冷卻取得 ==        
        skill_cooldown = sum(val for val, _ in effect_dict.get((f"技能【{selected_skill_name}】冷卻時間", "秒"), []))
        #== 指定技能變詠冷卻取得 ==
        selected_skill_cooldown_percent = sum(val for val, _ in effect_dict.get((f"技能【{selected_skill_name}】變動詠唱時間", "秒"), []))

        #ASPD計算
        atkaspd = -sum(val for val, _ in effect_dict.get(("(2轉以下)攻擊後延遲", "%"), []))
        #print(f"(2轉以下)攻擊後延遲減少：{atkaspd}%")
        aspdno = sum(val for val, _ in effect_dict.get(("(2轉以下)ASPD", ""), []))
        #print(f"(2轉以下)最終ASPD：{aspdno}")   
        atkaspd_2 = -sum(val for val, _ in effect_dict.get(("攻擊後延遲", "%"), []))        
        #print(f"攻擊後延遲減少：{atkaspd_2}%")
        aspdno_2 = sum(val for val, _ in effect_dict.get(("ASPD", ""), []))
        #print(f"最終ASPD：{aspdno_2}")        
        has_shield = True if global_armor_weapon_map.get(3, 0) == "armor" else False
        #print(f"副手拿盾：{has_shield}")
       
        if global_armor_weapon_map.get(3, 0) in ("Mweapon","Rweapon"):
            # 雙刀（右手/左手）
            #print("雙手模式")
            aspd = self.calc_aspd(
                WPASPDdata, job_id=job_id, agi=total_AGI, dex=total_DEX,
                dual_wield=True,
                right_weapon_type=global_weapon_type_map.get(4, 0),
                left_weapon_type=global_weapon_type_map.get(3, 0),
                cat1_rate=atkaspd, cat1_flat=aspdno,
                cat2_rate=atkaspd_2, cat2_flat=aspdno_2
            )
        else:
            #print("單手模式")
            # 一般（可持盾）
            aspd = self.calc_aspd(
                WPASPDdata, job_id=job_id, agi=total_AGI, dex=total_DEX,
                weapon_type=global_weapon_type_map.get(4, 0), has_shield=has_shield,
                cat1_rate=atkaspd, cat1_flat=aspdno,    # 15% + 2 點（也可用 0.15）
                cat2_rate=atkaspd_2, cat2_flat=aspdno_2
            )        

        
        gcdtotal_raw_s = update_skill_delay_labels(#更新固定變動冷卻後延數值
                skill_name=selected_skill_name,
                skill_map_all=skill_map_all,
                lua_text=self.lua_text,
                fix_label=self.fix_label,
                delay_label=self.Delay_label,
                cast_bar=self.cast_bar,
                skill_level=skill_lv,
                Equipfixed=fixed_cast*1000,
                Equipfixed_2=fixed_cast_percent,#固詠%
                basestat=(total_DEX+(total_INT/2)),
                Equipstat=variable_cast_percent,
                Equipgpost=skill_delay_percent,
                Equipspost=skill_cooldown*1000,
                selected_Equipspost=selected_skill_cooldown_percent*1000
            )
        

        if isinstance(aspd, (int, float)):            
            aspds = 50/(200-min(193,int(aspd)))
            if gcdtotal_raw_s <= 0:
                ASPD_GCD = 0
            else:
                ASPD_GCD = max(0,math.ceil((1 - ((1 / (50 / (200 - min(193,int(aspd))))) / gcdtotal_raw_s)) / 0.01))
            self.ASPD_label.setText(f"ASPD：{aspd} 每秒{aspds:.2f}下 (共延需求{ASPD_GCD}%)")
        else:
            self.ASPD_label.setText(f"ASPD：該職業不能拿此武器。")

        #=======================技能欄公式====================
        #====================DEF計算==================
        def calc_final_def_damage(d_ef: float, reduction_percent: float) -> float:
            """
            根據 Excel 公式計算最終物理傷害比例
            def: 後 DEF 數值
            reduction_percent: DEF 破防百分比（例如 64 表示 64%）
            回傳: 傷害倍率（小數，例如 0.4222）
            """
            
            reduction = reduction_percent / 100
            if reduction > 0.99:
                return 1.0
            adj = d_ef - (d_ef * reduction) - reduction
            numerator = 4000 + adj
            denominator = 4000 + adj * 10
            resistance = numerator / denominator
            return min(resistance, 1.0)  # ⬅️ 保證不超過 1.0
        #====================MRES,MDEF計算===================
        #====================MDEF計算==================
        def calc_final_mdef_damage(mdef: float, reduction_percent: float) -> float:
            """
            根據 Excel 公式計算最終魔法傷害比例
            mdef: 後 MDEF 數值
            reduction_percent: MDEF 破防百分比（例如 64 表示 64%）
            回傳: 傷害倍率（小數，例如 0.4222）
            """
            
            reduction = reduction_percent / 100
            if reduction > 0.99:
                return 1.0
            adj = mdef - (mdef * reduction) - reduction
            numerator = 1000 + adj
            denominator = 1000 + adj * 10
            resistance = numerator / denominator
            return min(resistance, 1.0)  # ⬅️ 保證不超過 1.0
        #====================RES/MRES計算==================
        def calc_final_res_damage(mres: float, reduction_percent: float) -> float:

            reduction = reduction_percent / 100
            if reduction > 0.99:
                return 1.0
            adj = mres - (mres * reduction) - reduction
            numerator = 2000 + adj
            denominator = 2000 + adj * 5
            resistance = numerator / denominator
            return min(resistance, 1.0)  # ⬅️ 保證不超過 1.0
            

        #物理破防
        def_reduction = ((get_effect_multiplier('D_Race_def', target_race))+(get_effect_multiplier('D_Race_def', 9999))+(get_effect_multiplier('D_class_def', target_class)))
        damage_nodef = calc_final_def_damage(target_def, def_reduction)             

        #魔法破防
        mdef_reduction = ((get_effect_multiplier('MD_Race_def', target_race))+(get_effect_multiplier('MD_Race_def', 9999))+(get_effect_multiplier('MD_class_def', target_class)))
        Mdamage_nomdef = calc_final_mdef_damage(target_mdef, mdef_reduction)       

        #res        
        res_reduction = ((get_effect_multiplier('D_Race_res', target_race))+(get_effect_multiplier('D_Race_res', 9999)))
        res_reduction = min(res_reduction, 50)#破抗性最大50%
        damage_nores = calc_final_res_damage(target_res, res_reduction)
        
        #MRES
        mres_reduction = ((get_effect_multiplier('MD_Race_res', target_race))+(get_effect_multiplier('MD_Race_res', 9999)))
        mres_reduction = min(mres_reduction, 50)#破抗性最大50%
        Mdamage_nomres = calc_final_res_damage(target_mres, mres_reduction)

        
        # 查詢屬性倍率函數
        def get_damage_multiplier(attacker_element: int, defender_element: int, level: int) -> int:
            if level not in damage_tables:
                raise ValueError("不支援的屬性等級（僅支援 Lv1~Lv4）")
            if attacker_element not in element_map or defender_element not in element_map:
                raise ValueError("屬性 ID 必須在 0~9 範圍內")

            return damage_tables[level][attacker_element][defender_element]

        
        # 武器體型懲罰(物理)
        def get_size_penalty(weapon_class: int, target_size: int) -> float:
            """根據武器類型與目標體型回傳懲罰倍率（小數，例如 1.0, 0.75）"""
            penalties = weapon_type_size_penalty.get(weapon_class, [100, 100, 100])
            if 0 <= target_size < len(penalties):
                return penalties[target_size] / 100.0
            return 1.0  # 預設值 100% → 1.0



        #==========================精煉計算=========================
        #武器ATK精煉計算
        patk_refine_total = 0
        atk_refine_total, patk_refine_total = self.calc_weapon_refine_atk(weaponR_Level, weaponRefineR, weaponGradeR)
        atk_refine_total_L, patk_refine_total_L = self.calc_weapon_refine_atk(weaponL_Level, weaponRefineL, weaponGradeL)#atk_refine_total_L 副手不計算ATK 只計算PATK
        #PATK(裝備+精煉+特性素質)
        globals()["total_PATK"] = PATK + int(total_POW/3) + int(total_CON/5) + patk_refine_total + patk_refine_total_L
        #武器MATK精煉計算
        smatk_refine_total = 0
        matk_refine_total, smatk_refine_total = self.calc_weapon_refine_matk(weaponR_Level, weaponRefineR, weaponGradeR)
        matk_refine_total_L, smatk_refine_total_L = self.calc_weapon_refine_matk(weaponL_Level, weaponRefineL, weaponGradeL)
        #print(f"精煉加成 MATK: {matk_refine_total}")
        #print(f"精煉加成 S.MATK: {smatk_refine_total}")
        #============================魔法各增傷計算區============================
        #SMATK(裝備+精煉+特性素質)
        total_SMATK = SMATK + int(total_SPL/3) + int(total_CON/5) + smatk_refine_total + smatk_refine_total_L
        
        
        def apply_stepwise_percent_mode(base, *bonuses_with_mode):
            """
            擴充版，每層乘完取整，依據 mode 控制加/減/忽略：
            - mode = 1      → 加成百分比：乘 (1 + bonus / 100)
            - mode = 1.4    → 特殊加成百分比：乘 (1.4 + bonus / 100)
            - mode = 0      → 原始倍率：乘 (bonus / 100)
            - mode = -1     → 減傷百分比：乘 (1 - bonus / 100)
            - mode = None   → 固定扣值：value -= bonus
            - mode = "raw"  → 直接乘：value *= bonus（不除以 100）
            - mode = "+"    → 直接加：value += bonus
            """
            value = base
            for bonus, mode in bonuses_with_mode:
                if mode is None:
                    value -= bonus
                elif mode == "raw":
                    value *= bonus
                elif mode == "+":
                    value += bonus
                else:
                    if mode == 1:
                        multiplier = 1 + bonus / 100
                    elif mode == 1.4:
                        multiplier = 1.4 + bonus / 100
                    elif mode == -1:
                        multiplier = 1 - bonus / 100
                    elif mode == 0:
                        multiplier = bonus / 100
                          
                    else:  # mode == 0
                        multiplier = bonus / 100
                    value = int(value * multiplier)
               # print(f"計算: {value}")
            return value

            

                
        def visual_length(s: str) -> int:
            """計算視覺寬度：全形字算2，半形算1"""
            width = 0
            for c in s:
                width += 2 if ord(c) > 255 else 1
            return width

        def pad_label(label: str, total_width: int = 20) -> str:
            """依據視覺寬度補空格，讓冒號後對齊"""
            space_count = total_width - visual_length(label)
            return label + " " * max(space_count, 0)
        

        #物理===================     
        #浸透勁效果

        def_reduction_temp = int(100-def_reduction) #總階級種族破防-浸透勁破防100% 
        WPINVESTIGATEATK = max(0,int((target_def/2) + (target_def/2)*(def_reduction_temp/100))) if GUSklv(266) == 1 else 0 
        target_defc = 0 if GUSklv(266) == 1 else target_defc
        #print(f"浸透勁效果後atk+{WPINVESTIGATEATK}")
        #近傷ATK
        #NATK = int(BaseLv/4) + int(total_STR) + int(total_DEX/5) + int(total_LUK/3) + int(total_POW*5)
        NATK = int((BaseLv/4) + (total_STR) + (total_DEX/5) + (total_LUK/3) + (total_POW*5))
        #遠傷ATK(弓槍樂器鞭子)
        #FATK = int(BaseLv/4) + int(total_STR/5) + int(total_DEX) + int(total_LUK/3) + int(total_POW*5)
        FATK = int((BaseLv/4) + (total_STR/5) + (total_DEX) + (total_LUK/3) + (total_POW*5))
        #後ATK (只給面板顯示不參與計算)
        AKTC = ATK_Mweapon + ATK_armor + atk_refine_total + WPINVESTIGATEATK
        #C.RATE
        total_CRATE = CRATE + int(total_CRT/3)
        if weapon_class in (11,13,14,17,18,19,20,21):#DEX系
            #武器基礎ATK(dex)
            BasicsWeaponATK = ATK_Mweapon * (1+ (total_DEX/200) + (weaponR_Level*0.05))
            
        else:#STR系
            #武器基礎ATK(STR)
            BasicsWeaponATK = ATK_Mweapon * (1+ (total_STR/200) + (weaponR_Level*0.05))
        
        #print(f"BasicsWeaponATK:{BasicsWeaponATK}")
        #精煉武器ATK
        refineWeaponATK = int(BasicsWeaponATK + atk_refine_total)       
        #print(f"refineWeaponATK:{refineWeaponATK}")

        #武器體型修正
        Weaponpunish = 1 if Ignore_size >= 100 else get_size_penalty(weapon_class, target_size)
        #取得武器小中大體型懲罰
        globals()["weapon_weapon_size0"] = get_size_penalty(weapon_class, 0)*100
        globals()["weapon_weapon_size1"] = get_size_penalty(weapon_class, 1)*100
        globals()["weapon_weapon_size2"] = get_size_penalty(weapon_class, 2)*100

        #print(f"Ignore_size:{Ignore_size}") 
        #print(f"武器體型修正:{Weaponpunish}")   
        #(精煉武器ATK*體型懲罰)+箭矢彈藥ATK
        refineammoATK = int(refineWeaponATK * Weaponpunish) + ammoATK
        
        #怒爆或致命塗毒 1+(怒爆20%/致命塗毒25%)*屬性倍率 
        #致命塗毒
        EDP = 1 + 0.25 * (get_damage_multiplier(5, target_element, target_element_lv)/100) if int(GUSklv(378)) == 1 else 1
        #怒爆
        MAGNUM = 1 + 0.2 * (get_damage_multiplier(3, target_element, target_element_lv)/100) if int(GUSklv(7)) == 1 else 1
        #print(f"EDP:{EDP},MAGNUM:{MAGNUM}")
        specialATK = int(refineammoATK * EDP * MAGNUM)

        #前素質總ATK
        if weapon_class in (11,13,14,17,18,19,20,21):#DEX系
            #ATKF = int((FATK*2) * (get_damage_multiplier(User_attack_element, target_element, target_element_lv)/100))
            ATKF = int((FATK*2) * (get_damage_multiplier(0, target_element, target_element_lv)/100)) #前段強制無屬 除非溫暖風轉屬
        else:#STR系
            ATKF = int((NATK*2) * (get_damage_multiplier(0, target_element, target_element_lv)/100)) #前段強制無屬 除非溫暖風轉屬
        
        #後武器總ATK
        ATKC_Mweapon_ALL = (specialATK + ATK_armor + WPINVESTIGATEATK) 
        #print(f"ATKC_Mweapon_ALL:{ATKC_Mweapon_ALL}")

        
        #魔法===================
        #前MATK
        MATKF = int(BaseLv/4) + int(total_INT*1.5) + int(total_DEX/5) + int(total_LUK/3) + int(total_SPL*5)
        #後MATK
        MATKC = MATK_armor + MATK_Mweapon + MATK_MweaponL + matk_refine_total + matk_refine_total_L
        #武器MATK
        MATK_Mweapon_ALL = MATKF + ((matk_refine_total + matk_refine_total_L + MATK_Mweapon + MATK_MweaponL) * (1+(weaponR_Level*0.1)))
        #print(f"武器MATK:{MATK_Mweapon_ALL}")
        #裝備MATK+魔力增幅+武器MATK
        armorMATK_MAGICPOWER = int(MATK_Mweapon_ALL * (1+(SKILL_HW_MAGICPOWER*0.05)) + MATK_armor)
        #print(f"裝備MATK+魔力增幅:{armorMATK_MAGICPOWER}")
        
        
        #======================取得技能欄公式======================    
        # === 取得技能等級輸入並設為全域
        text = self.skill_LV_input.text()
        globals()["Sklv"] = int(text) if text.lstrip('-').isdigit() else 0
        
        # === 取得使用者從 UI 下拉選單選擇的技能名稱
        #selected_skill_name = self.skill_box.currentText()#上面已經做過了
        #武器次數依照武器類型判斷
        skill_hits = self.skill_hits_input.text()#攻擊次數
        
        skill_hits = (replace_gusklv_calls(skill_hits))#替換使用技能參數
        expr = (replace_custom_calls(skill_hits))#替換武器類型

        def eval_hits(expr: str) -> int:
            expr = expr.strip()

            # 只允許數字、四則、括號、小數點、空白、%（需要就留，不需要可拿掉）
            if not re.fullmatch(r"[0-9+\-*/().\s%]*", expr):
                raise ValueError(f"公式含不允許字元：{expr}")

            val = eval(expr, {"__builtins__": None}, {})  # 關掉 builtins
            return int(val)  # 需要整數就轉 int（會截掉小數）

       
        skill_hits = eval_hits(expr)#計算最終次數

        #print(f"技能攻擊次數: {skill_hits}")
        # === [1] 取得技能 row
        skill_row = skill_df[skill_df["Name"] == selected_skill_name]
        if skill_row.empty:
            # 給一個「空內容但欄位齊全」的 Series
            skill_row = pd.Series({col: None for col in skill_df.columns})
        else:
            skill_row = skill_row.iloc[0]

        # [2] 根據種族選擇正確的公式，並同步 UI
        default_formula = str(skill_row["Calculation"]).strip()
        final_formula = default_formula
        globals()["SkillCode"] = str(skill_row["Code"]).strip()

        special_formula_ok = pd.notna(skill_row.get("Special_Calculation"))
        trigger_special = False

        # 先：種族判斷
        if special_formula_ok and pd.notna(skill_row.get("monster_race")):
            allowed_races = {r.strip() for r in str(skill_row["monster_race"]).split(",") if r.strip()}
            if str(target_race).strip() in allowed_races:
                trigger_special = True

        # 再：skill_buff 判斷（Use_skill_levels 裡有用到 buff 技能就觸發）
        if (not trigger_special) and special_formula_ok and pd.notna(skill_row.get("skill_buff")):
            buff_ids = []
            for x in str(skill_row["skill_buff"]).split(","):
                x = x.strip()
                if x.isdigit():
                    buff_ids.append(int(x))

            # ✅ 只要其中一個 buff 技能被使用過 (True) 就觸發
            if any(Use_skill_levels.get(bid, False) for bid in buff_ids):
                trigger_special = True

        # 套用特殊公式
        if trigger_special and special_formula_ok:
            final_formula = str(skill_row["Special_Calculation"]).strip()


        # 同步更新 UI
        self.skill_formula_input.setText(final_formula)

        # [3] 最終使用使用者輸入
        user_input_formula = self.skill_formula_input.text().strip()
        if user_input_formula and user_input_formula != final_formula:
            formula_str = user_input_formula
        else:
            formula_str = final_formula

        def parse_hits(value, sklv):
            """
            解析 hits 或 combo_hits 欄位，支援負數與公式。
            範例： (Sklv/3)+4 會以整數除法處理為 (Sklv // 3) + 4
            """
            try:
                # 若為 int 或 float，直接轉
                if isinstance(value, (int, float)):
                    return int(value)

                # 去除空白後判斷是否為整數字串（包含負數）
                stripped = str(value).strip()
                if stripped.lstrip("-").isdigit():
                    return int(stripped)

                # 將 '/' 換成 '//' 確保整數除法
                safe_expr = stripped.replace("/", "//")

                # 建立 Symbol 並解析表達式
                Sklv = Symbol("Sklv")
                expr = sympify(safe_expr)
                result = expr.evalf(subs={Sklv: sklv}, chop=True)  # chop=True 可去除浮點誤差

                return int(result)
            except Exception as e:
                print(f"[⚠️ hits 解析錯誤] 原始值: {value}, 錯誤: {e}")
                return 1  # 預設安全值


        # === [4] 主段傷害計算（含多段與 bonus 加值設定）
        repeat_count = self.skill_hits_input.text()
        #武器次數依照武器類型判斷
        #repeat_count = int(replace_custom_calls(repeat_count))
        #print(f"repeat_count技能攻擊次數: {repeat_count}")
        bonus_add_raw = skill_row.get("bonus_add", "")
        if pd.isna(bonus_add_raw) or str(bonus_add_raw).strip() == "":
            bonus_add = 0
        else:
            bonus_add = str(bonus_add_raw).strip()

        bonus_step = float(skill_row["bonus_step"]) if pd.notna(skill_row.get("bonus_step")) else 0
        decay_hits = int(skill_row["decay_hits"]) if pd.notna(skill_row.get("decay_hits")) else 0 
        combo_element = int(skill_row["combo_elementg"]) if pd.notna(skill_row.get("combo_elementg")) else 0
        attack_type = str(skill_row.get("attack_type", "")).lower() if pd.notna(skill_row.get("attack_type")) else "physical"
        #技能遠傷判斷
        skill_Rangedamage = int(skill_row["Rangedamage"]) if pd.notna(skill_row.get("Rangedamage")) else 0 
        #print(f"技能遠傷判斷: {skill_Rangedamage}")

        wpclass_skill_Rangedamage = skill_row.get("special_wprange", 0)

        # None / 空字串 / "nan" → 0
        if wpclass_skill_Rangedamage is None:
            wpclass_skill_Rangedamage = 0
        elif isinstance(wpclass_skill_Rangedamage, str):
            s = wpclass_skill_Rangedamage.strip()
            if s == "" or s.lower() == "nan":
                wpclass_skill_Rangedamage = 0
        else:
            # 數字型（含 numpy.float64）遇到 NaN → 0
            try:
                if math.isnan(float(wpclass_skill_Rangedamage)):
                    wpclass_skill_Rangedamage = 0
            except (TypeError, ValueError):
                pass

        #print(f"武器類型遠傷判斷代號: {wpclass_skill_Rangedamage}")

        allow = set()

        # 1) 單一數字：int / float（此時 NaN 已經被清成 0）
        if isinstance(wpclass_skill_Rangedamage, (int, float)):
            n = int(float(wpclass_skill_Rangedamage))
            if n != 0:
                allow.add(n)
        else:
            # 2) 多個數字字串： "1,5,6" / "8.0"
            for part in str(wpclass_skill_Rangedamage).split(","):
                part = part.strip()
                if not part:
                    continue
                try:
                    f = float(part)
                except ValueError:
                    continue
                if math.isnan(f):
                    continue
                if f.is_integer():
                    n = int(f)
                    if n != 0:
                        allow.add(n)


        # 最終判斷
        if weapon_class != 0 and weapon_class in allow:
            skill_Rangedamage = 1



        #技能爆傷判斷
        Critical_hit = float(skill_row["Critical_hit"]) if pd.notna(skill_row.get("Critical_hit")) else 0
        
        #print(f"攻擊模式：{attack_type}")
        

        
        bottom_result = []
        def compute_and_record_damage(formula, repeat_count=1, bonus_add=0, bonus_step=0, label="main", skill_hits=1, user_attack_element=0):
            
            results = []
            allowed_vars = {k: v for k, v in globals().items() if isinstance(v, (int, float))}
            symbols_dict = {k: Symbol(k) for k in allowed_vars}

            for i in range(repeat_count):
                add_expr = (str(bonus_add).strip() if bonus_add not in [None, "nan"] else "")
                step_expr = (str(bonus_step).strip() if bonus_step not in [None, "nan"] else "")

                # 嘗試解析 step
                try:
                    step_val = float(step_expr) if step_expr else 0.0
                except ValueError:
                    step_val = 0.0

                # === 如果沒有 decay 或沒有加成輸入，保持原公式 ===
                if repeat_count <= 1 and not add_expr and not step_expr:
                    full_formula = formula
                else:
                    if add_expr.startswith('*'):
                        # === 乘法模式 ===
                        try:
                            base_mult = float(add_expr[1:] or 1)
                        except ValueError:
                            base_mult = 1.0
                        current_mult = base_mult + step_val * i
                        full_formula = f"({formula}) * {current_mult}"

                    elif add_expr or step_expr:
                        # === 加減模式 ===
                        try:
                            base_add = float(add_expr or 0)
                        except ValueError:
                            base_add = 0.0
                        current_add = base_add + step_val * i
                        if current_add == 0:
                            full_formula = f"{formula}"  # 不顯示 +0
                        else:
                            sign = '+' if current_add > 0 else ''
                            full_formula = f"({formula}) {sign} {current_add}"
                    else:
                        # 完全沒輸入加成
                        full_formula = formula

                # === 套用替換函式 ===
                full_formula = replace_gsklv_calls(full_formula)#替換gsklv
                full_formula = replace_gusklv_calls(full_formula)#替換gusklv
                full_formula = replace_custom_calls(full_formula)#替換wpon(0)2:1
                full_formula_show,full_formula = eval_formula_with_vars(full_formula, allowed_vars)# 手動變數替換後的字串公式 支援捨去計算               
                skill_SpecialATK_show , skill_SpecialATK = eval_formula_with_vars(str(skill_row["skill_SpecialATK"]).strip() if pd.notna(skill_row.get("skill_SpecialATK")) else "0", allowed_vars) #技能隱藏段
                

                #print(f"轉換後的公式：{full_formula_show}")
                bottom_result.append(f"{pad_label('技能公式:')}[{i+1}/{repeat_count}] {full_formula_show}")
                #怪物減傷取得
                def get_damage_reduction_value(self):
                    text = self.damage_reduction_combobox.currentText()  # 例如 "100%"
                    percent = float(text.replace('%', ''))
                    value = percent / 100
                    return value
                


                try:
                    expr = sympify(full_formula, locals=symbols_dict)
                    used_symbols = {str(s) for s in expr.free_symbols}
                    missing_symbols = used_symbols - set(allowed_vars.keys())
                    if missing_symbols:
                        raise ValueError(f"公式中錯誤的符號： {missing_symbols}")

                    calc_result = expr.evalf(subs=allowed_vars)
                    #skill_result = round(calc_result, 2)
                    skill_result = int(calc_result)
                    #skill_result = calc_result

                    print(f"[{i+1}/{repeat_count}] 技能公式結果: {skill_result}")
                    
                    if attack_type == "magic":
                        final_damage = apply_stepwise_percent_mode(
                            #初始值
                            armorMATK_MAGICPOWER,
                            #MATK%
                            (MATK_percent,1),
                            #體型
                            (get_effect_multiplier('MD_size', target_size),1),
                            #屬性敵人
                            (get_effect_multiplier('MD_element', target_element) + get_effect_multiplier('MD_element', 10),1),
                            #敵人屬性耐性(1+萬紫+毒弱+彗星)
                            ((1 + skill_wanzih4_buff + skill_poison_weak_buff + magic_poison_buff),"raw"),
                            #屬性魔法
                            (get_effect_multiplier('MD_Damage', User_attack_element) + get_effect_multiplier('MD_Damage', 10),1),
                            #種族
                            (get_effect_multiplier('MD_Race', target_race) + get_effect_multiplier('MD_Race', 9999),1),
                            #階級
                            (get_effect_multiplier('MD_class', target_class),1),
                            #特定魔物增傷
                            (target_monsterMDamage,1),
                            #smatk 
                            (total_SMATK,1),
                            #技能倍率
                            (skill_result,0),
                            #屬性倍率
                            (get_damage_multiplier(User_attack_element, target_element, target_element_lv),0),
                            #敵人MRES減傷
                            (Mdamage_nomres,"raw"),
                            #敵人MDEF減傷
                            (Mdamage_nomdef,"raw"),
                            #敵人MDEF減算
                            (target_mdefc,None),
                            #裝備段技能增傷
                            (Use_Skills,1),
                            #技能段技能增傷
                            (passive_skill_buff,1),
                            #念力?
                            #潛擊 自動判斷階級
                            (sneak_MDattack_buff,1),
                            #屬性紋章 風水火地
                            (attribute_seal_buff,"raw")
                        )
                        
                    elif attack_type == "physical":
                        #先計算ATK%已利後續計算
                        ATK_percent_sign = int(ATKC_Mweapon_ALL * (ATK_percent/100))
                        final_damage_1 = apply_stepwise_percent_mode(
                            #初始值 後武器ATK
                            ATKC_Mweapon_ALL,
                            #種族
                            (get_effect_multiplier('D_Race', target_race) + get_effect_multiplier('D_Race', 9999),1),
                            #體型
                            (get_effect_multiplier('D_size', target_size),1),
                            #致命塗毒
                            (EDP_attack,1),
                            #屬性敵人
                            (get_effect_multiplier('D_element', target_element) + get_effect_multiplier('D_element', 10),1),
                            #階級
                            (get_effect_multiplier('D_class', target_class),1),
                            #特定魔物增傷
                            (target_monsterDamage,1),
                            #後總ATK
                            (ATK_percent_sign,"+"),
                            #敵人屬性耐性(1+萬紫+毒弱+彗星)
                            ((1 + skill_wanzih4_buff + skill_poison_weak_buff + magic_poison_buff),"raw"),
                        )
                        
                        #print(f"屬性倍率計算前: {final_damage_1}")
                        #屬性倍率
                        final_damage_1 = math.ceil(final_damage_1 * get_damage_multiplier(User_attack_element, target_element, target_element_lv) / 100)
                        #print(f"屬性倍率計算後: {final_damage_1}")
                        #最終ATK
                        final_damage_1 += ATKF
                        #print(f"最終ATK: {final_damage_1}")
                        #爆傷+技能半全爆擊判斷
                        CRI_Critical_hit = (Damage_CRI * Critical_hit)
                        #(潛擊)+(爪痕)+(撼動)
                        special_melee_BUFF = max(1, sneak_attack_buff + DARKCROW_attack_buff + RUSH_attack_buff)
                        #(潛擊)+(孢子)+(撼動)+(聖油)
                        special_away_BUFF = max(1, sneak_attack_buff + SPORE_attack_buff + RUSH_attack_buff + OLEUM_attack_buff)

                        #技能遠傷進傷
                        if skill_Rangedamage == 1:
                            MR_AttackDamage = RangeAttackDamage + BowAtk if weapon_class == 11 else RangeAttackDamage
                            specialatkbuff = special_away_BUFF
                        else:
                            MR_AttackDamage = MeleeAttackDamage
                            specialatkbuff = special_melee_BUFF

                        #是否技能爆擊/命中增傷
                        if Critical_hit < 0:#負值兩者不吃
                            Critical_hitmag = -40#不吃crate
                            CRI_Critical_hit = 0
                            excel_Damage_HIT = 0
                        elif Critical_hit == 0:#0值吃命中增傷
                            Critical_hitmag = -40
                            CRI_Critical_hit = 0
                            excel_Damage_HIT = Damage_HIT
                        elif Critical_hit > 0:#正值吃爆傷
                            Critical_hitmag = total_CRATE
                            excel_Damage_HIT = 0#技能爆擊不吃命中增傷
                        else:#非數字
                            Critical_hitmag = -40#不吃crate
                            excel_Damage_HIT = 0
                            CRI_Critical_hit = 0
                        #print(f"special_away_BUFF:{special_away_BUFF}")
                        #print(f"special_melee_BUFF:{special_melee_BUFF}")
                        if weapon_class in (11,13,14,17,18,19,20,21):#DEX系
                            final_damage = apply_stepwise_percent_mode(
                                #最終ATK初始值
                                final_damage_1,
                                #P.ATK
                                (total_PATK,1),
                                #物理命中傷害
                                (excel_Damage_HIT,1),
                                #爆傷
                                (CRI_Critical_hit,1),
                                #遠傷% 技能判斷
                                (MR_AttackDamage,1),
                                #技能倍率
                                (skill_result,0),
                                #敵人RES減傷
                                (damage_nores,"raw"),
                                #敵人DEF減傷
                                (damage_nodef,"raw"),
                                #敵人DEF減算
                                (target_defc,None),
                                #裝備段技能增傷
                                (Use_Skills,1),
                                #技能段技能增傷
                                (passive_skill_buff,1),
                                #C.RATE
                                (Critical_hitmag,1.4),
                                #(潛擊)+(孢子)+(爪痕)+(撼動) 遠傷判斷類型
                                (specialatkbuff,"raw"),
                                #屬性紋章 風水火地
                                (attribute_seal_buff,"raw")
                            )
                            #print(f"技能爆擊最終傷害: {final_damage}")
                        else:#STR系
                            final_damage = apply_stepwise_percent_mode(
                                #最終ATK初始值
                                final_damage_1,
                                #P.ATK
                                (total_PATK,1),
                                #武器修煉ATK
                                (WeaponMasteryATK,"+"),
                                #物理命中傷害
                                (excel_Damage_HIT,1),
                                #爆傷
                                (CRI_Critical_hit,1),
                                #近傷% 技能判斷
                                (MR_AttackDamage,1),
                                #技能倍率
                                (skill_result,0),
                                #高階拳刃修煉
                                (SKILL_ASC_KATAR,1),
                                #敵人RES減傷
                                (damage_nores,"raw"),
                                #敵人DEF減傷
                                (damage_nodef,"raw"),
                                #敵人DEF減算
                                (target_defc,None),
                                #裝備段技能增傷
                                (Use_Skills,1),
                                #技能段技能增傷
                                (passive_skill_buff,1),
                                #C.RATE
                                (Critical_hitmag,1.4),
                                #(潛擊)+(爪痕)+(撼動) 遠傷判斷類型
                                (specialatkbuff,"raw"),
                                #屬性紋章 風水火地
                                (attribute_seal_buff,"raw")
                            )
                            #print(f"技能爆擊最終傷害: {final_damage}")
                    
                    elif attack_type == "d_b":
                        #技能遠傷進傷
                        if skill_Rangedamage == 1:
                            MR_AttackDamage = RangeAttackDamage + BowAtk if weapon_class == 11 else RangeAttackDamage
                        else:
                            MR_AttackDamage = MeleeAttackDamage


                        default = 0#龍火只吃技能倍率 給他個0做基礎
                        final_damage = apply_stepwise_percent_mode(
                            default,
                            #技能倍率
                            (skill_result,"+"),
                            #敵人屬性耐性(1+萬紫+彗星)
                            ((1 + magic_poison_buff),"raw"),
                            #敵人RES減傷
                            (damage_nores,"raw"),
                            #敵人DEF減傷
                            (damage_nodef,"raw"),
                            #敵人DEF減算
                            (target_defc,None),
                            #裝備段技能增傷
                            (Use_Skills,1),
                            #技能段技能增傷
                            (passive_skill_buff,1),
                            #遠傷% 技能判斷
                            (MR_AttackDamage,1),
                            #屬性倍率
                            (get_damage_multiplier(User_attack_element, target_element, target_element_lv),0)
                        )
                        
                        

                    else:
                        raise ValueError(f"未知的攻擊類型: {attack_type}")
                    #最終隱藏段加算
                    final_damage += skill_SpecialATK
                    #最終怪物強制減傷(boss綠光)
                    final_damage = int(final_damage * get_damage_reduction_value(self))


                    if skill_hits < 0:# skill_hits < 0 表示這段總傷害要「均分」為多次
                        times = abs(skill_hits)
                        damage_by_hit = int(final_damage / times)
                        total_damage = damage_by_hit * times
                    else:
                        times = skill_hits
                        damage_by_hit = final_damage
                        total_damage = final_damage# * times

                    results.append({
                        "round": i+1,
                        "label": label,
                        "formula": full_formula,
                        "skill_result": skill_result,
                        "damage_by_hit": damage_by_hit,
                        "total_damage": total_damage,
                        "times": times,
                        "user_attack_element": user_attack_element,
                    })

                except Exception as e:
                    print(f"錯誤 [{i+1}/{repeat_count}]：", e)

            return results
       
        

        results = []
        results.extend(compute_and_record_damage(
            formula=formula_str,
            repeat_count=1 if skill_hits < 0 else skill_hits,
            bonus_add=bonus_add,
            bonus_step=bonus_step,
            label="main",
            skill_hits=skill_hits,  # 加入這個
            user_attack_element=User_attack_element
        ))
        
        
        # === [5] combo 計算（如果有）
        if pd.notna(skill_row.get("combo")) and pd.notna(skill_row.get("combo_hits")):

            # --- 先算：是否觸發「特殊替換」（種族 OR buff技能有被使用）---
            trigger_combo_special = False

            # 1) 種族觸發
            if pd.notna(skill_row.get("monster_race")):
                allowed_races = {r.strip() for r in str(skill_row["monster_race"]).split(",") if r.strip()}
                if str(target_race).strip() in allowed_races:
                    trigger_combo_special = True

            # 2) buff技能觸發（Use_skill_levels[skill_id] = True 代表使用過）
            if (not trigger_combo_special) and pd.notna(skill_row.get("skill_buff")):
                buff_ids = []
                for x in str(skill_row["skill_buff"]).split(","):
                    x = x.strip()
                    if x.isdigit():
                        buff_ids.append(int(x))

                if any(Use_skill_levels.get(bid, False) for bid in buff_ids):
                    trigger_combo_special = True

            # --- 決定 combo 公式：符合條件才用 combo_Special_Calculation ---
            combo_formula = str(skill_row["combo"]).strip()

            if (
                trigger_combo_special
                and pd.notna(skill_row.get("combo_Special_Calculation"))
                and str(skill_row.get("combo_Special_Calculation")).strip()
            ):
                combo_formula = str(skill_row["combo_Special_Calculation"]).strip()

            raw_combo_hits = parse_hits(skill_row["combo_hits"], Sklv)

            if raw_combo_hits < 0:
                combo_hits = abs(raw_combo_hits)
                label = "combo (均分)"
            else:
                combo_hits = raw_combo_hits
                label = "combo"

            # ✅ 套用 combo_element 若存在，暫時覆蓋 user_attack_element
            combo_element_val = User_attack_element
            if pd.notna(skill_row.get("combo_element")) and str(skill_row.get("combo_element")).strip():
                try:
                    combo_element_val = int(skill_row["combo_element"])
                    print(f"⚡ combo_element 套用屬性：{element_map.get(combo_element_val, combo_element_val)}")
                except Exception as e:
                    print(f"combo_element 解析錯誤：{e}")
                    combo_element_val = User_attack_element

            results.extend(compute_and_record_damage(
                formula=combo_formula,
                repeat_count=combo_hits,
                bonus_add=0,
                bonus_step=0,
                label=label,
                skill_hits=raw_combo_hits,
                user_attack_element=combo_element_val
            ))





        if results:
            self.skill_formula_result_input.setText(f"{results[0]['skill_result']} %")
        else:
            self.skill_formula_result_input.setText("0%")
            self.custom_calc_box.setPlainText("錯誤：無選擇職業、無技能公式、公式錯誤計算結果為0！")
        """
        for r in results:
            #print(f"=== 第 {r['round']} 次 ===")
            print(f"公式: {r['formula']}")
            #print(f"技能倍率: {r['skill_result']} %")
            #print(f"單次傷害: {r['damage_by_hit']}")
            #print(f"打擊次數: {r['times']} 次")
            print(f"總傷害: {r['total_damage']}")
            #print("--------------------------")
        """


         
        #=========================魔法各增傷計算顯示區=======================
        #print(f"前MATK: {MATKF} 後MATK:{MATKC} 武器MATK:{MATK_Mweapon} S.MATK:{total_SMATK}")  
        #print(f"打擊次數：{len(results)}")        
        result.append(f"{pad_label('使用技能:')}{selected_skill_name}")
        if not results:
            result.append("❌ 無法計算技能傷害，請檢查公式與變數")
            return

        # 預備總傷害合計
        all_total_damage = 0

        # 判斷是否存在 combo 均分段（技能 times > 1 且每段是均分）
        combo_split_results = [r for r in results[1:] if r["times"] > 1 and r["damage_by_hit"] * r["times"] == r["total_damage"]]

        # === 情境：主技能 + combo 均分段 ===
        if len(results) > 1 and combo_split_results:
            # 顯示主技能段
            r = results[0]
            main_element_name = element_map.get(r["user_attack_element"], f"未知({r['user_attack_element']})")
            result.append(f"【{main_element_name}】==================主技能總傷害===========================")
            result.append(f"單次傷害:     {r['damage_by_hit']:,}")
            result.append(f"打擊次數:     {r['times']} 次")
            result.append(f"主技能總傷害: {r['total_damage']:,}")
            all_total_damage += r['total_damage']

            # 顯示 combo 均分段（只取第一段為代表）
            r = combo_split_results[0]
            combo_total = r["damage_by_hit"] * r["times"]
            result.append(f"【{element_map.get(User_attack_element, User_attack_element)}】===============COMBO 技能（均分）========================")
            result.append(f"單次傷害(COMBO): {r['damage_by_hit']:,}")
            result.append(f"打擊次數(COMBO): {r['times']} 次")
            result.append(f"總傷害(COMBO):   {combo_total:,}")
            all_total_damage += combo_total

            # 顯示合計
            result.append(f" ")
            #result.append(f"============================總傷害合計=============================")
            result.append(f"總傷害:   {all_total_damage:,}")

        # === 正常多段技能（非均分）===
        elif len(results) > 1:
            result.append(f"【{element_map.get(User_attack_element, User_attack_element)}】===========以下總傷害數值（共 {len(results)} 次）====================")
            for idx, r in enumerate(results, start=1):
                result.append(f"第 {idx}/{len(results)} 次傷害: {r['total_damage']:,}")
                all_total_damage += r['total_damage']
                # result.append(f"------------------------------------------------------------------")
            result.append(f"總傷害:   {all_total_damage:,}")

        # === 單段技能 ===
        else:
            r = results[0]
            result.append(f"【{element_map.get(User_attack_element, User_attack_element)}】=================以下總傷害數值===========================")
            result.append(f"單次傷害: {r['damage_by_hit']:,}")
            result.append(f"打擊次數: {r['times']} 次")
            result.append(f"總傷害:   {r['total_damage']:,}")





        # ✅ 加上 decay_hits 顯示處理
        decay_hits = int(skill_row["decay_hits"]) if pd.notna(skill_row.get("decay_hits")) else 0
        #print(f"遞增/減次數：{decay_hits}")
        if decay_hits > 1:
            avg_damage = int(all_total_damage / decay_hits)
            result.append(f"遞增/減段數: {decay_hits} 段")
            result.append(f"平均每段傷害: {avg_damage:,}")
            #result.append(f"總傷害:   {avg_damage * decay_hits:,}")

        if attack_type == "magic":
            self.def_label.setVisible(False)
            self.def_input.setVisible(False)
            self.defc_label.setVisible(False)
            self.defc_input.setVisible(False)
            self.res_label.setVisible(False)
            self.res_input.setVisible(False)
            self.mdef_label.setVisible(True)
            self.mdef_input.setVisible(True)
            self.mdefc_label.setVisible(True)
            self.mdefc_input.setVisible(True)
            self.mres_label.setVisible(True)
            self.mres_input.setVisible(True)
            result.append(f"=========================以下各增傷數值===========================")
            result.append(f"{pad_label('前MATK:')}{MATKF:,}")
            result.append(f"{pad_label('後MATK:')}{MATKC:,}")
            result.append(f"{pad_label('武器MATK:')}{MATK_Mweapon:,}")
            result.append(f"{pad_label('裝備MATK+魔力:')}{armorMATK_MAGICPOWER}")
            result.append(f"{pad_label('MATK%:')}{round(MATK_percent)}%")
            result.append(f"{pad_label('魔法體型:')}{round(get_effect_multiplier('MD_size', target_size))}%")
            result.append(f"{pad_label('魔法屬性敵人:')}{round(get_effect_multiplier('MD_element', target_element) + get_effect_multiplier('MD_element', 10))}%")
            result.append(f"{pad_label('屬性魔法:')}{round(get_effect_multiplier('MD_Damage', User_attack_element) + get_effect_multiplier('MD_Damage', 10))}%")
            result.append(f"{pad_label('魔法種族:')}{round(get_effect_multiplier('MD_Race', target_race) + get_effect_multiplier('MD_Race', 9999))}%")
            result.append(f"{pad_label('魔法階級:')}{round(get_effect_multiplier('MD_class', target_class))}%")
            result.append(f"{pad_label('魔物增傷:')}{round(target_monsterMDamage)}%")
            result.append(f"{pad_label('S.MATK:')}{round(total_SMATK)}")
            result.append(f"{pad_label('技能倍率:')}{results[0]['skill_result']}%")
            result.append(f"{pad_label('屬性倍率:')}{get_damage_multiplier(User_attack_element, target_element, target_element_lv)}%")
            result.append(f"{pad_label('後MDEF:')}{target_mdef}")
            result.append(f"{pad_label('無視魔法階級防禦:')}{round(get_effect_multiplier('MD_class_def', target_class))}%")
            result.append(f"{pad_label('無視魔法種族防禦:')}{round(get_effect_multiplier('MD_Race_def', target_race) + get_effect_multiplier('MD_Race_def', 9999))}%")
            result.append(f"{pad_label('魔法破防後傷害:')}{Mdamage_nomdef * 100:.2f}%")
            result.append(f"{pad_label('前MDEF:')}{target_mdefc}")
            result.append(f"{pad_label('MRES:')}{target_mres}")
            result.append(f"{pad_label('無視魔法抗性%:')}{mres_reduction}%")
            result.append(f"{pad_label('魔法破抗性後傷害:')}{Mdamage_nomres * 100:.2f}%")
        
        elif attack_type == "physical":
            self.def_label.setVisible(True)
            self.def_input.setVisible(True)
            self.defc_label.setVisible(True)
            self.defc_input.setVisible(True)
            self.res_label.setVisible(True)
            self.res_input.setVisible(True)
            self.mdef_label.setVisible(False)
            self.mdef_input.setVisible(False)
            self.mdefc_label.setVisible(False)
            self.mdefc_input.setVisible(False)
            self.mres_label.setVisible(False)
            self.mres_input.setVisible(False)
            result.append(f"=========================以下各增傷數值===========================")
            if weapon_class in (11,13,14,17,18,19,20,21):#DEX系
                result.append(f"{pad_label('前ATK (DEX系):')}{FATK:,}")
            else:#STR系
                result.append(f"{pad_label('前ATK(STR系):')}{NATK:,}")
            result.append(f"{pad_label('後ATK:')}{AKTC:,}")
            result.append(f"{pad_label('武器ATK:')}{ATK_Mweapon:,}")
            result.append(f"{pad_label('物理ATK%:')}{round(ATK_percent)}%")
            result.append(f"{pad_label('物理體型:')}{round(get_effect_multiplier('D_size', target_size))}%")
            result.append(f"{pad_label('物理種族:')}{round(get_effect_multiplier('D_Race', target_race) + get_effect_multiplier('D_Race', 9999))}%")
            result.append(f"{pad_label('物理階級:')}{round(get_effect_multiplier('D_class', target_class))}%")
            result.append(f"{pad_label('魔物增傷:')}{round(target_monsterDamage)}%")
            result.append(f"{pad_label('P.ATK:')}{round(total_PATK)}")
            result.append(f"{pad_label('物理屬性敵人:')}{round(get_effect_multiplier('D_element', target_element) + get_effect_multiplier('D_element', 10))}%")
            result.append(f"{pad_label('物理命中:')}{round(Damage_HIT)}%")
            result.append(f"{pad_label('爆傷:')}{round(Damage_CRI)}%")
            if skill_Rangedamage == 1:#DEX系
                if weapon_class == 11:
                    result.append(f"{pad_label('遠傷:')}{round(RangeAttackDamage + BowAtk)}%")
                else:
                    result.append(f"{pad_label('遠傷:')}{round(RangeAttackDamage)}%")
                
            else:#STR系
                result.append(f"{pad_label('近傷:')}{round(MeleeAttackDamage)}%")
            result.append(f"{pad_label('CRATE:')}{round(total_CRATE)}")
            result.append(f"{pad_label('技能倍率:')}{results[0]['skill_result']}%")
            result.append(f"{pad_label('屬性倍率:')}{get_damage_multiplier(User_attack_element, target_element, target_element_lv)}%")
            result.append(f"{pad_label('武器體型修正:')}{Weaponpunish*100}%")
            result.append(f"{pad_label('後DEF:')}{target_def}")
            result.append(f"{pad_label('無視階級防禦:')}{round(get_effect_multiplier('D_class_def', target_class))}%")
            result.append(f"{pad_label('無視種族防禦:')}{round(get_effect_multiplier('D_Race_def', target_race) + get_effect_multiplier('D_Race_def', 9999))}%")
            result.append(f"{pad_label('物理破防後傷害:')}{damage_nodef * 100:.2f}%")
            result.append(f"{pad_label('前DEF:')}{target_defc}")
            result.append(f"{pad_label('RES:')}{target_res}")
            result.append(f"{pad_label('無視物理抗性%:')}{res_reduction}%")
            result.append(f"{pad_label('物理破抗性後傷害:')}{damage_nores * 100:.2f}%")

        elif attack_type == "d_b":
            self.def_label.setVisible(True)
            self.def_input.setVisible(True)
            self.defc_label.setVisible(True)
            self.defc_input.setVisible(True)
            self.res_label.setVisible(True)
            self.res_input.setVisible(True)
            self.mdef_label.setVisible(False)
            self.mdef_input.setVisible(False)
            self.mdefc_label.setVisible(False)
            self.mdefc_input.setVisible(False)
            self.mres_label.setVisible(False)
            self.mres_input.setVisible(False)
            result.append(f"=========================以下各增傷數值===========================")

            if weapon_class == 11:
                result.append(f"{pad_label('遠傷:')}{round(RangeAttackDamage + BowAtk)}%")
            else:
                result.append(f"{pad_label('遠傷:')}{round(RangeAttackDamage)}%")
            #屬性耐性 龍之氣息 預設屬性火，可使用盧恩石轉屬，轉屬後一樣看火屬耐性(屬性*火耐性)
            #屬性耐性 龍之氣息-水 預設屬性水，可使用盧恩石轉屬，轉屬後一樣看水屬耐性(屬性*水耐性)
            result.append(f"{pad_label('技能倍率:')}{results[0]['skill_result']}%")
            result.append(f"{pad_label('屬性倍率:')}{get_damage_multiplier(User_attack_element, target_element, target_element_lv)}%")







        else:
            raise ValueError(f"未知的攻擊類型: {attack_type}")
            
                        
        result.append(f"{pad_label('技能增傷(裝備段):')}{round(Use_Skills)}%")
        result.append(f"{pad_label('技能增傷(技能段):')}{round(passive_skill_buff)}%")
        result.append(f"==================================================================")
        result.append(f"{pad_label('技能等級:')}{Sklv}")
        #result.append(f"{pad_label('技能公式:')}{results[0]['formula']}")
        


        result.extend(bottom_result)#顯示前面儲存的公式
        self.custom_calc_box.setHtml(self.generate_highlighted_html(result))
        if self.auto_compare_checkbox.isChecked():
            self.compare_with_base()
        #self.custom_calc_box.setPlainText("\n".join(result))


    def _config_path(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(base_dir, "data")
        os.makedirs(data_dir, exist_ok=True)
        return os.path.join(data_dir, "config.json")

    def load_config(self):
        self.update_mode = "online_only"
        self.api_key = ""
        try:
            with open(self._config_path(), "r", encoding="utf-8") as f:
                cfg = json.load(f)
            self.update_mode = cfg.get("update_mode", self.update_mode)
            self.api_key = cfg.get("api_key", self.api_key)
        except Exception:
            pass

    def save_config(self):
        cfg = {
            "update_mode": getattr(self, "update_mode", "online_only"),
            "api_key": getattr(self, "api_key", ""),
        }
        try:
            with open(self._config_path(), "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"儲存設定失敗：{e}")


    def get_update_mode(self) -> str:
        if not hasattr(self, "update_mode"):
            self.load_config()
        return self.update_mode or "online_only"

    def get_api_key(self) -> str:
        if not hasattr(self, "api_key"):
            self.load_config()
        return self.api_key or ""

    def open_compile_set(self):
        self.load_config()
        dlg = PreferencesDialog(
            current_mode=self.update_mode,
            current_api_key=getattr(self, "api_key", ""),
            parent=self
        )
        if dlg.exec() == QDialog.Accepted:
            self.update_mode = dlg.selected_mode()
            self.api_key = dlg.api_key()
            self.save_config()
            #QMessageBox.information(self, "偏好設定", f"設定模式為：{self.update_mode}/n 已完成key儲存")



    def generate_highlighted_html(self, lines: list[str]) -> str:
        app = QApplication.instance()        
        if not app:
            raise RuntimeError("QApplication 尚未建立")

        palette = app.palette()
        window_color: QColor = palette.color(QPalette.Window)
        text_color: QColor = palette.color(QPalette.WindowText)

        # 根據亮度判斷主題
        # 若背景偏暗（亮度 < 128），則視為暗色模式
        brightness = (window_color.red() * 0.299 + window_color.green() * 0.587 + window_color.blue() * 0.114)
        dark_mode = brightness < 128

        if dark_mode:
            odd_color = "#FFFFFF"   # 白字
            even_color = "#AAAAAA"  # 灰字
        else:
            odd_color = "#000000"   # 黑字
            even_color = "#555555"  # 深灰字

        html_lines = []
        for i, line in enumerate(lines):
            color = even_color if i % 2 else odd_color
            html_lines.append(f'<span style="color:{color};">{line}</span>')

        html_result = (
            "<pre style='font-family: MingLiU; font-size: 11pt;'>\n"
            + "\n".join(html_lines)
            + "\n</pre>"
        )

        return html_result


        
    def apply_effect_mapping(self, effect_dict, prefix, names, key_template, index_override=None):
        for i, name in enumerate(names):
            idx = index_override[i] if index_override else i
            key = (key_template.format(name), "%")
            value = sum(val for val, _ in effect_dict.get(key, []))
            setattr(self, f"{prefix}_{idx}", value)

    def apply_all_damage_effects(self, effect_dict):
        # === 體型加成 ===
        size_names = ["小型", "中型", "大型"]
        for prefix in ["MD", "D"]:
            self.apply_effect_mapping(effect_dict, f"{prefix}_size", size_names, f"對 {{}} 敵人的{ '魔法' if prefix == 'MD' else '物理' }傷害")

        # === 屬性對象加成 ===
        element_target = ["無屬性", "水屬性", "地屬性", "火屬性", "風屬性",
                          "毒屬性", "聖屬性", "暗屬性", "念屬性", "不死屬性", "全屬性"]
        for prefix in ["MD", "D"]:
            self.apply_effect_mapping(effect_dict, f"{prefix}_element", element_target, f"對 {{}} 對象的{ '魔法' if prefix == 'MD' else '物理' }傷害")

        # === 屬性來源加成（屬性攻擊） ===
        for prefix in ["MD", "D"]:
            self.apply_effect_mapping(effect_dict, f"{prefix}_Damage", element_target, f"{{}} 的{ '魔法' if prefix == 'MD' else '物理' }傷害")

        # === 種族加成 ===
        race_names = ["無形", "不死", "動物", "植物", "昆蟲", "魚貝", "惡魔", "人形", "天使", "龍族", "全種族"]
        race_indexes = list(range(10)) + [9999]
        for prefix in ["MD", "D"]:
            self.apply_effect_mapping(effect_dict, f"{prefix}_Race", race_names, f"對 {{}} 型怪的{ '魔法' if prefix == 'MD' else '物理' }傷害", race_indexes)

        # === 階級加成 ===
        class_names = ["一般", "首領"]
        for prefix in ["MD", "D"]:
            self.apply_effect_mapping(effect_dict, f"{prefix}_class", class_names, f"對 {{}} 階級的{ '魔法' if prefix == 'MD' else '物理' }傷害")

        # === 無視階級防禦 ===
        class_def_names = ["一般", "首領", "玩家"]
        for prefix in ["MD", "D"]:
            self.apply_effect_mapping(effect_dict, f"{prefix}_class_def", class_def_names, f"無視 {{}} 階級的{ '魔法' if prefix == 'MD' else '物理' }防禦")

        # === 無視種族防禦 ===
        race_def_names = ["無形", "不死", "動物", "植物", "昆蟲", "魚貝", "惡魔", "人形", "天使", "龍族", "全種族"]
        race_indexes = list(range(10)) + [9999]
        for prefix in ["MD", "D"]:
            self.apply_effect_mapping(effect_dict, f"{prefix}_Race_def", race_def_names, f"無視 {{}} 型怪的{ '魔法' if prefix == 'MD' else '物理' }防禦", race_indexes)
        
        # === 無視種族抗性 ===
        race_def_names = ["無形", "不死", "動物", "植物", "昆蟲", "魚貝", "惡魔", "人形", "天使", "龍族", "全種族"]
        race_indexes = list(range(10)) + [9999]
        for prefix in ["MD", "D"]:
            self.apply_effect_mapping(effect_dict, f"{prefix}_Race_res", race_def_names, f"無視 {{}} 型怪的{ '魔法' if prefix == 'MD' else '物理' }抗性", race_indexes)

    
    def calc_weapon_refine_matk(self, weapon_Level, weaponRefineR, weaponGradeR):
        """
        回傳： (MATK 總加成, S.MATK 總加成)
        說明：
          1~4 階：每 +1 固定加成；超過安定值後，每 +1 額外給「浮動加成(取上限)」；
                  若精煉 > 15，則每超過 1 級，對「1~15」再各加一次 over16_bonus，共 15 倍。
          5 階：依品級每 +1 固定 MATK，加上每 +1 固定 +2 S.MATK。
        """
        if weapon_Level == 0 or weaponRefineR <= 0:
            return 0, 0

        # 每精煉+1 增加 MATK
        base_per_refine   = {1: 2, 2: 3, 3: 5, 4: 7, 5: 0}
        # 超過安定值後，每 +1 額外「浮動」增加的上限值
        extra_after_safe  = {1: 3, 2: 5, 3: 8, 4: 14, 5: 0}
        # 精煉 16 以上，每超過 1 級，對 1~15 各再加的數值
        over16_bonus      = {1: 3, 2: 5, 3: 7, 4: 10, 5: 0}
        # 安定值
        safe_threshold    = {1: 7, 2: 6, 3: 5, 4: 4, 5: 0}

        # 五階各品級的每 +1 MATK
        level5_grade_bonus = {
            0: 8.0,   # N
            1: 8.8,   # D
            2: 10.4,  # C
            3: 12.0,  # B
            4: 16.0   # A
        }
        # 五階每 +1 固定 +2 S.MATK
        smatk_bonus_per_refine = 2

        matk_total = 0.0
        total_SMATK = 0.0

        if weapon_Level < 5:
            # 固定加成：所有等級都算
            base = weaponRefineR * base_per_refine[weapon_Level]

            # 浮動加成：只在超過安定值的那幾級才算（取上限）
            safe = safe_threshold[weapon_Level]
            steps_after_safe = max(0, weaponRefineR - safe)
            variance = steps_after_safe * extra_after_safe[weapon_Level]

            # 16 以上額外加成：每超過 1 級，對「1~15」各再加一次（= 15 倍）
            steps_over16 = max(0, weaponRefineR - 15)
            over16 = steps_over16 * 15 * over16_bonus[weapon_Level]

            #matk_total = base + variance + over16
            matk_total = base + over16#安定後浮動加成暫時取消
            total_SMATK = 0.0

        else:  # weapon_Level == 5
            matk_per_refine = level5_grade_bonus.get(weaponGradeR, 0.0)
            matk_total = weaponRefineR * matk_per_refine
            total_SMATK = weaponRefineR * smatk_bonus_per_refine

        return matk_total, total_SMATK
        
    def calc_weapon_refine_atk(self, weapon_Level, weaponRefineR, weaponGradeR):
        """
        回傳： (ATK/MATK 總加成, P.ATK/S.MATK 總加成)
        說明：
          1~4 階：每 +1 固定加成；超過安定值後，每 +1 額外給「浮動加成(這裡取上限)」；
                  若精煉 > 15，則每超過 1 級，對「1~15」再各加一次 over16_bonus，共 15 倍。
          5 階：依品級每 +1 固定 ATK/MATK，加上每 +1 固定 +2 P.ATK/S.MATK。
        """
        if weapon_Level == 0 or weaponRefineR <= 0:
            return 0, 0

        # 每精煉+1 增加 ATK/MATK
        base_per_refine   = {1: 2, 2: 3, 3: 5, 4: 7, 5: 0}
        # 超過安定值後，每 +1 額外「浮動」增加的上限值（表格中的 1~X，這裡取 X 當上限）
        extra_after_safe  = {1: 3, 2: 5, 3: 8, 4: 14, 5: 0}
        # 精煉 16 以上，每超過 1 級，對 1~15 各再加的數值
        over16_bonus      = {1: 3, 2: 5, 3: 7, 4: 10, 5: 0}
        # 安定值
        safe_threshold    = {1: 7, 2: 6, 3: 5, 4: 4, 5: 4}

        # 五階各品級的每 +1 ATK/MATK
        level5_grade_bonus = {
            0: 8.0,   # N
            1: 8.8,   # D
            2: 10.4,  # C
            3: 12.0,  # B
            4: 16.0   # A
        }
        # 五階每 +1 固定 +2 P.ATK/S.MATK
        patk_bonus_per_refine = 2

        atk_total = 0.0
        total_PATK = 0.0

        if weapon_Level < 5:
            # 固定加成：所有等級都算
            base = weaponRefineR * base_per_refine[weapon_Level]

            # 浮動加成：只在超過安定值的那幾級才算（這裡取“上限”值）
            safe = safe_threshold[weapon_Level]
            steps_after_safe = max(0, weaponRefineR - safe)
            variance = steps_after_safe * extra_after_safe[weapon_Level]

            # 16 以上額外加成：每超過 1 級，對「1~15」各再加一次（= 15 倍）
            steps_over16 = max(0, weaponRefineR - 15)
            over16 = steps_over16 * 15 * over16_bonus[weapon_Level]

            #atk_total = base + variance + over16
            atk_total = base + over16#安定後浮動加成暫時取消
            total_PATK = 0.0

        else:  # weapon_Level == 5
            atk_per_refine = level5_grade_bonus.get(weaponGradeR, 0.0)
            atk_total = weaponRefineR * atk_per_refine
            total_PATK = weaponRefineR * patk_bonus_per_refine

        return atk_total, total_PATK



    def update_note_widget_with_delay(self, widget: QTextEdit, text: str):
        widget.setPlainText(text)

        def adjust():
            # ✅ 強制文字寬度套入 layout
            widget.document().setTextWidth(widget.viewport().width())
            self.adjust_textedit_height(widget)

        # 雙層 QTimer 保證 Qt 已繪製完畢
        QTimer.singleShot(0, lambda: QTimer.singleShot(0, adjust))

    def adjust_textedit_height(self, text_edit: QTextEdit):
        doc = text_edit.document()

        # 🔧 強制 layout
        doc.setTextWidth(text_edit.viewport().width())
        doc.adjustSize()  # 👈 這個是 Qt layout 關鍵

        text_edit.updateGeometry()
        text_edit.update()

        # 重新取得 layout 後的尺寸
        line_count = doc.blockCount()
        doc_size = doc.size().toSize()

        #print(f"📝 [{text_edit.objectName()}] 目前行數：{line_count}")
        #print(f"📐 Document size: {doc_size.width()} x {doc_size.height()}")

        margin = 3
        min_height = 27
        max_height = 400
        new_height = max(min_height, min(doc_size.height() + margin, max_height))

        #print(f"🪄 設定高度為：{new_height}")
        text_edit.setFixedHeight(new_height)



    def on_function_text_changed(self):
        
        sender = self.sender()  # 取得是哪個 QTextEdit 被改了
        if not sender:
            return

        object_name = sender.objectName()  # 例如 "頭上-函數"
        if not object_name.endswith("-函數"):
            return

        part_name = object_name.replace("-函數", "")
        lua_code = sender.toPlainText()

        #print(f"🔍 偵測到 {object_name} 變動，內容：\n{lua_code}")

        try:
            results = parse_lua_effects_with_variables(
                block_text=lua_code,
                refine_inputs={},
                get_values={},
                grade=0,
                unit_map=unit_map,
                size_map=size_map,
                effect_map=effect_map,
                hide_unrecognized=False
            )
            output = "\n".join(results)
        except Exception as e:
            output = f"⚠️ 錯誤：{e}"

        # 尋找對應的 詞條 欄位，名稱是 part_name-詞條
        target_name = f"{part_name}-詞條"
        for v in self.refine_inputs_ui.values():
            if v.get("note_ui") and v["note_ui"].objectName() == target_name:
                v["note_ui"].setPlainText(output)
                QTimer.singleShot(0, lambda w=v["note_ui"]: self.adjust_textedit_height(w))
                break
        

    def handle_note_text_clicked(self, event, part_name, text_widget_ui ,text_widget):
        '''
        處理詞條文字被點擊的事件
        '''
        self.clear_current_edit()
        self.current_edit_part = f"{part_name} - 詞條"
        self.current_edit_widget = text_widget
        self.current_edit_label.setText(f"目前部位：{self.current_edit_part}")
        print(f"目前部位：{self.current_edit_part}")
        self.unsync_button.setVisible(True)
        self.apply_to_note_button.setVisible(True)
        self.clear_field_button2.setVisible(True)
        self.unsync_button2.setVisible(True)
        self.apply_equip_button.setVisible(True)
        self.clear_field_button.setVisible(True)

        self.set_edit_lock(part_name, "note")
        for v in self.refine_inputs_ui.values():
            if "note" in v:
                v["note"].setStyleSheet("")
        text_widget_ui.setStyleSheet("background-color: #ff0000;")

        self.result_output.setPlainText(text_widget.toPlainText())
        self.tab_widget.setCurrentIndex(self.function_tab_index)

        QTextEdit.mousePressEvent(text_widget, event)  # 保留原始點擊事件行為


    def update_function_selector(self):
        self.function_selector.clear()
        for func_name, spec in function_defs.items():
            label = spec.get("desc", func_name)  # 顯示用中文描述
            self.function_selector.addItem(label, func_name)

        if self.function_selector.count() > 0:
            self.function_selector.setCurrentIndex(0)
            self.on_function_changed()

            
    def on_tab_changed(self, index):
        if index == self.function_tab_index:
            self.update_function_selector()
            self.update_all_notes_from_functions()  # ⬅️ 加這一行

        self.tab_widget.adjustSize()

        QTimer.singleShot(50, lambda: (
            self.tab_widget.repaint(),
        ))

    def update_all_notes_from_functions(self):
        for part_name, widgets in self.refine_inputs_ui.items():
            function_widget = widgets.get("function")
            note_widget = widgets.get("note_ui")
            if not function_widget or not note_widget:
                continue

            lua_code = function_widget.toPlainText()

            try:
                results = parse_lua_effects_with_variables(
                    block_text=lua_code,
                    refine_inputs={},
                    get_values={},
                    grade=0,
                    unit_map=unit_map,
                    size_map=size_map,
                    effect_map=effect_map,
                    hide_unrecognized=False
                )
                output = "\n".join(results)
            except Exception as e:
                output = f"⚠️ 錯誤：{e}"

            self.update_note_widget_with_delay(note_widget, output)


    def clear_global_state(self):#清除全域武器裝備技能等級並預先匯入基礎值
        #print("武器階級：", global_weapon_level_map)
        #print("防具階級：", global_armor_level_map)
        #print("武器類型：", global_weapon_type_map)
        #print("技能：", enabled_skill_levels)
        global_weapon_level_map.clear()
        global_armor_weapon_map.clear()
        global_armor_level_map.clear()
        global_weapon_type_map.clear()
        global_weapon_matk_map.clear()
        global_weapon_atk_map.clear()
        
        
        enabled_skill_levels.clear()
        Use_skill_levels.clear()
       # 你目前已知使用的 slot ID 範圍
        slot_ids = [10, 11, 12, 2, 4, 3, 5, 6, 7, 8,
                    30, 31, 32, 33, 34, 35, 41, 42, 43, 44]

        for slot in slot_ids:
            global_weapon_level_map[slot] = 0
            global_armor_weapon_map[slot] = 0
            global_armor_level_map[slot] = 0
            global_weapon_type_map[slot] = 0
            global_weapon_matk_map[slot] = 0
            global_weapon_atk_map[slot] = 0
        #self.update_combobox()

        #self.display_item_info()
        #self.display_all_effects()
        #self.update_all_notes_from_functions
        #self.replace_custom_calc_content
        #self.on_function_text_changed
        #print("清除完畢：============================")
        #print("武器階級：", global_weapon_level_map)
        #print("防具階級：", global_armor_level_map)
        #print("武器類型：", global_weapon_type_map)
        #print("技能：", enabled_skill_levels)

    def update_dex_int_half_note(self):#素質無詠計算
        raw_effects = getattr(self, "effect_dict_raw", {})

        # base
        try:
            base_dex = int(self.input_fields["DEX"].text())
        except:
            base_dex = 0
        try:
            base_int = int(self.input_fields["INT"].text())
        except:
            base_int = 0

        # job bonus
        job_id = self.input_fields["JOB"].currentData()
        tjob_bonus = job_dict.get(job_id, {}).get("TJobMaxPoint", [])
        dex_job = tjob_bonus[4] if len(tjob_bonus) > 4 else 0
        int_job = tjob_bonus[3] if len(tjob_bonus) > 3 else 0

        # equip bonus
        dex_equip = sum(val for val, _ in raw_effects.get(("DEX", ""), []))
        int_equip = sum(val for val, _ in raw_effects.get(("INT", ""), []))

        dex_total = base_dex + dex_job + dex_equip
        int_total = base_int + int_job + int_equip

        dex_part = dex_total
        int_part = int(int_total / 2)
        result = dex_part + int_part

        target = 265
        #gap = max(0, target - result)
        gap = target - result
        status = "✅" if gap <= 0 else "⚠️ 未達標"

        if gap <= 0:
            need_dex = gap
            need_int = gap * 2
            diff_text = f"　（超過：DEX {need_dex} 或 INT {need_int}）"
        else:
            need_dex = gap
            need_int = gap * 2
            diff_text = f"　（還差：DEX +{need_dex} 或 INT +{need_int}）"

        self.DEX_INT_265_label.setText(
            f"※素質無詠 {dex_part} + {int_part} = {result} {status}\n{diff_text}"
        )



    def calc_aspd(self,#攻速計算
        wpasdp_data: dict,
        job_id: int,
        agi: float,
        dex: float,
        *,
        # 一般模式用
        weapon_type: int | None = None,
        has_shield: bool = False,

        # 雙刀模式用
        dual_wield: bool = False,
        right_weapon_type: int | None = None,
        left_weapon_type: int | None = None,

        # 類別加成（rate 可傳 0.15 或 15 都可）
        cat1_rate: float = 0.0,
        cat1_flat: float = 0.0,
        cat2_rate: float = 0.0,
        cat2_flat: float = 0.0,

        # 最後四捨五入位數
        round_digits: int = 3,
    ) -> float:
        """
        回傳：套完基礎ASPD + 類別1/2 後的 ASPD，四捨五入到小數 round_digits 位（ROUND_HALF_UP）
        """

        def _rate_to_decimal(r: float) -> float:
            # 允許使用者傳 0.15 或 15（代表 15%）
            if r < 0:
                return r
            return r / 100.0 if r > 1 else r

        def _round_half_up(x: float, digits: int) -> float:
            q = Decimal("1").scaleb(-digits)  # e.g. digits=3 -> Decimal('0.001')
            return float(Decimal(str(x)).quantize(q, rounding=ROUND_HALF_UP))

        if job_id not in wpasdp_data:
            #raise KeyError(f"找不到 job_id={job_id} 的武器基礎ASPD表")
            return (f"未選擇職業或該職業不支援此武器。")

        job_table = wpasdp_data[job_id]

        cat1_rate = _rate_to_decimal(cat1_rate)
        cat2_rate = _rate_to_decimal(cat2_rate)

        # --- 1) 先算基礎 ASPD ---
        if dual_wield:
            if right_weapon_type is None or left_weapon_type is None:
                raise ValueError("dual_wield=True 時必須提供 right_weapon_type 與 left_weapon_type")

            base_r = job_table.get(right_weapon_type)
            base_l = job_table.get(left_weapon_type)
            if base_r is None or base_l is None:
                #raise KeyError("雙刀武器類型不在此 job 的表內")
                return (f"該職業不支援雙刀武器。")
            if base_r <= 0 or base_l <= 0:
                #raise ValueError("雙刀基礎ASPD <= 0，疑似不可用")
                return (f"雙刀基礎ASPD <= 0")

            aspd = (
                base_r
                + (base_l - 194) / 4
                + math.sqrt(agi * 10.01 + dex * 11 / 60) * 1.04518
            )

        else:
            if weapon_type is None:
                raise ValueError("dual_wield=False 時必須提供 weapon_type")

            base = job_table.get(weapon_type)
            if base is None:
                #raise KeyError(f"job_id={job_id} 不支援 weapon_type={weapon_type}")
                return (f"該職業不支援此武器。")
            if base <= 0:
                #raise ValueError("基礎ASPD <= 0，疑似不可用")
                return (f"基礎ASPD <= 0")

            stat_term = math.sqrt(agi * 10.09 + dex * 11 / 60)

            # 基礎ASPD145以上採用係數
            if base >= 145:
                stat_term *= (1 - (base - 144) / 50)

            shield_penalty = float(job_table.get(50, 0)) if has_shield else 0.0  # 通常是負數
            aspd = base + stat_term + shield_penalty

        # --- 2) 類別1 ---
        aspd_1 = 200 - (200 - aspd) * (1 - cat1_rate) + cat1_flat

        # --- 3) 類別2 ---
        aspd_2 = 195 - (195 - aspd_1) * (1 - cat2_rate) + cat2_flat

        # --- 4) 小數第 3 位（或你指定的位數） ---
        return _round_half_up(aspd_2, round_digits)


    def safe_update_textbox(self, textbox, text):
        scrollbar = textbox.verticalScrollBar()
        scroll_pos = scrollbar.value()
        textbox.setPlainText(text)
        scrollbar.setValue(scroll_pos)

    def toggle_equip_text_visibility(self):
        hidden = self.hide_unrecognized_checkbox.isChecked()
        self.equip_text.setVisible(not hidden)
        self.equip_text_label.setVisible(not hidden)
        self.combi_raw_text.setVisible(not hidden)
        
    def filter_effects(self, effects: list[str]) -> list[str]:
        hide_keywords = []
        if self.hide_physical_checkbox.isChecked():
            hide_keywords.extend(["物理", "爆擊", "CRI", "武器ATK" , "P.ATK"])
        if self.hide_magical_checkbox.isChecked():
            hide_keywords.extend(["魔法", "武器MATK", "S.MATK"])

        # 過濾物理/魔法關鍵字
        filtered = [line for line in effects if not any(k in line for k in hide_keywords)]

        # 過濾未辨識或需隱藏內容
        if self.hide_unrecognized_checkbox.isChecked():
            filtered = [
                line for line in filtered
                if not (line.startswith("🟡") or
                        line.startswith("⚠️") or
                        line.startswith("❌") or
                        line.startswith("📌") or
                        line.startswith("✅") or
                        line.startswith("⛔") or
                        line.startswith("可使用")
                        )
            ]
        return filtered
    
    def filter_skill_list(self):
        keyword = self.skill_search_bar.text().strip().lower()

        for name, checkbox in self.skill_checkboxes.items():
            if keyword in name.lower() or keyword in all_skill_entries[name]["type"].lower():
                checkbox.show()
            else:
                checkbox.hide()


    
    def normalize_effect_key(self, key: str) -> str:
        key = key.strip()

        # 只處理 固定 / 變動 詠唱
        key = key.replace("固定詠唱時間", "固定詠唱時間")
        key = key.replace("變動詠唱時間", "變動詠唱時間")

        return key

    def handle_exclusive_toggle(self, checkbox, group, checked):
        """處理 mutually exclusive 但允許取消的行為"""
        if checked:
            # 若這個 checkbox 被勾選，取消同組其他的
            for cb in self.exclusive_groups[group]:
                if cb is not checkbox:
                    cb.blockSignals(True)
                    cb.setChecked(False)
                    cb.blockSignals(False)
        else:
            # 若使用者取消勾選 → 不做任何事（允許取消）
            pass


    def try_extract_effect(self, line: str):
        import re

        # 統一處理 % 類型（+/-）
        match = re.match(r"(.+?)\s*([+-]?[0-9]+)\%$", line)
        if match:
            return match.group(1).strip(), int(match.group(2)), "%"

        # 處理 秒 類型（+/-）
        match = re.match(r"(.+?)\s*([+-]?[0-9.]+)\s*秒$", line)
        if match:
            return match.group(1).strip(), float(match.group(2)), "秒"

        # 處理 無單位數值（+/-）
        match = re.match(r"(.+?)\s*([+-]?[0-9]+)$", line)
        if match:
            return match.group(1).strip(), int(match.group(2)), ""

        return None
        
    def update_stat_bonus_display(self):
        try:
            job_id = self.input_fields["JOB"].currentData()
            tjob_bonus = job_dict.get(job_id, {}).get("TJobMaxPoint", [])
            stat_names = ["STR", "AGI", "VIT", "INT", "DEX", "LUK", "POW", "STA", "WIS", "SPL", "CON", "CRT"]

            raw_effects = getattr(self, "effect_dict_raw", {})

            for i, stat in enumerate(stat_names):
                job = tjob_bonus[i] if i < len(tjob_bonus) else 0
                try:
                    base = int(self.input_fields[stat].text())
                except:
                    base = 0

                entries = raw_effects.get((stat, ""), [])
                equip = sum(val for val, _ in entries)
                total = base + job + equip

                if stat in self.stat_bonus_labels:
                    self.stat_bonus_labels[stat].setFont(QFont("Consolas", 14))
                    self.stat_bonus_labels[stat].setText(f"{base:>3} +{job:>3} +{equip:>3} = {total:>3}")
        except Exception as e:
            print("顯示職業加成錯誤：", e)


    def calculate_tstat_total_used(self):
        total = 0
        for tstat in ["POW", "STA", "WIS", "SPL", "CON", "CRT"]:
            try:
                val = int(self.input_fields[tstat].text())
            except:
                val = 0
            total += val  # ✅ 每一點直接 +1
        return total

    def on_result_output_changed(self):
        if isinstance(self.result_output, QTextEdit):
            lua_code = self.result_output.toPlainText()
        else:
            lua_code = self.result_output.text()

        # === get(x) 對應 ===
        get_values = {}
        for stat_name, stat_id in self.stat_fields.items():
            try:
                get_values[stat_id] = int(self.input_fields[stat_name].text())
            except:
                get_values[stat_id] = 0

        # === refine_inputs: 所有部位 slot ➜ 精煉值 ===
        refine_inputs = {}
        for part_name, info in self.refine_parts.items():
            slot_id = info.get("slot")
            try:
                refine_inputs[slot_id] = self.refine_inputs_ui[part_name]["refine"].value()
            except:
                refine_inputs[slot_id] = 0

        # === 全域精煉 slot（GetLocation() 用）===
        try:
            current_location_slot = self.global_refine_input()
        except:
            current_location_slot = 0

        # === 全域階級（GetEquipGradeLevel(GetLocation()) 用）===
        try:
            grade = self.global_grade_combo.currentData()
        except:
            grade = 4

        try:
            results = parse_lua_effects_with_variables(
                block_text=lua_code,
                refine_inputs=refine_inputs,
                get_values=get_values,
                grade=grade,
                unit_map=unit_map,
                size_map=size_map,
                effect_map=effect_map,
                current_location_slot=current_location_slot  # ✅ 傳入現在位置 slot
            )
            results = self.filter_effects(results)
            explanation = "\n".join(results)
        except Exception as e:
            explanation = f"⚠️ 錯誤：{e}"

        self.syntax_result_box.setPlainText(explanation)




    def on_function_changed(self):
        self.skill_search_input.setVisible(False)
        func_name = self.function_selector.currentData()
        spec = function_defs.get(func_name, {})
        self.param_widgets.clear()

        while self.param_layout.count():
            item = self.param_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        row_layout = QHBoxLayout()

        for arg in spec.get("args", []):
            if arg.get("name") in ("無意義", "目標"):
                if arg.get("map") == "unit_map":
                    # 特殊情況：map 是 unit_map → 強制指定 1
                    self.param_widgets.append("1")
                elif "map" in arg and arg["map"].isdigit():
                    # 一般情況：map 本身就是數字字串
                    self.param_widgets.append(arg["map"])
                else:
                    # 其他情況：預設填 0
                    self.param_widgets.append("0")
                continue



            label = QLabel(arg["name"])
            row_layout.addWidget(label)

            if "map" in arg:
                if arg["map"].isdigit():
                    label_value = QLabel(f"(固定: {arg['map']})")
                    label_value.setObjectName("fixed")
                    self.param_widgets.append(arg["map"])
                    row_layout.addWidget(label_value)
                    row_layout.setFixedWidth(150)
                    
                elif arg["map"]:
                    if arg["map"] == "skill_map":
                        # ✅ 技能選單 + 外部搜尋框綁定
                        self.skill_search_input.setVisible(True)
                        combo = QComboBox()
                        combo.setFixedWidth(150)
                        combo.setEditable(False)

                        try:
                            value_map = eval(arg["map"])
                        except Exception:
                            value_map = {}
                            

                        all_items = list(value_map.items())
                        for k, v in all_items:
                            combo.addItem(v, k)

                        def filter_skill_combo():
                            keyword = self.skill_search_input.text().lower().strip()
                            combo.clear()
                            for k, v in all_items:
                                if keyword in v.lower() or keyword in str(k):
                                    combo.addItem(v, k)
                        try:
                            self.skill_search_input.textChanged.disconnect()
                        except TypeError:
                            pass
                        self.skill_search_input.textChanged.connect(filter_skill_combo)

                        self.param_widgets.append(combo)
                        row_layout.addWidget(combo)

                    else:
                        combo = QComboBox()
                        combo.setFixedWidth(150)
                        try:
                            value_map = eval(arg["map"])

                            if arg["map"] == "effect_map":
                                # 只有 effect_map 時才按名稱排序
                                items = sorted(value_map.items(), key=lambda item: item[1])
                            else:
                                items = value_map.items()

                            for k, v in items:
                                combo.addItem(v, k)

                        except Exception:
                            combo.addItem("（錯誤：找不到 map）", -1)
                        
                        self.param_widgets.append(combo)
                        row_layout.addWidget(combo)
                
            elif arg.get("type") == "value":
                spin = QSpinBox()
                spin.setRange(0, 999)
                spin.setFixedWidth(45)
                spin.setButtonSymbols(QSpinBox.NoButtons)
                spin.wheelEvent = lambda e: None
                self.param_widgets.append(spin)
                row_layout.addWidget(spin)

        row_widget = QWidget()
        row_widget.setLayout(row_layout)
        self.param_layout.addWidget(row_widget, alignment=Qt.AlignRight)




    

    def on_generate(self):
        func_name = self.function_selector.currentData()
        args = []
        for w in self.param_widgets:
            if isinstance(w, QComboBox):
                args.append(str(w.currentData()))
            elif isinstance(w, QSpinBox):
                args.append(str(w.value()))
            elif isinstance(w, str):  # 固定值
                args.append(w)
        result = f"{func_name}({', '.join(args)})"

        # ✅ 新增一行，不覆蓋
        existing = self.result_output.toPlainText()
        if existing.strip():
            new_text = existing + "\n" + result
        else:
            new_text = result
        self.result_output.setPlainText(new_text)

        # ✅ 自動捲到底（可選）
        self.result_output.verticalScrollBar().setValue(
            self.result_output.verticalScrollBar().maximum()
        )





    def recompile(self):
        data_folder = os.path.join(os.getcwd(), "DATA")

        # ===== 你要的完整清單 + 預設勾選 =====
        files_to_delete = [
            ("EquipmentProperties.lua", True),
            ("iteminfo_new.lua", True),
            ("EnchantList.lua", True),
            ("ItemDBNameTbl.lua", True),
            ("ItemReformSystem.lua", True),
            ("skill_tree.yml", False),
            ("skilltreeview.lub", False),
            ("skillneme.csv", False),
            ("skillbuff.lua", False),
            ("all_skill_entries.py", False),
            ("job_dict.py", False),
            ("EnchantName.lua", False),
        ]

        dialog = FileSelectionDialog(files_to_delete, data_folder, self)
        if dialog.exec() != QDialog.Accepted:
            return  # 使用者取消

        selected_files = dialog.get_selected_files()
        if not selected_files:
            QMessageBox.information(self, "取消", "沒有選擇任何檔案。")
            return

        # ===== 刪除檔案 =====
        try:
            for filename in selected_files:
                path = os.path.join(data_folder, filename)
                if os.path.exists(path):
                    os.remove(path)

            QMessageBox.information(self, "完成", "檔案已刪除，程式將重新啟動。")

            python = sys.executable
            os.execl(python, python, *sys.argv)

        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"發生錯誤：{str(e)}")



    def update_total_effect_display(self):
        keyword = self.total_filter_input.text().strip()
        if not keyword:
            lines = self.total_combined_raw
        else:
            lines = [line for line in self.total_combined_raw if keyword in line]

        self.safe_update_textbox(self.total_effect_text, "\n".join(lines))
        
    #被動技能給予的狀態
    def apply_skill_buffs_into_effect_dict(self, skillbuff_path, enabled_skill_levels, refine_inputs, get_values, grade):
        def GSklv(skill_id):
            return enabled_skill_levels.get(skill_id, 0)  # 若沒有這個技能，預設回傳 0

        try:
            with open(skillbuff_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            print(f"❌ 無法讀取 skillbuff.lua：{e}")
            return {}

        effect_dict = {}
        for skill_id, level in enabled_skill_levels.items():
            pattern = rf"\[{skill_id}\]\s*=\s*\{{(.*?)\}}"
            match = re.search(pattern, content, re.DOTALL)
            if not match:
                continue

            block = match.group(1)
            #block = re.sub(rf"GSklv\({skill_id}\)", str(level), block)
            block = re.sub(
                r"GSklv\(\s*(\d+)\s*\)",
                lambda m: str(GSklv(int(m.group(1)))),
                block,
                flags=re.IGNORECASE
            )

            parsed_lines = parse_lua_effects_with_variables(
                block,
                refine_inputs,
                get_values,
                grade,
                unit_map,
                size_map,
                effect_map,
                hide_unrecognized=True
            )
            #print("DEBUG parsed_lines:", parsed_lines)

            skill_name = skill_map.get(skill_id, f"技能ID {skill_id}")
            source_str = f"技能：{skill_name} Lv.{level}"

            for line in parsed_lines:
                # 濾掉 parser 的 debug 行
                if line.startswith(("📌", "✅", "❌")):
                    continue
                # 嘗試匹配格式："S.MATK +5"、"固定詠唱時間 -1.0 秒"
                match = re.match(r"(.+?)\s*([+-]?\d+(?:\.\d+)?)(?:\s*([^\d\s]+))?$", line)
                if not match:
                    continue

                key, val_str, unit = match.groups()
                unit = unit or ""   # ✅ 關鍵：None -> ""
                try:
                    value = float(val_str)
                except:
                    continue

                display_value = int(value) if value.is_integer() else round(value, 1)

                effect_dict.setdefault((key.strip(), unit), []).append((display_value, source_str))

        return effect_dict





    def display_all_effects(self):
        '''
        顯示所有部位的效果
        '''
        def extract_combi_ids(block_text: str) -> list[int]:
            import re
            match = re.search(r"Combiitem\s*=\s*{([^}]*)}", block_text)
            if match:
                return [int(i.strip()) for i in match.group(1).split(",")]
            return []

        def extract_combo_items(combo_text: str) -> set[int]:
            import re
            match = re.search(r"Item\s*=\s*{([^}]*)}", combo_text)
            if match:
                items = match.group(1).split(",")
                result = set()
                for x in items:
                    x = x.strip()
                    if x.isdigit():
                        result.add(int(x))
                    elif x != '':
                        print(f"⚠️ 無法轉換為整數: '{x}' in block: {combo_text}")
                return result
            return set()



        get_values = {}
        for label, gid in self.stat_fields.items():
            widget = self.input_fields[label]
            if isinstance(widget, QComboBox):
                get_values[gid] = widget.currentData()
            else:
                try:
                    get_values[gid] = int(widget.text())
                except ValueError:
                    get_values[gid] = 0

        # 🔁 等所有 stat 欄位都建立後，再註冊 textChanged
        if hasattr(self, "_update_stat_point_callback"):
            for attr in ["STR", "AGI", "VIT", "INT", "DEX", "LUK", "POW", "STA", "WIS", "SPL", "CON", "CRT", "BaseLv"]:
                self.input_fields[attr].textChanged.connect(self._update_stat_point_callback)

            # 主動執行一次，初始化顯示
            self._update_stat_point_callback()



        refine_inputs = {}
        # 先在外面準備一份「全 0」的 refine_inputs
        refine_inputs_base = {info["slot"]: 0 for info in self.refine_parts.values()}

        for label, info in self.refine_parts.items():
            slot_id = info["slot"]
            try:
                refine_inputs[slot_id] = int(self.input_fields[label].text())
            except:
                refine_inputs[slot_id] = 0

        effect_dict = {}
        base_effect_dict = {} 
        

        for part in self.refine_parts.values():#先清除部位 to itemid的對應
            slot_id = part["slot"]
            slot_item_id_map[slot_id] = 0

        for part_name, ui in self.refine_inputs_ui.items():
            # ▶️ 裝備主體處理
            equip_name = ui["equip"].text().strip()
            if equip_name:
                source_label = f"{part_name}：{equip_name}"  # or 卡片名稱 or 套裝來源
                source_label_base = f"{part_name}：{equip_name}（基礎）"
                for item_id, item in self.parsed_items.items():
                    if item["name"] == equip_name and item_id in self.equipment_data:
                        block_text = self.equipment_data[item_id]
                        grade = self.input_fields[f"{part_name}_階級"].currentIndex()
                        slot_id = self.refine_parts[part_name]["slot"]
                        slot_item_id_map[slot_id] = item_id  # 存入全域對應表

                        effects = parse_lua_effects_with_variables(
                            block_text,
                            refine_inputs,
                            get_values,
                            grade,
                            unit_map,
                            size_map,
                            effect_map,
                            hide_unrecognized=self.hide_unrecognized_checkbox.isChecked(),
                            hide_physical=self.hide_physical_checkbox.isChecked(),
                            hide_magical=self.hide_magical_checkbox.isChecked(),
                            current_location_slot=slot_id
                        )

                        filtered = self.filter_effects(effects)
                        for line in filtered:
                            if not line.strip():
                                continue
                            parsed = self.try_extract_effect(line)
                            if parsed:
                                key, value, unit = parsed
                                key = self.normalize_effect_key(key)
                                # 建立效果來源清單
                                effect_dict.setdefault((key, unit), []).append((value, source_label))
                            else:
                                text = line.strip()
                                if text:
                                    key = self.normalize_effect_key(text)

                                    # ✅ 純文字效果也寫入 effect_dict
                                    # value = 0, unit = ""
                                    effect_dict.setdefault((key, ""), []).append((0, source_label))

                        # --- 第二次：基礎能力（grade=0 + refine_inputs 全 0） ---
                        base_effects = parse_lua_effects_with_variables(
                            block_text,
                            refine_inputs_base,  # <- 全 0
                            get_values,
                            0,                   # <- grade 強制 0
                            unit_map,
                            size_map,
                            effect_map,
                            hide_unrecognized=self.hide_unrecognized_checkbox.isChecked(),
                            hide_physical=self.hide_physical_checkbox.isChecked(),
                            hide_magical=self.hide_magical_checkbox.isChecked(),
                            current_location_slot=slot_id
                        )

                        base_filtered = self.filter_effects(base_effects)
                        for line in base_filtered:
                            if not line.strip():
                                continue
                            parsed = self.try_extract_effect(line)
                            if parsed:
                                key, value, unit = parsed
                                key = self.normalize_effect_key(key)
                                base_effect_dict.setdefault((key, unit), []).append((value, source_label_base))

            # ▶️ 卡片欄處理（最多4張）
            for i, card_input in enumerate(ui["cards"]):
                grade = 0
                card_name = card_input.text().strip()
                if not card_name:
                    continue
                source_label = f"{part_name}：{card_name}"  # or 卡片名稱 or 套裝來源
                for item_id, item in self.parsed_items.items():
                    if item["name"] == card_name and item_id in self.equipment_data:
                        block_text = self.equipment_data[item_id]
                        grade = self.input_fields[f"{part_name}_階級"].currentIndex()
                        slot_id = self.refine_parts[part_name]["slot"]
                        effects = parse_lua_effects_with_variables(
                            block_text,
                            refine_inputs,
                            get_values,
                            grade,
                            unit_map=unit_map,
                            size_map=size_map,
                            effect_map=effect_map,
                            hide_unrecognized=self.hide_unrecognized_checkbox.isChecked(),
                            hide_physical=self.hide_physical_checkbox.isChecked(),
                            hide_magical=self.hide_magical_checkbox.isChecked(),
                            current_location_slot=slot_id    
                        )

                        filtered = self.filter_effects(effects)
                        for line in filtered:
                            if not line.strip():
                                continue
                            parsed = self.try_extract_effect(line)
                            if parsed:
                                key, value, unit = parsed
                                key = self.normalize_effect_key(key)
                                # 建立效果來源清單
                                effect_dict.setdefault((key, unit), []).append((value, source_label))
                            else:
                                text = line.strip()
                                if text:
                                    key = self.normalize_effect_key(text)

                                    # ✅ 純文字效果也寫入 effect_dict
                                    # value = 0, unit = ""
                                    effect_dict.setdefault((key, ""), []).append((0, source_label))
                                
            # ▶️ 詞條處理（如果有手動輸入）
            if "note" in ui:
                note_text = ui["note"].toPlainText().strip()
                if note_text:
                    grade = self.input_fields[f"{part_name}_階級"].currentIndex()
                    slot_id = self.refine_parts[part_name]["slot"]
                    source_label = f"{part_name}：詞條"

                    effects = parse_lua_effects_with_variables(
                        note_text,
                        refine_inputs,
                        get_values,
                        grade,
                        unit_map=unit_map,
                        size_map=size_map,
                        effect_map=effect_map,
                        hide_unrecognized=self.hide_unrecognized_checkbox.isChecked(),
                        hide_physical=self.hide_physical_checkbox.isChecked(),
                        hide_magical=self.hide_magical_checkbox.isChecked(),
                        current_location_slot=slot_id
                    )

                    filtered = self.filter_effects(effects)
                    for line in filtered:
                        if not line.strip():
                            continue
                        parsed = self.try_extract_effect(line)
                        if parsed:
                            key, value, unit = parsed
                            key = self.normalize_effect_key(key)

                            # 建立效果來源清單
                            effect_dict.setdefault((key, unit), []).append((value, source_label))
                        else:
                            text = line.strip()
                            if text:
                                key = self.normalize_effect_key(text)

                                # ✅ 純文字效果也寫入 effect_dict
                                # value = 0, unit = ""
                                effect_dict.setdefault((key, ""), []).append((0, source_label))

        # ▶️ 加入技能增益（例如料理等）
        for skill_name, entry in all_skill_entries.items():
            checkbox = self.skill_checkboxes.get(skill_name)
            if not checkbox or not checkbox.isChecked():
                continue  # 沒有勾選就跳過

            code_block = "\n".join(entry["code"])
            effects = parse_lua_effects_with_variables(
                code_block,
                refine_inputs,
                get_values,
                grade=0,
                unit_map=unit_map,
                size_map=size_map,
                effect_map=effect_map,
                hide_unrecognized=self.hide_unrecognized_checkbox.isChecked(),
                hide_physical=self.hide_physical_checkbox.isChecked(),
                hide_magical=self.hide_magical_checkbox.isChecked(),
                current_location_slot=None
            )

            source_label = f"{entry.get('type', '技能')}：{skill_name}"

            for line in self.filter_effects(effects):
                if not line.strip():
                    continue
                parsed = self.try_extract_effect(line)
                if parsed:
                    key, value, unit = parsed
                    key = self.normalize_effect_key(key)
                    effect_dict.setdefault((key, unit), []).append((value, source_label))
                    



        triggered_combos = set()
        combo_effects_all = []  # 用來儲存套裝效果（供分頁顯示）
        equipped_ids = set()  # 蒐集所有裝備物品ID（含卡片）

        # 先收集所有裝備 ID
        for part_name, ui in self.refine_inputs_ui.items():
            equip_name = ui["equip"].text().strip()
            if equip_name:
                for item_id, item in self.parsed_items.items():
                    if item["name"] == equip_name:
                        equipped_ids.add(item_id)
            for card_input in ui["cards"]:
                card_name = card_input.text().strip()
                if card_name:
                    for item_id, item in self.parsed_items.items():
                        if item["name"] == card_name:
                            equipped_ids.add(item_id)


        # 掃描每個裝備，看是否有 Combiitem 欄位
        for item_id in equipped_ids:
            block_text = self.equipment_data.get(item_id)
            if not block_text:
                continue
            combi_ids = extract_combi_ids(block_text)
            for combi_id in combi_ids:
                if combi_id in triggered_combos:
                    continue
                combo_block = self.equipment_data.get(combi_id)
                if not combo_block:
                    continue
                combo_items = extract_combo_items(combo_block)
                if combo_items.issubset(equipped_ids):
                    # ✅ 套裝條件成立，觸發效果
                    triggered_combos.add(combi_id)

                    # ✅ 生成完整的 grade dict（每個部位的 slot 與階級）
                    grade = {
                        self.refine_parts[part]["slot"]: self.input_fields[f"{part}_階級"].currentIndex()
                        for part in self.refine_parts
                    }

                    # 取得當前觸發套裝的部位 slot
                    slot_id = self.refine_parts[part_name]["slot"]

                    # 呼叫效果解析，傳入完整的 grade dict
                    effects = parse_lua_effects_with_variables(
                        combo_block,
                        refine_inputs,
                        get_values,
                        grade,  # ✅ 改為 dict
                        unit_map=unit_map,
                        size_map=size_map,
                        effect_map=effect_map,
                        hide_unrecognized=self.hide_unrecognized_checkbox.isChecked(),
                        hide_physical=self.hide_physical_checkbox.isChecked(),
                        hide_magical=self.hide_magical_checkbox.isChecked(),
                        current_location_slot=slot_id  
                    )

                    filtered = self.filter_effects(effects)
                    show_source = self.show_combo_source_checkbox.isChecked()
                    combo_items = extract_combo_items(combo_block)


                    # 將 itemid 映射成名稱
                    combo_item_names = []
                    for iid in combo_items:
                        name = self.parsed_items.get(iid, {}).get("name", f"ID:{iid}")
                        combo_item_names.append(f"[{name}]")

                    source_label = "、".join(combo_item_names) if combo_item_names else f"套裝ID {combi_id}"

                    if show_source:
                        combo_effects_all.append(f"🧩 套裝來源：{source_label}")
                        for line in filtered:
                            combo_effects_all.append(f"  {line}")
                            
                    else:
                        combo_effects_all.extend(filtered)# 加入縮排以便辨識
                        
                    for line in filtered:
                        m = re.match(r"(.+?) ([+\-]?\d+(?:\.\d+)?)(%|秒)?", line)
                        if m:
                            key = m[1].strip()
                            val = float(m[2]) if '.' in m[2] else int(m[2])
                            unit = m[3] if m[3] else ""
                            if not unit and "時間" in key:
                                unit = "秒"

                            source = f"套裝：{source_label}"  # ✅ 直接用來源變數
                            effect_dict.setdefault((key, unit), []).append((val, source))
                            self.effect_dict_raw = effect_dict  # 取能力值暫存
                            self.update_stat_bonus_display()    # ✅ 加這行：裝備資料全部準備好後更新素質顯示

                            




                    # 原本的解析邏輯也照做
                        parsed = self.try_extract_effect(line)
                        if parsed:
                            key, value, unit = parsed
                            key = self.normalize_effect_key(key)
                            #source_label = part_name  # or 卡片名稱 or 套裝來源

                            # 建立效果來源清單
                            #effect_dict.setdefault((key, unit), []).append((value, source_label))



        #被動技能給的BUFF
        
        skillbuff_path = os.path.join("data", "skillbuff.lua")
        skillbuff_effect_dict = self.apply_skill_buffs_into_effect_dict(skillbuff_path, enabled_skill_levels, refine_inputs, get_values, grade)
        for key, entries in skillbuff_effect_dict.items():
            if key in effect_dict:
                effect_dict[key].extend(entries)                
            else:
                effect_dict[key] = entries.copy()                
        for key, entries in skillbuff_effect_dict.items():
            if key in base_effect_dict:                
                base_effect_dict[key].extend(entries)
            else:                
                base_effect_dict[key] = entries.copy()

        
        # ✅ 排序合併結果
        combined = []
        show_source = self.show_combo_source_checkbox.isChecked()
        
        sort_mode = self.sort_mode_combo.currentText()

        if sort_mode == "來源順序":
            sorted_effect_items = effect_dict.items()

        elif sort_mode == "依名稱":
            def sort_key(item):
                (key, unit) = item[0]
                return (key, unit)
            sorted_effect_items = sorted(effect_dict.items(), key=sort_key)

        elif sort_mode in custom_sort_orders:  # ✅ 通用處理
            def sort_key(item):
                (key, unit) = item[0]
                return (get_custom_sort_value(key, sort_mode), key)
            sorted_effect_items = sorted(effect_dict.items(), key=sort_key)

        else:
            sorted_effect_items = effect_dict.items()  # fallback 保底



        # 排序應用在效果總表輸出
        for (key, unit), entries in sorted_effect_items:
        



            total = sum(val for val, _ in entries)
            #print(f"[DEBUG] key={key} unit={unit} total={total}")
            if unit == "秒":
                total = round(total, 1)
                value_str = f"{total:.1f}{unit}"
            else:
                value_str = f"{total:+g}{unit}"

            if show_source:
                for val, source in entries:
                    val_str = f"{val:.1f}{unit}" if unit == "秒" else f"{val:+g}{unit}"
                    combined.append(f"{key} {val_str}  ← 〔{source}〕")
                combined.append(f"🧮↳ {key} {value_str}  ← 〔總和〕🧮")
            else:
                combined.append(f"{key} {value_str}")
        



        #self.total_effect_text.setPlainText("\n".join(combined))
        #self.combo_effect_text.setPlainText("\n".join(combo_effects_all))
        self.total_combined_raw = combined  # 儲存未過濾的總表行
        self.safe_update_textbox(self.total_effect_text, "\n".join(combined))
        self.safe_update_textbox(self.combo_effect_text, "\n".join(combo_effects_all))
        # 不論有沒有套裝效果、裝備或技能，一律記錄 effect_dict
        self.effect_dict_raw = effect_dict
        self.base_effect_dict_raw = base_effect_dict#只紀錄裝備基礎能力不含精煉套裝
        self.update_stat_bonus_display()
        #運算

        #self.replace_custom_calc_content()


        

    def trigger_total_effect_update(self):#統一計算處理，除非特殊狀態不然不要單獨處理效果       
        '''
        計算統一處理，除非特殊狀態不然不要單獨處理效果
        '''        
        self.display_all_effects()
        self.display_item_info()        
        self.replace_custom_calc_content()
        self.update_dex_int_half_note()
        self.jobsphp_display()
        self.update_total_effect_display()#過濾總效果顯示



    def parse_equipment_blocks(self, content):
        import re

        blocks = {}
        pattern = re.compile(r"\[(\d+)\]\s*=\s*{", re.MULTILINE)
        matches = list(pattern.finditer(content))
        total = len(matches)
        print(f"📦 開始解析裝備區塊，共 {total} 筆資料")

        for i, match in enumerate(matches):
            item_id = int(match.group(1))
            start = match.end()
            end = matches[i+1].start() if i+1 < len(matches) else len(content)

            block_text = content[start:end].strip()

            # 加回完整大括號包裹，確保 block 格式正確
            block_text_full = "{" + block_text.rstrip(",") + "}"

            blocks[item_id] = block_text_full
            print(f"  → 處理中 {i+1}/{total} 筆", end="\r")
        print(f"\n✅ 解析完成，共 {len(blocks)} 筆裝備。")
        return blocks




        
    def closeEvent(self, event):
        reply = QMessageBox.question(
            self,
            "確認關閉",
            "確定要關閉應用程式嗎？未儲存的變更將會遺失。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()

    
    def load_saved_inputs(self, filename="saved_inputs.json"):
        if not os.path.exists(filename):
            return
        # 🔹 暫停所有 widget 的 signal
        for widget in self.findChildren(QWidget):
            widget.blockSignals(True)

        with open(filename, "r", encoding="utf-8") as f:
            saved_data = json.load(f)

        # input_fields 的 QComboBox 或 QLineEdit
        for key, val in saved_data.items():
            if key in self.input_fields:
                field = self.input_fields[key]
                if isinstance(field, QComboBox):
                    index = field.findText(val)
                    if index != -1:
                        field.setCurrentIndex(index)
                else:
                    field.setText(val)

        # 裝備與卡片欄位
        for part, info in self.refine_inputs_ui.items():
            equip_key = f"{part}_equip"
            if equip_key in saved_data:
                info["equip"].setText(saved_data[equip_key])
            for i in range(4):
                card_key = f"{part}_card{i+1}"
                if card_key in saved_data:
                    info["cards"][i].setText(saved_data[card_key])

        #怪物相關欄位
        self.size_box.setCurrentIndex(saved_data.get("size", 0))
        self.element_box.setCurrentIndex(saved_data.get("element", 0))
        self.race_box.setCurrentIndex(saved_data.get("race", 0))
        self.class_box.setCurrentIndex(saved_data.get("class", 0))
        self.def_input.setText(saved_data.get("def", "0"))
        self.defc_input.setText(saved_data.get("defc", "0"))
        self.res_input.setText(saved_data.get("res", "0"))
        self.mdef_input.setText(saved_data.get("mdef", "0"))
        self.mdefc_input.setText(saved_data.get("mdefc", "0"))
        self.mres_input.setText(saved_data.get("mres", "0"))
        self.element_lv_input.setText(saved_data.get("element_lv", "1"))
        
        # 🔹 恢復 signal
        for widget in self.findChildren(QWidget):
            widget.blockSignals(False)

        # 輸入空白並清空技能強制更新
        self.skill_filter_input.setText(" ")
        self.skill_filter_input.clear()
        # 技能欄位
        if "skill_name" in saved_data:
            index = self.skill_box.findText(saved_data["skill_name"])
            if index != -1:
                self.skill_box.setCurrentIndex(index)
        # note 欄位最後處理
        for part, info in self.refine_inputs_ui.items():
            note_key = f"{part}_note"
            if note_key in saved_data and "note" in info:
                info["note"].setPlainText(saved_data[note_key])

        
    def save_preset(self, part):
        info = self.refine_inputs_ui[part]
        name = info["preset_input"].text().strip()
        if not name:
            QMessageBox.warning(self, "錯誤", "請輸入儲存名稱")
            return
        data = {
            "equip": info["equip"].text(),
            "cards": [c.text() for c in info["cards"]],
            "note": info["note"].toPlainText(),
            "refine": info["refine"].text(),
            "grade": info["grade"].currentText()
        }

        path = os.path.join(self.preset_folder, f"{part}_{name}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        # 儲存成功後清空名稱輸入欄位
        info["preset_input"].clear()
        
        self.refresh_presets(part)

    def load_preset(self, part, preset_name):
        info = self.refine_inputs_ui[part]

        # 直接用對話框選到的 preset_name，而不是 combo.currentText()
        name = preset_name
        if not name:
            return

        path = os.path.join(self.preset_folder, f"{part}_{name}.json")
        if not os.path.exists(path):
            return

        # 確認是否覆蓋
        if info["equip"].text() or any(c.text() for c in info["cards"]) or info["note"].toPlainText():
            reply = QMessageBox.question(
                self, "覆蓋確認",
                f"目前 {part} 已有資料，確定要覆蓋？",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        
        info["preset_input"].setText(preset_name)#讀取檔名傳入名稱
        
        info["equip"].setText(data.get("equip", ""))
        for i in range(4):
            info["cards"][i].setText(data.get("cards", [""]*4)[i])
        info["note"].setPlainText(data.get("note", ""))

        # ✅ 這些也是保留
        info["refine"].setText(data.get("refine", "0"))
        grade = data.get("grade", "N")
        index = info["grade"].findText(grade)
        if index >= 0:
            info["grade"].setCurrentIndex(index)

        #self.display_item_info()
        self.trigger_total_effect_update()

    def delete_preset(self, part, name):
        if not name:
            return

        path = os.path.join(self.preset_folder, f"{part}_{name}.json")
        if os.path.exists(path):
            os.remove(path)

        # 刪掉後刷新一下清單（現在只是回傳清單，不會更新 combo）
        self.refresh_presets(part)


    def refresh_presets(self, part):
        files = os.listdir(self.preset_folder)
        names = [
            f[len(part)+1:-5]
            for f in files
            if f.startswith(part + "_") and f.endswith(".json")
        ]
        return sorted(names)

    def open_save_manager(self, part_name):
        save_list = self.refresh_presets(part_name)
        dialog = SaveManagerDialog(part_name, save_list, self.delete_preset, self)

        # 取得按鈕的螢幕座標
        button = self.refine_inputs_ui[part_name]["manage_btn"]
        global_pos = button.mapToGlobal(QPoint(0, 0))

        # 預設：放在按鈕右側
        x = global_pos.x() + button.width() + 10
        y = global_pos.y()

        # 取得母視窗範圍（相對螢幕的座標）
        parent_geom = self.geometry()
        parent_x, parent_y = parent_geom.x(), parent_geom.y()
        parent_width, parent_height = parent_geom.width(), parent_geom.height()

        # 對話框大小（已固定 300x400）
        dialog_width, dialog_height = dialog.width(), dialog.height()

        # ✅ 限制在母視窗範圍內
        if x + dialog_width > parent_x + parent_width:
            x = global_pos.x() - dialog_width - 50
        if y + dialog_height > parent_y + parent_height:
            y = parent_y + parent_height - dialog_height - 50
        if y < parent_y:  # 不要超出上邊界
            y = parent_y + 10

        # 移動到最終位置
        dialog.move(x, y)

        if dialog.exec():
            selected = dialog.selected_save
            if selected:
                self.load_preset(part_name, selected)










    def apply_selected_equip(self):

        if not self.current_edit_part:
            print("❌ 沒有選擇編輯部位")
            return

        selected_item = self.name_field.text().strip()
        if not selected_item:
            print("⚠️ 沒有選擇要套用的裝備")
            return

        part_name, field_type = self.current_edit_part.split(" - ")

        if part_name not in self.refine_inputs_ui:
            print(f"❌ 無法辨識部位：{part_name}")
            return

        ui = self.refine_inputs_ui[part_name]

        if field_type == "裝備":
            ui["equip"].setText(selected_item)
        elif field_type.startswith("卡片"):
            try:
                card_index = int(field_type[-1]) - 1
                if 0 <= card_index < 4:
                    ui["cards"][card_index].setText(selected_item)
                else:
                    print(f"❌ 卡片編號錯誤：{field_type}")
            except ValueError:
                print(f"❌ 無法解析卡片編號：{field_type}")
        else:
            print(f"❌ 不支援欄位類型：{field_type}")
            return
        

        # 最後刷新畫面
        
        #self.display_item_info()
        self.replace_custom_calc_content()

    def apply_result_to_note(self):

        if not self.current_edit_part:
            print("❌ 沒有選擇編輯部位")
            return

        part_name, field_type = self.current_edit_part.split(" - ")
        print(f"目前部位:{part_name} 位置:{field_type}")
        if field_type != "詞條":
            print("⚠️ 當前非詞條欄 ，無法套用語法")
            return

        if part_name not in self.refine_inputs_ui:
            print(f"❌ 無法辨識部位：{part_name}")
            return

        note_widget = self.refine_inputs_ui[part_name].get("note")
        if note_widget:
            new_text = self.result_output.toPlainText().strip()
            note_widget.setPlainText(new_text)
            print(f"✅ 已將語法套用至「{part_name}」詞條欄")
        else:
            print(f"❌ 找不到 {part_name} 的詞條欄位")
        
        # 最後刷新畫面
        #self.display_item_info()
        self.replace_custom_calc_content()




    def clear_selected_field(self):
        if not self.current_edit_part:
            print("❌ 沒有選擇編輯欄位")
            return

        part_name, field_type = self.current_edit_part.split(" - ")

        if part_name not in self.refine_inputs_ui:
            print(f"❌ 找不到部位：{part_name}")
            return

        ui = self.refine_inputs_ui[part_name]

        if field_type == "裝備":
            ui["equip"].clear()

        elif field_type.startswith("卡片"):
            try:
                idx = int(field_type[-1]) - 1
                if 0 <= idx < 4:
                    ui["cards"][idx].clear()
                else:
                    print("❌ 卡片欄位編號超出範圍")
            except ValueError:
                print("❌ 卡片欄位解析失敗")

        elif field_type == "詞條":
            if "note" in ui:
                ui["note"].clear()
            else:
                print(f"❌ 找不到詞條欄位於：{part_name}")

        else:
            print(f"❌ 不支援的欄位類型：{field_type}")
            return

        self.display_item_info()

        if field_type == "詞條":
            self.result_output.clear()



    def save_compare_base(self):
        self.auto_compare_checkbox.setChecked(False)
        self.trigger_total_effect_update()#儲存前強制運算
        text = self.custom_calc_box.toPlainText()
        with open("compare_base.txt", "w", encoding="utf-8") as f:
            f.write(text)
        QMessageBox.information(self, "儲存成功", "已儲存目前數據作為比對基準。")
        self.auto_compare_checkbox.setChecked(True)

    def compare_with_base(self):
        import re

        def parse_block(text):
            d = {}
            for line in text.splitlines():
                if ":" in line:
                    key, val = line.split(":", 1)
                    val = val.strip().replace(",", "")
                    num = re.findall(r"[-]?\d+\.?\d*", val)
                    if num:
                        d[key.strip()] = val
            return d

        try:
            with open("compare_base.txt", "r", encoding="utf-8") as f:
                base_text = f.read()
        except FileNotFoundError:
            QMessageBox.warning(self, "錯誤", "找不到比對基準，請先儲存。")
            return

        current_text = self.custom_calc_box.toPlainText()
        base = parse_block(base_text)
        current_lines = current_text.splitlines()

        def format_number(val_str):
            val = float(re.findall(r"[-]?\d+\.?\d*", val_str)[0])
            suffix = "%" if "%" in val_str else ""
            if val.is_integer():
                return f"{int(val):,}{suffix}"
            else:
                return f"{val:.2f}{suffix}"
                
        skip_compare_keys = {"技能公式", "技能說明"}  # 可加更多你不想比對的 key
        
        new_output = []
        for line in current_lines:
            if ":" not in line:
                new_output.append(line)
                continue

            key_part, val_part = line.split(":", 1)
            key = key_part.strip()
            val_clean = val_part.strip().replace(",", "")
            
            if key in skip_compare_keys:
                new_output.append(line)  # 直接加入不比對
                continue

            if key in base:
                try:
                    old_val_str = base[key]
                    new_val_str = val_clean

                    old_val = float(re.findall(r"[-]?\d+\.?\d*", old_val_str)[0])
                    new_val = float(re.findall(r"[-]?\d+\.?\d*", new_val_str)[0])

                    if old_val != new_val:
                        diff = new_val - old_val
                        sign = "+" if diff > 0 else "-"
                        suffix = "%" if "%" in new_val_str else ""
                        old_fmt = format_number(old_val_str)
                        new_fmt = format_number(new_val_str)

                        # 總傷害顯示百分比與差額
                        if "傷害" in key:
                            percent_val = abs(diff / old_val * 100)
                            diff_fmt = f"{sign}{int(abs(diff)):,} / {sign}{percent_val:.2f}%"
                            
                        elif "技能倍率" in key:
                            percent_val = abs(diff / old_val * 100)
                            diff_fmt = f"{sign}{int(abs(diff)):,}{suffix} / {sign}{percent_val:.2f}%"

                        else:
                            diff_fmt = f"{sign}{abs(diff):.0f}{suffix}"

                        arrow_str = f"{old_fmt} → {new_fmt}"
                        # 保留前綴與原有空格
                        prefix = line[:line.index(":") + 1]
                        suffix_space = val_part[:len(val_part) - len(val_part.lstrip())]
                        # 調整：括號前留 2 空格
                        new_line = f"{prefix}{suffix_space}{arrow_str}  ({diff_fmt})"
                        new_output.append(new_line)
                    else:
                        new_output.append(line)
                except Exception as e:
                    new_output.append(f"{line}  ⛔錯誤: {e}")

            else:
                new_output.append(line)

        self.custom_calc_box.setHtml(self.generate_highlighted_html(new_output))

        #self.custom_calc_box.setPlainText("\n".join(new_output))


    def dataloading(self, mode: str = "online_only"):
        """
        mode:
          - "online_only"   : 只用線上來源；但若本地已存在就不下載。缺檔才下載；失敗不回退本地
          - "local_only"    : 完全不碰網路；若缺檔才走本地解譯
        需求：專案中已定義 decompile_lub(), parse_lub_file(), self.parse_equipment_blocks()
        """
        import os, sys, re, subprocess, time
        from urllib.request import urlopen, Request
        from urllib.error import URLError, HTTPError

        self.current_file = None

        # === 線上來源（已整理好的 Lua） ===
        ONLINE_ITEMINFO_URL = "https://z2911902.github.io/ROItemSearchApp/data/iteminfo_new.lua"
        ONLINE_EQUIP_URL    = "https://z2911902.github.io/ROItemSearchApp/data/EquipmentProperties.lua"
        ONLINE_EnchantList_URL = "https://z2911902.github.io/ROItemSearchApp/data/EnchantList.lua"
        ONLINE_ItemDBNameTbl_URL = "https://z2911902.github.io/ROItemSearchApp/data/ItemDBNameTbl.lua"
        ONLINE_ItemReformSystem_URL = "https://z2911902.github.io/ROItemSearchApp/data/ItemReformSystem.lua"
        ONLINE_skill_tree_URL = "https://z2911902.github.io/ROItemSearchApp/data/skill_tree.yml"
        ONLINE_skilltreeview_URL = "https://z2911902.github.io/ROItemSearchApp/data/skilltreeview.lub"
        ONLINE_skillneme_URL = "https://z2911902.github.io/ROItemSearchApp/data/skillneme.csv"
        ONLINE_skillbuff_URL = "https://z2911902.github.io/ROItemSearchApp/data/skillbuff.lua"
        ONLINE_skill_entries_URL = "https://z2911902.github.io/ROItemSearchApp/data/all_skill_entries.py"
        ONLINE_job_dict_URL = "https://z2911902.github.io/ROItemSearchApp/data/job_dict.py"
        ONLINE_EnchantName_URL = "https://z2911902.github.io/ROItemSearchApp/data/EnchantName.lua"

        # === 路徑設定 ===
        if getattr(sys, 'frozen', False):
            BASE_DIR = os.path.dirname(sys.executable)
        else:
            BASE_DIR = os.path.dirname(os.path.abspath(__file__))

        data_dir = os.path.join(BASE_DIR, "data")
        os.makedirs(data_dir, exist_ok=True)
        iteminfo_path      = os.path.join(data_dir, "iteminfo_new.lua")
        equipment_lua_path = os.path.join(data_dir, "EquipmentProperties.lua")
        EnchantList_path  = os.path.join(data_dir, "EnchantList.lua")
        ItemDBNameTbl_path  = os.path.join(data_dir, "ItemDBNameTbl.lua")
        ItemReformSystem_path  = os.path.join(data_dir, "ItemReformSystem.lua")
        skill_tree_path  = os.path.join(data_dir, "skill_tree.yml")
        skilltreeview_path  = os.path.join(data_dir, "skilltreeview.lub")
        skillneme_path  = os.path.join(data_dir, "skillneme.csv")        
        skillbuff_path  = os.path.join(data_dir, "skillbuff.lua")
        skill_entries_path  = os.path.join(data_dir, "all_skill_entries.py")
        job_dict_path  = os.path.join(data_dir, "job_dict.py")
        EnchantName_path  = os.path.join(data_dir, "EnchantName.lua")
        

        # === 內嵌小工具 ===
        def _fmt_bytes(n: int) -> str:
            if n < 1024: return f"{n} B"
            if n < 1024**2: return f"{n/1024:.1f} KB"
            if n < 1024**3: return f"{n/1024**2:.2f} MB"
            return f"{n/1024**3:.2f} GB"

        def _progress_percent_line(done, total, speed_bps):
            if total and total > 0:
                percent = done / total * 100.0
                if speed_bps and speed_bps > 0:
                    eta = max(int((total - done) / speed_bps), 0)
                    return f"{percent:6.2f}%  { _fmt_bytes(done) } / { _fmt_bytes(total) }  { _fmt_bytes(int(speed_bps)) }/s  ETA {eta}s"
                else:
                    return f"{percent:6.2f}%  { _fmt_bytes(done) } / { _fmt_bytes(total) }"
            else:
                if speed_bps and speed_bps > 0:
                    return f"--.--%  { _fmt_bytes(done) } / ?  { _fmt_bytes(int(speed_bps)) }/s"
                else:
                    return f"--.--%  { _fmt_bytes(done) } / ?"

        def _download_with_progress(url: str, dest_path: str, timeout=30) -> bool:
            import time
            import ssl, certifi
            ssl._create_default_https_context = lambda: ssl.create_default_context(cafile=certifi.where())
            print(f"🌐 下載：{url}")
            req = Request(url, headers={"User-Agent": "ROItemSearchApp-Updater/1.2"})
            try:
                with urlopen(req, timeout=timeout) as resp:
                    # 取得 Content-Length（可能沒有）
                    try:
                        total = getattr(resp, "length", None) or int(resp.getheader("Content-Length") or 0)
                    except Exception:
                        total = 0

                    tmp = dest_path + ".tmp"
                    start = time.time()
                    done = 0
                    chunk = 64 * 1024  # 64KB

                    with open(tmp, "wb") as f:
                        while True:
                            data = resp.read(chunk)
                            if not data:
                                break
                            f.write(data)
                            done += len(data)

                            # 計算並用「同一行覆寫」呈現（與 parse_lub_file 的做法一致）
                            elapsed = max(time.time() - start, 1e-6)
                            speed = done / elapsed
                            line = _progress_percent_line(done, total, speed)
                            print(line, end="\r")  # 👈 只這行關鍵：同一行覆寫

                    print()  # 👈 下載結束補一個換行

                    # 基本健檢：避免 404 HTML
                    try:
                        with open(tmp, "rb") as tf:
                            head = tf.read(4096).decode("utf-8", errors="ignore").lower()
                            if "<html" in head:
                                print("❌ 下載內容疑似 HTML 錯誤頁，放棄覆蓋")
                                try: os.remove(tmp)
                                except: pass
                                return False
                    except Exception as e:
                        print(f"⚠️ 健檢失敗（但檔案已下載）：{e}")

                    os.replace(tmp, dest_path)
                    print(f"✅ 已覆蓋：{os.path.relpath(dest_path, BASE_DIR)}  (總計 { _fmt_bytes(done) })")
                    return True

            except (URLError, HTTPError) as e:
                print(f"❌ 下載失敗：{e}")
            except Exception as e:
                print(f"❌ 下載例外：{e}")
            return False



        def _looks_like_file_quick(path: str) -> bool:
            """根據副檔名做快速檢查，避免把下載後的 HTML/錯誤當成合法檔案。"""
            ext = os.path.splitext(path)[1].lower()

            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    txt = f.read(4096).lower()
            except:
                return False

            # --- 檢查是否 HTML（常見錯誤：下載失敗 → 拿到 404 HTML 頁面）---
            if "<html" in txt or "<!doctype html" in txt:
                return False

            # --- 不同副檔名分類判斷 ---
            if ext in (".lua", ".lub"):
                # Lua / Lub
                return any(k in txt for k in ("return", "=", "{", "iteminfo", "equipmentproperties"))

            elif ext == ".yml":
                # YAML
                return any(c in txt for c in (":", "-", "true", "false"))

            elif ext == ".csv":
                # CSV
                return ("," in txt or ";" in txt) and "\n" in txt

            else:
                # 未知類型 → 保守返回 True（你可改成 False）
                return True

        def _try_online_for(targets):
            """targets: [(url, dest_path), ...]；回傳是否成功至少一個"""
            updated = False
            for url, dest in targets:
                ok = _download_with_progress(url, dest)
                if ok and not _looks_like_file_quick(dest):
                    print(f"⚠️ 檔案格式可疑（非 Lua？）：{os.path.basename(dest)}")
                updated = updated or ok
            return updated

        # === 本地（GRF 解出/反編譯/整理）流程子函式（供回退/重建用） ===
        GRFCL_EXE    = os.path.join(BASE_DIR, "APP", "GrfCL.exe")
        GRF_PATH     = r"C:\Program Files (x86)\Gravity\RagnarokOnline\data.grf"
        UNLUAC_JAR   = os.path.join(BASE_DIR, "APP", "unluac.jar")        
        

        def extract_lub_from_grf(relative_path: str) -> bool:
            """從 GRF 解出指定 LUB 檔案。relative_path 必須像：
               data\\LuaFiles514\\Lua Files\\Enchant\\EnchantList.lub
            """
            if not os.path.exists(GRFCL_EXE):
                print(f"找不到 GrfCL.exe：{GRFCL_EXE}")
                return False

            print(f"📦 正在從 GRF 解壓：{relative_path}")
            result = subprocess.run([
                GRFCL_EXE,
                "-open", GRF_PATH,
                "-extractFolder", ".",
                relative_path,
                "-exit"
            ], cwd=BASE_DIR, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            if result.returncode != 0:
                print("❌ 解壓失敗：")
                print(result.stderr)
                return False

            print("✅ 解壓完成")
            return True


        def run_unluac(lub_file, lua_file):
            os.makedirs(data_dir, exist_ok=True)
            with open(lua_file, "w", encoding="utf-8") as out:
                subprocess.run(["java", "-jar", UNLUAC_JAR, lub_file], stdout=out, stderr=subprocess.DEVNULL)

        def split_local_variables(code: str) -> str:
            pattern = re.compile(r'^(\s*)local\s+([\w\s,]+?)\s*=\s*([^\n]+)$', re.MULTILINE)
            def replacer(m):
                indent, var_str, val_str = m.group(1), m.group(2), m.group(3)
                vars_ = [v.strip() for v in var_str.split(',')]
                vals_ = [v.strip() for v in val_str.split(',')]
                lines = []
                for i, var in enumerate(vars_):
                    val = vals_[i] if i < len(vals_) else 'nil'
                    lines.append(f"{indent}local {var} = {val}")
                return '\n'.join(lines)
            return pattern.sub(replacer, code)

        def flatten_array_fields(code: str) -> str:
            pattern = re.compile(r'^(\s*)(\w+)\s*=\s*\{\s*\n((?:\s*\d+\s*,?\n)+)(\s*)\}', re.MULTILINE)
            def replacer(m):
                indent, key, values_block = m.group(1), m.group(2), m.group(3)
                values = [v.strip().strip(',') for v in values_block.strip().splitlines() if v.strip()]
                return f"{indent}{key} = {{ {', '.join(values)} }}"
            return pattern.sub(replacer, code)

        def remove_specific_blocks(code: str, block_names) -> str:
            for name in block_names:
                pattern = re.compile(rf'{name}\s*=\s*\{{.*?\n\}}', re.DOTALL)
                code = pattern.sub('', code)
            return code

        def clean_lua_format(lua_file: str):
            with open(lua_file, "r", encoding="utf-8") as f:
                code = f.read()
            code = split_local_variables(code)
            code = flatten_array_fields(code)
            code = remove_specific_blocks(code, ["SkillGroup", "RefiningBonus", "GradeBonus"])
            with open(lua_file, "w", encoding="utf-8") as f:
                f.write(code)


        def local_fill_missing():
            """本地方式補齊缺檔（有就不動）。"""

            # --- iteminfo_new.lub（使用 decompile_lub） ---
            if not os.path.exists(iteminfo_path):
                lub_path = r"C:\Program Files (x86)\Gravity\RagnarokOnline\System\iteminfo_new.lub"
                print(f"⚙️ 反編譯 {lub_path} → {iteminfo_path}")
                if not decompile_lub(lub_path, iteminfo_path):
                    print("❌ 反編譯 iteminfo 失敗")
                    return False
            else:
                print("✅ iteminfo_new.lua 已存在，略過反編譯")

            # --- EquipmentProperties.lub（使用 unluac） ---
            if not os.path.exists(equipment_lua_path):
                print("📦 解出 EquipmentProperties.lub...")
                equip_lub_rel = r"data\LuaFiles514\Lua Files\EquipmentProperties\EquipmentProperties.lub"
                if not extract_lub_from_grf(equip_lub_rel):
                    print("❌ 解壓 EquipmentProperties.lub 失敗")
                    return False

                # GRF 解出後實際 LUB 檔案位置
                equip_lub_src = os.path.join(BASE_DIR, equip_lub_rel)

                print("🧩 正在反編譯 unluac...")
                run_unluac(equip_lub_src, equipment_lua_path)

                print("🧹 正在整理 Lua 格式...")
                clean_lua_format(equipment_lua_path)
            else:
                print("✅ EquipmentProperties.lua 已存在")

            # --- EnchantList.lub（使用 decompile_lub） ---
            if not os.path.exists(EnchantList_path):
                print("📦 解出 EnchantList.lub...")
                ench_rel = r"data\LuaFiles514\Lua Files\Enchant\EnchantList.lub"
                if extract_lub_from_grf(ench_rel):
                    ench_src = os.path.join(BASE_DIR, ench_rel)
                    print("🧩 使用 luadec 反編譯 EnchantList...")
                    if not decompile_lub(ench_src, EnchantList_path):
                        print("❌ 反編譯 EnchantList 失敗")
                        return False
            else:
                print("✅ EnchantList.lua 已存在")

            # --- ItemReformSystem.lub（使用 decompile_lub） ---
            if not os.path.exists(ItemReformSystem_path):
                print("📦 解出 ItemReformSystem.lub...")
                ench_rel = r"data\LuaFiles514\Lua Files\ItemReform\ItemReformSystem.lub"
                if extract_lub_from_grf(ench_rel):
                    ench_src = os.path.join(BASE_DIR, ench_rel)
                    print("🧩 使用 luadec 反編譯 ItemReformSystem...")
                    if not decompile_lub(ench_src, ItemReformSystem_path):
                        print("❌ 反編譯 ItemReformSystem 失敗")
                        return False
            else:
                print("✅ ItemReformSystem.lua 已存在")

            # --- ItemDBNameTbl.lub（使用 unluac） ---
            if not os.path.exists(ItemDBNameTbl_path):
                print("📦 解出 ItemDBNameTbl.lub...")
                db_rel = r"data\LuaFiles514\Lua Files\ItemDBNameTbl.lub"
                if extract_lub_from_grf(db_rel):
                    db_src = os.path.join(BASE_DIR, db_rel)
                    print("🧩 使用 unluac 反編譯 ItemDBNameTbl...")
                    run_unluac(db_src, ItemDBNameTbl_path)
            else:
                print("✅ ItemDBNameTbl.lua 已存在")

            # --- 全部完成後刪除 GRF 解出來的暫存 LuaFiles514 ---
            temp_folder = os.path.join(BASE_DIR, "data", "LuaFiles514")
            if os.path.exists(temp_folder):
                try:
                    import shutil
                    shutil.rmtree(temp_folder)
                    print(f"🗑️ 已刪除暫存資料夾：{temp_folder}")
                except Exception as e:
                    print(f"⚠️ 刪除暫存資料夾失敗：{e}")
            return True



        # === 判斷缺檔 ===
        miss_item  = not os.path.exists(iteminfo_path)
        miss_equip = not os.path.exists(equipment_lua_path)
        miss_EnchantList  = not os.path.exists(EnchantList_path)
        miss_ItemDBNameTbl  = not os.path.exists(ItemDBNameTbl_path)
        miss_ItemReformSystem  = not os.path.exists(ItemReformSystem_path)
        miss_skill_tree  = not os.path.exists(skill_tree_path)
        miss_skilltreeview  = not os.path.exists(skilltreeview_path)
        miss_skillneme = not os.path.exists(skillneme_path)
        miss_skillbuff = not os.path.exists(skillbuff_path)
        miss_skill_entries = not os.path.exists(skill_entries_path)
        miss_job_dict = not os.path.exists(job_dict_path)
        miss_EnchantName = not os.path.exists(EnchantName_path)
        


        # === 模式分流 ===
        if mode == "local_only":
            print(f"編譯方式 📖 本機模式")
            if not (os.path.exists(iteminfo_path) and os.path.exists(equipment_lua_path) and os.path.exists(EnchantList_path) and os.path.exists(ItemDBNameTbl_path) and os.path.exists(ItemReformSystem_path)):
                if not local_fill_missing():
                    print("❌ 本地補齊失敗"); return
        else:
            print(f"編譯方式 ☁️ 線上模式")
            # 只線上：若本地已存在就不下載；只有缺檔才下載。失敗則停止。            
            targets = []
            if miss_item:  targets.append((ONLINE_ITEMINFO_URL, iteminfo_path))
            if miss_equip: targets.append((ONLINE_EQUIP_URL,    equipment_lua_path))
            if miss_EnchantList: targets.append((ONLINE_EnchantList_URL,    EnchantList_path))
            if miss_ItemDBNameTbl: targets.append((ONLINE_ItemDBNameTbl_URL,    ItemDBNameTbl_path))
            if miss_ItemReformSystem: targets.append((ONLINE_ItemReformSystem_URL,    ItemReformSystem_path))
            if miss_skill_tree: targets.append((ONLINE_skill_tree_URL,    skill_tree_path))
            if miss_skilltreeview: targets.append((ONLINE_skilltreeview_URL,    skilltreeview_path))
            if miss_skillneme: targets.append((ONLINE_skillneme_URL,    skillneme_path))
            if miss_skillbuff: targets.append((ONLINE_skillbuff_URL,    skillbuff_path))
            if miss_skill_entries: targets.append((ONLINE_skill_entries_URL,    skill_entries_path))
            if miss_job_dict: targets.append((ONLINE_job_dict_URL,    job_dict_path))
            if miss_EnchantName: targets.append((ONLINE_EnchantName_URL,    EnchantName_path))
            
            if targets:
                _try_online_for(targets)
                # ⭐⭐⭐ 下載完成 → 強制重新啟動 ⭐⭐⭐
                print("🔄 線上資料已更新，重新啟動程式以避免舊快取造成錯誤...")

                import sys, os
                python = sys.executable
                os.execv(python, [python] + sys.argv)
            # 下載後再檢查一次，若仍缺則停止（不回退本地）
            required_files = [
                iteminfo_path,
                equipment_lua_path,
                EnchantList_path,
                ItemDBNameTbl_path,
                skill_tree_path,
                skilltreeview_path,
                skillneme_path,
                skillbuff_path,
                skill_entries_path,
                job_dict_path,
                EnchantName_path,
            ]
            if not all(os.path.exists(path) for path in required_files):
                print("❌ online_only 模式：仍有檔案缺失，停止")
                return

        # === 載入（無論來源） ===

        print("📖 載入 物品列表 ...")
        self.parsed_items = parse_lub_file(iteminfo_path)
        print("📖 載入 載入物品效果...")
        with open(equipment_lua_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.equipment_data = self.parse_equipment_blocks(content)
        print("📖 載入 技能清單...")
        load_skill_map("data/skillneme.csv") #讀取SKILL列表
        self.lua_text = load_skill_delay_lua("data/skilldelaylist.lua")#讀取技能延遲
        self.parsed_items = resolve_name_conflicts(self.parsed_items ,self.equipment_data)#重複物品名稱加上id
        return self.parsed_items

    def rebuild_skill_tab(self):
        """
        依照最新 all_skill_entries 重新生成技能/料理勾選區域
        （完全保留你原本 UI 的格式與邏輯）
        """

        # 1️⃣ 清除舊的 checkbox
        while self.skill_checkbox_layout.count():
            item = self.skill_checkbox_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)

        self.skill_checkboxes.clear()
        self.exclusive_groups.clear()

        # 2️⃣ 使用最新資料重建 UI
        from ItemSearchApp import DataRegistry
        all_skill_entries = DataRegistry.loaded_data["skills"]

        for name, data in all_skill_entries.items():

            checkbox = QCheckBox(f"{data['type']} {name}")
            self.skill_checkboxes[name] = checkbox
            self.skill_checkbox_layout.addWidget(checkbox)

            # 保留原本事件
            checkbox.stateChanged.connect(self.clear_global_state)
            checkbox.stateChanged.connect(self.trigger_total_effect_update)

            # exclusive 群組
            if "exclusive" in data:
                group = data["exclusive"]

                if group not in self.exclusive_groups:
                    self.exclusive_groups[group] = []

                self.exclusive_groups[group].append(checkbox)

                checkbox.toggled.connect(
                    lambda checked, c=checkbox, g=group:
                    self.handle_exclusive_toggle(c, g, checked)
                )

        print("✓ Skill/料理區塊已根據最新資料重新生成")

    def reload_job_list(self):
        """
        依照 DataRegistry.loaded_data['jobs'] 重新填入 JOB 下拉選單
        """
        if "JOB" not in self.input_fields:
            return  # 尚未初始化 UI

        combo: QComboBox = self.input_fields["JOB"]
        combo.blockSignals(True)  # 避免觸發 change 事件

        combo.clear()

        jobs = DataRegistry.loaded_data.get("jobs", {})

        for job_id, job_info in sorted(jobs.items()):
            combo.addItem(job_info["name"], job_id)

        combo.blockSignals(False)
        print("✓ JOB 下拉選單已重新載入")




    def refresh_skill_list(self):
        # 搜尋字（只過濾，不排序）
        query = ""
        if hasattr(self, "skill_search_input"):
            query = self.skill_search_input.text().strip().lower()

        # 目前職業 skill id
        job_id = self.input_fields["JOB"].currentData()
        skill_job_id = job_dict.get(job_id, {}).get("id")

        job_skills = []
        other_skills = []

        # ❗ 關鍵：完全依 all_skill_entries 原始順序走
        for name, data in all_skill_entries.items():
            # 搜尋過濾（不改順序）
            if query:
                hay = f"{data.get('type','')} {name}".lower()
                if query not in hay:
                    continue

            if skill_job_id in data.get("id", []):
                job_skills.append(name)
            else:
                other_skills.append(name)

        # 清空 layout（不刪 checkbox）
        while self.skill_checkbox_layout.count():
            item = self.skill_checkbox_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)

        # ===== 本職技能（原始順序）=====
        for name in job_skills:
            self.skill_checkbox_layout.addWidget(self.skill_checkboxes[name])

        # ===== 分隔線 =====
        if job_skills and other_skills:
            line = QFrame()
            line.setFrameShape(QFrame.HLine)
            line.setFrameShadow(QFrame.Sunken)
            line.setLineWidth(1)
            line.setStyleSheet("""
            QFrame {
                margin-top: 6px;
                margin-bottom: 6px;
            }
            """)
            self.skill_checkbox_layout.addWidget(line)

        # ===== 其他技能（原始順序）=====
        for name in other_skills:
            self.skill_checkbox_layout.addWidget(self.skill_checkboxes[name])







    def do_update(self):
        if not self._remote_version:
            QMessageBox.warning(self, "提示", "請先點『檢查更新』。")
            return

        ver = self._remote_version.strip()
        zip_url = ZIP_URL_TEMPLATE.format(ver=ver)

        updater_path = os.path.join(os.getcwd(), UPDATER_EXE)
        if not os.path.exists(updater_path):
            QMessageBox.critical(self, "更新失敗", f"找不到更新程式：{UPDATER_EXE}")
            return

        # 你要呼叫的格式：
        # update.exe  <zip_url>  ItemSearchApp.exe
        try:
            subprocess.Popen([updater_path, zip_url, TARGET_EXE], cwd=os.getcwd())
        except Exception as e:
            QMessageBox.critical(self, "更新失敗", f"啟動更新程式失敗：\n{e}")
            return

        # 更新器啟動後，主程式自己關掉比較乾淨（讓 updater 覆蓋檔案）
        self.close()

    def check_update(self):
        def fetch_release_notes(owner: str, repo: str, tag: str, timeout: int = 8) -> str:
            url = f"https://api.github.com/repos/{owner}/{repo}/releases/tags/{tag}"
            headers = {
                "Accept": "application/vnd.github+json",
                # 可加 UA，避免某些環境被擋
                "User-Agent": "ROItemSearchApp-Updater"
            }
            r = requests.get(url, headers=headers, timeout=timeout)
            r.raise_for_status()
            data = r.json()
            return data.get("body", "") or ""

        app_dir = os.getcwd()

        try:
            #local_ver = read_local_version(app_dir)
            local_ver = Version
        except Exception as e:
            QMessageBox.critical(self, "更新檢查失敗", f"讀取本機 version.txt 失敗：\n{e}")
            return

        try:
            remote_ver = read_remote_version(REMOTE_VERSION_URL)
        except Exception as e:
            QMessageBox.critical(self, "更新檢查失敗", f"讀取遠端 version.txt 失敗：\n{e}")
            return

        self._remote_version = remote_ver

        cmp_result = compare_versions(remote_ver, local_ver)

        if cmp_result > 0:
            release_url = f"https://github.com/z2911902/ROItemSearchApp/releases/tag/{remote_ver}"

            try:
                notes = fetch_release_notes("z2911902", "ROItemSearchApp", str(remote_ver))
            except Exception as e:
                notes = f"⚠ 無法取得更新內容：{e}\n\n你仍可前往 Release 頁面查看：\n{release_url}"

            dlg = UpdateDialog(
                local_ver=str(local_ver),
                remote_ver=str(remote_ver),
                notes_md=notes,
                release_url=release_url,
                parent=self
            )

            if dlg.exec() == QDialog.Accepted:
                self.do_update()



        elif cmp_result == 0:
            #self.action_do_update.setEnabled(False)
            QMessageBox.information(self, "已是最新版本", f"目前版本：{local_ver}\n最新版本：{remote_ver}")
        else:
            # 遠端版本比本地還小（可能你本機是測試版）
            #self.action_do_update.setEnabled(False)
            QMessageBox.information(
                self,
                "版本較新",
                f"目前版本：{local_ver}\n遠端版本：{remote_ver}\n\n你本機版本比遠端新。"
            )





    def __init__(self):
        
        #self.dataloading()#讀取並載入物品跟裝備能力
        
        super().__init__()
        self.setWindowTitle("RO物品查詢計算工具")
        self.current_edit_part = None  # 用來記錄目前正在編輯的部位名稱

        self.preset_folder = "equip_presets"
        os.makedirs(self.preset_folder, exist_ok=True)

        self.load_config()#讀取偏好設定

        
        # UI 元件初始化


        self.parsed_items = {}#預先初始化
        self.current_file = None # 尚未開啟任何檔案
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("輸入物品編號、名稱或內容...")
        
        self.search_input.textChanged.connect(self.update_combobox)

        self.result_box = QComboBox()
        self.result_box.currentIndexChanged.connect(self.display_item_info)
        self.result_box.currentIndexChanged.connect(self.update_total_effect_display)#過濾總效果顯示

        self.name_field = QLineEdit()
        self.name_field.setReadOnly(True)

        self.kr_name_field = QLineEdit()
        self.kr_name_field.setReadOnly(True)

        self.slot_field = QLineEdit()
        self.slot_field.setReadOnly(True)

        self.desc_text = QTextEdit()
        self.desc_text.setReadOnly(True)

        self.Combi_text = QTextEdit()
        self.Combi_text.setReadOnly(True)

        self.combi_raw_text = QTextEdit()
        self.desc_text.setReadOnly(True)

        self.equip_text = QTextEdit()
        self.equip_text.setReadOnly(True)

        self.sim_effect_label = QLabel("效果解析")
        #self.sim_effect_text = QTextEdit()
        #self.sim_effect_text.setReadOnly(True)






        # 建立輸入欄位
        self.input_fields = {}

        self.stat_fields = {
            "BaseLv": 11, "JobLv": 12, "JOB": 19, "MHP": 200 , "MSP": 202 ,
            "STR": 32, "AGI": 33, "VIT": 34, "INT": 35, "DEX": 36, "LUK": 37,
            "POW": 255, "STA": 256, "WIS": 257, "SPL": 258, "CON": 259, "CRT": 260,"石碑開啟格數": 263 ,"石碑精煉": 264
            
        }

        self.refine_parts = {
            # === 裝備部位 ===
            "頭上":   {"slot": 10, "type": "裝備"},
            "頭中":   {"slot": 11, "type": "裝備"},
            "頭下":   {"slot": 12, "type": "裝備"},
            "鎧甲":   {"slot": 2,  "type": "裝備"},
            "右手(武器)":   {"slot": 4,  "type": "裝備"},
            "左手(盾牌)":   {"slot": 3,  "type": "裝備"},
            "披肩":   {"slot": 5,  "type": "裝備"},
            "鞋子":   {"slot": 6,  "type": "裝備"},
            "飾品右": {"slot": 7,  "type": "裝備"},
            "飾品左": {"slot": 8,  "type": "裝備"},

            # === 影子裝備 ===
            "影子鎧甲":   {"slot": 30, "type": "影子"},
            "影子手套":   {"slot": 31, "type": "影子"},
            "影子盾牌":     {"slot": 32, "type": "影子"},
            "影子鞋子":   {"slot": 33, "type": "影子"},
            "影子耳環右": {"slot": 34, "type": "影子"},
            "影子墬子左": {"slot": 35, "type": "影子"},

            # === 服飾部位 ===
            "服飾頭上":   {"slot": 41, "type": "服飾"},
            "服飾頭中":   {"slot": 42, "type": "服飾"},
            "服飾頭下":   {"slot": 43, "type": "服飾"},
            "服飾斗篷":   {"slot": 44, "type": "服飾"},
            
            # === 石碑/寵物部位 === slot部位自定義，遊戲未定義此位置。
            "符文石碑":   {"slot": 100, "type": "石碑"},
            "寵物蛋":   {"slot": 101, "type": "寵物"},
            # === 技能欄位 === slot部位自定義，遊戲未定義此位置。
            "技能":   {"slot": 102, "type": "技能"},
        }
        def get_part_slot_from_source(source_str):
            for part_name, info in self.refine_parts.items():
                if part_name in source_str:
                    return info["slot"]
            return 9999  # 未知來源排最後

        # 三欄主視窗布局
        main_layout = QHBoxLayout()
        
        # ===== 左側：角色能力與裝備分頁 =====
        # 1. 建立分頁元件
        tab_widget = QTabWidget()
        tab_widget.setFixedWidth(340)
        # 2. 為每個分頁建立 ScrollArea → 放內容
        # === 分頁1：角色能力值 ===
        char_scroll = QScrollArea()
        char_scroll.setWidgetResizable(True)
        char_inner = QWidget()
        char_layout = QVBoxLayout(char_inner)
        char_scroll.setWidget(char_inner)
        char_layout.addWidget(QLabel("角色能力值"))
        # 儲存加成顯示欄位
        self.stat_bonus_labels = {}

        for label, gid in self.stat_fields.items():
            # ✅ MHP / MSP 同一行 + 加滑桿（HP% / SP%）
            if label == "MHP":
                row_layout = QHBoxLayout()
                row_layout.setAlignment(Qt.AlignLeft)

                # --- MHP ---
                mhp_label = QLabel("MHP")
                mhp_label.setFixedWidth(50)
                row_layout.addWidget(mhp_label)

                mhp_field = QLineEdit()
                mhp_field.setPlaceholderText("MHP (get(200))")
                mhp_field.textChanged.connect(self.trigger_total_effect_update)
                mhp_field.setMaximumWidth(100)
                self.input_fields["MHP"] = mhp_field
                row_layout.addWidget(mhp_field)

                # --- MSP ---
                msp_label = QLabel("MSP")
                msp_label.setFixedWidth(50)
                row_layout.addWidget(msp_label)

                msp_field = QLineEdit()
                msp_field.setPlaceholderText("MSP (get(202))")
                msp_field.textChanged.connect(self.trigger_total_effect_update)
                msp_field.setMaximumWidth(100)
                self.input_fields["MSP"] = msp_field
                row_layout.addWidget(msp_field)

                char_layout.addLayout(row_layout)

                # ===== 滑桿區：HP% / SP% =====
                self.hp_percent_label = QLabel("HP 100%：0 / 0")
                char_layout.addWidget(self.hp_percent_label)

                self.hp_slider = QSlider(Qt.Horizontal)
                self.hp_slider.setRange(0, 100)
                self.hp_slider.setValue(100)
                char_layout.addWidget(self.hp_slider)

                self.sp_percent_label = QLabel("SP 100%：0 / 0")
                char_layout.addWidget(self.sp_percent_label)

                self.sp_slider = QSlider(Qt.Horizontal)
                self.sp_slider.setRange(0, 100)
                self.sp_slider.setValue(100)
                char_layout.addWidget(self.sp_slider)
                self.hp_sp_widgets = [
                    mhp_label,
                    mhp_field,
                    msp_label,
                    msp_field,
                    self.hp_percent_label,
                    self.hp_slider,
                    self.sp_percent_label,
                    self.sp_slider,
                ]
                self.MHP_MSP_widgets = [
                    self.hp_percent_label,
                    self.sp_percent_label,
                ]
                
                # ===== 4轉職業 HP/SP 表 =====
                self.jobhp = 0
                self.jobsp = 0

                def update_hp_sp_slider_visibility():
                    job_id = self.input_fields["JOB"].currentData()

                    job_info = job_dict.get(job_id, {})
                    widget = job_info.get("HP_SP_widget", False)
                    MHP_MSP = job_info.get("MHP_MSP", False)

                    for w in self.hp_sp_widgets:
                        w.setVisible(widget)
                    for w in self.MHP_MSP_widgets:
                        w.setVisible(MHP_MSP)

                

                def update_job_4th_hpsp_bonus():
                    job_id = self.input_fields["JOB"].currentData()

                    try:
                        base_lv = int(self.input_fields["BaseLv"].text())
                    except:
                        base_lv = None

                    self.jobhp = 0
                    self.jobsp = 0

                    if base_lv and 201 <= base_lv <= 260:
                        idx = base_lv - 201
                        job_table = job_4th_hpsp.get(job_id)

                        if job_table:
                            hp_list = job_table.get("HP", [])
                            sp_list = job_table.get("SP", [])
                            if idx < len(hp_list):
                                self.jobhp = hp_list[idx]
                            if idx < len(sp_list):
                                self.jobsp = sp_list[idx]
                

                def _safe_int(text):
                    try:
                        return int(text)
                    except:
                        return 0 
                
                def fmt_stat(prefix: str, now, maxv, pct,
                             prefix_w: int = 6,
                             value_w: int = 9,
                             pct_w: int = 4) -> str:
                    """
                    格式化狀態顯示字串（HP / SP）
                    全形字寬=2，半形字寬=1
                    """

                    def visual_length(s: str) -> int:
                        width = 0
                        for c in s:
                            width += 2 if ord(c) > 255 else 1
                        return width

                    def pad(text: str, total_width: int) -> str:
                        space_count = total_width - visual_length(text)
                        return text + " " * max(space_count, 0)

                    return (
                        pad(prefix, prefix_w)
                        + pad(str(now), value_w)
                        + "/ "
                        + pad(str(maxv), value_w)
                        + pad(f"{pct}%", pct_w)
                    )

                def update_hp_sp_slider_display():
                    update_job_4th_hpsp_bonus()
                    
                    mhp_input = _safe_int(self.input_fields["MHP"].text())
                    msp_input = _safe_int(self.input_fields["MSP"].text())
                    HP = globals().get("HP", 0)
                    SP = globals().get("SP", 0)
                    HPPercent = globals().get("HPPercent", 0)
                    SPPercent = globals().get("SPPercent", 0)
                    VIT = globals().get("total_VIT", 0)
                    INT = globals().get("total_INT", 0)
                    #print(f"{self.jobhp} {self.jobsp} {HP} {SP} {HPPercent} {SPPercent} {VIT} {INT} {mhp_input} {msp_input}")

                    HP = HP * (1+HPPercent/100)
                    SP = SP * (1+SPPercent/100)
                    jobmaxhp = int(self.jobhp * ((100+VIT)/100) * (1+HPPercent/100) + HP)
                    jobmaxsp = int(self.jobsp * ((100+INT)/100) * (1+SPPercent/100) + SP)

                    # 使用者沒輸入或輸入 0 → 用職業表
                    globals()["MHP"] = mhp_input if mhp_input > 0 else jobmaxhp
                    globals()["MSP"] = msp_input if msp_input > 0 else jobmaxsp

                    hp_pct = self.hp_slider.value()
                    sp_pct = self.sp_slider.value()

                    globals()["MHP_NOW"] = int(MHP * hp_pct / 100) if MHP > 0 else 0
                    globals()["MSP_NOW"] = int(MSP * sp_pct / 100) if MSP > 0 else 0

                    # self.hp_percent_label.setText(f"HP：{MHP_NOW} / {MHP}  {hp_pct}%")
                    # self.sp_percent_label.setText(f"SP：{MSP_NOW} / {MSP}  {sp_pct}%")
                    self.hp_percent_label.setText(fmt_stat("HP：", MHP_NOW, MHP, hp_pct))
                    self.sp_percent_label.setText(fmt_stat("SP：", MSP_NOW, MSP, sp_pct))

                    # self.hp_percent_label.setText(hp_text)
                    # self.sp_percent_label.setText(sp_text)
                    self.hp_percent_label.setStyleSheet(
                        "font-family: Consolas, Menlo, monospace;"
                        "font-size: 18px;"
                    )
                    self.sp_percent_label.setStyleSheet(
                        "font-family: Consolas, Menlo, monospace;"
                        "font-size: 18px;"
                    )

                    
                def jobsphp_display():
                    update_hp_sp_slider_visibility()
                    update_hp_sp_slider_display()

                self.jobsphp_display = jobsphp_display#註冊到全域函數

                # 連動：滑桿、以及 MHP/MSP 被改時都要更新顯示
                self.hp_slider.valueChanged.connect(update_hp_sp_slider_display)                
                self.sp_slider.valueChanged.connect(update_hp_sp_slider_display)
                self.input_fields["MHP"].textChanged.connect(update_hp_sp_slider_display)
                self.input_fields["MSP"].textChanged.connect(update_hp_sp_slider_display)
                self.input_fields["JOB"].currentIndexChanged.connect(update_hp_sp_slider_display)
                

                self.input_fields["BaseLv"].textChanged.connect(update_hp_sp_slider_display)


                update_hp_sp_slider_display()
                continue



            # ✅ 已經在 MHP 那邊做掉了，MSP 這輪跳過
            if label == "MSP":
                continue
            row_layout = QHBoxLayout()
            row_layout.setAlignment(Qt.AlignLeft)
            row_label = QLabel(label)
            row_label.setFixedWidth(50)  # 可自行調整寬度
            row_layout.addWidget(row_label)
            
            if label == "JOB":
                combo = QComboBox()
                for job_id, job_info in sorted(job_dict.items()):
                    combo.addItem(job_info["name"], job_id)
                combo.currentIndexChanged.connect(self.trigger_total_effect_update)         
                #combo.currentIndexChanged.connect(filter_skills) #移動到filter_skills後面註冊
                combo.setMaximumWidth(210)#調整寬度
                self.input_fields[label] = combo
                row_layout.addWidget(combo)
                # ★ 新增：技能樹按鈕
                self.skill_btn = QPushButton("技能表")
                self.skill_btn.setFixedWidth(60)  # 控制按鈕大小
                self.skill_btn.clicked.connect(self.open_skill_tree)  # 呼叫你現有的技能樹視窗
                row_layout.addWidget(self.skill_btn)
            else:
                field = QLineEdit()
                field.setPlaceholderText(f"{label} (get({gid}))")
                field.textChanged.connect(self.trigger_total_effect_update)
                field.setMaximumWidth(50)#調整寬度
                self.input_fields[label] = field
                row_layout.addWidget(field)
                
                stat_names = ["STR", "AGI", "VIT", "INT", "DEX", "LUK", "POW", "STA", "WIS", "SPL", "CON", "CRT"]#ROCalculator
                if label in stat_names:
                    bonus_label = QLabel("= ?")
                    bonus_label.setFixedWidth(160)
                    bonus_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    row_layout.addWidget(bonus_label)
                    self.stat_bonus_labels[label] = bonus_label
                    if label == "VIT":
                        self.input_fields["VIT"].textChanged.connect(update_hp_sp_slider_display)
                    if label == "INT":
                        self.input_fields["INT"].textChanged.connect(update_hp_sp_slider_display)
                
                if label == "JobLv":
                    bonus_label = QLabel("(預留，目前無作用。)")
                    row_layout.addWidget(bonus_label)

                # ✅ 如果是 BaseLv，就加一個 QLabel 顯示素質點
                if label == "BaseLv":
                    self.stat_point_label = QLabel("（素質點：-）")
                    self.stat_point_label.setFixedWidth(180)
                    row_layout.addWidget(self.stat_point_label)

                    def update_stat_point():#取自ROCalculator
                        try:
                            lv = int(self.input_fields["BaseLv"].text())
                        except:
                            self.stat_point_label.setText("（素質點：-）")
                            return

                        # 直接從 JOB 下拉選單取得職業 ID
                        job_id = self.input_fields["JOB"].currentData()

                        # 計算素質點
                        total_pts = calculate_stat_points(lv, job_id)

                        used_pts = sum([
                            raising_stats(self.input_fields["STR"].text()),
                            raising_stats(self.input_fields["AGI"].text()),
                            raising_stats(self.input_fields["VIT"].text()),
                            raising_stats(self.input_fields["INT"].text()),
                            raising_stats(self.input_fields["DEX"].text()),
                            raising_stats(self.input_fields["LUK"].text())
                        ])
                        remain_pts = total_pts - used_pts
                        total_tpts = get_total_tstat_points(lv)
                        tstat_used = self.calculate_tstat_total_used()
                        tstat_remain = total_tpts - tstat_used

                        #self.stat_point_label.setText(f"（素質點：{total_pts} / 已用 {used_pts} / 剩餘 {remain_pts}｜特性點：{total_tpts} / 已用 {tstat_used} / 剩餘 {tstat_remain}）")
                        self.stat_point_label.setText(f"剩餘素質 {remain_pts}｜特性 {tstat_remain}")
                    # ❗ BaseLv 輸入時更新
                    field.textChanged.connect(update_stat_point)
                    self._update_stat_point_callback = update_stat_point  # ✅ 暫存回呼
                 # 🟣 隱藏「石碑」相關欄位
                if label in ["石碑開啟格數", "石碑精煉"]:
                    row_label.setVisible(False)
                    field.setVisible(False)
                    continue  # 不需要顯示在角色能力區     

            
            char_layout.addLayout(row_layout)
            char_layout.setAlignment(Qt.AlignTop)


        tab_widget.addTab(char_scroll, "角色能力值")
        update_hp_sp_slider_visibility()
        
        # === 分頁2：裝備設定 ===
        equip_scroll = QScrollArea()
        equip_scroll.setWidgetResizable(True)
        equip_inner = QWidget()
        equip_layout = QVBoxLayout(equip_inner)
        equip_scroll.setWidget(equip_inner)


        equip_layout.addWidget(QLabel("裝備與卡片設定"))

        self.refine_inputs_ui = {}
        visible_types = ["裝備", "影子", "服飾", "石碑", "寵物", "技能"]

        for part_name, info in self.refine_parts.items():
            if info["type"] not in visible_types:
                continue

            slot_id = info["slot"]
            
            def make_focus_func_focus(part_label, input_field, label_name):
                '''
                鎖定選擇的裝備、卡片、詞條欄位，如果為詞條就轉到函數分頁
                '''
                def focus(event):
                    self.clear_current_edit()

                    self.current_edit_part = f"{part_label} - {label_name}"
                    self.current_edit_label.setText(f"目前部位：{part_label} - {label_name}")
                    self.unsync_button.setVisible(True)
                    self.unsync_button2.setVisible(True)
                    self.apply_to_note_button.setVisible(True)
                    self.clear_field_button2.setVisible(True)
                    self.apply_equip_button.setVisible(True)
                    self.clear_field_button.setVisible(True)
                    
                    self.set_edit_lock(part_label, label_name)
                    input_field.setStyleSheet("background-color: #ff0000;")  # 紅
                    self.search_input.setFocus()  # ✅ 把焦點移到搜尋欄
                    # ✅ 若不是詞條，就切回裝備查詢分頁
                    if label_name != "note":
                        self.tab_widget.setCurrentIndex(self.search_tab_index)

                    # ✅ 只有左邊欄位有文字時才清空搜尋欄位
                    if input_field.text().strip():
                        self.search_input.setText("")

                    text = input_field.text().strip()
                    if text:
                        # 搜尋對應的物品 ID
                        for idx in range(self.result_box.count()):
                            item_id = self.result_box.itemData(idx)
                            item = self.filtered_items.get(item_id)
                            if item and item["name"] == text and item_id in self.equipment_data:

                                self.result_box.setCurrentIndex(idx)
                                break


                    QLineEdit.mousePressEvent(input_field, event)
                return focus
                
            

            part_label = QLabel(part_name)
            equip_layout.addWidget(part_label)

            part_ui = {}
            #equip_row_layout = QHBoxLayout()
            
                                    # ▶️ 儲存 / 載入 / 下拉 / 刪除控制列
            preset_row = QHBoxLayout()

            preset_name_input = QLineEdit()
            preset_name_input.setPlaceholderText("輸入儲存名稱")
            preset_name_input.setFixedWidth(160)

            save_btn = QPushButton("儲存")
            save_btn.setFixedWidth(40)
            save_btn.clicked.connect(lambda _, p=part_name: self.save_preset(p))

            #preset_combo = QComboBox()
            #preset_combo.setFixedWidth(100)
            #preset_combo.currentIndexChanged.connect(lambda _, p=part_name: self.load_preset(p))
            manage_btn = QPushButton("讀取裝備")
            manage_btn.clicked.connect(lambda _, p=part_name: self.open_save_manager(p))
            part_ui["manage_btn"] = manage_btn


            #delete_btn = QPushButton("刪除")
            #delete_btn.setFixedWidth(40)
            #delete_btn.clicked.connect(lambda _, p=part_name: self.delete_preset(p))

            preset_row.addWidget(preset_name_input)
            preset_row.addWidget(save_btn)
            #preset_row.addWidget(preset_combo)
            #preset_row.addWidget(delete_btn)
            preset_row.addWidget(manage_btn)

            equip_layout.addLayout(preset_row)

            # 保存元件供操作
            part_ui["preset_input"] = preset_name_input
            #part_ui["preset_combo"] = preset_combo

            # ▶️ 裝備欄位 + 清空（加上 container 才能單獨隱藏）
            equip_container = QWidget()
            equip_row_layout = QHBoxLayout(equip_container)
            equip_row_layout.setContentsMargins(0, 0, 0, 0)

            equip_input = QLineEdit()
            equip_input.setReadOnly(True)

            if part_name == "符文石碑":
                equip_input.setPlaceholderText("石碑名稱")
            elif part_name == "寵物蛋":
                equip_input.setPlaceholderText("寵物名稱")
            else:
                equip_input.setPlaceholderText("裝備名稱")

            equip_input.setMinimumWidth(100)
            equip_input.mousePressEvent = make_focus_func_focus(part_name, equip_input, "裝備")

            clear_equip_btn = QPushButton("清空")
            clear_equip_btn.setFixedWidth(40)
            clear_equip_btn.clicked.connect(self.clear_global_state)
            clear_equip_btn.clicked.connect(lambda _, field=equip_input: [field.clear(), self.trigger_total_effect_update()])
            

            equip_row_layout.addWidget(equip_input)
            equip_row_layout.addWidget(clear_equip_btn)

            # ★ 加入 layout
            equip_layout.addWidget(equip_container)

            # ★ 存入 part_ui
            part_ui["equip"] = equip_input
            part_ui["equip_container"] = equip_container


            # ▶️ 精煉欄位
            refine_input = QLineEdit()
            refine_input.setPlaceholderText("精煉")
            refine_input.setMaximumWidth(40)
            refine_input.setText('0')            
            refine_input.textChanged.connect(self.trigger_total_effect_update)
            equip_row_layout.addWidget(refine_input)
            part_ui["refine"] = refine_input
            self.input_fields[part_name] = refine_input

            # ▶️ 階級下拉
            grade_combo = QComboBox()
            if part_name == "符文石碑":
                grade_combo.addItems(["0", "1", "2", "3", "4", "5", "6" ])
                grade_combo.setMaximumWidth(50)
            elif part_name == "寵物蛋":
                grade_combo.addItems(["非常陌生", "稍微陌生", "普通", "稍微親密", "非常親密"])
                grade_combo.setMaximumWidth(95)
            else:
                grade_combo.addItems(["N", "D", "C", "B", "A"])
                grade_combo.setMaximumWidth(50)            
            grade_combo.currentIndexChanged.connect(self.trigger_total_effect_update)
            equip_row_layout.addWidget(grade_combo)
            part_ui["grade"] = grade_combo
            self.input_fields[f"{part_name}_階級"] = grade_combo

            # 🟢 特例：符文石碑 → 同步階級與精煉到 stat_fields

            if part_name == "符文石碑":

                def sync_stone_slots_delayed():
                    val_field = self.refine_inputs_ui["符文石碑"]["grade"]
                    grade_text = val_field.currentText().strip()
                    try:
                        grade_val = int(grade_text)
                    except ValueError:
                        grade_val = val_field.currentIndex()

                    stone_slot_field = self.input_fields.get("石碑開啟格數")
                    if stone_slot_field:
                        stone_slot_field.blockSignals(True)
                        stone_slot_field.setText(str(grade_val))
                        stone_slot_field.blockSignals(False)
                    self.trigger_total_effect_update()
                    
                def sync_stone_slots(*_):
                    # 🔹 延遲一個事件循環再執行，確保取到更新後的值
                    QTimer.singleShot(0, sync_stone_slots_delayed)

                def sync_stone_refine():
                    val_field = self.refine_inputs_ui["符文石碑"]["refine"]
                    text_val = val_field.text().strip()
                    try:
                        val = int(text_val)
                    except ValueError:
                        val = 0

                    stone_refine_field = self.input_fields.get("石碑精煉")
                    if stone_refine_field:
                        stone_refine_field.blockSignals(True)
                        stone_refine_field.setText(str(val))
                        stone_refine_field.blockSignals(False)
                    self.trigger_total_effect_update()

                grade_combo.currentIndexChanged.connect(sync_stone_slots)
                refine_input.textChanged.connect(sync_stone_refine)

            

            # ▶️ 將裝備行 layout 加進主 layout
            #equip_layout.addLayout(equip_row_layout)

            # ▶️ 卡片欄位們 + 清空按鈕
            card_inputs = []
            for i in range(4):
                card_row_layout = QHBoxLayout()
                card_row_layout.setSpacing(0)
                card_row_layout.setContentsMargins(0, 0, 0, 0)
                card_input = QLineEdit()
                
                card_input.setReadOnly(True)
                card_input.setPlaceholderText(f"卡片 {i+1}")
                card_input.mousePressEvent = make_focus_func_focus(part_name, card_input, f"卡片{i+1}")

                clear_card_btn = QPushButton("清空")
                clear_card_btn.setFixedWidth(40)
                clear_card_btn.clicked.connect(self.clear_global_state)
                clear_card_btn.clicked.connect(lambda _, field=card_input: [field.clear(), self.trigger_total_effect_update()])
                
                card_row_layout.addWidget(card_input)
                card_row_layout.addWidget(clear_card_btn)

                # 把卡片欄整行加進主裝備 layout
                card_container = QWidget()
                card_container.setLayout(card_row_layout)
                equip_layout.addWidget(card_container)

                card_inputs.append(card_input)
                


            # ▶️ 詞條欄位（多行文字）+ 清空
            note_text = QTextEdit()
            note_text.setPlaceholderText("lua函數")
            note_text.setObjectName(f"{part_name}-函數")  # 例如 "頭上-詞條"
            note_text.setFixedSize(260, 20)  # ✅ 固定寬與高（寬度固定在300）
            note_text.setContentsMargins(0, 0, 0, 0)
            note_text.setReadOnly(True) 
            note_text.setVisible(False)
            note_text.textChanged.connect(self.on_function_text_changed)

            note_text_ui = QTextEdit()
            note_text_ui.setPlaceholderText("自訂詞條效果")
            note_text_ui.setObjectName(f"{part_name}-詞條")  # 例如 "頭上-詞條"
            note_text_ui.setFixedSize(260, 20)  # ✅ 固定寬與高（寬度固定在300）
            note_text_ui.setContentsMargins(0, 0, 0, 0)
            note_text_ui.setReadOnly(True) 
            note_text_ui.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            note_text_ui.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            note_text_ui.mousePressEvent = lambda event, p=part_name, w=note_text_ui , u=note_text: self.handle_note_text_clicked(event, p, w , u)
            

            
            clear_note_btn = QPushButton("清空")
            clear_note_btn.setFixedWidth(40)
            clear_note_btn.clicked.connect(self.clear_global_state)
            clear_note_btn.clicked.connect(lambda _, field=note_text: [field.clear() ,self.trigger_total_effect_update()])
            
            
            note_row_layout = QHBoxLayout()
            note_row_layout.setContentsMargins(0, 0, 0, 0)
            note_row_layout.setSpacing(5)
            note_row_layout.addWidget(note_text)
            note_row_layout.addWidget(note_text_ui)
            note_row_layout.addWidget(clear_note_btn)

            note_container = QWidget()
            note_container.setLayout(note_row_layout)
            note_container.setFixedWidth(300)  # ✅ 包裹容器也設定固定寬度

            equip_layout.addWidget(note_container)
            
            

            part_ui["note"] = note_text  # ✅ 儲存以便之後取用
            part_ui["cards"] = card_inputs
            part_ui["note_ui"] = note_text_ui
            
            

            self.refine_inputs_ui[part_name] = part_ui
            self.refresh_presets(part_name)

            # 🟢 特例：符文石碑 → 隱藏卡片與詞條欄位
            if part_name in ("符文石碑", "寵物蛋"):
                # 隱藏卡片欄位
                for c in part_ui["cards"]:
                    c.setVisible(False)
                    parent_layout = c.parentWidget()
                    if parent_layout:
                        parent_layout.setVisible(False)

                # 隱藏詞條區
                if "note" in part_ui:
                    part_ui["note"].setVisible(False)
                if "note_ui" in part_ui:
                    part_ui["note_ui"].setVisible(False)
                note_widget = part_ui["note"].parentWidget()
                if note_widget:
                    note_widget.setVisible(False)

                # 🧩 若是寵物蛋，再隱藏精煉欄位
                if part_name == "寵物蛋" and "refine" in part_ui:
                    refine_widget = part_ui["refine"]
                    refine_widget.setVisible(False)
                    refine_parent = refine_widget.parentWidget()
                    if refine_parent:
                        refine_widget.hide()  # 雙保險：同時呼叫 hide()
            #技能只顯示詞條
            if part_name == "技能":
                equip_widget = part_ui["equip"]
                equip_widget.setVisible(False)
                part_ui["equip_container"].setVisible(False)
                # 隱藏卡片欄位
                for c in part_ui["cards"]:
                    c.setVisible(False)
                    parent_layout = c.parentWidget()
                    if parent_layout:
                        parent_layout.setVisible(False)

                refine_widget = part_ui["refine"]
                refine_widget.setVisible(False)

                grade_widget = part_ui["grade"]
                grade_widget.setVisible(False)




        tab_widget.addTab(equip_scroll, "裝備設定")
        
        

        # === 新增技能分頁（含搜尋） ===
        skill_page = QWidget()
        skill_layout = QVBoxLayout(skill_page)

        # 搜尋欄位
        search_layout = QHBoxLayout()
        search_label = QLabel("🔍 搜尋技能/料理：")
        self.skill_search_bar = QLineEdit()
        self.skill_search_bar.setPlaceholderText("輸入技能/料理名稱...")
        self.skill_search_bar.textChanged.connect(self.filter_skill_list)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.skill_search_bar)
        skill_layout.addLayout(search_layout)

        # 技能清單區塊（可滾動）
        self.skill_checkbox_area = QWidget()
        self.skill_checkbox_layout = QVBoxLayout(self.skill_checkbox_area)
        self.skill_checkbox_layout.setAlignment(Qt.AlignTop)

        self.skill_checkboxes = {}
        self.exclusive_groups = {}   # { group_name: [checkbox1, checkbox2] }

        for name, data in all_skill_entries.items():
            checkbox = QCheckBox(f"{data['type']} {name}")
            self.skill_checkboxes[name] = checkbox

            #checkbox.stateChanged.connect(self.clear_global_state)
            checkbox.stateChanged.connect(self.trigger_total_effect_update)

            # 判斷此技能是否有 exclusive 群組
            if "exclusive" in data:
                group = data["exclusive"]
                self.exclusive_groups.setdefault(group, []).append(checkbox)

                # 連接 "可取消" 的互斥控制函數
                checkbox.toggled.connect(
                    lambda checked, c=checkbox, g=group: self.handle_exclusive_toggle(c, g, checked)
                )


        # ✅ 建完後，用排序/搜尋規則把 checkbox 加到 layout
        self.refresh_skill_list()

        self.input_fields["JOB"].currentIndexChanged.connect(self.refresh_skill_list)#註冊下拉職業清單依照職業排序

            

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.skill_checkbox_area)

        # ✅ 讓技能清單填滿底部空間
        skill_layout.addWidget(scroll, stretch=1)

        # 加入主分頁
        tab_widget.addTab(skill_page, "增益技能/料理")



        # 先把 tab_widget 存起來（可選）
        self.tab_widget = tab_widget

        # ✅ 用一個容器把「tab + 狀態」上下包在一起
        left_panel = QWidget()
        left_panel.setFixedWidth(340)  

        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(6)

        # 上：三個分頁
        left_layout.addWidget(self.tab_widget, stretch=1)

        # 下：狀態區
        self.status_box = QGroupBox("攻速/詠唱顯示 [括弧內為技能需求秒數]")
        self.status_box.setMinimumHeight(100)  
        status_layout = QVBoxLayout(self.status_box)

        # self.status_label = QLabel("（狀態顯示區）")
        # self.status_label.setWordWrap(True)
        # status_layout.addWidget(self.status_label)
        # === 計算素質無詠 ===
        
        self.DEX_INT_265_label = QLabel("無詠計算")
        status_layout.addWidget(self.DEX_INT_265_label)
        self.fix_label = QLabel("fix")
        status_layout.addWidget(self.fix_label)
        self.Delay_label = QLabel("Delay")
        status_layout.addWidget(self.Delay_label)
        self.ASPD_label = QLabel("ASPD")
        status_layout.addWidget(self.ASPD_label)
        self.cast_bar = CastBarWidget(self)#詠唱條
        status_layout.addWidget(self.cast_bar)
        left_layout.addWidget(self.status_box, stretch=0)

        # ✅ 只加 left_panel 進去
        main_layout.addWidget(left_panel, 2)


        

        # ===== 中間：裝備查詢區塊 =====
        middle_widget = QWidget()
        middle_layout = QVBoxLayout(middle_widget)
        # 建立 TabWidget
        self.tab_widget = QTabWidget()

        # ====== 原本裝備查詢頁 ======
        middle_widget = QWidget()
        middle_layout = QVBoxLayout(middle_widget)
        # ...原本裝備查詢內容塞進 middle_layout...
        middle_scroll = QScrollArea()
        middle_scroll.setWidgetResizable(True)
        middle_scroll.setWidget(middle_widget)
        middle_scroll.setFixedWidth(500)

        equip_tab = QWidget()
        equip_layout = QVBoxLayout(equip_tab)
        equip_layout.addWidget(middle_scroll)
        self.search_tab_index = self.tab_widget.addTab(equip_tab, "裝備查詢")


        # ▶️ 編輯狀態 + 解除同步按鈕 + 全域精煉選單
        edit_status_layout = QHBoxLayout()
        self.current_edit_label = QLabel("目前部位：")
        self.unsync_button = QPushButton("🔓解除鎖定")
        self.unsync_button.setVisible(False)
        self.unsync_button.clicked.connect(self.clear_global_state)
        self.unsync_button.clicked.connect(self.clear_current_edit)
        self.unsync_button.clicked.connect(lambda: (setattr(self, "_last_calc_state", None), self.trigger_total_effect_update()))
        # ▶️ 套用按鈕
        self.apply_equip_button = QPushButton("套用")
        self.apply_equip_button.clicked.connect(self.clear_global_state)
        self.apply_equip_button.clicked.connect(self.apply_selected_equip)     
        self.apply_equip_button.clicked.connect(lambda: (setattr(self, "_last_calc_state", None), self.trigger_total_effect_update()))
        self.apply_equip_button.setVisible(False)
        
        self.clear_field_button = QPushButton("清空")
        self.clear_field_button.clicked.connect(self.clear_global_state)
        self.clear_field_button.clicked.connect(self.clear_selected_field)  
        self.clear_field_button.clicked.connect(lambda: (setattr(self, "_last_calc_state", None), self.trigger_total_effect_update()))
        self.clear_field_button.setVisible(False)


        # ✅ 全域精煉與階級欄位
        self.global_refine_input = QLineEdit()
        self.global_refine_input.setPlaceholderText("全域精煉")
        self.global_refine_input.setMaximumWidth(40)

        self.global_grade_combo = QComboBox()
        self.global_grade_combo.addItems(["N", "D", "C", "B", "A"])
        self.global_grade_combo.setMaximumWidth(50)
        self.global_refine_input.textChanged.connect(self.display_item_info)
        self.global_grade_combo.currentIndexChanged.connect(self.display_item_info)

        # 預設隱藏（只有在未編輯狀態時顯示）
        self.global_refine_input.setVisible(True)
        self.global_grade_combo.setVisible(True)

        
        # 擺進橫向排版
        edit_status_layout.addWidget(self.current_edit_label)
        edit_status_layout.addWidget(self.clear_field_button)
        edit_status_layout.addWidget(self.apply_equip_button)
        edit_status_layout.addWidget(self.unsync_button)
        edit_status_layout.addWidget(self.global_refine_input)
        edit_status_layout.addWidget(self.global_grade_combo)

        middle_layout.addLayout(edit_status_layout)
        def add_labeled_row(layout, label_text, widget, label_width=80):
            row = QHBoxLayout()
            label = QLabel(label_text)
            label.setFixedWidth(label_width)
            label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            row.addWidget(label)
            row.addWidget(widget)
            layout.addLayout(row)

        # 使用函式新增橫向排列項目
        add_labeled_row(middle_layout, "查詢關鍵字", self.search_input)
        add_labeled_row(middle_layout, "符合項目", self.result_box)
        #add_labeled_row(middle_layout, "中文名稱", self.name_field)
        #add_labeled_row(middle_layout, "韓文名稱", self.kr_name_field)
        #add_labeled_row(middle_layout, "鑲嵌孔數", self.slot_field)
        #middle_layout.addWidget(QLabel("物品說明"))
        middle_layout.addWidget(self.desc_text)
        middle_layout.addWidget(QLabel("套裝清單："))
        self.Combi_text.setFixedHeight(160)
        middle_layout.addWidget(self.Combi_text)
        self.btn_recompile = QPushButton("重新取得物品列表")
        self.btn_recompile.clicked.connect(self.recompile)
        middle_layout.addWidget(self.btn_recompile)
        #self.btn_recompile.setVisible(False)#重新編譯先隱藏
        
       

        # ====== 技能指令分頁 ======
        function_tab = QWidget()
        function_layout = QVBoxLayout(function_tab)

        # 建立第1個橫向 layout（標籤 + 解鎖）
        edit_function_layout = QHBoxLayout()

        self.function_selector = QComboBox()
        self.function_selector.setMaximumWidth(200)
        self.update_function_selector()

        self.se_function = QLabel("選擇函數：")
        self.unsync_button2 = QPushButton("🔓解除鎖定")
        self.unsync_button2.setVisible(False)
        self.unsync_button2.clicked.connect(self.clear_global_state)
        self.unsync_button2.clicked.connect(self.clear_current_edit)
        self.unsync_button2.clicked.connect(lambda: (setattr(self, "_last_calc_state", None), self.trigger_total_effect_update()))
        self.apply_to_note_button = QPushButton("套用到詞條")
        self.apply_to_note_button.setVisible(False)
        self.apply_to_note_button.clicked.connect(self.clear_global_state)
        self.apply_to_note_button.clicked.connect(self.apply_result_to_note)
        self.apply_to_note_button.clicked.connect(lambda: (setattr(self, "_last_calc_state", None), self.trigger_total_effect_update()))



        
        self.clear_field_button2 = QPushButton("清空")
        self.clear_field_button2.clicked.connect(self.clear_global_state)
        self.clear_field_button2.clicked.connect(self.clear_selected_field)
        self.clear_field_button2.clicked.connect(lambda: (setattr(self, "_last_calc_state", None), self.trigger_total_effect_update()))
        
        self.clear_field_button2.setVisible(False)

        # 🔍 建立全域技能搜尋欄位（放在你想要的位置）
        self.skill_search_input = QLineEdit()
        self.skill_search_input.setPlaceholderText("🔍 搜尋技能")
        self.skill_search_input.setVisible(False)
        
        
        edit_function_layout.addWidget(self.se_function)
        edit_function_layout.addWidget(self.skill_search_input)
        edit_function_layout.addWidget(self.clear_field_button2)
        edit_function_layout.addWidget(self.apply_to_note_button)

        edit_function_layout.addWidget(self.unsync_button2)
        function_layout.addLayout(edit_function_layout)

        # ✅ 建立第2個橫向 layout（函數選單 + 參數欄位）
        edit_function_layout2 = QHBoxLayout()  # 你漏了這行

        edit_function_layout2.addWidget(self.function_selector)


        # ✅ 參數區改用 HBoxLayout
        self.param_layout = QHBoxLayout()
        self.param_widgets = []
        edit_function_layout2.addLayout(self.param_layout)

        function_layout.addLayout(edit_function_layout2)

        
        # 按鈕
        self.gen_button = QPushButton("產生")
        function_layout.addWidget(self.gen_button)
        # 結果輸出
        self.result_output = QTextEdit()
        #self.result_output.setReadOnly(True)
        function_layout.addWidget(QLabel("產生的語法："))
        function_layout.addWidget(self.result_output)

        # 加入這段到合適 layout 中（中間區塊）
        self.syntax_result_label = QLabel("🧠 語法解析結果：")
        self.syntax_result_box = QTextEdit()
        self.syntax_result_box.setReadOnly(True)

        function_layout.addWidget(self.syntax_result_label)
        function_layout.addWidget(self.syntax_result_box)

        # 分頁加入
        self.function_tab_index = self.tab_widget.addTab(function_tab, "函數指令")
        main_layout.addWidget(self.tab_widget)

        # 預先初始化一次

        





        # ===== 右側：模擬結果 + 裝備原始屬性 =====
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setWidget(right_widget)

        self.equip_text_label = QLabel("裝備屬性原始內容")
        right_layout.addWidget(self.equip_text_label)
        right_layout.addWidget(self.equip_text)
        self.equip_text.setFixedHeight(160)
        right_layout.addWidget(self.combi_raw_text)
        self.combi_raw_text.setFixedHeight(160)
        right_layout.addWidget(self.sim_effect_label)
        
        #right_layout.addWidget(self.sim_effect_text)
        # === 效果解析分頁（兩個頁籤） ===
        self.sim_tabs = QTabWidget()
        right_layout.addWidget(self.sim_tabs)

        # 分頁1：單件裝備效果
        self.sim_effect_text = QTextEdit()
        self.sim_effect_text.setReadOnly(True)
        self.sim_tabs.addTab(self.sim_effect_text, "目前裝備效果")

        # 分頁2：總合套裝效果
        self.combo_effect_text = QTextEdit()
        self.combo_effect_text.setReadOnly(True)
        self.sim_tabs.addTab(self.combo_effect_text, "整體套裝效果")
        
        
        # 建立 總效果分頁 的容器
        total_tab_layout = QVBoxLayout()
        total_filter_input_sort_mode_combo = QHBoxLayout()

        # 🔍 篩選輸入欄
        self.total_filter_input = QLineEdit()
        self.total_filter_input.setPlaceholderText("🔍 篩選總效果（例如：詠唱）")
        self.total_filter_input.textChanged.connect(self.update_total_effect_display)        
        total_filter_input_sort_mode_combo.addWidget(self.total_filter_input)
        
        # 排序方式下拉選單
        self.sort_mode_combo = QComboBox()
        self.sort_mode_combo.addItems([
            "來源順序",          
            "依名稱",
            "增傷詞條",
            "ROCalculator輸入"
        ])
        self.sort_mode_combo.setCurrentText("增傷詞條")  # ✅ 預設選這個
        self.sort_mode_combo.currentIndexChanged.connect(self.trigger_total_effect_update)
        total_filter_input_sort_mode_combo.addWidget(self.sort_mode_combo)
        total_tab_layout.addLayout(total_filter_input_sort_mode_combo)
        
        # 📄 整體總效果文字框
        self.total_effect_text = QTextEdit()
        self.total_effect_text.setReadOnly(True)        
        total_tab_layout.addWidget(self.total_effect_text)

        # 將 layout 放進 QWidget，再加進分頁
        total_tab_widget = QWidget()
        total_tab_widget.setLayout(total_tab_layout)
        self.sim_tabs.addTab(total_tab_widget, "整體總效果")




        # 模擬效果隱藏選項
        self.hide_unrecognized_checkbox = QCheckBox("隱藏辨識內容")
        self.hide_unrecognized_checkbox.setChecked(True)  # 預設勾選
        
        self.hide_unrecognized_checkbox.stateChanged.connect(self.trigger_total_effect_update)
        #self.hide_unrecognized_checkbox.stateChanged.connect(self.display_item_info)
        #不控制裝備屬性原始內容顯示就註解掉下面那行
        self.hide_unrecognized_checkbox.stateChanged.connect(self.toggle_equip_text_visibility)
        right_layout.addWidget(self.hide_unrecognized_checkbox)
        
        # 效果解析下方
        self.hide_physical_checkbox = QCheckBox("隱藏物理")
        self.hide_magical_checkbox = QCheckBox("隱藏魔法")
        
        self.hide_physical_checkbox.stateChanged.connect(self.trigger_total_effect_update)
        self.hide_magical_checkbox.stateChanged.connect(self.trigger_total_effect_update)
        #self.hide_physical_checkbox.stateChanged.connect(self.display_item_info)
        #self.hide_magical_checkbox.stateChanged.connect(self.display_item_info)
        # ✅ 套裝來源顯示勾選框
        self.show_combo_source_checkbox = QCheckBox("顯示來源")
        self.show_combo_source_checkbox.setChecked(True)  # 預設勾選
        
        self.show_combo_source_checkbox.stateChanged.connect(self.trigger_total_effect_update)
        #self.show_combo_source_checkbox.stateChanged.connect(self.display_all_effects)

        # 減傷倍率下拉選單
        self.damage_reduction_label = QLabel("減傷倍率:")
        self.damage_reduction_combobox = QComboBox()
        self.damage_reduction_combobox.addItems(["100%" ,"10%", "1%", "0.1%"])
        self.damage_reduction_combobox.setCurrentIndex(0)
        self.damage_reduction_combobox.currentIndexChanged.connect(self.trigger_total_effect_update)  # 有需要就綁定 signal

        
        

        checkbox_layout = QHBoxLayout()
        checkbox_layout.addWidget(self.hide_unrecognized_checkbox)
        checkbox_layout.addWidget(self.show_combo_source_checkbox)
        checkbox_layout.addWidget(self.hide_physical_checkbox)
        checkbox_layout.addWidget(self.hide_magical_checkbox)
        checkbox_layout.addWidget(self.damage_reduction_label)
        checkbox_layout.addWidget(self.damage_reduction_combobox)
        
        right_layout.addLayout(checkbox_layout)

        # 建立新分頁：傷害計算
        self.custom_calc_tab = QWidget()
        layout = QVBoxLayout(self.custom_calc_tab)

        # 多行文字框
        #self.custom_calc_box = QTextEdit()
        #layout.addWidget(self.custom_calc_box)
        
        # 多行文字框
        self.custom_calc_box = QTextEdit()
        monospace_font = QFont("MingLiU")  # 或你喜歡的等寬字體，例如 "Courier New"
        monospace_font.setStyleHint(QFont.Monospace)
        #monospace_font.setPointSize(11)  # 依你的 UI 調整字體大小
        self.custom_calc_box.setFont(monospace_font)

        layout.addWidget(self.custom_calc_box)

        
        
        
        def filter_skills():
            text = self.skill_filter_input.text().strip().lower()
            self.skill_box.blockSignals(True)  # 暫時停止訊號，避免重複觸發

            self.skill_box.clear()

            for key, display_name in skill_map.items():
                skill_data = skill_map_all.get(key)
                slv = skill_data.get("Slv") if skill_data else None
                code = skill_data.get("Code") if skill_data else None
                job_id = self.input_fields["JOB"].currentData()#取得職業ID
                skill_job_box = job_dict[job_id]["selectskill"]#取得職業ID技能代號(過濾用)

                # 以 '/' 分隔出多個職業前綴
                job_prefixes = set(skill_job_box.split('/'))
                #print(f"過濾的前置:{job_prefixes}，取得職業代號:{skill_job_box}，取得職業ID:{job_id}，取得code:{code}")
                # 無搜尋文字時，只顯示有 Slv 的技能
                if text == "":
                    # 過濾 Slv 為空、空字串、None、NaN 
                    #if pd.notna(slv) and str(slv).strip() != "":
                    #   self.skill_box.addItem(skill_map[key], key)

                    # 只過濾skill_job_box
                    #if code and '_' in code:
                    #    code_prefix = code.split('_')[0]
                    #    if code_prefix in job_prefixes:
                    #        self.skill_box.addItem(skill_map[key], key)

                    # 1. Slv 不能為空、空字串、None、NaN
                    # 2. code 必須有，且 '_' 分割後的前綴必須在職業前綴清單裡
                    if pd.notna(slv) and str(slv).strip() != "":
                        if code and '_' in code:
                            code_prefix = code.split('_')[0]
                            if code_prefix in job_prefixes:
                                self.skill_box.addItem(skill_map[key], key)
                else:
                    # 有搜尋時顯示所有技能（包含沒有 Slv）
                    if text in display_name.lower():
                        self.skill_box.addItem(display_name, key)

            self.skill_box.blockSignals(False)
            self.filter_skills = filter_skills

            # 若有項目，自動選第一個並更新顯示
            if self.skill_box.count() > 0:
                self.skill_box.setCurrentIndex(0)
                update_skill_formula_display()
            else:
                # 清空顯示
                self.skill_formula_result_input.setText("0%")
                self.skill_LV_input.setText("0")
                self.skill_hits_input.setText("")

        combo.currentIndexChanged.connect(filter_skills)#註冊JOB變更時過濾技能列表
        combo.currentIndexChanged.connect(update_stat_point)  # 更新職業是否擴充判斷總素質點
        combo.currentIndexChanged.connect(update_hp_sp_slider_visibility)#更新HPSP滑桿顯示

        
        skill_select_layout_top = QHBoxLayout()
        skill_select_layout_bottom = QHBoxLayout()

        # 技能過濾輸入欄
        self.skill_filter_input = QLineEdit()
        self.skill_filter_input.setPlaceholderText("技能過濾")
        self.skill_filter_input.setFixedWidth(80)
        skill_select_layout_top.addWidget(self.skill_filter_input)

        # 🔹 清空按鈕
        self.clear_filter_button = QPushButton("清空")
        self.clear_filter_button.setFixedWidth(50)
        self.clear_filter_button.setToolTip("清空過濾")
        self.clear_filter_button.clicked.connect(self.skill_filter_input.clear)
        skill_select_layout_top.addWidget(self.clear_filter_button)

        # 綁定過濾事件
        self.skill_filter_input.textChanged.connect(filter_skills)
        


        def update_skill_formula_display():
            current_data = self.skill_box.currentData()
            skill_data = skill_map_all.get(current_data)

            # 沒有資料時清空
            if not skill_data or not skill_data.get("Calculation"):
                self.skill_formula_result_input.setText("0%")
                self.skill_LV_input.setText("0")
                self.skill_hits_input.setText("")
                return

            # 技能公式
            formula = skill_data.get("Calculation", "")
            self.skill_formula_input.setText(str(formula))

            # 技能等級
            skill_lv_raw = skill_data.get("Slv", "")
            try:
                lv = float(skill_lv_raw)
                self.skill_LV_input.setText(f"{lv:.0f}")
            except:
                lv = 1
                self.skill_LV_input.setText("")

            # 打擊次數（支援公式 + 負數）
            skill_hits = skill_data.get("hits", "")
            try:
                expr = sympify(str(skill_hits))
                hits_result = int(expr.evalf(subs={"Sklv": lv}))
                self.skill_hits_input.setText(f"{hits_result}")
            except:
                self.skill_hits_input.setText(str(skill_hits))





            # 設定屬性下拉
            element_key = skill_data.get("element", "")
            index = self.attack_element_box.findData(element_key)
            if index != -1:
                self.attack_element_box.setCurrentIndex(index)

            # 呼叫更新計算
            self.replace_custom_calc_content()

        # 技能下拉選單
        self.skill_box = QComboBox()
        self.skill_box.setFixedWidth(160)

        for key in skill_map:
            skill_data = skill_map_all.get(key)
            slv = skill_data.get("Slv") if skill_data else None
            code = skill_data.get("Code") if skill_data else None
            job_id = self.input_fields["JOB"].currentData()#取得職業ID
            skill_job_box = job_dict[job_id]["selectskill"]#取得職業ID技能代號(過濾用)

            # 以 '/' 分隔出多個職業前綴
            job_prefixes = set(skill_job_box.split('/'))

            # 過濾 Slv 為空、空字串、None、NaN 
            #if pd.notna(slv) and str(slv).strip() != "":
            #   self.skill_box.addItem(skill_map[key], key)

            #過濾職業技能
            #if code and '_' in code:
            #    code_prefix = code.split('_')[0]
            #    if code_prefix in job_prefixes:
            #        self.skill_box.addItem(skill_map[key], key)

            # 1. Slv 不能為空、空字串、None、NaN
            # 2. code 必須有，且 '_' 分割後的前綴必須在職業前綴清單裡
            if pd.notna(slv) and str(slv).strip() != "":
                if code and '_' in code:
                    code_prefix = code.split('_')[0]
                    if code_prefix in job_prefixes:
                        self.skill_box.addItem(skill_map[key], key)

        # 綁定更新函式
        self.skill_box.currentIndexChanged.connect(update_skill_formula_display)


        skill_select_layout_top.addWidget(self.skill_box)

        # 技能等級
        self.skill_LV_input = QLineEdit()
        self.skill_LV_input.setPlaceholderText("技能等級")
        #self.skill_LV_input.setReadOnly(True)
        self.skill_LV_input.setFixedWidth(40)
        skill_select_layout_top.addWidget(self.skill_LV_input)

        # 攻擊屬性
        self.attack_element_box = QComboBox()
        for key in range(0, 10):
            self.attack_element_box.addItem(element_map[key], key)
        self.attack_element_box.setFixedWidth(80)
        skill_select_layout_top.addWidget(self.attack_element_box)
        
        # 公式結果欄
        
        self.skill_hits_input = QLineEdit()
        self.skill_hits_input.setPlaceholderText("次數")
        self.skill_hits_input.setText("1")
        self.skill_hits_input.setReadOnly(True)
        self.skill_hits_input.setFixedWidth(120)
        skill_select_layout_top.addWidget(self.skill_hits_input)


        # 技能公式欄
        self.skill_formula_input = QLineEdit()
        self.skill_formula_input.setPlaceholderText("技能公式")
        self.skill_formula_input.setFixedWidth(480)
        skill_select_layout_bottom.addWidget(self.skill_formula_input)

        # 公式結果欄
        self.skill_formula_result_input = QLineEdit()
        self.skill_formula_result_input.setPlaceholderText("公式結果")
        self.skill_formula_result_input.setReadOnly(True)
        self.skill_formula_result_input.setFixedWidth(120)
        skill_select_layout_bottom.addWidget(self.skill_formula_result_input)
        

        
        layout.insertLayout(0, skill_select_layout_top)
        layout.insertLayout(1, skill_select_layout_bottom)
        
        # 建立水平區塊
        button_row = QHBoxLayout()

        self.save_compare_button = QPushButton("儲存比對基準")
        self.save_compare_button.clicked.connect(lambda: (setattr(self, "_last_calc_state", None), self.save_compare_base()))

        button_row.addWidget(self.save_compare_button)

        # 中間新增勾選框
        self.auto_compare_checkbox = QCheckBox("持續比對")
        button_row.addWidget(self.auto_compare_checkbox)
        
        self.compare_button = QPushButton("手動執行比對")
        self.compare_button.clicked.connect(self.compare_with_base)
        button_row.addWidget(self.compare_button)
        
        # self.reskill_map_button = QPushButton("重新載入技能表")
        # self.reskill_map_button.clicked.connect(load_skill_map)
        # self.reskill_map_button.clicked.connect(filter_skills)
        
        # button_row.addWidget(self.reskill_map_button)
        self.skillEditor_button = QPushButton("編輯技能")
        self.skillEditor_button.clicked.connect(lambda: open_skill_editor(self))
        button_row.addWidget(self.skillEditor_button)


        layout.addLayout(button_row)

        # 把這整排按鈕加進主 layout（通常是 QVBoxLayout）
        layout.addLayout(button_row)


        # 插入分隔線（放在第 2 行之後）
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        layout.insertWidget(2, separator)
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        layout.insertWidget(4, separator)

        # === 特殊效果勾選區塊 ===

        # 使用 QGridLayout 來自動排版，每行最多放 4 個
        special_checkbox_layout = QGridLayout()
        
        # 特殊效果增傷處理區
        self.special_checkboxes = {
            "wanzih_checkbox": QCheckBox("萬紫/震裂(巔峰4)"),
            "poison_weak_checkbox": QCheckBox("毒耐性弱化"),
            "magic_poison_checkbox": QCheckBox("魔力中毒"),
            "attribute_seal_checkbox": QCheckBox("屬性紋章(水地火風)"),
            "sneak_attack_checkbox": QCheckBox("潛擊(近遠魔)"),
            "SPORE_attack_checkbox": QCheckBox("爆炸孢子(遠)"),            
            "DARKCROW_attack_checkbox": QCheckBox("致命爪痕(近)"),
            "RUSH_attack_checkbox": QCheckBox("衝擊撼動(近遠)"),            
            "OLEUM_attack_checkbox": QCheckBox("聖油洗禮(遠)"),



            # 可在這裡繼續新增更多項目
        }


        # 加入 layout（最多每行 4 個）
        max_per_row = 5
        for index, (key, checkbox) in enumerate(self.special_checkboxes.items()):
            row = index // max_per_row
            col = index % max_per_row
            special_checkbox_layout.addWidget(checkbox, row, col)

        layout.addLayout(special_checkbox_layout)
        
        # ✅ 在這裡綁定觸發
        for checkbox in self.special_checkboxes.values():
            checkbox.stateChanged.connect(self.replace_custom_calc_content)

        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        layout.insertWidget(6, separator)


        # === 建立目標設定區塊 ===
        target_layout = QHBoxLayout()

        # 建立下拉選單函式
        def make_combobox(label_text, options, visible_keys=None):
            sub_layout = QVBoxLayout()
            label = QLabel(label_text)
            box = QComboBox()
            
            if visible_keys is None:
                visible_keys = options.keys()
            
            for key in visible_keys:
                box.addItem(options[key], key)
            
            sub_layout.addWidget(label)
            sub_layout.addWidget(box)
            return sub_layout, box

        # 體型
        size_layout, self.size_box = make_combobox("體型", size_map)
        target_layout.addLayout(size_layout)

        # 屬性
        # 只顯示 element_map 前 10 個 key（0~9）
        visible_element_keys = [k for k in element_map if k <= 9]
        element_layout, self.element_box = make_combobox("屬性", element_map, visible_element_keys)
        target_layout.addLayout(element_layout)
        
        element_lv_input_layout = QVBoxLayout()
        element_lv_input_label = QLabel("等級")
        self.element_lv_input = QLineEdit()
        self.element_lv_input.setFixedWidth(30)
        self.element_lv_input.setPlaceholderText("1")
        validator = QIntValidator(1, 4, self)
        self.element_lv_input.setValidator(validator)
        element_lv_input_layout.addWidget(element_lv_input_label)
        element_lv_input_layout.addWidget(self.element_lv_input)
        target_layout.addLayout(element_lv_input_layout)

        # 同樣方式套用在 race_map（假設你也要限制）
        visible_race_keys = [k for k in race_map if k <= 9]
        race_layout, self.race_box = make_combobox("種族", race_map, visible_race_keys)
        target_layout.addLayout(race_layout)


        # 階級
        visible_class_keys = [k for k in class_map if k <= 1]  # 依你需求調整
        class_layout, self.class_box = make_combobox("階級", class_map, visible_class_keys)
        target_layout.addLayout(class_layout)

        # MDEF / MRES 輸入欄

        
        defc_layout = QVBoxLayout()
        self.defc_label = QLabel("前DEF")
        self.defc_input = QLineEdit()
        self.defc_input.setFixedWidth(60)
        self.defc_input.setPlaceholderText("0")
        self.mdefc_label = QLabel("前MDEF")
        self.mdefc_input = QLineEdit()
        self.mdefc_input.setFixedWidth(60)
        self.mdefc_input.setPlaceholderText("0")
        defc_layout.addWidget(self.defc_label)
        defc_layout.addWidget(self.defc_input)
        defc_layout.addWidget(self.mdefc_label)
        defc_layout.addWidget(self.mdefc_input)
        target_layout.addLayout(defc_layout)

        def_layout = QVBoxLayout()
        self.def_label = QLabel("後DEF")
        self.def_input = QLineEdit()
        self.def_input.setFixedWidth(60)
        self.def_input.setPlaceholderText("0")
        self.mdef_label = QLabel("後MDEF")
        self.mdef_input = QLineEdit()
        self.mdef_input.setFixedWidth(60)
        self.mdef_input.setPlaceholderText("0")
        def_layout.addWidget(self.def_label)
        def_layout.addWidget(self.def_input)        
        def_layout.addWidget(self.mdef_label)
        def_layout.addWidget(self.mdef_input)
        target_layout.addLayout(def_layout)


        res_layout = QVBoxLayout()
        self.res_label = QLabel("RES")
        self.res_input = QLineEdit()
        self.res_input.setFixedWidth(60)
        self.res_input.setPlaceholderText("0")
        self.mres_label = QLabel("MRES")
        self.mres_input = QLineEdit()
        self.mres_input.setFixedWidth(60)
        self.mres_input.setPlaceholderText("0")
        res_layout.addWidget(self.res_label)
        res_layout.addWidget(self.res_input)
        res_layout.addWidget(self.mres_label)
        res_layout.addWidget(self.mres_input)
        target_layout.addLayout(res_layout)
        
        self.def_label.setVisible(False)
        self.def_input.setVisible(False)
        self.defc_label.setVisible(False)
        self.defc_input.setVisible(False)
        self.res_label.setVisible(False)
        self.res_input.setVisible(False)
        
        # 把整排放到主要 layout
        
        layout.addLayout(target_layout)
        
        # ComboBox 的綁定 修改觸發計算
        self.size_box.currentIndexChanged.connect(self.replace_custom_calc_content)
        self.element_box.currentIndexChanged.connect(self.replace_custom_calc_content)
        self.race_box.currentIndexChanged.connect(self.replace_custom_calc_content)
        self.class_box.currentIndexChanged.connect(self.replace_custom_calc_content)
        self.attack_element_box.currentIndexChanged.connect(self.replace_custom_calc_content)

        # LineEdit 的綁定（使用 editingFinished 避免每次打字都觸發）
        #self.monsterDamage_input.editingFinished.connect(self.replace_custom_calc_content)#指定魔物增傷UI
        self.def_input.editingFinished.connect(self.replace_custom_calc_content)
        self.defc_input.editingFinished.connect(self.replace_custom_calc_content)
        self.res_input.editingFinished.connect(self.replace_custom_calc_content)
        self.mdef_input.editingFinished.connect(self.replace_custom_calc_content)
        self.mdefc_input.editingFinished.connect(self.replace_custom_calc_content)
        self.mres_input.editingFinished.connect(self.replace_custom_calc_content)


        self.btn_open_monster_lookup = QPushButton("查詢怪物")
        self.btn_open_monster_lookup.clicked.connect(self.open_monster_lookup)
        layout.addWidget(self.btn_open_monster_lookup)
        # 新增按鈕
        self.replace_calc_button = QPushButton("計算")
        self.replace_calc_button.clicked.connect(lambda: (setattr(self, "_last_calc_state", None), self.trigger_total_effect_update()))
        layout.addWidget(self.replace_calc_button)

        self.sim_tabs.addTab(self.custom_calc_tab, "傷害計算")







        # ===== 合併三欄 =====
        #main_layout.addWidget(left_scroll, 2)#已分頁取代
        #main_layout.addWidget(middle_scroll, 3)
        main_layout.addWidget(right_scroll, 3)
        self.setLayout(main_layout)


        # 初始化下拉選單
        self.update_combobox(initial=True)
        self.current_edit_part = None  # 用來追蹤目前編輯哪個欄位

        #根據 checkbox 狀態隱藏或顯示
        self.toggle_equip_text_visibility()


        #讀取.json存檔 250611更動工具列讀取
        #self.load_saved_inputs()
        



        #讀取完先計算一次        
        
        #self.display_all_effects()
        



        # 初始顯示一次
        
        #self.update_dex_int_half_note()
        self.result_output.textChanged.connect(self.on_result_output_changed)
        self.gen_button.clicked.connect(self.on_generate)
        self.function_selector.currentIndexChanged.connect(self.on_function_changed)
        self.on_function_changed()
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        # 綁定輸入欄事件（動態更新）
        #self.input_fields["DEX"].textChanged.connect(self.update_dex_int_half_note)
        #self.input_fields["INT"].textChanged.connect(self.update_dex_int_half_note)
        self.hp_slider.valueChanged.connect(self.replace_custom_calc_content)                
        self.sp_slider.valueChanged.connect(self.replace_custom_calc_content)
        self.unsync_button.clicked.connect(update_hp_sp_slider_display)
        self.unsync_button2.clicked.connect(update_hp_sp_slider_display)        
        self.apply_equip_button.clicked.connect(update_hp_sp_slider_display)
        self.apply_to_note_button.clicked.connect(update_hp_sp_slider_display)

        #開啟選單欄 
        self.update_window_title()
        self.setup_menu()
        
    
    def setup_menu(self):
        menubar = QMenuBar(self)

        # === 檔案選單 ===
        file_menu = menubar.addMenu("檔案")

        open_action = QAction("開啟", self)
        open_action.triggered.connect(self.open_project_file)
        file_menu.addAction(open_action)        

        open_rrf_action = QAction("從RO重播檔(.rrf)匯入裝備", self)
        open_rrf_action.triggered.connect(self.open_rrf_and_import)
        file_menu.addAction(open_rrf_action)        

        save_action = QAction("存檔", self)
        save_action.triggered.connect(self.save_file)
        file_menu.addAction(save_action)

        save_as_action = QAction("另存新檔", self)
        save_as_action.triggered.connect(self.save_as_file)
        file_menu.addAction(save_as_action)

        ROC_save_as_action = QAction("另存到.ROC(ROCalculator)", self)
        ROC_save_as_action.triggered.connect(
            lambda checked=False: self.add_effects_from_variables("data/default.txt", equipid_mapping, status_mapping)
        )   

        file_menu.addAction(ROC_save_as_action)
        
        gamedata_menu = menubar.addMenu("遊戲資訊")
        # === 建立選單：附魔工具 ===
        enchant_action = QAction("附魔查詢工具", self)
        enchant_action.triggered.connect(self.open_enchant_tool)

        gamedata_menu.addAction(enchant_action)

        # === 建立選單：改造工具 ===
        reform_action = QAction("改造查詢工具", self)
        reform_action.triggered.connect(self.open_reform_tool)

        gamedata_menu.addAction(reform_action)
            # === 建立選單：技能欄 ===
        # skill_tree_action = QAction("技能欄", self)
        # skill_tree_action.triggered.connect(self.open_skill_tree)
        # gamedata_menu.addAction(skill_tree_action)

        # === 設定選單 ===
        settings_menu = menubar.addMenu("設定")

        preferences_action = QAction("偏好設定", self)
        preferences_action.triggered.connect(self.open_compile_set)
        settings_menu.addAction(preferences_action)

        
        menu_update = menubar.addMenu("更新")

        self.action_check_update = QAction("檢查更新", self)
        self.action_do_update = QAction("立即更新", self)
        self.action_do_update.setEnabled(False)  # 預設不能按

        menu_update.addAction(self.action_check_update)
        #menu_update.addAction(self.action_do_update)

        self.action_check_update.triggered.connect(self.check_update)
        self.action_do_update.triggered.connect(self.do_update)

        self._remote_version = None  # 存檢查到的遠端版本
        # # === 說明選單 ===
        # help_menu = menubar.addMenu("說明")

        # help_action = QAction("使用說明", self)
        # help_action.triggered.connect#(self.show_help)
        # help_menu.addAction(help_action)

        # about_action = QAction("關於", self)
        # about_action.triggered.connect#(self.show_about)
        # help_menu.addAction(about_action)
        
        # === 加入選單到主 layout ===
        self.layout().setMenuBar(menubar)
        


    def add_effects_from_variables(self, template_path, equipid_mapping, status_mapping):  # 直接輸出 .ROC
        import json, copy, os, base64
        from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

        # === 擷取類別或全域變數 ===
        context = globals()

        # === 讀取模板 JSON ===
        with open(template_path, "r", encoding="utf-8") as f:
            template = json.load(f)
        new_data = copy.deepcopy(template)

        # === 找到主手裝備的 effectlist ===
        equip_list = new_data.get("Equip", [])
        if not equip_list:
            QMessageBox.warning(self, "錯誤", "模板檔案中沒有 Equip 資料")
            return
        effect_list = equip_list[0].get("effectlist", [])

        # === 根據 equipid_mapping 新增效果到 Equip ===
        for var_name, effect_id in equipid_mapping.items():
            if var_name in context:
                value = context[var_name]
                if value == 0:
                    continue  # value 是 0 就略過，不輸出也不新增
                new_effect = {
                    "EffectNumber": value,
                    "EffectType": {"id": effect_id},
                    "Enable": True
                }
                effect_list.append(new_effect)
                print(f"✅ 已新增效果：{effect_id} = {value}")
            else:
                print(f"⚠️ 找不到變數：{var_name}，略過。")

        # === 根據 status_mapping 更新 Status ===
        status_data = new_data.get("Status", {})
        if status_data:
            for var_name, status_key in status_mapping.items():
                if var_name in context:
                    new_value = context[var_name]
                    old_value = status_data.get(status_key, None)
                    status_data[status_key] = new_value
                    print(f"🔄 Status[{status_key}] 從 {old_value} → {new_value}")
                else:
                    print(f"⚠️ 找不到變數：{var_name}（對應 Status[{status_key}]），略過。")
        else:
            print("⚠️ 模板中沒有 Status 區塊。")

        # === 更新技能code ===
        if "Skill" in new_data and isinstance(new_data["Skill"], dict):
            old_value = new_data["Skill"].get("id", None)
            new_data["Skill"]["id"] = SkillCode
            print(f"🔄 Skill['id'] 從 {old_value} → {SkillCode}")
        else:
            print("⚠️ 模板中沒有 Skill 區塊或格式不正確")

        # === 根據 weapon_mapping 更新 Weapon===
        weapon_data = new_data.get("Weapon", {})
        if weapon_data:
            for var_name, weapon_key in weapon_mapping.items():
                if var_name in context:
                    new_value = context[var_name]

                    # 正規化成多層鍵列表
                    if isinstance(weapon_key, (tuple, list)):
                        keys = list(weapon_key)
                    else:
                        keys = [weapon_key]

                    # 先取舊值（不建立缺失的中間層）
                    cur = weapon_data
                    old_value = None
                    found = True
                    for k in keys[:-1]:
                        if isinstance(cur, dict) and k in cur:
                            cur = cur[k]
                        else:
                            found = False
                            break
                    if found and isinstance(cur, dict) and keys[-1] in cur:
                        old_value = cur[keys[-1]]

                    # 設定新值（必要時建立中間層）
                    cur = weapon_data
                    for k in keys[:-1]:
                        if k not in cur or not isinstance(cur[k], dict):
                            cur[k] = {}
                        cur = cur[k]
                    cur[keys[-1]] = new_value

                    path_str = "][".join(map(str, keys))
                    print(f"🔄 Weapon[{path_str}] 從 {old_value} → {new_value}")
                else:
                    print(f"⚠️ 找不到變數：{var_name}（對應 Weapon[{weapon_key}]），略過。")
        else:
            print("⚠️ 模板中沒有 Weapon 區塊。")


        # === 根據 SubWeapon_mapping 更新 SubWeapon ===
        subweapon_data = new_data.get("SubWeapon", {})
        if subweapon_data:
            for var_name, subweapon_key in SubWeapon_mapping.items():
                if var_name in context:
                    new_value = context[var_name]

                    # subweapon_key 可能是單層或雙層 key
                    if isinstance(subweapon_key, tuple) and len(subweapon_key) == 2:
                        first, second = subweapon_key
                        if first in subweapon_data and isinstance(subweapon_data[first], dict):
                            old_value = subweapon_data[first].get(second, None)
                            subweapon_data[first][second] = new_value
                            print(f"🔄 SubWeapon[{first}][{second}] 從 {old_value} → {new_value}")
                        else:
                            print(f"⚠️ SubWeapon 中沒有 {first} 層級，略過。")
                    else:
                        old_value = subweapon_data.get(subweapon_key, None)
                        subweapon_data[subweapon_key] = new_value
                        print(f"🔄 SubWeapon[{subweapon_key}] 從 {old_value} → {new_value}")
                else:
                    print(f"⚠️ 找不到變數：{var_name}（對應 SubWeapon[{subweapon_key}]），略過。")
        else:
            print("⚠️ 模板中沒有 SubWeapon 區塊。")


        # === 從視窗標題推斷檔名 ===
        full_title = self.windowTitle().strip() or "RO物品查詢計算工具 - 未命名"
        if " - " in full_title:
            filename_part = full_title.split(" - ", 1)[1]
        else:
            filename_part = "未命名"

        for bad_char in '\\/:*?"<>|':
            filename_part = filename_part.replace(bad_char, "_")

        filename_part = os.path.splitext(filename_part)[0]
        suggested_filename = f"{filename_part}.roc"

        # === 顯示另存新檔 ===
        app = QApplication.instance() or QApplication([])
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "另存 ROC 檔",
            suggested_filename,
            "ROC 檔案 (*.roc)"
        )

        if not file_path:
            return

        # 確保副檔名正確
        if not file_path.lower().endswith(".roc"):
            file_path += ".roc"

        # === 直接轉成 base64 並寫出 ROC 檔 ===
        try:
            encoded = base64.b64encode(json.dumps(new_data, ensure_ascii=False).encode("utf-8")).decode("utf-8")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(encoded)
            print(f"✅ 已新增效果並更新 Status，直接輸出 ROC 檔：{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"ROC 轉換或儲存失敗：{e}")
            print(f"❌ 轉換失敗：{e}")





        
        
    def save_as_file(self):
        # 預設開啟的資料夾
        default_dir = os.path.join(os.getcwd(),"裝備")

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "另存新檔",
            default_dir,  # ✅ 預設路徑
            "JSON Files (*.json)"
        )

        if file_path:
            # 確保副檔名是 .json
            if not file_path.lower().endswith(".json"):
                file_path += ".json"

            self.save_to_file(file_path)
            
    def save_to_file(self, file_path):
        data = {}

        # 儲存 input_fields
        for key, field in self.input_fields.items():
            if isinstance(field, QComboBox):
                data[key] = field.currentText()
            else:
                data[key] = field.text()

        # 儲存裝備與卡片欄位
        for part, info in self.refine_inputs_ui.items():
            data[f"{part}_equip"] = info["equip"].text()
            for i, card_input in enumerate(info["cards"]):
                data[f"{part}_card{i+1}"] = card_input.text()
            if "note" in info:
                data[f"{part}_note"] = info["note"].toPlainText()

        # 技能與怪物資訊整合
        data["skill_name"] = self.skill_box.currentText()
        data["size"] = self.size_box.currentIndex()
        data["element"] = self.element_box.currentIndex()
        data["race"] = self.race_box.currentIndex()
        data["class"] = self.class_box.currentIndex()
        data["mdef"] = self.mdef_input.text()
        data["mdefc"] = self.mdefc_input.text()
        data["mres"] = self.mres_input.text()
        data["def"] = self.def_input.text()
        data["defc"] = self.defc_input.text()
        data["res"] = self.res_input.text()
        data["element_lv"] = self.element_lv_input.text()

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.current_file = file_path
            self.update_window_title()
        except Exception as e:
            QMessageBox.critical(self, "儲存失敗", f"無法儲存檔案：\n{e}")


    def save_file(self):
        if not self.current_file:
            self.save_as_file()  # 如果還沒指定檔案，就當成另存新檔
        else:
            self.save_to_file(self.current_file)


    def load_json_direct(self, file_path):
        try:
            self.skill_filter_input.clear()
            self.load_saved_inputs(file_path)
            #self.current_file = file_path # 不更新目前檔案路徑，保持為空
            self.update_window_title()
            # self.display_all_effects()
            # self.update_dex_int_half_note()
            # self.jobsphp_display()
            self.refresh_skill_list()
            # self.replace_custom_calc_content()
            self.trigger_total_effect_update()
            #QMessageBox.information(self, "完成", f"已載入：{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"載入失敗：\n{str(e)}")
        # ★★★ 讀取成功 → 刪除 JSON 檔 ★★★
        try:
            os.remove(file_path)
            print(f"已刪除暫存 JSON：{file_path}")
        except Exception as e:
            print(f"刪除 JSON 失敗：{e}")

    def open_rrf_and_import(self):
        import subprocess, os, json

        # 執行 rrf_to_App.py
        #subprocess.run(["python", "rrf_to_App.py"])
        json_path = run_rrf_main()
        if not json_path:
            return
        bridge_file = "tmp/rrf_output_path.txt"

        if not os.path.exists(bridge_file):
            QMessageBox.warning(self, "錯誤", "沒有收到 rrf_to_App.py 的 JSON 輸出路徑")
            return

        # 讀出 JSON 檔案路徑
        with open(bridge_file, "r", encoding="utf-8") as f:
            json_path = f.read().strip()

        if not os.path.exists(json_path):
            QMessageBox.warning(self, "錯誤", f"找不到 JSON 檔案：{json_path}")
            return

        # ★ 自動載入 JSON（不跳視窗）
        self.load_json_direct(json_path)


    def open_project_file(self):
        # 設定預設資料夾
        default_dir = os.path.join(os.getcwd(),"裝備")
    
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "選擇專案檔",
            default_dir,  # ✅ 預設資料夾
            "JSON Files (*.json)"
        )
        if not file_path:
            return

        try:
            self.skill_filter_input.clear()
            self.clear_global_state()
            self.load_saved_inputs(file_path)
            self.current_file = file_path
            self.update_window_title()
            # self.display_all_effects()
            # self.replace_custom_calc_content()
            # self.update_dex_int_half_note()
            # self.jobsphp_display()
            self.refresh_skill_list()
            self.trigger_total_effect_update()


        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"載入失敗：\n{str(e)}")



    def clear_current_edit(self):
        self.current_edit_part = None
        self.current_edit_label.setText("目前部位：")
        self.unsync_button.setVisible(False)
        self.apply_equip_button.setVisible(False)
        self.unsync_button2.setVisible(False)
        self.apply_to_note_button.setVisible(False)
        self.clear_field_button2.setVisible(False)
        self.clear_field_button.setVisible(False)

        for part_name, widgets in self.refine_inputs_ui.items():
            widgets["equip"].setEnabled(True)
            widgets["refine"].setEnabled(True)
            widgets["grade"].setEnabled(True)
            for card_input in widgets["cards"]:
                card_input.setEnabled(True)
            # ✅ 移除所有欄位的背景色
            widgets["equip"].setStyleSheet("")
            for card_input in widgets["cards"]:
                card_input.setStyleSheet("")
            widgets["note"].setStyleSheet("")
            widgets["note_ui"].setStyleSheet("")
            
        #self.display_item_info()
        #self.display_all_effects()
        #self.replace_custom_calc_content()

        self.global_refine_input.setVisible(True)
        self.global_grade_combo.setVisible(True)





    def set_edit_lock(self, part_name, field_name):


        #self.display_item_info()
        self.global_refine_input.setVisible(False)
        self.global_grade_combo.setVisible(False)
        self.trigger_total_effect_update()


    def update_combobox(self, initial=False):
        keyword_text = self.search_input.text().strip()
        self.result_box.clear()

        # 以空白分割關鍵字（自動忽略多餘空白）
        keywords = keyword_text.split()

        self.filtered_items = {}

        for k, v in self.parsed_items.items():
            # 只保留有裝備效果資料的項目
            if k not in self.equipment_data:
                continue

            # 將可搜尋內容合併成一個字串
            searchable_text = " ".join([
                str(k),
                v['name'],
                " ".join(v['description'])
            ])

            # 所有關鍵字都必須命中
            if all(keyword in searchable_text for keyword in keywords):
                self.filtered_items[k] = v

        for item_id in sorted(self.filtered_items):
            item = self.filtered_items[item_id]
            self.result_box.addItem(f"{item_id} - {item['name']}", item_id)

        if self.result_box.count() > 0:
            self.result_box.setCurrentIndex(0)
            self.display_item_info()

            


   
    def display_item_info(self, refine_override=None, grade_override=None):
        '''
        根據目前選取的物品，顯示其詳細資訊
        '''
        index = self.result_box.currentIndex()
        if index == -1:
            return
        item_id = self.result_box.currentData()
        item = self.filtered_items.get(item_id)
        if not item:
            return
        self.name_field.setText(item['name'])
        self.kr_name_field.setText(item['kr_name'])
        self.slot_field.setText(str(item['slot']))

        html = convert_description_to_html(item['description'])
        self.desc_text.setHtml(html)
        # 顯示裝備原始資料區塊（若有）
        if item_id in self.equipment_data:
            block_text = self.equipment_data[item_id]
            # === Combiitem → 顯示套裝需求（裝備名稱） ===
            # 需求：使用 Combiitem 裡的「套裝ID」去找對應套裝區塊，並解析其中 Item={...} 的需求裝備。
            def _extract_combi_ids(_block_text: str) -> list[int]:
                m = re.search(r"Combiitem\s*=\s*\{([^}]*)\}", _block_text)
                if not m:
                    return []
                ids: list[int] = []
                for x in m.group(1).split(','):
                    x = x.strip()
                    if x.isdigit():
                        ids.append(int(x))
                return ids

            def _extract_combo_items(_combo_text: str) -> list[int]:
                m = re.search(r"Item\s*=\s*\{([^}]*)\}", _combo_text)
                if not m:
                    return []
                out: list[int] = []
                for x in m.group(1).split(','):
                    x = x.strip()
                    if x.isdigit():
                        out.append(int(x))
                # 去重但保留順序
                seen = set()
                uniq = []
                for i in out:
                    if i not in seen:
                        seen.add(i)
                        uniq.append(i)
                return uniq

            combi_ids = _extract_combi_ids(block_text)
            combi_lines: list[str] = []
            if combi_ids:
                #combi_lines.append("========= Combiitem 套裝需求 =========")
                for combi_id in combi_ids:
                    combo_block = self.equipment_data.get(combi_id, "")
                    need_ids = _extract_combo_items(combo_block)

                    combo_name = self.parsed_items.get(combi_id, {}).get("name", f"套裝ID {combi_id}")
                    if not need_ids:
                        #combi_lines.append(f"🧩 {combo_name}（{combi_id}）：（找不到 Item={{...}}）")
                        combi_lines.append(f"🧩 {combo_name}：（找不到 Item={{...}}）")
                        continue

                    need_names = [self.parsed_items.get(iid, {}).get("name", f"ID:{iid}") for iid in need_ids]
                    #combi_lines.append(f"🧩 {combo_name}（{combi_id}）")
                    combi_lines.append(f"🧩 {combo_name}")
                    combi_lines.append("↳  需求：" + "、".join(need_names))
            if not combi_ids:
                self.combi_raw_text.clear()
            else:
                raw_blocks = []
                for cid in combi_ids:
                    combo_block = self.equipment_data.get(cid, "")
                    if combo_block:
                        raw_blocks.append(f"[{cid}] = {{\n{combo_block}\n}}")
                    else:
                        raw_blocks.append(f"[{cid}] 找不到資料")

                self.combi_raw_text.setPlainText("\n\n".join(raw_blocks))


            fullCombi_text = ("\n".join(combi_lines) if combi_lines else "")
            self.Combi_text.setPlainText(fullCombi_text)


            full_text = f"[{item_id}] = {{\n{block_text}\n}}"
            self.equip_text.setPlainText(full_text)
        else:
            self.equip_text.setPlainText("（此物品無對應裝備屬性資料）")
        # 模擬效果解析
        if item_id in self.equipment_data:
            # 偵測是否需要精煉欄位
            #self.refine_input.setVisible("GetRefineLevel(" in block_text)

            # 整理 get(...) 對應值
            get_values = {}
            for label, gid in self.stat_fields.items():
                widget = self.input_fields[label]
                if isinstance(widget, QComboBox):
                    get_values[gid] = widget.currentData()
                else:
                    try:
                        get_values[gid] = int(widget.text())
                    except ValueError:
                        get_values[gid] = 0

            # 整理 GetRefineLevel(...) 對應值
            refine_inputs = {}
            for label, info in self.refine_parts.items():
                slot_id = info["slot"]
                # 如果你原本使用 slot_id 做什麼，照樣用

                text = self.input_fields[label].text()
                try:
                    refine_inputs[slot_id] = int(text)
                except ValueError:
                    refine_inputs[slot_id] = 0

            # 裝備階級 GetEquipGradeLevel
            grade = 0
            if hasattr(self, "current_edit_part") and self.current_edit_part:
                part_name = self.current_edit_part.split(" - ")[0]
                key = f"{part_name}_階級"
                if key in self.input_fields:
                    grade = self.input_fields[key].currentIndex()
            
            hide_physical = self.hide_physical_checkbox.isChecked()
            hide_magical = self.hide_magical_checkbox.isChecked()
            hide_unrecognized = self.hide_unrecognized_checkbox.isChecked()
            # 抓目前裝備部位的 slot ID
            current_slot = None
            if self.current_edit_part:
                part_name = self.current_edit_part.split(" - ")[0]
                current_slot = self.refine_parts.get(part_name, {}).get("slot")
                grade = self.input_fields.get(f"{part_name}_階級", self.global_grade_combo).currentIndex()
            else:
                # ⬅️ 若沒選部位就用全域
                current_slot = None
                try:
                    refine_inputs[99] = int(self.global_refine_input.text())  # slot=99 為假設值
                except:
                    refine_inputs[99] = 0
                grade = self.global_grade_combo.currentIndex()


            # 呼叫新模擬效果解析器
            effects = parse_lua_effects_with_variables(
                block_text,
                refine_inputs,
                get_values,
                grade,
                unit_map,
                size_map,
                effect_map,
                hide_unrecognized,
                current_location_slot=current_slot or 99
            )


            hide_keywords = []
            if hide_physical:
                hide_keywords.append("物理")
            if hide_magical:
                hide_keywords.append("魔法")
                
            filtered_effects = self.filter_effects(effects)
            effect_dict = {}
            for line in filtered_effects:
                parsed = self.try_extract_effect(line)
                if parsed:
                    key, value, unit = parsed
                    key = self.normalize_effect_key(key)
                    #source_label = part_name  # or 卡片名稱 or 套裝來源

                    # 建立效果來源清單
                    #effect_dict.setdefault((key, unit), []).append((value, source_label))


                else:
                    continue  # 無法解析就略過，不佔用空間



            combined = []
            show_source = self.show_combo_source_checkbox.isChecked()
            for (key, unit), entries in sorted(effect_dict.items(), key=lambda x: x[0][0]):
                total = sum(val for val, _ in entries)
                if unit == "秒":
                    total = round(total, 1)
                    value_str = f"{total:+.1f}{unit}"
                else:
                    value_str = f"{total:+g}{unit}"

                if show_source:
                    for val, source in entries:
                        val_str = f"{val:+.1f}{unit}" if unit == "秒" else f"{val:+d}{unit}"
                        combined.append(f"{key} {val_str}  ← 〔{source}〕")
                    combined.append(f"🧮↳ {key} {value_str}  ← 〔總和〕🧮")
                else:
                    combined.append(f"{key} {value_str}")
    




            self.sim_effect_text.setPlainText("\n".join(combined))
            # 顯示結果
            self.sim_effect_text.setPlainText("\n".join(filtered_effects))
            
            self.display_all_effects()#這邊只顯示目前裝備效果 需要單獨處理 不然會影響最終顯示
            
            
        else:
            self.sim_effect_text.setPlainText("（無可解析效果）")
            

if __name__ == "__main__":
    app = QApplication(sys.argv)

    loading = LoadingDialog()
    loading.show()    

    window = ItemSearchApp()
    worker = InitWorker(app_instance=window)
    DataRegistry.window = window

    worker.log_signal.connect(loading.append_text)
    worker.progress_signal.connect(loading.update_progress)

    def on_done(data):
        
        print("📖 載入 外部MAP ...")
        DataRegistry.reload_all()
        loading.append_text("初始化完成，正在更新介面...")
        # ✅ 主執行緒更新 UI
        window.parsed_items = data or {}
        window.update_combobox()

        window.resize(1650, 900)
        window.show()

        QTimer.singleShot(1000, loading.close)

    worker.done_signal.connect(on_done)
    worker.start()

    sys.exit(app.exec())


# 技能計算BUG觀察紀錄
# 毀滅彗星5等
# 技能%等級是否-1%
# 245 -0
# 246 -0
# 247
# 248 -0
# 249
# 250 -0
# 251 -1
# 252 
# 253 -1 
# 260 -0