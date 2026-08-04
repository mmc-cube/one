"""Export the private Excel project catalog into backend-only JSON."""

from __future__ import annotations

import json
import os
from pathlib import Path

import openpyxl


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = Path(r"D:\Working Repository\总表.xlsx")
SOURCE = Path(os.environ.get("MCU_SOURCE_XLSX", DEFAULT_SOURCE))
TARGET = ROOT / "data" / "projects.json"


def clean(value: object) -> str:
    return str(value or "").strip()


def main() -> None:
    if not SOURCE.exists():
        raise SystemExit(f"找不到内容库：{SOURCE}")

    workbook = openpyxl.load_workbook(SOURCE, read_only=True, data_only=True)
    worksheet = workbook.active
    rows = worksheet.iter_rows(values_only=True)
    headers = [clean(value) for value in next(rows)]
    projects: list[dict[str, object]] = []

    for index, row in enumerate(rows, start=1):
        record = dict(zip(headers, row))
        title = clean(record.get("系统名"))
        if not title:
            continue
        projects.append(
            {
                "id": index,
                "title": title,
                "components": clean(record.get("元器件清单")),
                "features": clean(record.get("功能清单")),
                "hardware_cost": record.get("硬件成本"),
                "status": clean(record.get("状态")),
                "notes": clean(record.get("备注")),
            }
        )

    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(json.dumps(projects, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已导出 {len(projects)} 条项目记录到 {TARGET}")


if __name__ == "__main__":
    main()
