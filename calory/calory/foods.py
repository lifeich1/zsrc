"""食物库：加载与校验、名称匹配、单位换算、热量与宏量计算。

单位约定：

- 质量/体积单位（``g``/``克``/``kg``/``ml``/``毫升``/``l``/``升``）按克直接换算，
  其中 ``ml`` 近似 ``1 ml = 1 g``（饮料场景足够）；
- 其余单位（``个``/``片``/``杯``/``碗``/``份``…）依赖食物自带的 ``grams``（单个单位克重）。
"""

from __future__ import annotations

import re
from pathlib import Path

from . import store
from .models import Entry, Food

# 单位 -> 克
MASS_UNITS: dict[str, float] = {
    "g": 1.0,
    "克": 1.0,
    "gram": 1.0,
    "grams": 1.0,
    "gm": 1.0,
    "kg": 1000.0,
    "千克": 1000.0,
    "公斤": 1000.0,
    "ml": 1.0,
    "毫升": 1.0,
    "l": 1000.0,
    "升": 1000.0,
    "liter": 1000.0,
    "litre": 1000.0,
}

_AMOUNT_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*([^\d\s]*)\s*$")


def normalize_unit(unit: str | None) -> str:
    return str(unit or "").strip().lower()


def mass_factor(unit: str | None) -> float | None:
    """质量/体积单位对应的克数，非质量单位返回 ``None``。"""
    return MASS_UNITS.get(normalize_unit(unit))


def parse_amount(text: str) -> tuple[float, str | None]:
    """解析 ``200g`` / ``2个`` / ``1.5`` 这类数量串，返回 ``(数量, 单位或 None)``。"""
    raw = str(text).strip()
    match = _AMOUNT_RE.match(raw)
    if not match:
        raise ValueError(f"无法解析数量「{text}」（示例：200g、2个、1.5）")
    qty = float(match.group(1))
    if qty <= 0:
        raise ValueError(f"数量必须大于 0：{text}")
    unit = match.group(2) or None
    return qty, unit


# ---------------------------------------------------------------- 加载 / 保存


def _coerce(food: Food) -> Food:
    food.per = float(food.per or 1)
    food.kcal = float(food.kcal)
    food.protein_g = float(food.protein_g or 0)
    food.fat_g = float(food.fat_g or 0)
    food.carb_g = float(food.carb_g or 0)
    if food.grams is not None:
        food.grams = float(food.grams)
    food.aliases = [str(a) for a in (food.aliases or [])]
    if food.per <= 0:
        raise ValueError(f"食物「{food.name}」的 per 必须大于 0")
    if food.kcal < 0:
        raise ValueError(f"食物「{food.name}」的 kcal 不能为负")
    if mass_factor(food.unit) is None and not food.grams:
        raise ValueError(
            f"食物「{food.name}」的单位是「{food.unit}」，必须提供 grams（单个单位克重）"
        )
    return food


def load_foods(path: str | Path | None = None) -> list[Food]:
    """读取食物库；文件不存在返回空列表。

    支持两种顶层结构：``{"version": 1, "foods": [...]}`` 或裸数组。
    """
    data = store.read_json(path or store.foods_file(), None)
    if data is None:
        return []
    if isinstance(data, dict):
        raw = data.get("foods") or []
    elif isinstance(data, list):
        raw = data
    else:
        raise ValueError("foods.json 顶层必须是对象或数组")
    if not isinstance(raw, list):
        raise ValueError("foods.json 的 foods 必须是数组")

    foods: list[Food] = []
    seen: set[str] = set()
    for index, item in enumerate(raw, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"foods.json 第 {index} 条不是对象")
        try:
            food = Food.from_dict(item)
        except TypeError as exc:
            raise ValueError(
                f"foods.json 第 {index} 条缺少必填字段（id/name/kcal）：{exc}"
            ) from exc
        food = _coerce(food)
        if not food.id or not food.name:
            raise ValueError(f"foods.json 第 {index} 条缺少 id 或 name")
        if food.id in seen:
            raise ValueError(f"foods.json 存在重复 id：{food.id}")
        seen.add(food.id)
        foods.append(food)
    return foods


def save_foods(foods: list[Food], path: str | Path | None = None) -> Path:
    return store.write_json(
        path or store.foods_file(),
        {"version": 1, "foods": [food.to_dict() for food in foods]},
    )


# ---------------------------------------------------------------- 匹配


def _names(food: Food) -> list[str]:
    return [food.name, *food.aliases]


def find_food(query: str, foods: list[Food]) -> Food | None:
    """按 精确 id -> 精确名称 -> 精确别名 -> 包含匹配 的顺序查找。"""
    raw = str(query).strip()
    if not raw:
        return None
    lowered = raw.lower()
    for food in foods:
        if food.id.lower() == lowered:
            return food
    for food in foods:
        if food.name.lower() == lowered:
            return food
    for food in foods:
        if any(alias.lower() == lowered for alias in food.aliases):
            return food
    contains = [
        food for food in foods if any(lowered in name.lower() for name in _names(food))
    ]
    if not contains:
        return None
    # 名称最短者最贴近查询
    return min(contains, key=lambda f: (len(f.name), f.name))


def suggest_foods(query: str, foods: list[Food], limit: int = 5) -> list[Food]:
    """模糊匹配候选，供未命中时提示。"""
    import difflib

    raw = str(query).strip().lower()
    if not raw:
        return []
    scored: list[tuple[float, Food]] = []
    for food in foods:
        best = 0.0
        for name in _names(food):
            target = name.lower()
            ratio = difflib.SequenceMatcher(None, raw, target).ratio()
            if raw in target or target in raw:
                ratio = max(ratio, 0.9)
            best = max(best, ratio)
        scored.append((best, food))
    scored.sort(key=lambda item: (-item[0], item[1].name))
    return [food for score, food in scored[:limit] if score > 0.3]


# ---------------------------------------------------------------- 换算与计算


def base_grams(food: Food) -> float:
    """食物营养值（``per`` 个 ``unit``）对应的克数。"""
    factor = mass_factor(food.unit)
    if factor is not None:
        return food.per * factor
    if not food.grams:
        raise ValueError(
            f"食物「{food.name}」缺少 grams，无法把「{food.unit}」换算成克"
        )
    return food.per * food.grams


def to_grams(food: Food, qty: float, unit: str | None = None) -> float:
    """把 ``qty + unit`` 换算成克；``unit`` 为空时使用食物默认单位。"""
    chosen = unit or food.unit
    factor = mass_factor(chosen)
    if factor is not None:
        return qty * factor
    if not food.grams:
        raise ValueError(
            f"食物「{food.name}」缺少 grams，无法按「{chosen}」计量；请改用 g"
        )
    return qty * food.grams


def compute_entry(food: Food, qty: float, unit: str | None = None) -> Entry:
    """按食物库数据计算一条记录（热量与宏量为写入时快照）。"""
    grams = to_grams(food, qty, unit)
    factor = grams / base_grams(food)
    return Entry(
        name=food.name,
        qty=float(qty),
        unit=unit or food.unit,
        grams=round(grams, 1),
        kcal=round(food.kcal * factor, 1),
        protein_g=round(food.protein_g * factor, 1),
        fat_g=round(food.fat_g * factor, 1),
        carb_g=round(food.carb_g * factor, 1),
        food_id=food.id,
    )


def custom_entry(
    name: str,
    kcal: float,
    protein_g: float = 0.0,
    fat_g: float = 0.0,
    carb_g: float = 0.0,
    qty: float = 1.0,
    unit: str = "份",
    grams: float = 0.0,
) -> Entry:
    """食物库没有时手动录入一条记录。"""
    if not str(name).strip():
        raise ValueError("名称不能为空")
    return Entry(
        name=str(name).strip(),
        qty=float(qty),
        unit=unit,
        grams=float(grams),
        kcal=round(float(kcal), 1),
        protein_g=round(float(protein_g or 0), 1),
        fat_g=round(float(fat_g or 0), 1),
        carb_g=round(float(carb_g or 0), 1),
        food_id=None,
    )


# ---------------------------------------------------------------- 写入食物库


def unique_id(base: str, foods: list[Food]) -> str:
    """生成不与现有食物冲突的 id。"""
    slug = re.sub(r"\s+", "-", str(base).strip()) or "food"
    existing = {food.id for food in foods}
    if slug not in existing:
        return slug
    index = 2
    while f"{slug}-{index}" in existing:
        index += 1
    return f"{slug}-{index}"


def build_food(
    name: str,
    kcal: float,
    per: float = 100.0,
    unit: str = "g",
    protein_g: float = 0.0,
    fat_g: float = 0.0,
    carb_g: float = 0.0,
    grams: float | None = None,
    aliases: list[str] | None = None,
    source: str = "",
    food_id: str | None = None,
) -> Food:
    """构造一条食物数据（不落盘）。"""
    if not str(name).strip():
        raise ValueError("食物名称不能为空")
    return _coerce(
        Food(
            id=food_id or str(name).strip(),
            name=str(name).strip(),
            kcal=float(kcal),
            unit=unit,
            per=float(per),
            protein_g=float(protein_g or 0),
            fat_g=float(fat_g or 0),
            carb_g=float(carb_g or 0),
            grams=None if grams is None else float(grams),
            aliases=list(aliases or []),
            source=source,
        )
    )


def append_food(food: Food, foods: list[Food], path: str | Path | None = None) -> Food:
    """追加到食物库并保存；id 冲突时自动加后缀。"""
    food.id = unique_id(food.id, foods)
    foods.append(food)
    save_foods(foods, path)
    return food
