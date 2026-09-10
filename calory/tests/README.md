# calory/tests —— 测试索引

> 给维护者与 AI 助手的索引：先读本文件了解测试分布，**不要为定位用例而通读 700 行测试文件**。
> 上游说明见 [../README.md](../README.md)。

## 运行

```bash
cd calory
python3 -m unittest discover tests                       # 全部（77 个用例）
python3 -m unittest tests.test_calory.MatchFoodTest -v   # 单个测试类
python3 -W error::DeprecationWarning -m unittest discover tests   # 把弃用警告当失败
```

需要 Python 3.10+（代码使用 `X | None` 注解）。

## 隔离机制

`TempHomeMixin` 把环境变量 `CALORY_HOME` 指向临时目录，因此测试不会读写仓库里的 `data/`。
涉及文件读写的测试类**必须继承它**，并在 `setUp()` 中调用 `super().setUp()`。

## 测试分布（`test_calory.py`）

| 测试类 | 覆盖内容 |
| --- | --- |
| `DateParsingTest` | 相对日期别名、绝对格式、`MM-DD` 补年、非法值、月份/周界/月界/区间 |
| `JsonIoTests` | JSON 原子写回读、缺失文件默认值、坏 JSON 报错、无残留临时文件 |
| `DayLogStoreTest` | 每日记录往返与快照保持、空记录删文件、日期列表过滤、未知字段兼容 |
| `WeightStoreTest` | 体重往返与 `latest()`、清空后删文件 |
| `ConfigTest` | 默认配置、读写往返、`resolve_meal()` 前缀/歧义、仓库 `config.json` 可解析 |
| `UnitConversionTest` | `g/克/kg/ml` 换算、默认单位、计数单位依赖 `grams`、`parse_amount()` |
| `ComputeEntryTest` | 线性缩放、按个与按克等价、四舍五入、`custom_entry()` |
| `MatchFoodTest` | 匹配优先级（id→名称→别名→包含）、无命中、模糊候选排序 |
| `LoadFoodsTest` | 裸数组/重复 id/缺字段/非质量单位缺 grams/非法顶层、保存往返、id 唯一化、内置库校验、`notes` 往返与旧数据兼容 |
| `DayLogEditTest` | 按餐次追加、正/负索引与越界、多次增删后合计一致性、`is_empty()` |
| `ReportRenderTest` | 进度条边界、达标判定、日报/周报/月报/体重渲染、sparkline |
| `CliEndToEndTest` | `add→show→rm` 全流程、多次增删合计、未命中食物、`--custom`、`weight/week/month/target`、`food add` 估算强制 `--notes` |

## 新增测试约定

- 纯计算/渲染的用例不碰文件系统，直接构造模型对象。
- 文件读写用例继承 `TempHomeMixin`。
- CLI 端到端用 `cli.main([...])` 并配合 `contextlib.redirect_stdout/redirect_stderr`，断言**退出码**与关键文案，不要断言完整排版。
- 新增食物库或数据格式字段时，同步在 `LoadFoodsTest` / `DayLogStoreTest` 补一条兼容性用例。
