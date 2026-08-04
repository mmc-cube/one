"""Import the private component index into a portable project catalog."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = Path(
    os.environ.get(
        "MCU_COMPONENT_SOURCE",
        r"C:\Users\cqiyu\.claude\skills\stm32-reverse-xls\scripts\component_3col_map.json",
    )
)
DEFAULT_OUTPUT = ROOT / "data" / "component_catalog.json"

SENSOR_PREFIXES = {
    "温湿度", "温度", "气体", "粉尘", "光照", "超声波", "人体", "红外", "运动", "心率",
    "指纹", "称重", "压力", "水质", "土壤湿度", "火焰", "门磁", "雨滴", "水位", "声音传感器",
    "电压传感器", "风速风向", "S12SD", "定位", "识别", "RTC", "电源", "旋钮电位器", "霍尔",
    "红外循迹", "ADC采集", "摄像头", "激光测距",
}
ACTUATOR_PREFIXES = {
    "电机", "蜂鸣器", "声音", "继电器", "电磁锁", "MOSFET", "水泵", "风扇", "加热", "制冷",
    "雾化加湿", "UV杀菌", "LED", "遮阳帘",
}


def component_kind(category: str) -> str:
    prefix = category.split("-", 1)[0]
    if category == "电机-编码器":
        return "sensor"
    if category == "电源-供电":
        return "reference"
    if prefix == "显示":
        return "display"
    if category == "按键":
        return "sensor"
    if prefix in SENSOR_PREFIXES:
        return "sensor"
    if prefix in ACTUATOR_PREFIXES:
        return "actuator"
    return "reference"


def sanitize_library_match(value: object) -> dict[str, object] | None:
    if not isinstance(value, dict) or not str(value.get("folder", "")).strip():
        return None
    return {
        "folder": str(value.get("folder", ""))[:240],
        "subdirs": [str(item)[:160] for item in value.get("subdirs", []) if str(item).strip()],
        "files": [str(item)[:160] for item in value.get("files", []) if str(item).strip()],
    }


def import_catalog(source: Path, output: Path) -> dict[str, object]:
    with source.open("r", encoding="utf-8") as file:
        raw = json.load(file)

    records = []
    for index, mapping in enumerate(raw.get("mappings", []), start=1):
        if not isinstance(mapping, dict):
            continue
        category = str(mapping.get("category", "")).strip()
        if not category:
            continue
        keywords = [str(item).strip() for item in mapping.get("keywords", []) if str(item).strip()]
        library_matches = [
            sanitized
            for item in mapping.get("library_matches", [])
            if (sanitized := sanitize_library_match(item)) is not None
        ]
        records.append(
            {
                "id": f"component-{index:03d}",
                "category": category,
                "kind": component_kind(category),
                "keywords": keywords,
                "total_table_hits": int(mapping.get("total_table_hits", 0) or 0),
                "library_matches": library_matches,
                "datasheet_url": str(mapping.get("datasheet_url", "") or "")[:500],
                "supplemental": category == "按键",
            }
        )

    payload = {
        "summary": {
            "total": len(records),
            "selectable": sum(item["kind"] != "reference" for item in records),
            "with_library": sum(bool(item["library_matches"]) for item in records),
        },
        "source": {
            "lib_base": str(raw.get("config", {}).get("lib_base", "")),
            "note": "Backend-only metadata retained for future component resource packaging.",
        },
        "components": records,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Import the component index used by the web application")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    payload = import_catalog(args.source, args.output)
    print(
        f"Imported {payload['summary']['total']} components "
        f"({payload['summary']['selectable']} selectable) to {args.output}"
    )


if __name__ == "__main__":
    main()
