import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from component_library import fixed_components, fixed_description  # noqa: E402
import server  # noqa: E402


class ComponentLibraryTests(unittest.TestCase):
    def test_known_component_uses_bound_sentence(self):
        self.assertEqual(fixed_description("DHT11", "sensor"), "读取环境温度与相对湿度数据。")

    def test_combined_actuator_matches_specific_load(self):
        description = fixed_description("水泵 + 继电器驱动模块", "actuator")
        self.assertIn("灌溉、补水或循环", description)

    def test_unknown_component_uses_kind_fallback(self):
        component = fixed_components(["自定义检测模块"], "sensor")[0]
        self.assertEqual(component["name"], "自定义检测模块")
        self.assertIn("读取", component["description"])

    def test_password_lock_rule_fallback_avoids_environment_sensors(self):
        solution = server.build_solution("基于STM32的电子密码锁设计", 1, 3, 2)
        names = solution["sensors"]["items"]
        self.assertEqual(names, ["AS608 指纹识别模块", "4×4矩阵键盘", "门磁传感器"])
        self.assertNotIn("purpose", solution["sensors"])
        self.assertEqual(len(solution["sensors"]["components"]), 3)


if __name__ == "__main__":
    unittest.main()
