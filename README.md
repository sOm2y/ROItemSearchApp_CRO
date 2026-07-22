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

## 装备文字本地化

上游游戏物品数据保留在 `data/iteminfo_new.lua` 和 `data/User_iteminfo_new.lua`，本仓库的简体名称和说明按 Item ID 存放在 `lang/items/zh_CN.json`。程序运行时应用语言覆盖，不直接修改上游 Lua，因此更新游戏数据时不会覆盖简体翻译。

当前物品文本以 OpenCC 繁转简结果作为初稿，仍需按照 CRO 官方译名持续校对。开发者可以在安装 `opencc-python-reimplemented` 后重新生成：

```bash
python scripts/generate_item_zh_cn.py
python tools/check_item_localization.py
```

人工校对请写入 `lang/items/zh_CN_overrides.json`；程序会在自动转换结果之后应用这个文件，重新生成基础语言包时不会覆盖人工译名。

可以通过第三方数据库 Divine Pride 的公开 cRO 物品页，按 Item ID 核对 cRO 客户端简体名称。命令默认只预览，确认后使用 `--write` 写入人工覆盖：

```bash
python scripts/sync_divine_pride_items.py 24208
python scripts/sync_divine_pride_items.py 24208 --write
```

批量处理可以使用 `--ids-file`，请求之间默认间隔一秒。说明文字不会默认覆盖；确认页面当前 cRO 说明适用后，可显式增加 `--include-description`。

全量校对采用三个独立层级，加载顺序为：

1. `zh_CN.json`：OpenCC 生成的简体初稿。
2. `zh_CN_divine_pride.json`：Divine Pride cRO 批量校对结果。
3. `zh_CN_overrides.json`：人工修正，始终具有最高优先级。

先执行不联网的全量计划检查：

```bash
python scripts/sync_divine_pride_items.py --all --plan
```

建议先运行 100 条试验批次：

```bash
python scripts/sync_divine_pride_items.py --all --write --resume --limit 100
```

试验结果确认后继续全量运行：

```bash
python scripts/sync_divine_pride_items.py --all --write --resume
```

全量模式默认跳过已经带有 Divine Pride 名称来源记录的条目，每 25 条原子保存校对层和断点。网络错误默认重试 3 次；中断后可以再次使用 `--resume`。失败条目记录在 `build/divine_pride_item_sync_failures.json`，修复网络或页面问题后重跑同一命令即可继续处理。

为防止 Divine Pride 的跨服务器回退名称、外文或乱码污染简体名称，批量模式只会自动接受“与当前本地名称完全一致”的结果。不同名称会先保留当前运行时名称，并写入 `lang/items/zh_CN_divine_pride_review.json` 等待人工审核。可随时重新生成便于查看的 CSV：

```bash
python scripts/review_divine_pride_item_names.py
```

确认采用其中的简体中文名称后，可以执行：

```bash
python scripts/approve_simplified_divine_pride_names.py
```

该命令会采用通过简体字形检查的候选名称。对于 `暗神官卡片` / `闇神官卡片` 这类转为简体后与现有名称等价的中文异体名称，以及项目维护者明确确认的 cRO 中文职业名差异，界面继续显示简体名称，并把候选名称录入搜索别名。日文、韩文、纯外文及可逆识别的韩文乱码不会采用。已采用记录输出到 `reports/divine_pride_item_name_approved.csv`；未采用记录继续保留在 `reports/divine_pride_item_name_review.csv`，程序仍显示原名称。

全量校对默认只采用名称，不批量写入说明文字。可以使用 `--delay`、`--retries`、`--retry-backoff`、`--checkpoint-every` 和 `--limit` 调整请求节奏及批次大小。

简体名称、繁体原名、内部资源名和 Item ID 都可以用于装备搜索。计算脚本、DBName、资源名和旧存档稳定字段不会被翻译。

装备效果解析器同样采用“稳定键与显示文本分离”的方式：内部仍使用原有计算关键字，简体界面在输出前应用 `lang/effects/zh_CN.json`，因此效果加总、筛选和旧存档不会因为繁简转换而改变。

## 职业名称本地化

职业属性和技能关联继续以 `data/job_dict.py` 中的 Job ID 与内部代码为准，界面名称覆盖存放在 `lang/jobs/zh_CN.json` 和 `lang/jobs/en_US.json`。主界面、技能树及 RRF 转换结果会按当前语言显示职业名称。

新保存的 JSON 会同时记录兼容字段 `JOB` 和稳定字段 `JOB_ID`。读取时支持旧繁体名称、简体名称、英文名称、内部名称和数字 Job ID，因此切换界面语言不会导致旧存档丢失职业选择。

## 技能名称本地化

技能公式、技能树依赖和装备效果计算继续使用 `data/skillneme.csv` 中的 Skill ID、Code 和原始名称。简体显示名称按 Skill ID 存放在 `lang/skills/zh_CN.json`，人工校对应写入 `lang/skills/zh_CN_overrides.json`。

重新生成和检查技能语言包：

```bash
python scripts/generate_skill_zh_cn.py
python tools/check_skill_localization.py
```

主界面技能选择、技能搜索、函数参数补完、技能树和 RRF 伤害记录均使用本地化显示名称。搜索同时支持 Skill ID、内部 Code、繁体原名和简体名称。新存档会额外记录稳定的 `skill_id`，旧存档中的繁体技能名仍可读取。

## 怪物名称本地化

怪物属性和查询仍以 Monster ID 为稳定键。程序会合并 `data/monsters.json` 中的预设和 `data/monster/*.json` 中的 API 缓存，并通过 `lang/monsters/zh_CN.json` 提供简体显示名称；人工校对应写入 `lang/monsters/zh_CN_overrides.json`。

重新生成和检查怪物语言包：

```bash
python scripts/generate_monster_zh_cn.py
python tools/check_monster_localization.py
```

怪物查询支持 Monster ID、简体名、繁体原名、缓存名称和内部 DBName。预设列表、查询结果及 RRF 中能够匹配本地目录的目标名称会按当前语言显示；未知数字 ID 仍可继续通过 Divine Pride API 查询。

当前覆盖仓库内已有的 17 个预设/缓存 Monster ID。完整 CRO 怪物目录尚未纳入仓库，后续接入稳定数据源后可沿用同一覆盖机制扩充。

## 来源与致谢

本项目基于 [z2911902/ROItemSearchApp](https://github.com/z2911902/ROItemSearchApp) 的代码与功能设计继续开发。感谢原作者及原项目贡献者提供的基础实现。

原项目使用教学可参考[巴哈姆特文章](https://forum.gamer.com.tw/C.php?bsn=4212&snA=439281&tnum=1)。由于本仓库针对 CRO 独立演进，部分界面和功能可能与文章内容不同。

## 免责声明

本项目为非官方玩家工具，与 Gravity、CRO《仙境传说：起源》运营方及相关权利方无隶属或授权关系。游戏名称、商标和数据的权利归其各自权利人所有。
