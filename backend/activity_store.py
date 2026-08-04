"""Persistent activity records used by the local test-event admin console."""

from __future__ import annotations

import json
import threading
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


MAX_RECORDS = 5000


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def topic_domain(topic: str) -> str:
    lowered = topic.lower()
    domains = (
        ("电机控制", ("电机", "pid", "调速", "编码器")),
        ("环境监测", ("温湿度", "环境", "空气质量", "气象")),
        ("智能农业", ("温室", "大棚", "农业", "灌溉", "土壤")),
        ("安防门禁", ("门禁", "门锁", "密码锁", "安防", "防盗")),
        ("健康监护", ("老人", "监护", "心率", "血氧", "医疗")),
        ("智能车辆", ("小车", "车辆", "循迹", "避障", "停车")),
        ("物联网", ("物联网", "mqtt", "wifi", "云端", "远程")),
        ("电源电子", ("高压", "逆变", "开关电源", "dc-dc", "dcdc")),
    )
    for label, markers in domains:
        if any(marker in lowered for marker in markers):
            return label
    return "其他"


class ActivityStore:
    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.RLock()
        self._data = self._load()

    @staticmethod
    def empty_data() -> dict[str, Any]:
        return {
            "version": 1,
            "events": [],
            "topics": [],
            "component_feedback": [],
            "feedback": [],
            "errors": [],
        }

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return self.empty_data()
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return self.empty_data()
        baseline = self.empty_data()
        if not isinstance(data, dict):
            return baseline
        for key, default in baseline.items():
            if key == "version":
                continue
            if not isinstance(data.get(key), list):
                data[key] = default
        data["version"] = 1
        return data

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self.path)

    @staticmethod
    def _new_id(prefix: str) -> str:
        return f"{prefix}_{uuid.uuid4().hex[:12]}"

    def _append(self, collection: str, record: dict[str, Any]) -> dict[str, Any]:
        records = self._data[collection]
        records.append(record)
        if len(records) > MAX_RECORDS:
            del records[: len(records) - MAX_RECORDS]
        return record

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return json.loads(json.dumps(self._data, ensure_ascii=False))

    def record_event(
        self,
        event_type: str,
        session_id: str,
        *,
        topic: str = "",
        status: str = "success",
        engine: str = "",
        duration_ms: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            record = self._append(
                "events",
                {
                    "id": self._new_id("evt"),
                    "type": event_type,
                    "session_id": session_id,
                    "topic": topic[:200],
                    "status": status,
                    "engine": engine,
                    "duration_ms": max(0, int(duration_ms)),
                    "metadata": metadata or {},
                    "created_at": utc_now(),
                },
            )
            self._save()
            return record

    def record_evaluations(
        self,
        session_id: str,
        topics: list[dict[str, Any]],
        engine: str,
        duration_ms: int,
    ) -> None:
        with self._lock:
            created_at = utc_now()
            for topic in topics:
                title = str(topic.get("title", ""))[:200]
                self._append(
                    "topics",
                    {
                        "id": self._new_id("topic"),
                        "session_id": session_id,
                        "title": title,
                        "domain": topic_domain(title),
                        "hardware_score": topic.get("hardware_score"),
                        "software_score": topic.get("software_score"),
                        "total_score": topic.get("total_score"),
                        "conclusion": str(topic.get("conclusion", "")),
                        "reason": str(topic.get("reason", ""))[:500],
                        "engine": engine,
                        "status": "已评估",
                        "selected_components": {},
                        "design_generated": False,
                        "pdf_export_count": 0,
                        "pdf_exported_at": "",
                        "created_at": created_at,
                    },
                )
            self._append(
                "events",
                {
                    "id": self._new_id("evt"),
                    "type": "topic_evaluated",
                    "session_id": session_id,
                    "topic": str(topics[0].get("title", ""))[:200] if topics else "",
                    "status": "success",
                    "engine": engine,
                    "duration_ms": max(0, int(duration_ms)),
                    "metadata": {"topic_count": len(topics)},
                    "created_at": created_at,
                },
            )
            self._save()

    def record_recommendation(
        self,
        session_id: str,
        topic: str,
        payload: dict[str, Any],
        duration_ms: int,
    ) -> None:
        recommendations = payload.get("recommendations", {})
        with self._lock:
            self._append(
                "events",
                {
                    "id": self._new_id("evt"),
                    "type": "components_recommended",
                    "session_id": session_id,
                    "topic": topic[:200],
                    "status": "success",
                    "engine": str(payload.get("engine", "")),
                    "duration_ms": max(0, int(duration_ms)),
                    "metadata": {"recommendations": recommendations},
                    "created_at": utc_now(),
                },
            )
            self._save()

    @staticmethod
    def _component_names(items: Any) -> list[str]:
        if not isinstance(items, list):
            return []
        names: list[str] = []
        for item in items:
            if isinstance(item, dict):
                name = str(item.get("name", "")).strip()
                quantity = max(1, int(item.get("quantity", 1)))
                names.extend([name] * quantity)
            else:
                name = str(item).strip()
                names.append(name)
        return [name for name in names if name]

    def record_design(
        self,
        session_id: str,
        topic: str,
        components: dict[str, Any],
        engine: str,
        duration_ms: int,
    ) -> None:
        with self._lock:
            selected = {kind: self._component_names(components.get(kind)) for kind in ("display", "sensor", "actuator")}
            recommendation = next(
                (
                    event
                    for event in reversed(self._data["events"])
                    if event.get("type") == "components_recommended"
                    and event.get("session_id") == session_id
                    and event.get("topic") == topic
                ),
                None,
            )
            recommended_raw = (recommendation or {}).get("metadata", {}).get("recommendations", {})
            for kind in ("display", "sensor", "actuator"):
                recommended = self._component_names(recommended_raw.get(kind, []))
                final = selected[kind]
                recommended_keys = {name.lower() for name in recommended}
                final_keys = {name.lower() for name in final}
                self._append(
                    "component_feedback",
                    {
                        "id": self._new_id("component"),
                        "session_id": session_id,
                        "topic": topic[:200],
                        "domain": topic_domain(topic),
                        "category": kind,
                        "recommended": recommended,
                        "selected": final,
                        "retained": [name for name in recommended if name.lower() in final_keys],
                        "removed": [name for name in recommended if name.lower() not in final_keys],
                        "added": [name for name in final if name.lower() not in recommended_keys],
                        "engine": engine,
                        "created_at": utc_now(),
                    },
                )
            topic_record = next(
                (
                    item
                    for item in reversed(self._data["topics"])
                    if item.get("session_id") == session_id and item.get("title") == topic
                ),
                None,
            )
            if topic_record:
                topic_record["selected_components"] = selected
                topic_record["design_generated"] = True
                topic_record["status"] = "已生成方案"
                topic_record["design_engine"] = engine
            self._append(
                "events",
                {
                    "id": self._new_id("evt"),
                    "type": "design_generated",
                    "session_id": session_id,
                    "topic": topic[:200],
                    "status": "success",
                    "engine": engine,
                    "duration_ms": max(0, int(duration_ms)),
                    "metadata": {"components": selected},
                    "created_at": utc_now(),
                },
            )
            self._save()

    def record_pdf_export(self, session_id: str, topic: str, status: str = "opened") -> None:
        with self._lock:
            created_at = utc_now()
            topic_record = next(
                (
                    item
                    for item in reversed(self._data["topics"])
                    if item.get("session_id") == session_id and item.get("title") == topic
                ),
                None,
            )
            if topic_record and status == "opened":
                topic_record["pdf_export_count"] = int(topic_record.get("pdf_export_count", 0)) + 1
                topic_record["pdf_exported_at"] = created_at
                topic_record["status"] = "已导出 PDF"
            self._append(
                "events",
                {
                    "id": self._new_id("evt"),
                    "type": "pdf_export_opened" if status == "opened" else "pdf_export_failed",
                    "session_id": session_id,
                    "topic": topic[:200],
                    "status": "success" if status == "opened" else "failed",
                    "engine": "browser-print",
                    "duration_ms": 0,
                    "metadata": {},
                    "created_at": created_at,
                },
            )
            self._save()

    def record_error(
        self,
        *,
        endpoint: str,
        session_id: str,
        message: str,
        status_code: int,
        topic: str = "",
        engine: str = "",
        duration_ms: int = 0,
        error_type: str = "请求处理失败",
        level: str = "中",
    ) -> str:
        with self._lock:
            error_id = self._new_id("error")
            self._append(
                "errors",
                {
                    "id": error_id,
                    "level": level,
                    "type": error_type,
                    "endpoint": endpoint,
                    "status_code": int(status_code),
                    "engine": engine,
                    "topic": topic[:200],
                    "session_id": session_id,
                    "occurred_at": utc_now(),
                    "status": "待处理",
                    "message": message[:1000],
                    "duration_ms": max(0, int(duration_ms)),
                    "token_usage": None,
                    "retry_success": None,
                    "admin_note": "",
                },
            )
            self._save()
            return error_id

    @staticmethod
    def _paginate(records: list[dict[str, Any]], page: int, page_size: int) -> dict[str, Any]:
        page = max(1, page)
        page_size = max(1, min(100, page_size))
        start = (page - 1) * page_size
        return {"items": records[start : start + page_size], "total": len(records), "page": page, "page_size": page_size}

    def overview(self) -> dict[str, Any]:
        data = self.snapshot()
        events = data["events"]
        today = datetime.now(timezone.utc).date().isoformat()
        today_events = [event for event in events if str(event.get("created_at", "")).startswith(today)]
        today_sessions = {event.get("session_id") for event in today_events if event.get("session_id")}
        counts = Counter(event.get("type") for event in today_events)
        all_counts = Counter(event.get("type") for event in events)
        trend: list[dict[str, Any]] = []
        for offset in range(6, -1, -1):
            day = (datetime.now(timezone.utc).date() - timedelta(days=offset)).isoformat()
            day_events = [event for event in events if str(event.get("created_at", "")).startswith(day)]
            day_counts = Counter(event.get("type") for event in day_events)
            trend.append({"date": day[5:], "evaluations": day_counts["topic_evaluated"], "designs": day_counts["design_generated"], "pdf_exports": day_counts["pdf_export_opened"]})
        popular = Counter(item.get("title") for item in data["topics"] if item.get("title"))
        return {
            "metrics": {
                "users_today": len(today_sessions),
                "evaluations_today": counts["topic_evaluated"],
                "designs_today": counts["design_generated"],
                "pdf_exports_today": counts["pdf_export_opened"],
                "pdf_export_rate": round(100 * all_counts["pdf_export_opened"] / max(1, all_counts["design_generated"]), 1),
            },
            "funnel": {
                "opened": len({event.get("session_id") for event in events if event.get("session_id")}),
                "evaluated": all_counts["topic_evaluated"],
                "configured": all_counts["components_recommended"],
                "generated": all_counts["design_generated"],
                "exported": all_counts["pdf_export_opened"],
            },
            "trend": trend,
            "popular_topics": [{"name": name, "count": count} for name, count in popular.most_common(5)],
            "recent_feedback": list(reversed(data["feedback"][-5:])),
            "recent_errors": list(reversed(data["errors"][-5:])),
        }

    def topics_page(self, params: dict[str, list[str]]) -> dict[str, Any]:
        records = list(reversed(self.snapshot()["topics"]))
        search = params.get("search", [""])[0].strip().lower()
        domain = params.get("domain", [""])[0].strip()
        engine = params.get("engine", [""])[0].strip()
        status = params.get("status", [""])[0].strip()
        if search:
            records = [item for item in records if search in str(item.get("title", "")).lower()]
        if domain:
            records = [item for item in records if item.get("domain") == domain]
        if engine:
            records = [item for item in records if item.get("engine") == engine]
        if status:
            records = [item for item in records if item.get("status") == status]
        return self._paginate(records, int(params.get("page", ["1"])[0]), int(params.get("page_size", ["10"])[0]))

    def component_report(self, params: dict[str, list[str]]) -> dict[str, Any]:
        records = list(reversed(self.snapshot()["component_feedback"]))
        domain = params.get("domain", [""])[0].strip()
        category = params.get("category", [""])[0].strip()
        if domain:
            records = [item for item in records if item.get("domain") == domain]
        if category:
            records = [item for item in records if item.get("category") == category]
        recommended = sum(len(item.get("recommended", [])) for item in records)
        retained = sum(len(item.get("retained", [])) for item in records)
        added = sum(len(item.get("added", [])) for item in records)
        removed = sum(len(item.get("removed", [])) for item in records)
        retained_rank = Counter(name for item in records for name in item.get("retained", []))
        removed_rank = Counter(name for item in records for name in item.get("removed", []))
        added_rank = Counter(name for item in records for name in item.get("added", []))
        page = self._paginate(records, int(params.get("page", ["1"])[0]), int(params.get("page_size", ["10"])[0]))
        page.update(
            {
                "metrics": {"recommended": recommended, "retention_rate": round(100 * retained / max(1, recommended), 1), "added": added, "removed": removed},
                "rankings": {
                    "retained": retained_rank.most_common(5),
                    "removed": removed_rank.most_common(5),
                    "added": added_rank.most_common(5),
                },
            }
        )
        return page

    def feedback_page(self, params: dict[str, list[str]]) -> dict[str, Any]:
        records = list(reversed(self.snapshot()["feedback"]))
        status = params.get("status", [""])[0].strip()
        if status:
            records = [item for item in records if item.get("status") == status]
        page = self._paginate(records, int(params.get("page", ["1"])[0]), int(params.get("page_size", ["10"])[0]))
        ratings = [float(item.get("rating", 0)) for item in records if item.get("rating")]
        page["metrics"] = {
            "total": len(records),
            "average_rating": round(sum(ratings) / max(1, len(ratings)), 1),
            "pending": sum(item.get("status") == "待处理" for item in records),
            "resolved": sum(item.get("status") == "已处理" for item in records),
        }
        return page

    def errors_page(self, params: dict[str, list[str]]) -> dict[str, Any]:
        snapshot = self.snapshot()
        records = list(reversed(snapshot["errors"]))
        status = params.get("status", [""])[0].strip()
        endpoint = params.get("endpoint", [""])[0].strip()
        if status:
            records = [item for item in records if item.get("status") == status]
        if endpoint:
            records = [item for item in records if item.get("endpoint") == endpoint]
        page = self._paginate(records, int(params.get("page", ["1"])[0]), int(params.get("page_size", ["10"])[0]))
        affected = {item.get("session_id") for item in records if item.get("session_id")}
        endpoints = Counter(item.get("endpoint") for item in records if item.get("endpoint"))
        failed_requests = sum(int(item.get("status_code", 0)) >= 400 for item in snapshot["errors"])
        request_total = len(snapshot["events"]) + failed_requests
        page["metrics"] = {
            "total": len(records),
            "affected_users": len(affected),
            "unresolved": sum(item.get("status") != "已解决" for item in records),
            "failure_rate": round(100 * failed_requests / max(1, request_total), 2),
        }
        page["endpoint_distribution"] = endpoints.most_common(6)
        return page

    def update_record(self, collection: str, record_id: str, status: str, admin_note: str) -> dict[str, Any] | None:
        if collection not in {"feedback", "errors"}:
            return None
        with self._lock:
            record = next((item for item in self._data[collection] if item.get("id") == record_id), None)
            if not record:
                return None
            record["status"] = status[:20]
            record["admin_note"] = admin_note[:1000]
            record["updated_at"] = utc_now()
            self._save()
            return json.loads(json.dumps(record, ensure_ascii=False))
