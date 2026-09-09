"""calory 单元测试。

运行：
    cd calory && python3 -m unittest discover tests
"""

from __future__ import annotations

import contextlib
import io
import os
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from calory import cli, config, foods, report, store  # noqa: E402
from calory.models import Config, DayLog, Entry, MacroTargets, WeightLog  # noqa: E402


class TempHomeMixin:
    """把 CALORY_HOME 指向临时目录，隔离测试数据。"""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._old_home = os.environ.get("CALORY_HOME")
        os.environ["CALORY_HOME"] = self._tmp.name

    def tearDown(self) -> None:
        if self._old_home is None:
            os.environ.pop("CALORY_HOME", None)
        else:
            os.environ["CALORY_HOME"] = self._old_home
        self._tmp.cleanup()


class DateParsingTest(unittest.TestCase):
    TODAY = date(2025, 9, 10)

    def test_relative_aliases(self) -> None:
        cases = {
            "today": date(2025, 9, 10),
            "今天": date(2025, 9, 10),
            "yesterday": date(2025, 9, 9),
            "昨天": date(2025, 9, 9),
            "前天": date(2025, 9, 8),
            "tomorrow": date(2025, 9, 11),
            "明天": date(2025, 9, 11),
            "": date(2025, 9, 10),
            None: date(2025, 9, 10),
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(store.parse_date(text, today=self.TODAY), expected)

    def test_absolute_formats(self) -> None:
        for text in ("2025-09-01", "2025/09/01", "2025.09.01", "20250901"):
            with self.subTest(text=text):
                self.assertEqual(
                    store.parse_date(text, today=self.TODAY), date(2025, 9, 1)
                )

    def test_month_day_fills_current_year(self) -> None:
        for text in ("09-01", "9/1", "9.1"):
            with self.subTest(text=text):
                self.assertEqual(
                    store.parse_date(text, today=self.TODAY), date(2025, 9, 1)
                )

    def test_date_object_passthrough(self) -> None:
        d = date(2024, 1, 2)
        self.assertEqual(store.parse_date(d, today=self.TODAY), d)

    def test_invalid_raises(self) -> None:
        for text in ("不是日期", "2025-13-01", "13-40", "2025/9"):
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    store.parse_date(text, today=self.TODAY)

    def test_parse_month(self) -> None:
        self.assertEqual(store.parse_month("2025-09"), (2025, 9))
        self.assertEqual(store.parse_month("202509"), (2025, 9))
        self.assertEqual(store.parse_month("2025/9"), (2025, 9))
        self.assertEqual(store.parse_month(None, today=self.TODAY), (2025, 9))
        with self.assertRaises(ValueError):
            store.parse_month("2025", today=self.TODAY)

    def test_week_bounds(self) -> None:
        monday, sunday = store.week_bounds(self.TODAY)
        self.assertEqual(monday, date(2025, 9, 8))
        self.assertEqual(sunday, date(2025, 9, 14))
        self.assertEqual(store.week_bounds(date(2025, 9, 8)), (monday, sunday))
        self.assertEqual(store.week_bounds(date(2025, 9, 14)), (monday, sunday))

    def test_month_bounds(self) -> None:
        self.assertEqual(store.month_bounds(2025, 9), (date(2025, 9, 1), date(2025, 9, 30)))
        self.assertEqual(
            store.month_bounds(2025, 12), (date(2025, 12, 1), date(2025, 12, 31))
        )
        self.assertEqual(
            store.month_bounds(2024, 2), (date(2024, 2, 1), date(2024, 2, 29))
        )

    def test_date_range(self) -> None:
        days = store.date_range(date(2025, 9, 8), date(2025, 9, 10))
        self.assertEqual([d.isoformat() for d in days], ["2025-09-08", "2025-09-09", "2025-09-10"])
        self.assertEqual(store.date_range(date(2025, 9, 10), date(2025, 9, 8)), [])


class JsonIoTests(TempHomeMixin, unittest.TestCase):
    def test_write_then_read(self) -> None:
        path = Path(self._tmp.name) / "sub" / "a.json"
        store.write_json(path, {"b": 1, "中文": "值"})
        self.assertEqual(store.read_json(path), {"b": 1, "中文": "值"})
        self.assertTrue(path.read_text(encoding="utf-8").endswith("\n"))

    def test_read_missing_returns_default(self) -> None:
        self.assertIsNone(store.read_json(Path(self._tmp.name) / "nope.json"))
        self.assertEqual(
            store.read_json(Path(self._tmp.name) / "nope.json", default={}), {}
        )

    def test_read_broken_json_raises(self) -> None:
        path = Path(self._tmp.name) / "broken.json"
        path.write_text("{not json", encoding="utf-8")
        with self.assertRaises(ValueError):
            store.read_json(path)

    def test_no_tmp_file_left(self) -> None:
        path = Path(self._tmp.name) / "a.json"
        store.write_json(path, {"x": 1})
        leftovers = [p.name for p in path.parent.iterdir() if p.name != "a.json"]
        self.assertEqual(leftovers, [])


class DayLogStoreTest(TempHomeMixin, unittest.TestCase):
    def _entry(self, name: str = "鸡胸肉", kcal: float = 330.0) -> Entry:
        return Entry(
            name=name,
            qty=200,
            unit="g",
            grams=200,
            kcal=kcal,
            protein_g=62.0,
            fat_g=7.2,
            carb_g=0.0,
            food_id="chicken-breast",
        )

    def test_load_missing_is_empty(self) -> None:
        log = store.load_day("2025-09-10")
        self.assertEqual(log.date, "2025-09-10")
        self.assertTrue(log.is_empty())
        self.assertEqual(log.totals()["kcal"], 0.0)

    def test_roundtrip_keeps_snapshot(self) -> None:
        log = store.load_day("2025-09-10")
        log.add("lunch", self._entry())
        store.save_day(log)
        back = store.load_day("2025-09-10")
        self.assertEqual(len(back.meals["lunch"]), 1)
        entry = back.meals["lunch"][0]
        self.assertEqual(entry.food_id, "chicken-breast")
        self.assertEqual(entry.grams, 200)
        self.assertAlmostEqual(back.totals()["kcal"], 330.0)
        self.assertAlmostEqual(back.totals()["protein_g"], 62.0)

    def test_saving_empty_day_removes_file(self) -> None:
        log = store.load_day("2025-09-10")
        log.add("lunch", self._entry())
        store.save_day(log)
        path = store.day_path(date(2025, 9, 10))
        self.assertTrue(path.exists())
        log.remove("lunch", 1)
        self.assertIsNone(store.save_day(log))
        self.assertFalse(path.exists())

    def test_list_day_dates_filtered(self) -> None:
        for text in ("2025-09-08", "2025-09-10", "2025-10-01"):
            log = store.load_day(text)
            log.add("lunch", self._entry())
            store.save_day(log)
        self.assertEqual(
            [d.isoformat() for d in store.list_day_dates()],
            ["2025-09-08", "2025-09-10", "2025-10-01"],
        )
        self.assertEqual(
            [d.isoformat() for d in store.list_day_dates(date(2025, 9, 9), date(2025, 9, 30))],
            ["2025-09-10"],
        )

    def test_unknown_fields_ignored(self) -> None:
        """旧版本数据多出字段时不应报错（向前兼容）。"""
        log = DayLog.from_dict(
            {
                "date": "2025-09-10",
                "future_key": 1,
                "meals": {
                    "lunch": [
                        {"name": "米饭", "qty": 150, "unit": "g", "grams": 150,
                         "kcal": 174, "legacy_note": "x"}
                    ]
                },
            }
        )
        self.assertEqual(log.meals["lunch"][0].name, "米饭")
        self.assertEqual(log.meals["lunch"][0].food_id, None)


class WeightStoreTest(TempHomeMixin, unittest.TestCase):
    def test_roundtrip_and_latest(self) -> None:
        w = store.load_weight()
        self.assertEqual(w.entries, {})
        w.record("2025-09-10", 70.5)
        w.record("2025-09-08", 71.0)
        store.save_weight(w)
        back = store.load_weight()
        self.assertEqual(back.sorted_items(), [("2025-09-08", 71.0), ("2025-09-10", 70.5)])
        self.assertEqual(back.latest(), ("2025-09-10", 70.5))

    def test_empty_log_removes_file(self) -> None:
        store.save_weight(WeightLog(entries={"2025-09-10": 70.0}))
        self.assertTrue(store.weight_file().exists())
        self.assertIsNone(store.save_weight(WeightLog()))
        self.assertFalse(store.weight_file().exists())


class ConfigTest(TempHomeMixin, unittest.TestCase):
    def test_defaults_when_missing(self) -> None:
        cfg = config.load_config()
        self.assertEqual(cfg.target_kcal, 2000.0)
        self.assertEqual(cfg.macro_targets.protein_g, 120.0)
        self.assertEqual(cfg.meals, ["breakfast", "lunch", "dinner", "snack"])
        self.assertEqual(cfg.label("lunch"), "午餐")

    def test_roundtrip(self) -> None:
        cfg = Config(
            target_kcal=1800.0,
            macro_targets=MacroTargets(protein_g=130, fat_g=60, carb_g=200),
            weight_target_kg=68.5,
            meals=["breakfast", "lunch", "dinner"],
            meal_labels={"breakfast": "早餐", "lunch": "午餐", "dinner": "晚餐"},
        )
        config.save_config(cfg)
        back = config.load_config()
        self.assertEqual(back.target_kcal, 1800.0)
        self.assertEqual(back.macro_targets.carb_g, 200.0)
        self.assertEqual(back.weight_target_kg, 68.5)
        self.assertEqual(back.meals, ["breakfast", "lunch", "dinner"])

    def test_resolve_meal(self) -> None:
        cfg = Config()
        self.assertEqual(cfg.resolve_meal("lunch"), "lunch")
        self.assertEqual(cfg.resolve_meal("LUNCH"), "lunch")
        self.assertEqual(cfg.resolve_meal("午餐"), "lunch")
        self.assertEqual(cfg.resolve_meal("加"), "snack")
        with self.assertRaises(ValueError):
            cfg.resolve_meal("夜宵")
        with self.assertRaises(ValueError):
            cfg.resolve_meal("")

    def test_resolve_meal_ambiguous(self) -> None:
        cfg = Config(meals=["lunch", "lunch2"], meal_labels={})
        with self.assertRaises(ValueError):
            cfg.resolve_meal("lun")

    def test_config_json_from_repo_file(self) -> None:
        """仓库里的 config.json 必须能被解析。"""
        cfg = config.load_config(Path(__file__).resolve().parent.parent / "config.json")
        self.assertEqual(cfg.target_kcal, 2000.0)
        self.assertEqual(cfg.meal_labels["dinner"], "晚餐")


class UnitConversionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.chicken = foods.build_food(
            "鸡胸肉", 165, per=100, unit="g", protein_g=31.0, fat_g=3.6
        )
        self.egg = foods.build_food(
            "鸡蛋", 72, per=1, unit="个", grams=50, protein_g=6.3, fat_g=4.8, carb_g=0.4
        )
        self.milk = foods.build_food(
            "全脂牛奶", 61, per=100, unit="ml", protein_g=3.2, fat_g=3.3, carb_g=4.8
        )

    def test_mass_units(self) -> None:
        cases = [(200, "g", 200.0), (150, "克", 150.0), (0.2, "kg", 200.0), (1, "千克", 1000.0)]
        for qty, unit, expected in cases:
            with self.subTest(unit=unit):
                self.assertAlmostEqual(foods.to_grams(self.chicken, qty, unit), expected)

    def test_ml_counts_as_gram(self) -> None:
        self.assertAlmostEqual(foods.to_grams(self.milk, 250, "ml"), 250.0)
        self.assertAlmostEqual(foods.to_grams(self.milk, 250, "毫升"), 250.0)

    def test_default_unit_used_when_missing(self) -> None:
        self.assertAlmostEqual(foods.to_grams(self.chicken, 100), 100.0)
        self.assertAlmostEqual(foods.to_grams(self.egg, 2), 100.0)

    def test_count_unit_uses_grams(self) -> None:
        self.assertAlmostEqual(foods.to_grams(self.egg, 2, "个"), 100.0)

    def test_count_unit_without_grams_raises(self) -> None:
        bread = foods.build_food("白面包", 265, per=100, unit="g")
        with self.assertRaises(ValueError):
            foods.to_grams(bread, 1, "片")

    def test_base_grams(self) -> None:
        self.assertAlmostEqual(foods.base_grams(self.chicken), 100.0)
        self.assertAlmostEqual(foods.base_grams(self.egg), 50.0)
        self.assertAlmostEqual(foods.base_grams(self.milk), 100.0)

    def test_parse_amount(self) -> None:
        self.assertEqual(foods.parse_amount("200g"), (200.0, "g"))
        self.assertEqual(foods.parse_amount("2 个"), (2.0, "个"))
        self.assertEqual(foods.parse_amount("1.5"), (1.5, None))
        self.assertEqual(foods.parse_amount(" 0.25 kg "), (0.25, "kg"))
        for bad in ("", "abc", "g", "-1", "0"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    foods.parse_amount(bad)


class ComputeEntryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.chicken = foods.build_food(
            "鸡胸肉", 165, per=100, unit="g", protein_g=31.0, fat_g=3.6, carb_g=0.0,
            aliases=["鸡胸"], source="USDA",
        )
        self.egg = foods.build_food(
            "鸡蛋", 72, per=1, unit="个", grams=50, protein_g=6.3, fat_g=4.8, carb_g=0.4
        )

    def test_scales_linearly(self) -> None:
        entry = foods.compute_entry(self.chicken, 200, "g")
        self.assertAlmostEqual(entry.kcal, 330.0)
        self.assertAlmostEqual(entry.protein_g, 62.0)
        self.assertAlmostEqual(entry.fat_g, 7.2)
        self.assertAlmostEqual(entry.carb_g, 0.0)
        self.assertAlmostEqual(entry.grams, 200.0)
        self.assertEqual(entry.unit, "g")
        self.assertEqual(entry.food_id, "鸡胸肉")

    def test_same_grams_give_same_result(self) -> None:
        by_count = foods.compute_entry(self.egg, 2, "个")
        by_weight = foods.compute_entry(self.egg, 100, "g")
        self.assertAlmostEqual(by_count.kcal, by_weight.kcal)
        self.assertAlmostEqual(by_count.kcal, 144.0)
        self.assertAlmostEqual(by_count.protein_g, 12.6)

    def test_rounding_to_one_decimal(self) -> None:
        entry = foods.compute_entry(self.chicken, 137, "g")
        self.assertEqual(entry.kcal, round(165 * 1.37, 1))
        self.assertEqual(entry.grams, 137.0)

    def test_custom_entry(self) -> None:
        entry = foods.custom_entry("外卖炒饭", 700, protein_g=20, fat_g=25, carb_g=90)
        self.assertEqual(entry.name, "外卖炒饭")
        self.assertEqual(entry.unit, "份")
        self.assertIsNone(entry.food_id)
        self.assertAlmostEqual(entry.kcal, 700.0)
        with self.assertRaises(ValueError):
            foods.custom_entry("  ", 100)


class MatchFoodTest(unittest.TestCase):
    def setUp(self) -> None:
        self.library = [
            foods.build_food("鸡胸肉", 165, per=100, unit="g", aliases=["鸡胸", "chicken breast"], food_id="chicken-breast"),
            foods.build_food("鸡蛋", 72, per=1, unit="个", grams=50, aliases=["蛋"]),
            foods.build_food("蛋炒饭", 200, per=100, unit="g", aliases=["炒饭"]),
            foods.build_food("米饭", 116, per=100, unit="g", aliases=["白米饭"]),
        ]

    def test_id_exact_wins(self) -> None:
        self.assertEqual(foods.find_food("chicken-breast", self.library).name, "鸡胸肉")

    def test_name_exact_wins_over_alias(self) -> None:
        self.assertEqual(foods.find_food("鸡蛋", self.library).name, "鸡蛋")

    def test_alias_exact(self) -> None:
        self.assertEqual(foods.find_food("炒饭", self.library).name, "蛋炒饭")
        self.assertEqual(foods.find_food("chicken breast", self.library).name, "鸡胸肉")

    def test_contains_prefers_shortest_name(self) -> None:
        self.assertEqual(foods.find_food("蛋", self.library).name, "鸡蛋")
        self.assertEqual(foods.find_food("米", self.library).name, "米饭")

    def test_no_match(self) -> None:
        self.assertIsNone(foods.find_food("披萨", self.library))
        self.assertIsNone(foods.find_food("", self.library))

    def test_suggest_orders_by_similarity(self) -> None:
        hits = foods.suggest_foods("鸡胸", self.library)
        self.assertTrue(hits)
        self.assertEqual(hits[0].name, "鸡胸肉")

    def test_suggest_empty_for_unrelated(self) -> None:
        self.assertEqual(foods.suggest_foods("zzz", self.library), [])


class LoadFoodsTest(TempHomeMixin, unittest.TestCase):
    def _write(self, payload: object) -> None:
        store.write_json(store.foods_file(), payload)

    def test_missing_file_returns_empty(self) -> None:
        self.assertEqual(foods.load_foods(), [])

    def test_bare_list_supported(self) -> None:
        self._write([{"id": "a", "name": "食物", "kcal": 10, "per": 100, "unit": "g"}])
        library = foods.load_foods()
        self.assertEqual(len(library), 1)
        self.assertEqual(library[0].name, "食物")

    def test_duplicate_id_rejected(self) -> None:
        self._write(
            {
                "foods": [
                    {"id": "a", "name": "A", "kcal": 10, "per": 100, "unit": "g"},
                    {"id": "a", "name": "B", "kcal": 20, "per": 100, "unit": "g"},
                ]
            }
        )
        with self.assertRaises(ValueError):
            foods.load_foods()

    def test_missing_name_rejected(self) -> None:
        self._write({"foods": [{"id": "a", "kcal": 10, "per": 100, "unit": "g"}]})
        with self.assertRaises(ValueError):
            foods.load_foods()

    def test_count_unit_without_grams_rejected(self) -> None:
        self._write({"foods": [{"id": "a", "name": "A", "kcal": 10, "per": 1, "unit": "碗"}]})
        with self.assertRaises(ValueError):
            foods.load_foods()

    def test_bad_top_level_rejected(self) -> None:
        self._write("nope")
        with self.assertRaises(ValueError):
            foods.load_foods()

    def test_save_roundtrip(self) -> None:
        library = [foods.build_food("米饭", 116, per=100, unit="g", protein_g=2.6)]
        foods.save_foods(library)
        back = foods.load_foods()
        self.assertEqual(back[0].id, "米饭")
        self.assertAlmostEqual(back[0].protein_g, 2.6)

    def test_append_food_uniquifies_id(self) -> None:
        library = [foods.build_food("米饭", 116, per=100, unit="g")]
        foods.save_foods(library)
        added = foods.append_food(foods.build_food("米饭", 120, per=100, unit="g"), library)
        self.assertEqual(added.id, "米饭-2")
        self.assertEqual(len(foods.load_foods()), 2)

    def test_builtin_library_loads(self) -> None:
        path = Path(__file__).resolve().parent.parent / "data" / "foods.json"
        library = foods.load_foods(path)
        self.assertGreaterEqual(len(library), 90)
        self.assertEqual(len({food.id for food in library}), len(library))
        self.assertIn("鸡蛋", {food.name for food in library})


class DayLogEditTest(unittest.TestCase):
    @staticmethod
    def _entry(name: str, kcal: float, protein: float = 0.0) -> Entry:
        return Entry(name=name, qty=1, unit="份", grams=0, kcal=kcal, protein_g=protein)

    def test_add_appends_per_meal(self) -> None:
        day = DayLog(date="2025-09-10")
        day.add("lunch", self._entry("米饭", 174))
        day.add("lunch", self._entry("鸡胸肉", 330))
        day.add("dinner", self._entry("面条", 220))
        self.assertEqual([e.name for e in day.meals["lunch"]], ["米饭", "鸡胸肉"])
        self.assertEqual([e.name for e in day.meals["dinner"]], ["面条"])
        self.assertAlmostEqual(day.totals()["kcal"], 724.0)

    def test_remove_positive_index_is_one_based(self) -> None:
        day = DayLog(date="2025-09-10")
        day.add("lunch", self._entry("A", 100))
        day.add("lunch", self._entry("B", 200))
        removed = day.remove("lunch", 1)
        self.assertEqual(removed.name, "A")
        self.assertEqual([e.name for e in day.meals["lunch"]], ["B"])
        self.assertAlmostEqual(day.totals()["kcal"], 200.0)

    def test_remove_last(self) -> None:
        day = DayLog(date="2025-09-10")
        day.add("lunch", self._entry("A", 100))
        day.add("lunch", self._entry("B", 200))
        self.assertEqual(day.remove("lunch", -1).name, "B")
        self.assertAlmostEqual(day.totals()["kcal"], 100.0)

    def test_remove_out_of_range(self) -> None:
        day = DayLog(date="2025-09-10")
        day.add("lunch", self._entry("A", 100))
        for index in (0, 2, -2, 9):
            with self.subTest(index=index):
                with self.assertRaises(IndexError):
                    day.remove("lunch", index)

    def test_remove_missing_meal(self) -> None:
        with self.assertRaises(IndexError):
            DayLog(date="2025-09-10").remove("dinner", 1)

    def test_totals_stay_consistent_after_edits(self) -> None:
        day = DayLog(date="2025-09-10")
        for index in range(5):
            day.add("lunch", self._entry(f"食物{index}", 100, protein=10))
        day.remove("lunch", 3)
        day.remove("lunch", -1)
        day.add("dinner", self._entry("晚餐", 250, protein=20))
        totals = day.totals()
        self.assertAlmostEqual(totals["kcal"], 100 * 3 + 250)
        self.assertAlmostEqual(totals["protein_g"], 10 * 3 + 20)
        self.assertEqual(len(day.meals["lunch"]), 3)

    def test_is_empty(self) -> None:
        day = DayLog(date="2025-09-10")
        self.assertTrue(day.is_empty())
        day.add("lunch", self._entry("A", 100))
        self.assertFalse(day.is_empty())
        day.remove("lunch", 1)
        self.assertTrue(day.is_empty())


class ReportRenderTest(unittest.TestCase):
    def setUp(self) -> None:
        self.config = Config()

    def test_progress_bar_bounds(self) -> None:
        self.assertEqual(report.progress_bar(0), "[" + "░" * report.BAR_WIDTH + "]")
        self.assertEqual(report.progress_bar(1), "[" + "█" * report.BAR_WIDTH + "]")
        self.assertEqual(report.progress_bar(2), report.progress_bar(1))
        self.assertEqual(report.progress_bar(-1), report.progress_bar(0))
        self.assertEqual(report.progress_bar(0.5).count("█"), report.BAR_WIDTH // 2)

    def test_is_on_target(self) -> None:
        self.assertTrue(report.is_on_target(2000, 2000))
        self.assertTrue(report.is_on_target(1850, 2000))
        self.assertFalse(report.is_on_target(1700, 2000))
        self.assertFalse(report.is_on_target(100, 0))

    def test_render_day_contains_details(self) -> None:
        day = DayLog(date="2025-09-10")
        day.add("lunch", Entry(name="鸡胸肉", qty=200, unit="g", grams=200, kcal=330, protein_g=62))
        text = report.render_day(day, self.config)
        self.assertIn("2025-09-10", text)
        self.assertIn("周三", text)
        self.assertIn("午餐", text)
        self.assertIn("鸡胸肉", text)
        self.assertIn("330", text)
        self.assertIn("16.5%", text)
        self.assertIn("剩余", text)

    def test_render_day_empty(self) -> None:
        text = report.render_day(DayLog(date="2025-09-10"), self.config)
        self.assertIn("还没有记录", text)
        self.assertIn("0 / 2000 kcal", text)

    def test_render_day_overflow(self) -> None:
        day = DayLog(date="2025-09-10")
        day.add("lunch", Entry(name="大餐", qty=1, unit="份", grams=0, kcal=2500))
        text = report.render_day(day, self.config)
        self.assertIn("超出 500", text)

    def test_render_week_summary(self) -> None:
        days = []
        for offset, kcal in enumerate((2000, 1800, 1000)):
            day = DayLog(date=store.date_range(date(2025, 9, 8), date(2025, 9, 10))[offset].isoformat())
            day.add("lunch", Entry(name="餐", qty=1, unit="份", grams=0, kcal=kcal, protein_g=50))
            days.append(day)
        weight = WeightLog(entries={"2025-09-08": 71.0, "2025-09-10": 70.4})
        text = report.render_week(days, self.config, date(2025, 9, 8), date(2025, 9, 14), weight)
        self.assertIn("周报", text)
        self.assertIn("已记录 3 / 7 天", text)
        self.assertIn("日均  1600 kcal", text)
        self.assertIn("达标  2 / 3 天", text)
        self.assertIn("体重  2025-09-08 71 kg → 2025-09-10 70.4 kg（↓ 0.6 kg）", text)

    def test_render_week_empty(self) -> None:
        text = report.render_week([], self.config, date(2025, 9, 8), date(2025, 9, 14))
        self.assertIn("区间内没有记录", text)

    def test_render_month_groups_weeks(self) -> None:
        days = []
        for iso in ("2025-09-01", "2025-09-10"):
            day = DayLog(date=iso)
            day.add("lunch", Entry(name="餐", qty=1, unit="份", grams=0, kcal=2000))
            days.append(day)
        text = report.render_month(days, self.config, 2025, 9)
        self.assertIn("2025年9月 月报", text)
        self.assertIn("按周：", text)
        self.assertIn("第 1 周", text)
        self.assertIn("第 2 周", text)

    def test_sparkline(self) -> None:
        self.assertEqual(report.sparkline([]), "")
        self.assertEqual(len(report.sparkline([70, 71, 72])), 3)
        self.assertEqual(report.sparkline([70, 70]), "▄▄")

    def test_render_weight(self) -> None:
        weight = WeightLog(entries={"2025-09-08": 71.0, "2025-09-09": 70.7})
        config_obj = Config(weight_target_kg=70.0)
        text = report.render_weight(weight, config_obj)
        self.assertIn("最近 2 条", text)
        self.assertIn("2025-09-09", text)
        self.assertIn("距目标 0.7 kg", text)

    def test_render_weight_empty(self) -> None:
        self.assertIn("还没有记录", report.render_weight(WeightLog(), self.config))


class CliEndToEndTest(TempHomeMixin, unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()
        foods.save_foods(
            [
                foods.build_food("鸡胸肉", 165, per=100, unit="g", protein_g=31.0, fat_g=3.6),
                foods.build_food("米饭", 116, per=100, unit="g", protein_g=2.6, carb_g=25.9),
            ]
        )

    def _run(self, *argv: str) -> tuple[int, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.main(list(argv))
        return code, out.getvalue() + err.getvalue()

    def test_add_show_rm_flow(self) -> None:
        code, out = self._run("add", "lunch", "鸡胸肉", "200g")
        self.assertEqual(code, 0)
        self.assertIn("330", out)

        code, out = self._run("show")
        self.assertEqual(code, 0)
        self.assertIn("午餐", out)
        self.assertIn("330", out)

        code, out = self._run("rm", "lunch", "1")
        self.assertEqual(code, 0)
        self.assertIn("已删除", out)

        code, out = self._run("show")
        self.assertIn("还没有记录", out)

    def test_totals_after_multiple_adds_and_removes(self) -> None:
        for amount in ("100g", "100g", "150g"):
            code, _ = self._run("add", "lunch", "米饭", amount)
            self.assertEqual(code, 0)
        code, out = self._run("rm", "lunch", "2")
        self.assertEqual(code, 0)
        # 100 + 150 = 250 g 米饭 -> 290 kcal
        self.assertIn("290 / 2000 kcal", out)

    def test_add_unknown_food_fails(self) -> None:
        code, out = self._run("add", "lunch", "披萨", "1个")
        self.assertEqual(code, 1)
        self.assertIn("食物库里没有", out)

    def test_rm_on_empty_day_fails(self) -> None:
        code, out = self._run("rm", "lunch", "1")
        self.assertEqual(code, 1)
        self.assertIn("没有记录", out)

    def test_add_custom(self) -> None:
        code, out = self._run("add", "dinner", "--custom", "外卖炒饭", "700", "--p", "20")
        self.assertEqual(code, 0)
        self.assertIn("700 kcal", out)
        day = store.load_day(None)
        self.assertEqual(day.meals["dinner"][0].food_id, None)

    def test_weight_week_month_target_flow(self) -> None:
        self.assertEqual(self._run("add", "lunch", "米饭", "200g")[0], 0)
        self.assertEqual(self._run("weight", "70")[0], 0)

        code, out = self._run("weight")
        self.assertEqual(code, 0)
        self.assertIn("最近 1 条", out)

        code, out = self._run("week")
        self.assertEqual(code, 0)
        self.assertIn("周报", out)
        self.assertIn("232 kcal", out)  # 200 g 米饭

        code, out = self._run("week", "-1")
        self.assertEqual(code, 0)
        self.assertIn("周报", out)

        code, out = self._run("month")
        self.assertEqual(code, 0)
        self.assertIn("月报", out)

        code, out = self._run("target", "1800", "--protein", "130", "--weight", "68")
        self.assertEqual(code, 0)
        self.assertIn("热量  1800 kcal", out)
        self.assertIn("蛋白 130 g", out)
        self.assertIn("体重  68 kg", out)

        # 目标写入 config.json 后，日报按新目标计算
        code, out = self._run("show")
        self.assertIn("/ 1800 kcal", out)

    def test_weight_rejects_non_positive(self) -> None:
        code, out = self._run("weight", "0")
        self.assertEqual(code, 1)
        self.assertIn("必须大于 0", out)


if __name__ == "__main__":
    unittest.main()
