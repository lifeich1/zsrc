# calory/calory —— 源码模块索引

> 给维护者与 AI 助手的索引：**先读本文件，再按需读代码**，可避免逐个打开源文件的开销。
> 上游说明见 [../README.md](../README.md)。

## 模块职责

| 文件 | 职责 | 关键 API |
| --- | --- | --- |
| `cli.py` | argparse 子命令分发；所有用户可见文案与错误处理 | `build_parser()`、`main(argv)`、`_handle_*()`、`_register_*()`、`_fail()` |
| `models.py` | 纯数据 dataclass 与序列化，不含业务逻辑 | `Food`、`Entry`、`DayLog`、`WeightLog`、`MacroTargets`、`Config`；`to_dict()` / `from_dict()` |
| `store.py` | 路径解析、JSON 原子写、日期解析、每日记录与体重读写 | `home()`、`parse_date()`、`parse_month()`、`week_bounds()`、`month_bounds()`、`date_range()`、`load_day()`、`save_day()`、`list_day_dates()`、`load_weight()`、`save_weight()`、`read_json()`、`write_json()` |
| `foods.py` | 食物库加载校验、名称匹配、单位换算、热量计算 | `load_foods()`、`save_foods()`、`find_food()`、`suggest_foods()`、`parse_amount()`、`mass_factor()`、`base_grams()`、`to_grams()`、`compute_entry()`、`custom_entry()`、`build_food()`、`append_food()` |
| `report.py` | 纯文本渲染（日报/周报/月报/体重趋势），无副作用 | `render_day()`、`render_week()`、`render_month()`、`render_weight()`、`progress_bar()`、`sparkline()`、`is_on_target()`、`fmt_num()` |
| `config.py` | `config.json` 读写与默认值 | `load_config()`、`save_config()` |

## 依赖方向（不要反向）

```
cli    ──> config, foods, store, report
report ──> store, models
store  ──> models
foods  ──> store, models
config ──> store, models
```

无循环导入；`models.py` 不导入本项目任何模块。

## 数据流

1. 记录：`cli._handle_add` → `config.load_config()` 解析餐次 → `foods.find_food()` + `foods.parse_amount()` → `foods.compute_entry()`（生成快照）→ `store.load_day()` / `day.add()` / `store.save_day()`
2. 查看：`cli._handle_show` → `store.load_day()` → `report.render_day()`
3. 汇总：`cli._handle_week/month` → `store.date_range()` 逐日 `load_day()` → `report.render_week/month()`

## 改动前必读的不变量

- **Entry 是快照**：`kcal`/`protein_g`/`fat_g`/`carb_g` 在记录时写死，之后修改 `foods.json` 不改动历史记录；只有 `food_id` 是引用。
- **单位换算**：质量/体积单位（`g`/`克`/`kg`/`ml`/`升`）按克换算（`ml ≈ 1 g`）；其余单位依赖 `Food.grams`，缺失时 `foods.to_grams()` 抛 `ValueError`。
- **`Food.per` 语义**：营养值对应「`per` 个 `unit`」。`unit` 为 `g`/`ml` 时 `per` 通常为 100；计数单位时 `per` 通常为 1。
- **空记录不落盘**：`store.save_day()` 在 `DayLog.is_empty()` 时删除对应文件。
- **原子写**：所有写盘都走 `store.write_json()`（同目录临时文件 + `os.replace`），不要直接 `open(..., "w")`。
- **`from_dict()` 忽略未知字段**：新增字段时旧数据文件仍可读，无需迁移。
- **日期解析唯一入口**：`store.parse_date()` / `store.parse_month()`，支持 `today`/`今天`/`昨天`/`前天`、`YYYY-MM-DD`、`MM-DD`。
- **达标口径**：`report.ON_TARGET_TOLERANCE`（默认 ±10%）。

## 常见改动落点

| 需求 | 改动点 |
| --- | --- |
| 新增子命令 | `cli.py` 写 `_handle_xxx(args)` + `_register_xxx(sub)`，并在 `build_parser()` 注册；出错统一 `_fail(msg)` 返回 1 |
| 新增食物字段 | `models.Food` 加带默认值的字段 → `foods._coerce()` 校验 → 需要时在 `foods.compute_entry()` 使用；旧 `foods.json` 不必改 |
| 新增/改名餐次 | 只改 `config.json` 的 `meals` / `meal_labels`；`Config.resolve_meal()` 自动支持中文标签与唯一前缀 |
| 调整报表格式 | 只改 `report.py`；`cli.py` 不拼报表文案 |
| 调整目标或达标口径 | `config.json` + `report.ON_TARGET_TOLERANCE` |

## 约定

- 只用标准库，**不引入第三方依赖**。
- 注释、异常信息、CLI 输出一律中文。
- 全量类型注解，文件头 `from __future__ import annotations`。
- 改动涉及职责/接口/数据格式时，**同步更新本文件与 `../README.md`**。
