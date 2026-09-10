"""calory 命令行：argparse 子命令分发。

每个子命令把 ``handler`` 挂到解析结果上，``main()`` 只负责调度。
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta

from . import __version__, config, foods, report, store
from .models import Food
from .report import fmt_num as _num

EPILOG = """\
示例：
  cal add lunch 鸡胸肉 200g          记录一条食物
  cal add lunch 鸡蛋 2个
  cal add dinner --custom 外卖炒饭 700 --p 20 --f 25 --c 90
  cal show today                     查看当日明细与合计
  cal rm today lunch 2               删除当日午餐第 2 条
  cal week -1                        查看上周汇总
  cal month 2025-09
  cal weight 70.5                    记录体重
  cal food search 鸡                  搜索食物库
  cal target 2000 --protein 120      修改目标
"""


# ---------------------------------------------------------------- 小工具


def _fail(message: str) -> int:
    print(f"错误：{message}", file=sys.stderr)
    return 1


def _food_summary(food: Food) -> str:
    """一行描述一条食物。"""
    if food.unit in ("g", "ml"):
        portion = f"每 {_num(food.per)} {food.unit}"
    elif food.grams:
        portion = f"每 {_num(food.per)} {food.unit}（{_num(food.grams)} g）"
    else:
        portion = f"每 {_num(food.per)} {food.unit}"
    macros = (
        f"蛋白 {_num(food.protein_g)}g / 脂肪 {_num(food.fat_g)}g / "
        f"碳水 {_num(food.carb_g)}g"
    )
    source = f" [{food.source}]" if food.source else ""
    notes = f" — {food.notes}" if food.notes else ""
    return f"{food.name}（{food.id}） {portion}：{_num(food.kcal)} kcal，{macros}{source}{notes}"


def _match_all(keyword: str, library: list[Food]) -> list[Food]:
    """子串匹配（名称/别名/id），无命中时退回模糊候选。"""
    needle = keyword.strip().lower()
    if not needle:
        return []
    hits = [
        food
        for food in library
        if needle in food.name.lower()
        or needle in food.id.lower()
        or any(needle in alias.lower() for alias in food.aliases)
    ]
    return hits or foods.suggest_foods(keyword, library)


# ---------------------------------------------------------------- food 子命令


def _handle_food_list(args: argparse.Namespace) -> int:
    library = foods.load_foods()
    if not library:
        print("食物库为空。用 cal food add 添加，或检查 data/foods.json。")
        return 0
    print(f"食物库共 {len(library)} 条：")
    for index, food in enumerate(library, start=1):
        print(f"{index:>3}. {_food_summary(food)}")
    return 0


def _handle_food_search(args: argparse.Namespace) -> int:
    library = foods.load_foods()
    hits = _match_all(args.keyword, library)
    if not hits:
        print(f"没有找到与「{args.keyword}」相近的食物。可用 cal food add 添加。")
        return 1
    print(f"与「{args.keyword}」相关的 {len(hits)} 条：")
    for index, food in enumerate(hits, start=1):
        print(f"{index:>3}. {_food_summary(food)}")
    return 0


def _handle_food_add(args: argparse.Namespace) -> int:
    source = (args.source or "").strip()
    notes = (args.notes or "").strip()
    if source == "估算" and not notes:
        return _fail("source=估算 时必须提供 --notes 说明估算依据（如「按瘦肉 100g + 油 15g 加权」）")
    library = foods.load_foods()
    try:
        per, unit = foods.parse_amount(args.per)
    except ValueError as exc:
        return _fail(f"--per 参数无效：{exc}")
    try:
        food = foods.build_food(
            name=args.name,
            kcal=args.kcal,
            per=per,
            unit=unit or "g",
            protein_g=args.protein,
            fat_g=args.fat,
            carb_g=args.carb,
            grams=args.grams,
            aliases=args.alias,
            source=source,
            notes=notes,
            food_id=args.id,
        )
    except ValueError as exc:
        return _fail(str(exc))
    same_id = [item for item in library if item.id == food.id]
    if same_id:
        return _fail(
            f"食物库已有 id「{food.id}」：{same_id[0].name}；"
            "如需新增请用 --id 指定不同 id"
        )
    foods.append_food(food, library)
    print(f"已加入食物库：{_food_summary(food)}")
    return 0


def _register_food(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser("food", help="食物库操作（list/search/add）")
    food_sub = parser.add_subparsers(dest="food_command", metavar="ACTION")

    list_parser = food_sub.add_parser("list", help="列出食物库")
    list_parser.set_defaults(handler=_handle_food_list)

    search_parser = food_sub.add_parser("search", help="搜索食物")
    search_parser.add_argument("keyword", help="名称、别名或 id 关键词")
    search_parser.set_defaults(handler=_handle_food_search)

    add_parser = food_sub.add_parser("add", help="新增食物")
    add_parser.add_argument("name", help="食物名称")
    add_parser.add_argument("--per", default="100g", help="营养值对应份量，如 100g、1个（默认 100g）")
    add_parser.add_argument("--kcal", type=float, required=True, help="每份热量")
    add_parser.add_argument("--p", "--protein", dest="protein", type=float, default=0.0, help="每份蛋白质（g）")
    add_parser.add_argument("--f", "--fat", dest="fat", type=float, default=0.0, help="每份脂肪（g）")
    add_parser.add_argument("--c", "--carb", dest="carb", type=float, default=0.0, help="每份碳水（g）")
    add_parser.add_argument("--grams", type=float, help="非质量单位（个/杯/份…）的单个克重")
    add_parser.add_argument("--alias", action="append", default=[], help="别名，可重复")
    add_parser.add_argument("--source", default="", help="数据来源，如 USDA / CFCT / 估算")
    add_parser.add_argument("--notes", "--basis", dest="notes", default="", help="备注；source=估算 时必填估算依据")
    add_parser.add_argument("--id", help="自定义 id（默认取名称）")
    add_parser.set_defaults(handler=_handle_food_add)

    parser.set_defaults(handler=lambda args: parser.print_help() or 0)


# ---------------------------------------------------------------- add 子命令


def _default_amount(food: Food) -> tuple[float, str]:
    """未给数量时的默认份量：质量单位用 ``per``，计数单位用 1。"""
    if foods.mass_factor(food.unit) is not None:
        return food.per, food.unit
    return 1.0, food.unit


def _print_suggestions(keyword: str, library: list[Food]) -> None:
    print(f"食物库里没有「{keyword}」。", file=sys.stderr)
    hits = foods.suggest_foods(keyword, library)
    if hits:
        print("相近候选：", file=sys.stderr)
        for index, food in enumerate(hits, start=1):
            print(f"  {index}. {_food_summary(food)}", file=sys.stderr)
    print(
        "可用 cal add <餐次> --custom 名称 --kcal 热量 手动录入，"
        "或用 cal food add 加入食物库。",
        file=sys.stderr,
    )


def _print_totals(config_obj, day) -> None:
    totals = day.totals()
    targets = config_obj.macro_targets
    print(
        f"{day.date} 合计 {_num(totals['kcal'])} / {_num(config_obj.target_kcal)} kcal"
        f"（蛋白 {_num(totals['protein_g'])}/{_num(targets.protein_g)} g，"
        f"脂肪 {_num(totals['fat_g'])}/{_num(targets.fat_g)} g，"
        f"碳水 {_num(totals['carb_g'])}/{_num(targets.carb_g)} g）"
    )


def _handle_add(args: argparse.Namespace) -> int:
    config_obj = config.load_config()
    try:
        meal = config_obj.resolve_meal(args.meal)
        day = store.load_day(args.date)
        if args.custom:
            name = args.custom[0]
            if args.kcal is not None:
                kcal = args.kcal
            elif len(args.custom) > 1:
                try:
                    kcal = float(args.custom[1])
                except ValueError:
                    return _fail(f"--custom 的热量无法解析：{args.custom[1]}")
            else:
                return _fail("--custom 需要给出热量，如 --custom 外卖炒饭 700")
            entry = foods.custom_entry(
                name,
                kcal,
                protein_g=args.protein,
                fat_g=args.fat,
                carb_g=args.carb,
                qty=args.qty,
                unit=args.unit,
                grams=args.grams,
            )
        else:
            if not args.item:
                return _fail("请给出食物名称，或用 --custom 手动录入")
            library = foods.load_foods()
            food = foods.find_food(args.item, library)
            if food is None:
                _print_suggestions(args.item, library)
                return 1
            if args.amount:
                qty, unit = foods.parse_amount(args.amount)
            else:
                qty, unit = _default_amount(food)
            entry = foods.compute_entry(food, qty, unit)
    except ValueError as exc:
        return _fail(str(exc))

    day.add(meal, entry)
    store.save_day(day)
    print(
        f"已记录 {config_obj.label(meal)} · {entry.name} "
        f"{_num(entry.qty)}{entry.unit} · {_num(entry.kcal)} kcal"
    )
    _print_totals(config_obj, day)
    return 0


def _register_add(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser("add", help="记录一条食物")
    parser.add_argument("meal", help="餐次：breakfast/lunch/dinner/snack 或 早/午/晚/加餐")
    parser.add_argument("item", nargs="?", help="食物名称（食物库中的名称或别名）")
    parser.add_argument("amount", nargs="?", help="数量，如 200g、2个；省略则用默认份量")
    parser.add_argument("-d", "--date", help="日期，默认今天（today/昨天/2025-09-10）")
    parser.add_argument(
        "--custom",
        nargs="+",
        metavar="名称 热量",
        help="手动录入（食物库没有时）：--custom 名称 热量",
    )
    parser.add_argument("--kcal", type=float, help="热量（配合 --custom）")
    parser.add_argument("--p", "--protein", dest="protein", type=float, default=0.0, help="蛋白质（g）")
    parser.add_argument("--f", "--fat", dest="fat", type=float, default=0.0, help="脂肪（g）")
    parser.add_argument("--c", "--carb", dest="carb", type=float, default=0.0, help="碳水（g）")
    parser.add_argument("--qty", type=float, default=1.0, help="手动录入的数量（默认 1）")
    parser.add_argument("--unit", default="份", help="手动录入的单位（默认 份）")
    parser.add_argument("--grams", type=float, default=0.0, help="手动录入的克重（可选）")
    parser.set_defaults(handler=_handle_add)


# ---------------------------------------------------------------- show / rm 子命令


def _handle_show(args: argparse.Namespace) -> int:
    config_obj = config.load_config()
    day = store.load_day(args.date)
    print(report.render_day(day, config_obj))
    return 0


def _handle_rm(args: argparse.Namespace) -> int:
    config_obj = config.load_config()
    tokens = list(args.targets)
    date_text = None
    # 第一个 token 不是餐次时视为日期（例如 cal rm 昨天 晚餐 1）
    try:
        config_obj.resolve_meal(tokens[0])
    except ValueError:
        date_text = tokens.pop(0)
    if not tokens:
        return _fail(
            f"无法把「{date_text}」识别为餐次或日期；"
            "用法：cal rm [日期] 餐次 [序号]，例如 cal rm lunch 2"
        )
    try:
        meal = config_obj.resolve_meal(tokens.pop(0))
    except ValueError as exc:
        return _fail(str(exc))
    index_text = tokens.pop(0) if tokens else "last"
    if tokens:
        return _fail(f"参数过多：{' '.join(tokens)}")

    day = store.load_day(date_text)
    raw = str(index_text).strip().lower()
    if raw in ("last", "最后", "-1"):
        index = -1
    else:
        try:
            index = int(raw)
        except ValueError:
            return _fail(f"索引必须是数字或 last：{index_text}")
    try:
        entry = day.remove(meal, index)
    except IndexError as exc:
        return _fail(str(exc))
    store.save_day(day)
    print(
        f"已删除 {day.date} {config_obj.label(meal)} · {entry.name} "
        f"{_num(entry.qty)}{entry.unit} · {_num(entry.kcal)} kcal"
    )
    _print_totals(config_obj, day)
    return 0


def _register_show(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser("show", help="查看某天的明细与合计")
    parser.add_argument(
        "date", nargs="?", help="日期，默认今天（today/昨天/2025-09-10）"
    )
    parser.set_defaults(handler=_handle_show)


def _register_rm(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser("rm", help="删除某条记录")
    parser.add_argument(
        "targets",
        nargs="+",
        metavar="[日期] 餐次 [序号]",
        help="如：lunch / lunch 2 / today lunch 2 / 昨天 晚餐 1",
    )
    parser.set_defaults(handler=_handle_rm)


# ---------------------------------------------------------------- weight 子命令


def _handle_weight(args: argparse.Namespace) -> int:
    config_obj = config.load_config()
    weight = store.load_weight()
    if args.kg is None or args.show:
        print(report.render_weight(weight, config_obj))
        return 0
    if args.kg <= 0:
        return _fail("体重必须大于 0")
    try:
        day = store.parse_date(args.date)
    except ValueError as exc:
        return _fail(str(exc))
    weight.record(day.isoformat(), args.kg)
    store.save_weight(weight)
    print(f"已记录体重 {day.isoformat()} {_num(args.kg)} kg")

    items = weight.sorted_items()
    if len(items) >= 2:
        prev_day, prev_kg = items[-2]
        delta = args.kg - prev_kg
        arrow = "↓" if delta < 0 else ("↑" if delta > 0 else "→")
        print(
            f"较上次（{prev_day} {_num(prev_kg)} kg）{arrow} {_num(abs(delta))} kg"
        )
    if config_obj.weight_target_kg:
        delta = args.kg - config_obj.weight_target_kg
        if delta <= 0:
            print(f"已达成目标 {_num(config_obj.weight_target_kg)} kg")
        else:
            print(f"距目标 {_num(config_obj.weight_target_kg)} kg 还差 {_num(delta)} kg")
    return 0


def _register_weight(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser("weight", help="记录或查看体重")
    parser.add_argument("kg", nargs="?", type=float, help="体重（kg）；省略则展示记录与趋势")
    parser.add_argument("-d", "--date", help="日期，默认今天")
    parser.add_argument("--show", action="store_true", help="只展示，不记录")
    parser.set_defaults(handler=_handle_weight)


# ---------------------------------------------------------------- week / month 子命令


def _handle_week(args: argparse.Namespace) -> int:
    config_obj = config.load_config()
    anchor = date.today() + timedelta(weeks=args.offset)
    start, end = store.week_bounds(anchor)
    days = [store.load_day(day) for day in store.date_range(start, end)]
    print(report.render_week(days, config_obj, start, end, store.load_weight()))
    return 0


def _handle_month(args: argparse.Namespace) -> int:
    config_obj = config.load_config()
    try:
        year, month = store.parse_month(args.month)
    except ValueError as exc:
        return _fail(str(exc))
    start, end = store.month_bounds(year, month)
    days = [store.load_day(day) for day in store.date_range(start, end)]
    print(report.render_month(days, config_obj, year, month, store.load_weight()))
    return 0


def _register_week(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser("week", help="查看周报")
    parser.add_argument(
        "offset",
        nargs="?",
        type=int,
        default=0,
        help="周偏移：0 本周（默认）、-1 上周、1 下周",
    )
    parser.set_defaults(handler=_handle_week)


def _register_month(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser("month", help="查看月报")
    parser.add_argument("month", nargs="?", help="月份，如 2025-09；默认当月")
    parser.set_defaults(handler=_handle_month)


# ---------------------------------------------------------------- target 子命令


def _render_target(config_obj) -> str:
    targets = config_obj.macro_targets
    weight = (
        "未设置" if config_obj.weight_target_kg is None else f"{_num(config_obj.weight_target_kg)} kg"
    )
    meals = " / ".join(f"{meal} {config_obj.label(meal)}" for meal in config_obj.meals)
    return "\n".join(
        [
            "当前目标",
            report.SEPARATOR,
            f"热量  {_num(config_obj.target_kcal)} kcal",
            f"宏量  蛋白 {_num(targets.protein_g)} g   脂肪 {_num(targets.fat_g)} g   碳水 {_num(targets.carb_g)} g",
            f"体重  {weight}",
            f"餐次  {meals}",
        ]
    )


def _handle_target(args: argparse.Namespace) -> int:
    config_obj = config.load_config()
    changed = False
    if args.kcal is not None:
        if args.kcal <= 0:
            return _fail("目标热量必须大于 0")
        config_obj.target_kcal = float(args.kcal)
        changed = True
    if args.protein is not None:
        if args.protein < 0:
            return _fail("蛋白质目标不能为负")
        config_obj.macro_targets.protein_g = float(args.protein)
        changed = True
    if args.fat is not None:
        if args.fat < 0:
            return _fail("脂肪目标不能为负")
        config_obj.macro_targets.fat_g = float(args.fat)
        changed = True
    if args.carb is not None:
        if args.carb < 0:
            return _fail("碳水目标不能为负")
        config_obj.macro_targets.carb_g = float(args.carb)
        changed = True
    if args.weight is not None:
        config_obj.weight_target_kg = None if args.weight <= 0 else float(args.weight)
        changed = True
    if changed:
        config.save_config(config_obj)
        print(f"已更新 {store.config_file()}")
    print(_render_target(config_obj))
    return 0


def _register_target(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser("target", help="查看或修改目标（不传参数则只查看）")
    parser.add_argument("kcal", nargs="?", type=float, help="每日目标热量")
    parser.add_argument("--p", "--protein", dest="protein", type=float, help="蛋白质目标（g）")
    parser.add_argument("--f", "--fat", dest="fat", type=float, help="脂肪目标（g）")
    parser.add_argument("--c", "--carb", dest="carb", type=float, help="碳水目标（g）")
    parser.add_argument("--weight", type=float, help="体重目标（kg），填 0 表示清除")
    parser.set_defaults(handler=_handle_target)


# ---------------------------------------------------------------- 解析器


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cal",
        description="每日菜单记录与热量计算",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-V", "--version", action="version", version=f"calory {__version__}"
    )
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")
    _register_add(sub)
    _register_show(sub)
    _register_rm(sub)
    _register_weight(sub)
    _register_week(sub)
    _register_month(sub)
    _register_target(sub)
    _register_food(sub)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 0
    handler = getattr(args, "handler", None)
    if handler is None:
        parser.error(f"未实现的子命令：{args.command}")
        return 2
    try:
        return handler(args) or 0
    except KeyboardInterrupt:
        print("已中断", file=sys.stderr)
        return 130
    except (ValueError, IndexError, FileNotFoundError) as exc:
        return _fail(str(exc))
