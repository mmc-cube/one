import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from component_catalog import load_component_catalog, public_component_options  # noqa: E402
from import_components import component_kind, import_catalog  # noqa: E402


class ComponentCatalogTests(unittest.TestCase):
    def test_imported_catalog_has_all_source_categories(self) -> None:
        catalog = load_component_catalog()
        self.assertEqual(catalog["summary"]["total"], 104)
        self.assertEqual(len(catalog["components"]), 104)
        self.assertGreaterEqual(catalog["summary"]["with_library"], 70)

    def test_component_classification_keeps_encoder_as_sensor(self) -> None:
        self.assertEqual(component_kind("电机-编码器"), "sensor")
        self.assertEqual(component_kind("电机-驱动-TB6612"), "actuator")
        self.assertEqual(component_kind("主控-STM32F103C8T6"), "reference")
        self.assertEqual(component_kind("电源-供电"), "reference")

    def test_pid_options_are_bounded_and_hide_unrelated_components(self) -> None:
        result = public_component_options("基于STM32的PID直流电机控制系统", [])
        names = " ".join(item["name"] for items in result["options"].values() for item in items)
        self.assertLessEqual(result["visible_count"], 20)
        self.assertIn("电机-编码器", names)
        self.assertIn("电源-ACS712", names)
        self.assertIn("电机-驱动-TB6612", names)
        self.assertNotIn("温湿度-DHT11", names)
        self.assertNotIn("心率-MAX30102", names)
        self.assertNotIn("水位", names)

    def test_public_options_do_not_expose_library_paths(self) -> None:
        result = public_component_options("智能温室控制系统", [])
        serialized = json.dumps(result, ensure_ascii=False)
        self.assertNotIn("library_matches", serialized)
        self.assertNotIn("lib_base", serialized)
        self.assertNotIn("folder", serialized)

    def test_importer_preserves_private_packaging_metadata(self) -> None:
        source_payload = {
            "config": {"lib_base": "D:/private-components"},
            "mappings": [
                {
                    "category": "温湿度-DHT11",
                    "keywords": ["dht11"],
                    "total_table_hits": 2,
                    "library_matches": [{"folder": "DHT11", "subdirs": ["src"], "files": ["dht11.c"]}],
                }
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.json"
            output = Path(directory) / "catalog.json"
            source.write_text(json.dumps(source_payload, ensure_ascii=False), encoding="utf-8")
            imported = import_catalog(source, output)
        self.assertEqual(imported["source"]["lib_base"], "D:/private-components")
        self.assertEqual(imported["components"][0]["library_matches"][0]["folder"], "DHT11")


if __name__ == "__main__":
    unittest.main()
