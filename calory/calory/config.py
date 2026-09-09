"""config.json 的读取、保存与默认值。"""

from __future__ import annotations

from pathlib import Path

from . import store
from .models import Config


def load_config(path: str | Path | None = None) -> Config:
    """读取配置；文件不存在或为空时返回默认配置。"""
    data = store.read_json(path or store.config_file(), None)
    if not data:
        return Config()
    return Config.from_dict(data)


def save_config(config: Config, path: str | Path | None = None) -> Path:
    return store.write_json(path or store.config_file(), config.to_dict())
