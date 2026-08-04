"""Local one-sentence descriptions bound to common MCU components."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
LIBRARY_PATH = ROOT / "data" / "component_descriptions.json"


def normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]", "", value.lower())


def load_library(path: Path = LIBRARY_PATH) -> dict[str, list[dict[str, Any]]]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    return {kind: records for kind, records in data.items() if isinstance(records, list)}


COMPONENT_LIBRARY = load_library()


FALLBACK_DESCRIPTIONS = {
    "sensor": "读取与题目相关的状态或测量数据，并传递给单片机进行判断。",
    "display": "显示与题目相关的核心数据、设置参数和系统运行状态。",
    "actuator": "接收单片机控制信号并执行与题目相关的实际动作。",
}


def fixed_description(item: str, kind: str) -> str:
    normalized_item = normalize(item)
    best: tuple[int, str] | None = None
    for record in COMPONENT_LIBRARY.get(kind, []):
        generic_record = kind == "actuator" and normalize(str(record.get("name", ""))) == "继电器驱动模块"
        aliases = [str(record.get("name", "")), *[str(value) for value in record.get("aliases", [])]]
        for alias in aliases:
            normalized_alias = normalize(alias)
            if normalized_alias and normalized_alias in normalized_item:
                priority = len(normalized_alias) if generic_record else 100 + len(normalized_alias)
                candidate = (priority, str(record.get("description", "")))
                if candidate[1] and (best is None or candidate[0] > best[0]):
                    best = candidate
    return best[1] if best else FALLBACK_DESCRIPTIONS[kind]


def fixed_components(items: list[str], kind: str) -> list[dict[str, str]]:
    return [{"name": item, "description": fixed_description(item, kind)} for item in items]
