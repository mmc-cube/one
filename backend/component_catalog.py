"""Topic-aware access to the private component catalog."""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any

from design_rules import NETWORK_TERMS, component_matches, domain_profile, is_pid_dc_motor_topic


ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "data" / "component_catalog.json"
OPTION_LIMITS = {"display": 2, "sensor": 11, "actuator": 8}


def normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]", "", value.lower())


def load_component_catalog(path: Path = CATALOG_PATH) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    components = data.get("components")
    if not isinstance(components, list):
        raise ValueError("元器件目录格式不正确")
    return data


def search_text(record: dict[str, Any]) -> str:
    return " ".join([str(record.get("category", "")), *[str(item) for item in record.get("keywords", [])]])


def record_matches(record: dict[str, Any], terms: tuple[str, ...] | list[str]) -> bool:
    values = [str(record.get("category", "")), *[str(item) for item in record.get("keywords", [])]]
    return any(component_matches(value, term) for value in values for term in terms)


def domain_option_terms(topic: str, kind: str) -> tuple[str, ...] | None:
    if is_pid_dc_motor_topic(topic):
        return {
            "display": ("OLED", "LCD1602"),
            "sensor": (
                "编码器", "ACS712", "INA226", "霍尔", "光电", "红外对射", "电压传感器", "ADC采集", "按键", "旋钮"
            ),
            "actuator": ("直流电机", "TB6612", "L298N", "L9110S", "MOSFET", "LED", "蜂鸣器"),
        }[kind]
    if any(word in topic for word in ("温室", "大棚", "灌溉", "农业", "种植")):
        return {
            "display": ("OLED", "LCD1602"),
            "sensor": ("DHT", "SHT30", "BME280", "DS18B20", "土壤湿度", "BH1750", "光敏", "MQ135", "MH-Z19", "按键"),
            "actuator": ("水泵", "风扇", "加热", "制冷", "雾化", "继电器", "补光", "遮阳帘", "LED", "蜂鸣器"),
        }[kind]
    if any(word in topic for word in ("密码锁", "门禁", "智能锁", "电子锁", "门锁")):
        return {
            "display": ("OLED", "LCD1602"),
            "sensor": ("AS608", "RC522", "门磁", "按键", "红外", "DS1302", "DS3231"),
            "actuator": ("电磁锁", "舵机", "继电器", "LED", "蜂鸣器"),
        }[kind]
    if any(word in topic for word in ("火灾", "消防", "烟雾")):
        return {
            "display": ("OLED", "LCD1602"),
            "sensor": ("MQ2", "MQ5", "MQ7", "温度", "火焰", "粉尘", "人体红外", "按键"),
            "actuator": ("蜂鸣器", "LED", "继电器", "水泵", "风扇"),
        }[kind]
    if any(term.lower() in topic.lower() for term in NETWORK_TERMS):
        return {
            "display": ("OLED", "LCD1602"),
            "sensor": ("DHT", "SHT30", "BME280", "DS18B20", "BH1750", "光敏", "MQ135", "粉尘", "人体红外", "按键"),
            "actuator": ("LED", "蜂鸣器", "继电器", "风扇", "水泵"),
        }[kind]
    return None


def relevance_score(
    record: dict[str, Any],
    topic: str,
    project_text: str,
    profile: dict[str, list[str]] | None,
) -> float:
    text = search_text(record)
    score = min(8.0, math.log2(1 + max(0, int(record.get("total_table_hits", 0)))))
    if record.get("library_matches"):
        score += 2
    if any(normalize(keyword) and normalize(keyword) in normalize(topic) for keyword in record.get("keywords", [])):
        score += 30
    if any(normalize(keyword) and normalize(keyword) in normalize(project_text) for keyword in record.get("keywords", [])):
        score += 12
    if profile:
        pool_key = {"display": "displays", "sensor": "sensors", "actuator": "actuators"}.get(record.get("kind"))
        if pool_key and any(record_matches(record, [allowed]) for allowed in profile.get(pool_key, [])):
            score += 80
    if record.get("supplemental"):
        score += 70
    return score


def public_component_options(
    topic: str,
    related_projects: list[dict[str, str]],
    catalog: dict[str, Any] | None = None,
) -> dict[str, object]:
    data = catalog or load_component_catalog()
    profile = domain_profile(topic)
    project_text = " ".join(
        f"{project.get('title', '')} {project.get('components', '')} {project.get('features', '')}"
        for project in related_projects
    )
    options: dict[str, list[dict[str, object]]] = {kind: [] for kind in OPTION_LIMITS}
    for kind, limit in OPTION_LIMITS.items():
        candidates = [item for item in data["components"] if item.get("kind") == kind]
        option_terms = domain_option_terms(topic, kind)
        if option_terms:
            candidates = [
                item for item in candidates
                if record_matches(item, option_terms) or bool(item.get("supplemental"))
            ]
        ranked = sorted(
            candidates,
            key=lambda item: (
                relevance_score(item, topic, project_text, profile),
                int(item.get("total_table_hits", 0)),
            ),
            reverse=True,
        )[:limit]
        options[kind] = [
            {
                "id": item["id"],
                "name": item["category"],
                "model": " / ".join(item.get("keywords", [])[:2]) or "元器件库",
                "usage_count": int(item.get("total_table_hits", 0)),
                "has_library": bool(item.get("library_matches")),
                "supplemental": bool(item.get("supplemental")),
            }
            for item in ranked
        ]
    return {
        "topic": topic,
        "options": options,
        "visible_count": sum(len(items) for items in options.values()),
        "catalog_count": int(data.get("summary", {}).get("total", len(data["components"]))),
    }
