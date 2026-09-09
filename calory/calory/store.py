"""存储层：JSON 原子读写、路径解析、日期/月份参数解析。

数据根目录默认为本包的上级目录（``calory/``），可用环境变量 ``CALORY_HOME``
覆盖，方便测试与多份数据并存。
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from .models import DayLog, WeightLog

# ---------------------------------------------------------------- 路径


def home() -> Path:
    """calory 数据根目录。"""
    override = os.environ.get("CALORY_HOME")
    if override:
        return Path(override).expanduser()
    return Path(__file__).resolve().parent.parent


def data_dir() -> Path:
    return home() / "data"


def meals_dir() -> Path:
    return data_dir() / "meals"


def foods_file() -> Path:
    return data_dir() / "foods.json"


def weight_file() -> Path:
    return data_dir() / "weight.json"


def config_file() -> Path:
    return home() / "config.json"


# ---------------------------------------------------------------- JSON 读写


def read_json(path: str | Path, default: Any = None) -> Any:
    """读取 JSON；文件不存在返回 ``default``，格式错误抛 ``ValueError``。"""
    p = Path(path)
    if not p.exists():
        return default
    try:
        with p.open(encoding="utf-8") as fh:
            return json.load(fh)
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON 解析失败 {p}: {exc}") from exc


def write_json(path: str | Path, data: Any) -> Path:
    """原子写入 JSON（同目录临时文件 + ``os.replace``），避免写坏数据。"""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(p.parent), prefix=p.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        os.replace(tmp, p)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    return p


# ---------------------------------------------------------------- 日期解析

_RELATIVE_DAYS: dict[str, int] = {
    "today": 0,
    "今天": 0,
    "yesterday": -1,
    "昨天": -1,
    "前天": -2,
    "tomorrow": 1,
    "明天": 1,
}

_DATE_FORMATS = ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%Y%m%d")
# MM-DD 手工解析：strptime 对缺年份的输入在 Python 3.15 起行为会变。
_MONTH_DAY_RE = re.compile(r"^(\d{1,2})[-/.](\d{1,2})$")


def parse_date(text: str | date | None, today: date | None = None) -> date:
    """解析日期参数。

    支持：``today`` / ``今天`` / ``昨天`` / ``前天`` / ``明天``、
    ``YYYY-MM-DD``（也接受 ``/`` ``.`` 分隔与 ``YYYYMMDD``）、``MM-DD``（补当年）。
    ``None`` 或空串表示今天。
    """
    base = today or date.today()
    if isinstance(text, date):
        return text
    raw = "" if text is None else str(text).strip()
    if not raw:
        return base
    key = raw.lower()
    if key in _RELATIVE_DAYS:
        return base + timedelta(days=_RELATIVE_DAYS[key])
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    match = _MONTH_DAY_RE.match(raw)
    if match:
        month, day_of_month = int(match.group(1)), int(match.group(2))
        try:
            return date(base.year, month, day_of_month)
        except ValueError as exc:
            raise ValueError(f"无法解析日期「{text}」：{exc}") from exc
    raise ValueError(f"无法解析日期「{text}」（支持 today/昨天/YYYY-MM-DD/MM-DD）")


_MONTH_FORMATS = ("%Y-%m", "%Y/%m", "%Y.%m", "%Y%m")


def parse_month(text: str | None, today: date | None = None) -> tuple[int, int]:
    """解析月份参数：``YYYY-MM`` / ``YYYYMM``，空值表示当月。"""
    base = today or date.today()
    raw = "" if text is None else str(text).strip()
    if not raw:
        return base.year, base.month
    for fmt in _MONTH_FORMATS:
        try:
            parsed = datetime.strptime(raw, fmt).date()
            return parsed.year, parsed.month
        except ValueError:
            continue
    raise ValueError(f"无法解析月份「{text}」（支持 YYYY-MM）")


def week_bounds(day: date) -> tuple[date, date]:
    """返回 ``day`` 所在周的周一与周日。"""
    monday = day - timedelta(days=day.weekday())
    return monday, monday + timedelta(days=6)


def month_bounds(year: int, month: int) -> tuple[date, date]:
    """返回该月第一天与最后一天。"""
    first = date(year, month, 1)
    if month == 12:
        last = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last = date(year, month + 1, 1) - timedelta(days=1)
    return first, last


def date_range(start: date, end: date) -> list[date]:
    """含首尾的连续日期列表。"""
    if end < start:
        return []
    return [start + timedelta(days=i) for i in range((end - start).days + 1)]


# ---------------------------------------------------------------- 每日记录


def day_path(day: date) -> Path:
    return meals_dir() / f"{day.isoformat()}.json"


def load_day(day: str | date, today: date | None = None) -> DayLog:
    """读取某天的记录，不存在时返回空的 ``DayLog``。"""
    d = parse_date(day, today)
    data = read_json(day_path(d))
    if not data:
        return DayLog(date=d.isoformat())
    return DayLog.from_dict(data)


def save_day(day_log: DayLog) -> Path | None:
    """保存某天的记录；记录为空时删除文件，避免留下空壳。"""
    d = parse_date(day_log.date)
    day_log.date = d.isoformat()
    path = day_path(d)
    if day_log.is_empty():
        path.unlink(missing_ok=True)
        return None
    return write_json(path, day_log.to_dict())


def list_day_dates(start: date | None = None, end: date | None = None) -> list[date]:
    """列出已有记录的日期（升序），可按区间过滤。"""
    directory = meals_dir()
    if not directory.is_dir():
        return []
    days: list[date] = []
    for path in sorted(directory.glob("*.json")):
        try:
            days.append(date.fromisoformat(path.stem))
        except ValueError:
            continue
    if start:
        days = [d for d in days if d >= start]
    if end:
        days = [d for d in days if d <= end]
    return days


# ---------------------------------------------------------------- 体重


def load_weight() -> WeightLog:
    data = read_json(weight_file(), None)
    if not data:
        return WeightLog()
    return WeightLog.from_dict(data)


def save_weight(weight: WeightLog) -> Path | None:
    if not weight.entries:
        path = weight_file()
        path.unlink(missing_ok=True)
        return None
    return write_json(weight_file(), weight.to_dict())
