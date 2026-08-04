import tempfile
import unittest
from pathlib import Path


import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from activity_store import ActivityStore  # noqa: E402


class ActivityStoreTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.store = ActivityStore(Path(self.temporary.name) / "activity.json")

    def tearDown(self):
        self.temporary.cleanup()

    def test_records_complete_evaluation_to_pdf_funnel(self):
        topic = "基于STM32的PID直流电机控制系统"
        self.store.record_evaluations(
            "session-a",
            [{
                "title": topic,
                "hardware_score": 7.2,
                "software_score": 6.5,
                "total_score": 6.9,
                "conclusion": "需要一定基础",
                "reason": "需要完成闭环控制。",
            }],
            "rules",
            125,
        )
        recommendation = {
            "engine": "rules",
            "recommendations": {
                "display": [{"name": "OLED"}],
                "sensor": [{"name": "编码器"}, {"name": "电流检测"}],
                "actuator": [{"name": "TB6612FNG"}],
            },
        }
        self.store.record_recommendation("session-a", topic, recommendation, 20)
        self.store.record_design(
            "session-a",
            topic,
            {
                "display": [{"name": "OLED"}],
                "sensor": [{"name": "编码器"}, {"name": "按键"}],
                "actuator": [{"name": "DRV8871"}],
            },
            "rules",
            240,
        )
        self.store.record_pdf_export("session-a", topic)

        overview = self.store.overview()
        self.assertEqual(overview["funnel"]["evaluated"], 1)
        self.assertEqual(overview["funnel"]["configured"], 1)
        self.assertEqual(overview["funnel"]["generated"], 1)
        self.assertEqual(overview["funnel"]["exported"], 1)

        topics = self.store.topics_page({"page": ["1"], "page_size": ["10"]})
        self.assertEqual(topics["items"][0]["status"], "已导出 PDF")
        self.assertEqual(topics["items"][0]["pdf_export_count"], 1)

        report = self.store.component_report({"page": ["1"], "page_size": ["10"]})
        self.assertEqual(report["metrics"]["recommended"], 4)
        self.assertEqual(report["metrics"]["added"], 2)
        self.assertEqual(report["metrics"]["removed"], 2)

    def test_error_can_be_filtered_and_resolved(self):
        error_id = self.store.record_error(
            endpoint="/api/topics/evaluate",
            session_id="session-b",
            message="请求失败",
            status_code=500,
            topic="测试题目",
            level="高",
        )
        result = self.store.errors_page({"status": ["待处理"], "page": ["1"], "page_size": ["10"]})
        self.assertEqual(result["total"], 1)
        self.assertGreater(result["metrics"]["failure_rate"], 0)

        updated = self.store.update_record("errors", error_id, "已解决", "已经确认并修复")
        self.assertIsNotNone(updated)
        self.assertEqual(updated["status"], "已解决")
        self.assertEqual(updated["admin_note"], "已经确认并修复")


if __name__ == "__main__":
    unittest.main()
