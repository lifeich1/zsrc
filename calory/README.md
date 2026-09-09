# calory

记录每日菜单、计算热量与宏量营养素的小工具。

- 纯 Python 3 标准库实现，**零第三方依赖**；
- 数据是纯文本 JSON，git diff 友好、可跨设备同步；
- 食物库可自建（内置约 100 条常见食物，标注来源）。

## 快速开始

```bash
cd calory

./cal add lunch 鸡胸肉 200g      # 记录午餐
./cal add lunch 鸡蛋 2个
./cal show                       # 看当天明细与合计
./cal weight 70.5                # 记录体重
./cal week                       # 本周汇总
```

`./cal --help` 查看全部命令。

## 目录结构

```
calory/
├── cal                    # 可执行入口（python3）
├── config.json            # 个人目标：热量、宏量、体重、餐次
├── calory/
│   ├── cli.py             # 子命令分发
│   ├── models.py          # 数据模型（Food/Entry/DayLog/WeightLog/Config）
│   ├── store.py           # JSON 原子读写、路径与日期解析
│   ├── foods.py           # 食物库加载/匹配、单位换算、热量计算
│   ├── report.py          # 日报/周报/月报渲染、进度条、体重趋势
│   └── config.py          # config.json 读写
├── data/
│   ├── foods.json         # 食物营养库（可自建）
│   ├── meals/
│   │   └── 2025-09-10.json
│   └── weight.json        # 体重记录
└── tests/
    └── test_calory.py
```

数据根目录默认为本目录，可用环境变量 `CALORY_HOME` 指向别处（测试或维护多份数据时很方便）。

## 命令

| 命令 | 说明 |
| --- | --- |
| `cal add <餐次> <食物> [数量]` | 记录一条；数量如 `200g`、`2个`，省略则用食物默认份量 |
| `cal add <餐次> --custom 名称 热量 [--p/--f/--c]` | 食物库没有时手动录入 |
| `cal show [日期]` | 当天（或指定日期）明细 + 合计 + 目标达成进度条 |
| `cal rm [日期] <餐次> [序号\|last]` | 删除某条记录，默认删最后一条 |
| `cal week [偏移]` | 周报：`0` 本周、`-1` 上周 |
| `cal month [YYYY-MM]` | 月报：按周分组 + 汇总 |
| `cal weight [kg]` | 记录体重；不传参数则展示记录与趋势 |
| `cal target [...]` | 查看/修改目标 |
| `cal food list\|search\|add` | 食物库操作 |

餐次支持英文键（`breakfast`/`lunch`/`dinner`/`snack`）与中文标签（`早餐`/`午餐`/`晚餐`/`加餐`），也接受唯一前缀（如 `加` → `snack`）。

日期参数支持 `today`、`今天`、`昨天`、`前天`、`2025-09-10`、`09-10`（补当年）。

### 示例

```bash
./cal add breakfast 全麦面包 80g
./cal add lunch 鸡胸肉 200g
./cal add lunch 米饭 150g
./cal add dinner --custom 外卖炒饭 700 --p 20 --f 25 --c 90
./cal add snack 苹果 1个 -d 昨天

./cal show
./cal rm lunch 2                 # 删当天午餐第 2 条
./cal rm 昨天 晚餐 last

./cal week -1
./cal month 2025-09

./cal weight 70.5
./cal weight                     # 展示最近记录与趋势图

./cal target 2000 --protein 120 --fat 65 --carb 220 --weight 70
./cal food search 鸡
./cal food add "自制沙拉" --per 1份 --grams 200 --kcal 180 --p 6 --f 12 --c 14
```

`cal show` 输出示例：

```
2025-09-10 周三   目标 2000 kcal
────────────────────────────────────────────────────────
早餐  全麦面包 80g  196.8 kcal  P6.8 F2.7 C32.8
午餐  鸡胸肉 200g  330 kcal  P62 F7.2 C0
    米饭 150g  174 kcal  P3.9 F0.4 C38.8
────────────────────────────────────────────────────────
合计  1707.8 / 2000 kcal  [██████████░░] 85.4%  剩余 292.2
宏量  蛋白 111.4/120 g（93%）   脂肪 46/65 g（71%）   碳水 200.6/220 g（91%）
```

## 数据格式

### `data/meals/YYYY-MM-DD.json`

```json
{
  "date": "2025-09-10",
  "meals": {
    "lunch": [
      {
        "food_id": "chicken-breast",
        "name": "鸡胸肉",
        "qty": 200, "unit": "g", "grams": 200,
        "kcal": 330, "protein_g": 62, "fat_g": 7.2, "carb_g": 0
      }
    ]
  }
}
```

热量与宏量是**写入时的快照**：之后修改 `foods.json` 不会改动历史记录，`food_id` 仅用于追溯来源。

### `data/foods.json`

```json
{
  "version": 1,
  "foods": [
    {"id": "rice-cooked", "name": "米饭", "aliases": ["白米饭"], "per": 100, "unit": "g",
     "kcal": 116, "protein_g": 2.6, "fat_g": 0.3, "carb_g": 25.9, "source": "CFCT"},
    {"id": "egg", "name": "鸡蛋", "aliases": ["蛋"], "per": 1, "unit": "个", "grams": 50,
     "kcal": 72, "protein_g": 6.3, "fat_g": 4.8, "carb_g": 0.4, "source": "USDA"}
  ]
}
```

- `per` + `unit`：营养值对应的份量，如「每 100 g」「每 1 个」；
- `grams`：非质量单位（个/根/杯/勺/份）的单个克重，用于换算；
- `source`：数据来源（`USDA` / `CFCT` 中国食物成分表 / `估算`）。

### `data/weight.json`

```json
{"entries": {"2025-09-10": 70.5}}
```

### `config.json`

```json
{
  "target_kcal": 2000,
  "macro_targets": {"protein_g": 120, "fat_g": 65, "carb_g": 220},
  "weight_target_kg": 70,
  "meals": ["breakfast", "lunch", "dinner", "snack"],
  "meal_labels": {"breakfast": "早餐", "lunch": "午餐", "dinner": "晚餐", "snack": "加餐"}
}
```

## 单位与换算

| 输入单位 | 处理方式 |
| --- | --- |
| `g` / `克` / `kg` / `千克` | 按质量换算 |
| `ml` / `毫升` / `l` / `升` | 近似 `1 ml = 1 g`（饮料场景足够） |
| `个` / `根` / `片` / `杯` / `勺` / `份` … | 依赖食物数据里的 `grams`（单个克重） |

若某食物的单位不是质量单位又没有 `grams`，`cal add` 会报错，提示改用 `g` 或补充食物库。

## 达标判定

周报/月报中的「达标」指当天总热量落在目标热量的 ±10% 区间内（见 `report.ON_TARGET_TOLERANCE`）。

## 测试

```bash
cd calory
python3 -m unittest discover tests
```

## 数据是否入库

默认建议把 `data/` 与 `config.json` 一起提交，方便多设备同步。若想本地私有，在仓库 `.gitignore` 里加：

```
calory/data/meals/
calory/data/weight.json
```
