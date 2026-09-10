# calory/data —— 数据文件索引

> 给维护者与 AI 助手的索引：先读本文件了解格式，**不要为看结构而逐个打开 JSON**。
> 上游说明见 [../README.md](../README.md)，数据格式的代码实现在 `../calory/store.py` 与 `../calory/foods.py`。

## 文件一览

| 文件 | 内容 | 由谁生成 |
| --- | --- | --- |
| `foods.json` | 食物营养库（当前 101 条，带 `version`） | 手写或用 `cal food add` |
| `meals/YYYY-MM-DD.json` | 每日菜单记录，一天一个文件 | `cal add` / `cal rm` |
| `weight.json` | 体重记录 | `cal weight` |

`meals/` 与 `weight.json` 按需创建；某天记录被删空、体重记录被清空时，对应文件会被自动删除（见 `store.save_day()` / `store.save_weight()`）。

## `foods.json`

顶层支持 `{"version": 1, "foods": [...]}` 或裸数组。每条字段：

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `id` | ✅ | 唯一标识，英文 slug 或中文名均可；重复会导致加载失败 |
| `name` | ✅ | 展示名称，也是默认匹配名 |
| `aliases` | | 别名数组，参与匹配与搜索 |
| `per` | ✅ | 营养值对应的份量数值（如 100） |
| `unit` | ✅ | 份量单位：`g`/`ml`/`个`/`根`/`杯`/`勺`/`份`… |
| `kcal` | ✅ | 每 `per unit` 的热量 |
| `protein_g` / `fat_g` / `carb_g` | | 每 `per unit` 的宏量（克），缺省 0 |
| `grams` | | **非质量单位必填**：单个单位的克重（如 `个: 50`） |
| `source` | | 数据来源，如 `USDA` / `CFCT` / `估算` |

## `meals/YYYY-MM-DD.json`

```json
{
  "date": "2025-09-10",
  "meals": {
    "lunch": [
      {"food_id": "chicken-breast", "name": "鸡胸肉", "qty": 200, "unit": "g", "grams": 200,
       "kcal": 330, "protein_g": 62, "fat_g": 7.2, "carb_g": 0}
    ]
  }
}
```

- 餐次键与 `config.json` 的 `meals` 对应（`breakfast`/`lunch`/`dinner`/`snack`）。
- `kcal` 与宏量是**写入时的快照**，不会跟随 `foods.json` 变化；`food_id` 仅用于追溯。
- 文件名必须是 `YYYY-MM-DD`，否则 `store.list_day_dates()` 会跳过该文件。

## `weight.json`

```json
{"entries": {"2025-09-10": 70.5}}
```

键为 ISO 日期，值为 kg。

## 手工编辑须知

1. `id` 必须唯一；非质量单位必须给 `grams`，否则 `load_foods()` 直接报错。
2. 增删当日记录优先用 CLI（`cal add` / `cal rm`），手改 JSON 容易破坏快照或餐次键。
3. 改完跑一次校验：`cd calory && python3 -m unittest discover tests`。
4. 数据量小，按天分文件是为了 git diff 干净、多设备冲突面小——不要合并成单个流水账。

## 是否纳入 git

默认提交（便于多设备同步）。若想本地私有，在仓库根 `.gitignore` 添加：

```
calory/data/meals/
calory/data/weight.json
```
