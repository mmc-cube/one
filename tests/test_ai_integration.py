import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import server  # noqa: E402


class FakeAI:
    configured = True
    model = "fake-model"

    def chat_json(self, system_prompt, payload):
        if "逐题评估" in payload["task"]:
            return {
                "topics": [
                    {
                        "title": item["title"],
                        "hardware_score": 6.2,
                        "software_score": 7.4,
                        "conclusion": "推荐",
                        "reason": "测试 AI 评分结果",
                    }
                    for item in payload["topics"]
                ]
            }
        return {
            "sensors": {
                "components": [
                    {"name": "DHT22 温湿度传感器", "description": "AI：读取窗帘附近的温湿度。"},
                    {"name": "BH1750 光照传感器", "description": "AI：读取窗边光照强度。"},
                    {"name": "多余传感器", "description": "AI：不应保留。"},
                ],
            },
            "displays": {
                "components": [{"name": "LCD1602", "description": "AI：显示窗帘状态。"}],
            },
            "actuators": {
                "components": [
                    {"name": "LED + 继电器", "description": "AI：显示运行状态。"},
                    {"name": "步进电机", "description": "AI：带动窗帘开合。"},
                ],
            },
            "function_lines": ["AI 生成功能一", "AI 生成功能二"],
            "oled_pages": [
                {"title": "实时状态", "lines": ["Light: 1200lx", "Rain : NO", "Curt : OPEN", "MODE : AUTO"]},
                {"title": "控制状态", "lines": ["Motor: STOP", "Limit: OK", "Cause: Light", "KEY1: Next"]},
            ],
        }


class OfflineAI:
    configured = False
    model = ""


class AIIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.original_ai = server.AI
        server.AI = FakeAI()

    def tearDown(self):
        server.AI = self.original_ai

    def test_ai_evaluation_is_normalized(self):
        topic = "智能温湿度控制系统"
        baseline = server.evaluate_topic(topic, 1)
        result = server.evaluate_topics_with_ai([topic], [baseline])[0]
        self.assertEqual(result["title"], topic)
        self.assertLessEqual(result["total_score"], 6.8)

    def test_common_project_receives_high_feasibility_score(self):
        result = server.evaluate_topic("基于STM32的指纹密码电子门锁设计", 1)
        self.assertGreaterEqual(result["hardware_score"], 8.0)
        self.assertGreaterEqual(result["software_score"], 8.0)

    def test_common_topics_keep_high_but_distinct_scores(self):
        temperature = server.evaluate_topic("基于单片机的智能温湿度控制系统", 1)
        lock = server.evaluate_topic("基于STM32的电子密码锁设计", 2)
        iot = server.evaluate_topic("基于物联网的环境监测系统", 3)
        self.assertGreater(lock["total_score"], temperature["total_score"])
        self.assertGreater(iot["total_score"], temperature["total_score"])
        self.assertGreaterEqual(iot["total_score"], 8.0)

    def test_requested_difficulty_hierarchy_is_reflected_in_feasibility(self):
        power = server.evaluate_topic("基于STM32的开关电源控制系统设计", 1)
        thermal = server.evaluate_topic("基于单片机的智能风扇温控系统", 2)
        pid = server.evaluate_topic("基于STM32的PID直流电机调速系统", 3)
        stepper = server.evaluate_topic("基于STM32的步进电机位置控制系统", 4)
        sensor = server.evaluate_topic("基于单片机的光照强度监测系统", 5)
        self.assertLess(power["total_score"], thermal["total_score"])
        self.assertLess(thermal["total_score"], pid["total_score"])
        self.assertLess(pid["total_score"], stepper["total_score"])
        self.assertLess(stepper["total_score"], sensor["total_score"])

    def test_pid_motor_is_materially_less_feasible_than_lock_and_iot(self):
        pid = server.evaluate_topic("基于STM32的PID直流电机控制系统", 1)
        lock = server.evaluate_topic("基于STM32的电子密码锁设计", 2)
        iot = server.evaluate_topic("基于物联网的环境监测系统", 3)
        self.assertLess(pid["hardware_score"], 8.0)
        self.assertLess(pid["software_score"], 7.0)
        self.assertLess(pid["total_score"], iot["total_score"])
        self.assertLess(pid["total_score"], lock["total_score"])
        self.assertEqual(pid["conclusion"], "需要一定基础")

    def test_ai_reason_is_used_when_it_is_topic_safe(self):
        topic = "基于STM32的电子密码锁设计"
        baseline = server.evaluate_topic(topic, 1)
        result = server.evaluate_topics_with_ai([topic], [baseline])[0]
        self.assertEqual(result["reason"], "测试 AI 评分结果")

    def test_ai_design_is_count_limited_and_rule_checked(self):
        topic = "智能照明控制系统"
        baseline = server.build_solution(topic, 1, 2, 2)
        result = server.enhance_solution_with_ai(topic, baseline, 1, 2, 2)
        self.assertEqual(len(result["sensors"]["items"]), 2)
        self.assertEqual(len(result["displays"]["items"]), 1)
        self.assertEqual(len(result["actuators"]["items"]), 2)
        self.assertNotIn("继电器", result["actuators"]["items"][0])
        self.assertIn("ULN2003", result["actuators"]["items"][1])
        self.assertEqual(result["design_logic"]["function_lines"], ["AI 生成功能一", "AI 生成功能二"])
        self.assertEqual(len(result["design_logic"]["oled_pages"]), 2)
        self.assertEqual(result["design_logic"]["oled_pages"][0]["lines"], ["Light: 1200lx", "Rain : NO", "Curt : OPEN", "MODE : AUTO"])
        self.assertEqual(result["description_mode"], "fixed")
        self.assertIn("读取环境温度", result["sensors"]["components"][0]["description"])

    def test_ai_description_mode_uses_topic_specific_sentence(self):
        topic = "智能照明控制系统"
        baseline = server.build_solution(topic, 1, 2, 2, "ai")
        result = server.enhance_solution_with_ai(topic, baseline, 1, 2, 2, "ai")
        self.assertEqual(result["description_mode"], "ai")
        self.assertEqual(result["sensors"]["components"][1]["description"], "AI：读取窗边光照强度。")

    def test_pid_motor_rejects_irrelevant_ai_text_and_uses_pid_fallback(self):
        topic = "基于STM32的PID直流电机控制系统"
        baseline = server.build_solution(topic, 1, 3, 2)
        result = server.enhance_solution_with_ai(topic, baseline, 1, 3, 2)
        functions = "\n".join(result["design_logic"]["function_lines"])
        oled_text = "\n".join(
            " ".join(page["lines"]) for page in result["design_logic"]["oled_pages"]
        )
        self.assertIn("PID", functions)
        self.assertNotIn("阈值", functions)
        self.assertIn("PWM", oled_text)
        self.assertNotIn("阈值", oled_text)

    def test_component_recommendations_use_ai_and_default_counts(self):
        result = server.recommend_components("基于STM32的PID直流电机控制系统")
        self.assertEqual(result["engine"], "ai")
        self.assertEqual(result["counts"], {"display": 1, "sensor": 3, "actuator": 2})
        self.assertEqual(len(result["recommendations"]["display"]), 1)
        self.assertEqual(len(result["recommendations"]["sensor"]), 4)
        self.assertEqual(len(result["recommendations"]["actuator"]), 2)
        supplemental = [item for item in result["recommendations"]["sensor"] if item.get("supplemental")]
        self.assertEqual(len(supplemental), 1)
        self.assertTrue(any(marker in supplemental[0]["name"].lower() for marker in ("按键", "键盘", "button", "keypad")))

    def test_rule_recommendations_change_with_topic(self):
        server.AI = OfflineAI()
        pid = server.recommend_components("基于STM32的PID直流电机控制系统")
        greenhouse = server.recommend_components("基于STM32的智能温室控制系统")
        pid_sensors = [item["name"] for item in pid["recommendations"]["sensor"]]
        greenhouse_sensors = [item["name"] for item in greenhouse["recommendations"]["sensor"]]
        self.assertNotEqual(pid_sensors, greenhouse_sensors)
        self.assertIn("增量式编码器", pid_sensors)
        self.assertTrue(any("温湿度" in name for name in greenhouse_sensors))
        self.assertTrue(any(item.get("supplemental") for item in greenhouse["recommendations"]["sensor"]))

    def test_common_domains_filter_ai_noise_and_keep_default_shape(self):
        cases = [
            ("基于STM32的PID直流电机控制系统", ("编码器", "电流", "测速"), ("水位", "温湿度")),
            ("基于STM32的智能温室控制系统", ("温湿度", "土壤湿度", "光照"), ("编码器", "水位")),
            ("基于STM32的指纹密码门禁系统", ("指纹", "门磁", "射频"), ("温湿度", "水位")),
            ("基于STM32的火灾消防报警系统", ("烟雾", "温度", "火焰"), ("水位", "编码器")),
            ("基于ESP32的物联网环境监测站", ("温湿度", "光照", "空气质量"), ("编码器", "水位")),
        ]
        for topic, required_markers, forbidden_markers in cases:
            with self.subTest(topic=topic):
                result = server.recommend_components(topic)
                sensors = result["recommendations"]["sensor"]
                actuators = result["recommendations"]["actuator"]
                regular = [item for item in sensors if not item.get("supplemental")]
                supplemental = [item for item in sensors if item.get("supplemental")]
                names = " ".join(item["name"] for item in regular)
                self.assertEqual(len(result["recommendations"]["display"]), 1)
                self.assertEqual(len(regular), 3)
                self.assertEqual(len(supplemental), 1)
                self.assertEqual(len(actuators), 2)
                for marker in required_markers:
                    self.assertIn(marker, names)
                for marker in forbidden_markers:
                    self.assertNotIn(marker, names)

    def test_selected_components_are_locked_and_button_is_supplemental(self):
        counts = {"display": 1, "sensor": 3, "actuator": 2}
        raw = {
            "display": [{"name": "LCD1602", "model": "HD44780", "quantity": 1}],
            "sensor": [
                {"name": "增量式编码器", "model": "AB 相", "quantity": 2},
                {"name": "ACS712", "model": "20A", "quantity": 1},
                {"name": "独立按键模块", "model": "参数设置", "quantity": 1, "supplemental": True},
            ],
            "actuator": [
                {"name": "TB6612FNG", "model": "双路 H 桥", "quantity": 1},
                {"name": "直流减速电机", "model": "12V", "quantity": 1},
            ],
        }
        selected = server.normalize_selected_components(raw, counts)
        self.assertEqual(len(selected["sensor"]), 4)
        baseline = server.build_selected_solution("PID 直流电机控制", selected)
        result = server.enhance_solution_with_ai(
            "PID 直流电机控制", baseline, 1, 3, 2, locked_components=selected
        )
        self.assertEqual(result["sensors"]["items"], selected["sensor"])
        self.assertEqual(result["displays"]["items"], selected["display"])
        self.assertEqual(result["actuators"]["items"], selected["actuator"])

    def test_required_controller_is_applied(self):
        selected = {"display": ["OLED"], "sensor": ["编码器"], "actuator": ["TB6612FNG"]}
        solution = server.build_selected_solution("PID 直流电机控制", selected)
        server.apply_special_requirements(solution, selected, "必须使用 STM32F407")
        self.assertEqual(solution["design_logic"]["controller"]["name"], "STM32F407")
        self.assertIn("定制约束：必须使用 STM32F407", solution["design_logic"]["function_lines"])

    def test_forbidden_selected_component_reports_conflict(self):
        selected = {"display": ["OLED"], "sensor": ["编码器"], "actuator": ["L298N 电机驱动"]}
        solution = server.build_selected_solution("PID 直流电机控制", selected)
        with self.assertRaisesRegex(ValueError, "特殊要求与当前选择冲突"):
            server.apply_special_requirements(solution, selected, "不能使用 L298N")


if __name__ == "__main__":
    unittest.main()
