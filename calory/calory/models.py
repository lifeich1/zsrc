"""数据模型：食物、条目、每日记录、体重记录、配置。

全部为纯数据 dataclass，附带 ``to_dict`` / ``from_dict`` 以便 JSON 序列化。
``from_dict`` 会忽略未知字段，保证旧数据文件向前兼容。
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import Any, Iterator


def _filter(cls: type, data: dict[str, Any]) -> dict[str, Any]:
    names = {f.name for f in dataclasses.fields(cls)}
    return {k: v for k, v in data.items() if k in names}


@dataclass
class Food:
    """食物库中的一条食物。

    营养值对应 ``per`` 个 ``unit``：

    - ``unit`` 为 ``g`` / ``ml`` 时 ``per`` 通常是 100（即每 100 g / 100 ml）；
    - 其他单位（个/只/片/杯/份…）时 ``per`` 通常是 1，``grams`` 给出单个单位的克重。
    """

    id: str
    name: str
    kcal: float
    unit: str = "g"
    per: float = 100.0
    protein_g: float = 0.0
    fat_g: float = 0.0
    carb_g: float = 0.0
    grams: float | None = None
    aliases: list[str] = field(default_factory=list)
    source: str = ""

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Food":
        return cls(**_filter(cls, data))


@dataclass
class Entry:
    """一天里的一条记录。

    ``kcal`` 与宏量是**写入时的快照**：之后修改食物库不会改动历史记录，
    同时保留 ``food_id`` 以便追溯来源。
    """

    name: str
    qty: float
    unit: str
    grams: float
    kcal: float
    protein_g: float = 0.0
    fat_g: float = 0.0
    carb_g: float = 0.0
    food_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Entry":
        return cls(**_filter(cls, data))


@dataclass
class DayLog:
    """某一天的菜单记录，按餐次分组。"""

    date: str
    meals: dict[str, list[Entry]] = field(default_factory=dict)

    def meal(self, name: str) -> list[Entry]:
        return self.meals.setdefault(name, [])

    def add(self, meal: str, entry: Entry) -> Entry:
        self.meal(meal).append(entry)
        return entry

    def remove(self, meal: str, index: int) -> Entry:
        """删除某餐次第 ``index`` 条（1 起）。索引非法时抛 ``IndexError``。"""
        entries = self.meals.get(meal)
        if not entries:
            raise IndexError(f"「{meal}」没有记录")
        if index == 0 or abs(index) > len(entries):
            raise IndexError(f"「{meal}」只有 {len(entries)} 条记录，无法删除第 {index} 条")
        if index > 0:
            return entries.pop(index - 1)
        return entries.pop(index)

    def iter_entries(self) -> Iterator[tuple[str, Entry]]:
        for meal, entries in self.meals.items():
            for entry in entries:
                yield meal, entry

    def totals(self) -> dict[str, float]:
        total = {"kcal": 0.0, "protein_g": 0.0, "fat_g": 0.0, "carb_g": 0.0}
        for _, entry in self.iter_entries():
            total["kcal"] += entry.kcal
            total["protein_g"] += entry.protein_g
            total["fat_g"] += entry.fat_g
            total["carb_g"] += entry.carb_g
        return total

    def is_empty(self) -> bool:
        return not any(self.meals.values())

    def to_dict(self) -> dict[str, Any]:
        return {
            "date": self.date,
            "meals": {
                meal: [entry.to_dict() for entry in entries]
                for meal, entries in self.meals.items()
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DayLog":
        meals: dict[str, list[Entry]] = {}
        for meal, entries in (data.get("meals") or {}).items():
            meals[meal] = [Entry.from_dict(e) for e in entries]
        return cls(date=str(data.get("date", "")), meals=meals)


@dataclass
class WeightLog:
    """体重记录：``{"2025-09-10": 70.5}``（ISO 日期 -> kg）。"""

    entries: dict[str, float] = field(default_factory=dict)

    def record(self, date: str, kg: float) -> float:
        self.entries[date] = float(kg)
        return self.entries[date]

    def sorted_items(self) -> list[tuple[str, float]]:
        return sorted(self.entries.items())

    def latest(self) -> tuple[str, float] | None:
        items = self.sorted_items()
        return items[-1] if items else None

    def to_dict(self) -> dict[str, Any]:
        return {"entries": dict(sorted(self.entries.items()))}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WeightLog":
        entries = data.get("entries") if isinstance(data, dict) else None
        if not isinstance(entries, dict):
            entries = {}
        return cls(entries={str(k): float(v) for k, v in entries.items()})


@dataclass
class MacroTargets:
    """每日宏量营养素目标（克）。"""

    protein_g: float = 120.0
    fat_g: float = 65.0
    carb_g: float = 220.0

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "MacroTargets":
        return cls(**_filter(cls, data or {}))


def _default_meals() -> list[str]:
    return ["breakfast", "lunch", "dinner", "snack"]


def _default_meal_labels() -> dict[str, str]:
    return {
        "breakfast": "早餐",
        "lunch": "午餐",
        "dinner": "晚餐",
        "snack": "加餐",
    }


@dataclass
class Config:
    """个人目标配置（config.json）。"""

    target_kcal: float = 2000.0
    macro_targets: MacroTargets = field(default_factory=MacroTargets)
    weight_target_kg: float | None = None
    meals: list[str] = field(default_factory=_default_meals)
    meal_labels: dict[str, str] = field(default_factory=_default_meal_labels)

    def label(self, meal: str) -> str:
        return self.meal_labels.get(meal, meal)

    def resolve_meal(self, name: str) -> str:
        """把用户输入解析成餐次键：支持英文键、中文标签、前缀匹配。"""
        raw = str(name).strip()
        if not raw:
            raise ValueError("餐次不能为空")
        if raw in self.meals:
            return raw
        lowered = raw.lower()
        for meal in self.meals:
            if meal.lower() == lowered:
                return meal
        for meal in self.meals:
            if self.label(meal) == raw:
                return meal
        candidates = [m for m in self.meals if m.lower().startswith(lowered) or self.label(m).startswith(raw)]
        if len(candidates) == 1:
            return candidates[0]
        if candidates:
            raise ValueError(f"餐次「{name}」有歧义：{', '.join(candidates)}")
        raise ValueError(f"未知餐次「{name}」，可用：{', '.join(self.meals)}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_kcal": self.target_kcal,
            "macro_targets": self.macro_targets.to_dict(),
            "weight_target_kg": self.weight_target_kg,
            "meals": list(self.meals),
            "meal_labels": dict(self.meal_labels),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Config":
        data = data or {}
        meals = data.get("meals") or _default_meals()
        labels = data.get("meal_labels") or _default_meal_labels()
        return cls(
            target_kcal=float(data.get("target_kcal", 2000.0)),
            macro_targets=MacroTargets.from_dict(data.get("macro_targets")),
            weight_target_kg=(
                None
                if data.get("weight_target_kg") in (None, "")
                else float(data["weight_target_kg"])
            ),
            meals=[str(m) for m in meals],
            meal_labels={str(k): str(v) for k, v in labels.items()},
        )
