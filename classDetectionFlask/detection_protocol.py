import time
import uuid
from datetime import datetime


BEHAVIOR_NAMES = {
    "raise_hand": "举手互动",
    "read": "阅读",
    "write": "书写",
    "phone": "疑似玩手机",
    "head_down": "持续低头",
    "lie_desk": "趴桌",
    "sleep": "疑似睡觉",
    "focus": "专注学习",
}

BEHAVIOR_ALIASES = {
    "raise_hand": {"raise_hand", "hand", "hand_raising", "hand-raising", "raise hand", "举手"},
    "read": {"read", "reading", "book", "阅读", "读书"},
    "write": {"write", "writing", "书写", "写字"},
    "phone": {"phone", "cellphone", "mobile", "play_phone", "playing phone", "玩手机", "手机"},
    "head_down": {"head_down", "head-down", "low_head", "low-head", "bow", "lower_head", "低头", "持续低头"},
    "lie_desk": {"lie_desk", "lie-desk", "desk", "lean_desk", "lean-desk", "table", "sleep on desk", "趴桌", "靠桌子"},
    "sleep": {"sleep", "sleeping", "asleep", "睡觉", "疑似睡觉"},
}

RISK_WEIGHT = {"normal": 0, "low": 1, "medium": 2, "high": 3}
WATCH_BEHAVIORS = ["sleep", "lie_desk", "head_down", "phone", "focus"]


def normalize_behavior_label(label):
    raw = str(label or "").strip()
    key = raw.lower().replace(" ", "_")
    for behavior, aliases in BEHAVIOR_ALIASES.items():
        if raw in aliases or key in aliases:
            return behavior
    return key


def behavior_name(behavior_type):
    return BEHAVIOR_NAMES.get(behavior_type, behavior_type or "检测事件")


def risk_name(risk_level):
    return {"normal": "正常", "low": "低", "medium": "中", "high": "高"}.get(risk_level, "正常")


def format_duration(seconds):
    value = max(0, int(round(seconds or 0)))
    if value >= 60:
        return f"{value // 60}分{value % 60:02d}秒"
    return f"{value}秒"


class DetectionProtocolAdapter:
    """Convert unstable model outputs into the demo system data protocol.

    Input can be raw model labels and optional detection boxes. Output is a
    stable socket payload consumed by Vue pages and Spring Boot warning records.
    """

    protocol_version = "classroom-demo-v1"

    def __init__(self, fps=20, source_type="video", source_name="", session_id=None):
        self.fps = fps if fps and fps > 0 else 20
        self.frame_seconds = 1.0 / self.fps
        self.source_type = source_type
        self.source_name = source_name or source_type
        self.session_id = session_id or f"DEMO-{uuid.uuid4().hex[:8].upper()}"
        self.frame_index = 0
        self.started_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.stats = {
            key: {"behaviorType": key, "behaviorName": behavior_name(key), "durationSeconds": 0.0, "count": 0, "confidence": 0.0}
            for key in WATCH_BEHAVIORS
        }
        self.consecutive = {key: 0.0 for key in WATCH_BEHAVIORS}
        self.emitted = set()
        self.current_risk = "normal"
        self.current_reason = ""
        self.events = []

    def update(self, labels, detections=None, progress=None):
        self.frame_index += 1
        detections = detections or []
        raw_labels = list(labels or [])
        normalized = [normalize_behavior_label(label) for label in raw_labels]
        detected = set(normalized)
        focused = {"raise_hand", "read", "write"}
        if focused.intersection(detected):
            detected.add("focus")

        confidence_by_behavior = self._confidence_by_behavior(detections)
        for behavior in WATCH_BEHAVIORS:
            if behavior in detected:
                stat = self.stats[behavior]
                stat["durationSeconds"] += self.frame_seconds
                stat["count"] += 1
                stat["confidence"] = max(stat["confidence"], confidence_by_behavior.get(behavior, 0.82))
                self.consecutive[behavior] += self.frame_seconds
            else:
                self.consecutive[behavior] = 0.0

        warning = self._build_warning()
        if warning:
            self.events.insert(0, warning)
            self.current_risk = warning["riskLevel"]
            self.current_reason = warning["reason"]

        payload = {
            "protocolVersion": self.protocol_version,
            "sessionId": self.session_id,
            "sourceType": self.source_type,
            "sourceName": self.source_name,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "frameIndex": self.frame_index,
            "progress": progress,
            "labels": raw_labels,
            "normalizedLabels": normalized,
            "displayLabels": [behavior_name(label) for label in normalized],
            "detections": detections,
            "behaviorStats": self._stats_payload(),
            "warningState": {
                "riskLevel": self.current_risk,
                "reason": self.current_reason,
                "durations": {key: round(value["durationSeconds"], 1) for key, value in self.stats.items()},
                "consecutiveDurations": {key: round(value, 1) for key, value in self.consecutive.items()},
                "warning": warning,
            },
            "events": self.events[:10],
        }
        return payload

    def complete(self):
        return {
            "protocolVersion": self.protocol_version,
            "sessionId": self.session_id,
            "sourceType": self.source_type,
            "sourceName": self.source_name,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "completed": True,
            "progress": 100,
            "behaviorStats": self._stats_payload(),
            "events": self.events,
            "warningState": {
                "riskLevel": self.current_risk,
                "reason": self.current_reason,
                "durations": {key: round(value["durationSeconds"], 1) for key, value in self.stats.items()},
                "consecutiveDurations": {key: round(value, 1) for key, value in self.consecutive.items()},
                "warning": None,
            },
        }

    def _confidence_by_behavior(self, detections):
        result = {}
        for item in detections:
            behavior = normalize_behavior_label(item.get("behaviorType") or item.get("label"))
            confidence = float(item.get("confidence") or 0)
            result[behavior] = max(result.get(behavior, 0), confidence)
        return result

    def _stats_payload(self):
        total = sum(item["durationSeconds"] for item in self.stats.values()) or 1
        payload = []
        for key, item in self.stats.items():
            seconds = item["durationSeconds"]
            payload.append({
                "behaviorType": key,
                "behaviorName": item["behaviorName"],
                "durationSeconds": round(seconds, 1),
                "durationText": format_duration(seconds),
                "count": item["count"],
                "ratio": round(seconds / total * 100, 1),
                "confidence": round(item["confidence"], 3) if item["confidence"] else 0,
            })
        return payload

    def _build_warning(self):
        candidates = []
        if "sleep" not in self.emitted and (self.consecutive["sleep"] >= 10 or self.stats["sleep"]["durationSeconds"] >= 10):
            candidates.append(("sleep", "high", "疑似睡觉持续超过10秒，建议生成高风险检测事件。"))
        if "lie_desk" not in self.emitted and (self.consecutive["lie_desk"] >= 10 or self.stats["lie_desk"]["durationSeconds"] >= 10):
            candidates.append(("lie_desk", "high", "趴桌行为持续超过10秒，建议生成高风险检测事件。"))
        if "head_down" not in self.emitted and (self.consecutive["head_down"] >= 15 or self.stats["head_down"]["durationSeconds"] >= 15):
            candidates.append(("head_down", "medium", "持续低头超过15秒，建议生成中风险检测事件。"))
        if "phone" not in self.emitted and self.stats["phone"]["durationSeconds"] >= 15:
            candidates.append(("phone", "low", "疑似玩手机累计超过15秒，建议作为课堂异常事件记录。"))
        if not candidates:
            return None

        candidates.sort(key=lambda item: RISK_WEIGHT[item[1]], reverse=True)
        behavior, risk_level, reason = candidates[0]
        self.emitted.add(behavior)
        stat = self.stats[behavior]
        return {
            "eventId": f"{self.session_id}-{len(self.events) + 1:03d}",
            "sourceType": self.source_type,
            "sourceName": self.source_name,
            "behaviorType": behavior,
            "behaviorName": behavior_name(behavior),
            "riskLevel": risk_level,
            "riskName": risk_name(risk_level),
            "durationSeconds": round(stat["durationSeconds"], 1),
            "durationText": format_duration(stat["durationSeconds"]),
            "confidence": round(stat["confidence"] or 0.85, 3),
            "reason": reason,
            "triggerTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": "待跟进",
        }


def demo_frame_payload(source_type="video", source_name="demo"):
    """Fallback payload for integration tests or unstable model phases."""
    adapter = DetectionProtocolAdapter(20, source_type, source_name, f"DEMO-{int(time.time())}")
    payload = None
    for _ in range(220):
        payload = adapter.update(["lie_desk"], progress=60)
    return payload or adapter.complete()
