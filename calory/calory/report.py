"""日报/周报/月报渲染：纯文本 + ASCII 进度条与体重趋势。

渲染函数只接收模型对象，不产生副作用，便于单测。
"""

from __future__ import annotations

from datetime import date, timedelta

from . import store
from .models import Config, DayLog, WeightLog

WEEKDAYS = ("周一", "周二", "周三", "周四", "周五", "周六", "周日")
BAR_WIDTH = 12
SEPARATOR = "─" * 56
ON_TARGET_TOLERANCE = 0.1  # 热量在目标 ±10% 内算达标


def fmt_num(value: float) -> str:
    """去掉多余小数点：330.0 -> 330，62.5 -> 62.5。"""
    return f"{value:g}"


def weekday_cn(iso_date: str) -> str:
    try:
        return WEEKDAYS[date.fromisoformat(iso_date).weekday()]
    except ValueError:
        return ""


def progress_bar(ratio: float, width: int = BAR_WIDTH) -> str:
    filled = int(round(min(max(ratio, 0.0), 1.0) * width))
    return "[" + "█" * filled + "░" * (width - filled) + "]"


def percent(actual: float, target: float) -> float:
    return actual / target * 100 if target else 0.0


def is_on_target(kcal: float, target: float, tolerance: float = ON_TARGET_TOLERANCE) -> bool:
    if target <= 0:
        return False
    return abs(kcal - target) <= target * tolerance


# ---------------------------------------------------------------- 日报


def render_day(day: DayLog, config: Config) -> str:
    lines = [
        f"{day.date} {weekday_cn(day.date)}   目标 {fmt_num(config.target_kcal)} kcal",
        SEPARATOR,
    ]
    meals = list(config.meals)
    for meal, entries in day.meals.items():
        if meal not in meals and entries:
            meals.append(meal)

    has_entry = False
    for meal in meals:
        entries = day.meals.get(meal) or []
        label = config.label(meal)
        for index, entry in enumerate(entries):
            has_entry = True
            prefix = label if index == 0 else " " * len(label)
            lines.append(
                f"{prefix}  {entry.name} {fmt_num(entry.qty)}{entry.unit}"
                f"  {fmt_num(entry.kcal)} kcal"
                f"  P{fmt_num(entry.protein_g)}"
                f" F{fmt_num(entry.fat_g)}"
                f" C{fmt_num(entry.carb_g)}"
            )
    if not has_entry:
        lines.append("（这一天还没有记录）")

    lines.append(SEPARATOR)
    totals = day.totals()
    ratio = totals["kcal"] / config.target_kcal if config.target_kcal else 0.0
    rest = config.target_kcal - totals["kcal"]
    rest_text = f"剩余 {fmt_num(rest)}" if rest >= 0 else f"超出 {fmt_num(-rest)}"
    lines.append(
        f"合计  {fmt_num(totals['kcal'])} / {fmt_num(config.target_kcal)} kcal  "
        f"{progress_bar(ratio)} {ratio * 100:.1f}%  {rest_text}"
    )
    targets = config.macro_targets
    lines.append(
        f"宏量  蛋白 {fmt_num(totals['protein_g'])}/{fmt_num(targets.protein_g)} g"
        f"（{percent(totals['protein_g'], targets.protein_g):.0f}%）"
        f"   脂肪 {fmt_num(totals['fat_g'])}/{fmt_num(targets.fat_g)} g"
        f"（{percent(totals['fat_g'], targets.fat_g):.0f}%）"
        f"   碳水 {fmt_num(totals['carb_g'])}/{fmt_num(targets.carb_g)} g"
        f"（{percent(totals['carb_g'], targets.carb_g):.0f}%）"
    )
    return "\n".join(lines)


# ---------------------------------------------------------------- 区间汇总


def _weight_change(
    weight: WeightLog | None, start: date, end: date
) -> tuple[tuple[str, float], tuple[str, float]] | None:
    if not weight:
        return None
    items = [
        (day, kg)
        for day, kg in weight.sorted_items()
        if start.isoformat() <= day <= end.isoformat()
    ]
    if not items:
        return None
    return items[0], items[-1]


def _summary_lines(
    logged: list[DayLog],
    config: Config,
    start: date,
    end: date,
    weight: WeightLog | None,
) -> list[str]:
    total_days = (end - start).days + 1
    sum_kcal = sum(day.totals()["kcal"] for day in logged)
    sum_protein = sum(day.totals()["protein_g"] for day in logged)
    sum_fat = sum(day.totals()["fat_g"] for day in logged)
    sum_carb = sum(day.totals()["carb_g"] for day in logged)
    count = len(logged)
    on_target = sum(1 for day in logged if is_on_target(day.totals()["kcal"], config.target_kcal))

    lines = [
        SEPARATOR,
        f"已记录 {count} / {total_days} 天",
        f"日均  {fmt_num(sum_kcal / count)} kcal"
        f"   蛋白 {fmt_num(sum_protein / count)} g"
        f"   脂肪 {fmt_num(sum_fat / count)} g"
        f"   碳水 {fmt_num(sum_carb / count)} g",
        f"达标  {on_target} / {count} 天"
        f"（热量在目标 {fmt_num(config.target_kcal)} kcal 的 ±"
        f"{ON_TARGET_TOLERANCE * 100:.0f}% 内）",
    ]
    change = _weight_change(weight, start, end)
    if change:
        (first_day, first_kg), (last_day, last_kg) = change
        if first_day == last_day:
            lines.append(f"体重  {first_day} {fmt_num(first_kg)} kg")
        else:
            delta = last_kg - first_kg
            arrow = "↓" if delta < 0 else ("↑" if delta > 0 else "→")
            lines.append(
                f"体重  {first_day} {fmt_num(first_kg)} kg → {last_day} {fmt_num(last_kg)} kg"
                f"（{arrow} {fmt_num(abs(delta))} kg）"
            )
    return lines


def _daily_lines(logged: list[DayLog], config: Config) -> list[str]:
    lines = []
    for day in logged:
        totals = day.totals()
        mark = "达标" if is_on_target(totals["kcal"], config.target_kcal) else "  "
        lines.append(
            f"{day.date} {weekday_cn(day.date)}  {fmt_num(totals['kcal']):>5} kcal"
            f"   P{fmt_num(totals['protein_g'])}"
            f" F{fmt_num(totals['fat_g'])}"
            f" C{fmt_num(totals['carb_g'])}  {mark}"
        )
    return lines


def render_week(
    days: list[DayLog],
    config: Config,
    start: date,
    end: date,
    weight: WeightLog | None = None,
) -> str:
    title = f"{start.isoformat()} ~ {end.isoformat()} 周报"
    lines = [title, SEPARATOR]
    logged = [day for day in days if not day.is_empty()]
    if not logged:
        lines.append("（区间内没有记录）")
        return "\n".join(lines)
    lines.extend(_daily_lines(logged, config))
    lines.extend(_summary_lines(logged, config, start, end, weight))
    return "\n".join(lines)


def render_month(
    days: list[DayLog],
    config: Config,
    year: int,
    month: int,
    weight: WeightLog | None = None,
) -> str:
    start, end = store.month_bounds(year, month)
    title = f"{year}年{month}月 月报"
    lines = [title, SEPARATOR]
    logged = [day for day in days if not day.is_empty()]
    if not logged:
        lines.append("（区间内没有记录）")
        return "\n".join(lines)

    weeks: dict[date, list[DayLog]] = {}
    for day in logged:
        monday = store.week_bounds(date.fromisoformat(day.date))[0]
        weeks.setdefault(monday, []).append(day)

    lines.append("按周：")
    for index, (monday, week_days) in enumerate(sorted(weeks.items()), start=1):
        sunday = monday + timedelta(days=6)
        kcal = sum(day.totals()["kcal"] for day in week_days)
        lines.append(
            f"  第 {index} 周（{monday.strftime('%m-%d')} ~ {sunday.strftime('%m-%d')}）"
            f"  记录 {len(week_days)} 天   日均 {fmt_num(kcal / len(week_days))} kcal"
        )
    lines.extend(_summary_lines(logged, config, start, end, weight))
    return "\n".join(lines)


# ---------------------------------------------------------------- 体重趋势


SPARK_BLOCKS = "▁▂▃▄▅▆▇█"


def sparkline(values: list[float]) -> str:
    """把数值序列压成一行方块图。"""
    if not values:
        return ""
    low, high = min(values), max(values)
    if high == low:
        return SPARK_BLOCKS[3] * len(values)
    span = high - low
    return "".join(
        SPARK_BLOCKS[min(len(SPARK_BLOCKS) - 1, int((value - low) / span * (len(SPARK_BLOCKS) - 1) + 0.5))]
        for value in values
    )


def render_weight(weight: WeightLog, config: Config, limit: int = 30) -> str:
    items = weight.sorted_items()
    lines = ["体重记录", SEPARATOR]
    if not items:
        lines.append("（还没有记录，用 cal weight 70.5 记录）")
        return "\n".join(lines)

    recent = items[-limit:]
    values = [kg for _, kg in recent]
    lines.append(f"最近 {len(recent)} 条  {sparkline(values)}")
    for day, kg in recent:
        diff = ""
        if config.weight_target_kg:
            delta = kg - config.weight_target_kg
            diff = f"  距目标 {fmt_num(abs(delta))} kg" + ("（已达成）" if delta <= 0 else "")
        lines.append(f"  {day}  {fmt_num(kg)} kg{diff}")
    return "\n".join(lines)
