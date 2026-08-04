import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from design_rules import apply_component_rules, build_design_logic, choose_controller, filter_domain_items  # noqa: E402


class DesignRulesTests(unittest.TestCase):
    def test_default_controller_is_stm32(self) -> None:
        self.assertEqual(choose_controller("智能温湿度控制系统")["name"], "STM32F103C8T6")

    def test_explicit_esp32_is_respected(self) -> None:
        self.assertEqual(choose_controller("基于 ESP32 的环境监测系统")["name"], "ESP32-S3-N8R2")

    def test_relay_is_completed_with_real_load(self) -> None:
        result = apply_component_rules("智能大棚灌溉系统", ["DHT22"], ["OLED"], ["继电器x1"])
        self.assertIn("水泵 + 继电器驱动模块", result["actuators"])

    def test_led_does_not_use_relay(self) -> None:
        result = apply_component_rules("灯光控制系统", ["光敏传感器"], ["OLED"], ["LED + 继电器"])
        self.assertNotIn("继电器", result["actuators"][0])
        self.assertIn("GPIO", result["actuators"][0])

    def test_networking_is_only_added_when_requested(self) -> None:
        offline = build_design_logic("温湿度控制系统", ["DHT22"], ["OLED"], ["风扇"])
        online = build_design_logic("物联网温湿度控制系统", ["DHT22"], ["OLED"], ["风扇"])
        self.assertFalse(offline["networking"]["enabled"])
        self.assertTrue(online["networking"]["enabled"])
        self.assertIn("APP", online["networking"]["question"])

    def test_alarm_uses_silenced_state_machine(self) -> None:
        logic = build_design_logic("消防报警系统", ["火焰传感器"], ["OLED"], ["蜂鸣器告警模块"])
        titles = [item["title"] for item in logic["control_rules"]]
        self.assertIn("报警静默状态机", titles)

    def test_aquaculture_domain_prioritizes_oxygen_pump(self) -> None:
        result = apply_component_rules(
            "水产养殖水质监测与增氧控制系统",
            ["TDS传感器", "PH传感器", "浊度传感器"],
            ["OLED"],
            ["换水泵 + 继电器驱动模块", "水泵 + 继电器驱动模块"],
        )
        self.assertIn("增氧泵 + 继电器驱动模块", result["actuators"])
        self.assertIn("DS18B20 水温传感器", result["sensors"])

    def test_lock_domain_removes_unneeded_relay_from_stepper(self) -> None:
        result = apply_component_rules(
            "指纹密码电子门锁设计",
            ["环境温湿度传感器", "光敏传感器", "土壤湿度传感器"],
            ["OLED"],
            ["28BYJ-48 步进电机 + ULN2003 驱动板 + 继电器驱动模块", "蜂鸣器"],
        )
        self.assertEqual(result["sensors"][0], "AS608 指纹识别模块")
        self.assertEqual(result["actuators"][0], "电磁锁 + 继电器驱动模块")

    def test_stepper_motor_never_uses_relay_as_its_driver(self) -> None:
        result = apply_component_rules(
            "步进电机控制模块",
            ["光敏传感器"],
            ["OLED"],
            ["28BYJ-48 步进电机 + ULN2003 驱动板 + 继电器驱动模块"],
        )
        self.assertIn("ULN2003", result["actuators"][0])
        self.assertNotIn("继电器", result["actuators"][0])

    def test_fire_alarm_domain_excludes_water_level_sensor(self) -> None:
        result = apply_component_rules(
            "火灾烟雾监测与报警系统",
            ["MQ-2 烟雾传感器", "水位传感器", "DHT11"],
            ["OLED"],
            ["蜂鸣器", "排水泵 + 继电器模块"],
        )
        self.assertNotIn("水位传感器", result["sensors"])
        self.assertIn("火焰传感器", result["sensors"])

    def test_lock_function_design_uses_lock_flow_not_threshold_template(self) -> None:
        logic = build_design_logic(
            "指纹密码电子门锁设计",
            ["AS608 指纹识别模块", "4×4矩阵键盘", "门磁传感器"],
            ["OLED"],
            ["电磁锁 + 继电器驱动模块", "有源蜂鸣器"],
        )
        functions = "\n".join(logic["function_lines"])
        self.assertIn("身份验证", functions)
        self.assertIn("输错密码", functions)
        self.assertNotIn("阈值控制", functions)

    def test_greenhouse_display_design_lists_data_and_threshold_pages(self) -> None:
        logic = build_design_logic("智能温湿度灌溉系统", ["DHT22"], ["OLED"], ["水泵", "风扇"])
        pages = "\n".join(logic["display_design"])
        self.assertIn("Temp: 25.6C", pages)
        self.assertIn("PUMP: OFF", pages)
        self.assertIn("阈值设置", pages)

    def test_oled_pages_are_strictly_four_lines(self) -> None:
        logic = build_design_logic("智能温湿度灌溉系统", ["DHT22"], ["OLED"], ["水泵", "风扇"])
        self.assertEqual(len(logic["oled_pages"]), 3)
        self.assertTrue(all(len(page["lines"]) == 4 for page in logic["oled_pages"]))
        self.assertEqual(logic["oled_pages"][0]["lines"][0], "Temp: 25.6C")

    def test_pid_domain_filters_irrelevant_sensor_and_fills_count(self) -> None:
        result = filter_domain_items(
            "基于STM32的PID直流电机控制系统",
            "sensor",
            ["增量式编码器", "水位传感器", "人体红外传感器", "按键模块"],
            4,
        )
        self.assertEqual(len(result), 4)
        self.assertNotIn("水位传感器", result)
        self.assertNotIn("人体红外传感器", result)
        self.assertIn("ACS712 电流传感器", result)
        self.assertIn("光电测速模块", result)


if __name__ == "__main__":
    unittest.main()
