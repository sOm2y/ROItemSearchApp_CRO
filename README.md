# ROItemSearchApp_CRO

[![GitHub Downloads](https://img.shields.io/github/downloads/sOm2y/ROItemSearchApp_CRO/total)](https://github.com/sOm2y/ROItemSearchApp_CRO/releases)
[![GitHub Release](https://img.shields.io/github/v/release/sOm2y/ROItemSearchApp_CRO)](https://github.com/sOm2y/ROItemSearchApp_CRO/releases/latest)

本仓库从原项目 [z2911902/ROItemSearchApp](https://github.com/z2911902/ROItemSearchApp) 剥离并独立维护，专门针对 CRO《仙境传说：起源》的游戏数据、装备环境和使用需求进行适配。

这不是原项目的通用发行分支。CRO 相关功能、数据兼容、简体中文化和 Windows 构建版本均在本仓库单独开发与发布。

## 项目定位

- 面向 CRO《仙境传说：起源》玩家。
- 查询装备并汇总装备、卡片、附魔和套装能力。
- 提供技能树、附魔、装备改造、箱子物品和怪物查询工具。
- 支持 RRF 转换、伤害记录与统计分析。
- 支持简体中文、繁体中文和英文界面。
- 保持旧 JSON、ROC 和 RRF 数据中的稳定字段兼容。

## 下载

请从本仓库的 [Releases 页面](https://github.com/sOm2y/ROItemSearchApp_CRO/releases) 下载最新 Windows 版本。

发布包 `ROItemSearchApp.zip` 内包含：

- `ItemSearchApp.exe`：主程序
- `update.exe`：更新程序
- 程序运行所需的 `APP`、`data`、`lang` 等资源目录

解压完整 ZIP 后运行 `ItemSearchApp.exe`，不要只单独复制 EXE。

## 开发运行

推荐使用 Python 3.11：

```bash
python -m venv .venv
```

Windows：

```powershell
.venv\Scripts\activate
python -m pip install -r requirements.txt
python ItemSearchApp.py
```

macOS / Linux：

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
python ItemSearchApp.py
```

## 来源与致谢

本项目基于 [z2911902/ROItemSearchApp](https://github.com/z2911902/ROItemSearchApp) 的代码与功能设计继续开发。感谢原作者及原项目贡献者提供的基础实现。

原项目使用教学可参考[巴哈姆特文章](https://forum.gamer.com.tw/C.php?bsn=4212&snA=439281&tnum=1)。由于本仓库针对 CRO 独立演进，部分界面和功能可能与文章内容不同。

## 免责声明

本项目为非官方玩家工具，与 Gravity、CRO《仙境传说：起源》运营方及相关权利方无隶属或授权关系。游戏名称、商标和数据的权利归其各自权利人所有。
