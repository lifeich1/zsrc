---
name: calory
description: 记录每日饮食并按食物库计算热量与宏量营养素（蛋白质/脂肪/碳水），查看当天、本周、本月汇总与体重趋势。当用户提到吃了什么、要记录某一餐、询问今天还能吃多少热量、查看热量或体重统计时使用。
license: MIT
metadata:
  author: lintd
  version: "1.0"
---

# calory —— 每日热量与宏量记录

容器内已装好 `cal` 命令（`/usr/local/bin/cal`，wrapper 会自动挑选 Python 解释器），
数据根目录是挂载进来的仓库目录 `/calory`（宿主 `zsrc/calory/`），
所以每次记录都会直接落到 git 可追踪的 JSON 文件里。

## 基本约定

- 餐次：`breakfast` / `lunch` / `dinner` / `snack`，也接受中文 `早餐` / `午餐` / `晚餐` / `加餐` 与唯一前缀（如 `加`）。
- 日期：默认今天。支持 `today` / `今天` / `昨天` / `前天`、`2025-09-10`、`09-10`，用 `-d` 指定，如 `cal add snack 苹果 1个 -d 昨天`。
- 数量：`200g`、`2个`、`1杯`……省略则用食物库里的默认份量。质量单位（`g`/`克`/`kg`/`ml`/`升`）按克换算；计数单位（`个`/`杯`/`份`…）依赖食物库里的单个克重。
- 输出是中文纯文本，没有 JSON 选项；需要核对数值时读输出，或 `cat /calory/data/meals/<YYYY-MM-DD>.json`。
- 热量与宏量是**写入时的快照**：之后改食物库不会影响历史记录。

## 常用命令

| 目的 | 命令 |
| --- | --- |
| 看当天明细与合计 | `cal show` |
| 看指定日期 | `cal show 昨天` |
| 记录一餐 | `cal add lunch 鸡胸肉 200g` |
| 食物库没有时手录 | `cal add dinner --custom 外卖炒饭 700 --p 20 --f 25 --c 90` |
| 删除某条 | `cal rm lunch 2` / `cal rm 昨天 晚餐 last` |
| 查食物库 | `cal food search 鸡` |
| 周报 / 月报 | `cal week`、`cal week -1`、`cal month 2025-09` |
| 体重 | `cal weight 70.5` / `cal weight` |
| 查看或修改目标 | `cal target` / `cal target 2000 --protein 120 --fat 65 --carb 220` |

## 记录流程

1. 先 `cal food search <关键词>` 确认食物在不在库；
2. 在库：`cal add <餐次> <食物名或别名> <数量>`；
3. 不在库：`cal add <餐次> --custom <名称> <kcal> [--p --f --c]`，常用食物可先用 `cal food add` 建条目；
4. 记录完用 `cal show` 复核合计与进度条，再向用户汇报已摄入与剩余热量。

## 不要做的事

- 不要手写或编辑 `/calory/data/meals/*.json`、`/calory/data/weight.json`——一律走 CLI，避免破坏快照语义与餐次结构。
- 不要自己按「每 100g」心算份量：`cal` 会按 `qty` + `unit` 自动换算。
- 记录完成后提醒用户：数据落在仓库 `calory/data/`，需要自己 `git add` / `git commit` 才会同步到其他设备。
