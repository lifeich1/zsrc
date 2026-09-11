---
name: calory
description: 记录每日饮食并按食物库计算热量与宏量营养素（蛋白质/脂肪/碳水），查看当天、本周、本月汇总与体重趋势。当用户提到吃了什么、要记录某一餐、询问今天还能吃多少热量、查看热量或体重统计时使用。
license: MIT
metadata:
  author: lintd
  version: "1.3"
---

# calory —— 每日热量与宏量记录

容器内已装好 `cal` 命令（`/usr/local/bin/cal`，wrapper 会自动挑选 Python 解释器），
数据根目录是挂载进来的仓库 `/zsrc` 下的 `calory/`（宿主 `zsrc/calory/`），
所以每次记录都会直接落到 git 可追踪的 JSON 文件里。

## 基本约定

- 餐次：`breakfast` / `lunch` / `dinner` / `snack`，也接受中文 `早餐` / `午餐` / `晚餐` / `加餐` 与唯一前缀（如 `加`）。
- 日期：默认今天。支持 `today` / `今天` / `昨天` / `前天`、`2025-09-10`、`09-10`，用 `-d` 指定，如 `cal add snack 苹果 1个 -d 昨天`。
- 数量：`200g`、`2个`、`1杯`……省略则用食物库里的默认份量。质量单位（`g`/`克`/`kg`/`ml`/`升`）按克换算；计数单位（`个`/`杯`/`份`…）依赖食物库里的单个克重。
- 输出是中文纯文本，没有 JSON 选项；需要核对数值时读输出，或 `cat /zsrc/calory/data/meals/<YYYY-MM-DD>.json`。
- 热量与宏量是**写入时的快照**：之后改食物库不会影响历史记录。

## 数据来源（新入库强制）

新食物的营养值**必须先查权威数据源**，再用 `cal food add --source <来源>` 标注来源。
**不得凭记忆填写热量，不得留空 `--source`**。

| 优先级 | 来源标签 | 数据源 | 适用场景 | 在线查询方式 |
| --- | --- | --- | --- | --- |
| 1 | `CFCT` | 中国食物成分表（第6版）· 中国疾控中心营养与健康所编著 | 中餐食材、中式加工食品、主食、蔬菜、肉类 | 检索已有库内 CFCT 条目比对口径；或查询公开转载（网易、薄荷等第三方转载，需与 CFCT 原始数值交叉核对） |
| 2 | `USDA` | USDA FoodData Central · 美国农业部农业研究局 | 西方食物、基础食材、预包装食品、通用鱼类/肉类 | https://fdc.nal.usda.gov/（网页搜索）；或 API：`curl -s "https://api.nal.usda.gov/fdc/v1/foods/search?api_key=DEMO_KEY&query=<英文名>"`（DEMO_KEY 每小时 30 次） |
| 3 | `估算` | 多源交叉估算 | 外卖、餐厅混合菜、两权威源均查不到的食物 | 按主要原料重量加权估算，在汇报中说明估算依据与主要原料数值 |

规则：
- **中餐食物优先查 CFCT**；CFCT 查不到再用 USDA；两者都查不到才允许标 `估算`。
- 查 USDA 时先用中文名搜，搜不到换英文名，对比 `per 100 g` 基值。
- `估算` 条目必须用 `--notes` 给出具体估算依据（如 `--notes "按瘦肉 100g + 油 15g 加权"`），CLI 会强制校验；禁止无依据写数。
- 新 food id 入库后 `cal show` 复核，确保预估值与当日合计不异常。

## 常用命令

| 目的 | 命令 |
| --- | --- |
| 看当天明细与合计 | `cal show` |
| 看指定日期 | `cal show 昨天` |
| 记录一餐 | `cal add lunch 鸡胸肉 200g` |
| 食物库没有时手录 | `cal add dinner --custom 外卖炒饭 700 --p 20 --f 25 --c 90` |
| 删除某条 | `cal rm lunch 2` / `cal rm 昨天 晚餐 last` |
| 查食物库 | `cal food search 鸡 / cal food list` |
| 新增食物条目（须带来源） | `cal food add 鸡胸肉 --kcal 165 --p 31 --f 3.6 --source USDA` |
| 新增估算条目（须带估算依据） | `cal food add 外卖炒饭 --kcal 700 --p 20 --f 25 --c 90 --source 估算 --notes "按米饭 400g + 油 15g 加权"` |
| 周报 / 月报 | `cal week`、`cal week -1`、`cal month 2025-09` |
| 体重 | `cal weight 70.5` / `cal weight` |
| 查看或修改目标 | `cal target` / `cal target 2000 --protein 120 --fat 65 --carb 220` |

## 记录流程

1. 先 `cal food search <关键词>` 确认食物在不在库；
2. 在库：`cal add <餐次> <食物名或别名> <数量>`；
3. 不在库：`cal add <餐次> --custom <名称> <kcal> [--p --f --c]`，常用食物可先用 `cal food search <名称>` 查重后 `cal food add` 建条目（**必须先查权威数据源并带 `--source`，估算则额外加 `--notes` 说明依据，见「数据来源」节**）；
4. 记录完用 `cal show` 复核合计与进度条，再向用户汇报已摄入与剩余热量。

## 已知限制（实测）

- **`--source` 非 `估算` 时不被 CLI 校验**：`cal food add X --kcal 100`（不带来源）仍会
  静默成功，条目也不会显示 `[来源]` 标签。
  只有 `--source 估算` 会强制要求 `--notes`（CLI 会报错）。
  所以非估算来源的条目「必须带 `--source`」仍是自律约定，
  每次 `cal food add` 后用 `cal food search <名称>` 复核标签是否写进去了。
- **`cal food add` 不校验重名，重名会静默劫持记录**：只校验 `id`，而 `id` 默认取名称，
  所以中文重名几乎不会撞 id，同名条目可以重复入库；此后 `cal add <名称>` 会静默命中其中一条
  （实测命中了后入库的那条），既不报歧义也不警告。入库前必须先 `cal food search <名称>` 查重；
  误建后按 id 精确记录（`cal add lunch rice-cooked 100g`），并手工从 `foods.json` 删掉多余条目
  （`cal food` 没有删除子命令，`foods.json` 允许手编）。
- **`--kcal` 只对 `--custom` 生效**：`cal add snack 苹果 1个 --kcal 999` 会静默忽略 `--kcal`，
  仍按食物库快照记 95 kcal，不报错。别用它覆盖库值或核对数值。
- **`cal add` 的日期只能走 `-d`**：位置参数固定是 `<餐次> <食物> <数量>`，写成
  `cal add 前天 早餐 米饭 100g` 会报 `unrecognized arguments: 100g`（exit 2），
  正确写法是 `cal add 早餐 米饭 100g -d 前天`。只有 `cal show` / `cal rm` 把日期当位置参数。
- **质量单位的食物不能按「杯/份」计量**：库内 `酸奶` 是「每 100 g」，`cal add lunch 酸奶 1杯`
  会报「缺少 grams，无法按「杯」计量；请改用 g」；改用 `g` / `ml`，或先给该食物补 `grams`。
- **`CALORY_HOME` 必须指向含 `cal` 入口脚本的仓库根**：`/usr/local/bin/cal` 只是挑解释器的
  wrapper，会 `exec "$CALORY_HOME/cal"`（默认 `/zsrc/calory`）；指向裸数据目录会报
  `can't open file '.../cal'`。要在别处试命令得整仓复制（连 `calory/` 包一起）。
- **改过 `foods.json` 后跑一次自检**：`cd /zsrc/calory && python3 -m unittest discover tests`
  （80 用例；测试自己把 `CALORY_HOME` 指到临时目录，不会碰真实数据）。
- **容器内 `/zsrc` 是完整 git 工作树**（整个仓库含 `.git` 一起挂载），但镜像内不保证有
  `git` 二进制，也没配 `user.name` / `user.email` 与推送凭证，所以 `git status` / `git log`
  能不能跑取决于镜像；`git add` / `git commit` / `git push` 仍建议在宿主仓库做，
  不要因为容器里 `git` 能用就往容器里塞凭证。
- **估算依据存于 `foods.json` 的 `notes` 字段**：`--source 估算` 的条目 CLI 强制要求
  `--notes`，估算依据落盘后可回溯；`cal food search` 也会展示。
  之前的旧条目无 `notes` 字段则视为空缺（向前兼容）。
- **不要用 `head`/`tail`/`less` 管道截断 `cal` 输出**：SIGPIPE 未处理，会抛
  `BrokenPipeError` 回溯（如 `cal food list | head`）。需要少看几行就直接跑完整命令，
  输出本来就不长。

## 不要做的事

- 不要手写或编辑 `/zsrc/calory/data/meals/*.json`、`/zsrc/calory/data/weight.json`——一律走 CLI，避免破坏快照语义与餐次结构。
- 不要凭记忆填热量或留空 `--source`：新入库食物必须先查 CFCT/USDA 权威数据源（见「数据来源」节），无法查到权威数值才允许标 `估算` 并用 `--notes` 给出估算依据。
- 不要自己按「每 100g」心算份量：`cal` 会按 `qty` + `unit` 自动换算。
- 记录完成后提醒用户：数据落在仓库 `calory/data/`（容器内 `/zsrc/calory/data/`），需要自己 `git add` / `git commit` 才会同步到其他设备。
