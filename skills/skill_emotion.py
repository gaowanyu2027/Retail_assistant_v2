"""
SKII-3：表情分析技能
统计顾客情绪分布、正负情感趋势、分时段对比
"""
from collections import defaultdict, deque
from typing import Any
from datetime import datetime

from cv_engine.tracker import TrackState


class SkillEmotion:
    """表情分析技能（纯逻辑，不依赖LLM）

    输出维度：
    - distribution: 7类表情的计数分布
    - positive_rate: 正向情绪 (happy+neutral) 占比
    - trend: 分前后半段的正向率变化 → 情感趋势结论
    - records: 最近N条表情记录
    """

    def __init__(self):
        # 表情计数
        self._emotion_counts: dict[str, int] = defaultdict(int)
        # 分时段: [(timestamp, emotion), ...]
        self._timeline: deque[tuple[float, str]] = deque(maxlen=10000)
        # 最近记录
        self._recent: deque[dict] = deque(maxlen=200)
        self._total_faces: int = 0

    def process(self, tracks: list[TrackState], timestamp: float):
        """每帧处理表情数据"""
        for t in tracks:
            if t.emotion != "unknown" and t.emotion_conf > 0.3:
                self._emotion_counts[t.emotion] += 1
                self._total_faces += 1
                self._timeline.append((timestamp, t.emotion))
                self._recent.append({
                    "track_id": t.track_id,
                    "emotion": t.emotion,
                    "emotion_cn": t.emotion if t.emotion == "unknown" else "",
                    "conf": t.emotion_conf,
                    "timestamp": datetime.now().isoformat(),
                })

    def get_stats(self) -> dict[str, Any]:
        """获取表情统计"""
        return {
            "total_faces": self._total_faces,
            "distribution": dict(self._emotion_counts),
            "positive_count": sum(self._emotion_counts.get(e, 0) for e in ("happy", "neutral")),
            "negative_count": sum(self._emotion_counts.get(e, 0) for e in ("angry", "disgust", "fear", "sad")),
            "dominant_emotion": max(self._emotion_counts, key=self._emotion_counts.get) if self._emotion_counts else "none",
            "timestamp": datetime.now().isoformat(),
        }

    def get_trend(self) -> dict[str, Any]:
        """分前后半段情感趋势分析"""
        if len(self._timeline) < 10:
            return {"trend": "not_enough_data", "early_rate": 0, "late_rate": 0, "conclusion": "数据不足"}

        total = len(self._timeline)
        mid = total // 2
        early_positive = 0
        late_positive = 0
        for i, (_, emotion) in enumerate(self._timeline):
            if emotion in ("happy", "neutral"):
                if i < mid:
                    early_positive += 1
                else:
                    late_positive += 1

        early_count = mid
        late_count = total - mid
        early_rate = early_positive / early_count if early_count else 0.0
        late_rate = late_positive / late_count if late_count else 0.0
        delta = late_rate - early_rate

        if delta > 0.1:
            conclusion = "顾客情绪明显好转，购物体验改善"
        elif delta > 0.03:
            conclusion = "顾客情绪略有改善"
        elif delta < -0.1:
            conclusion = "顾客情绪明显下降，建议关注服务或环境"
        elif delta < -0.03:
            conclusion = "顾客情绪轻微下降"
        else:
            conclusion = "顾客情绪基本稳定，无明显变化"

        return {
            "early_count": early_count,
            "late_count": late_count,
            "early_rate": round(early_rate, 3),
            "late_rate": round(late_rate, 3),
            "delta": round(delta, 3),
            "conclusion": conclusion,
            "timestamp": datetime.now().isoformat(),
        }

    def get_recent(self, limit: int = 20) -> list[dict]:
        if limit <= 0:
            limit = len(self._recent)
        return list(self._recent)[-limit:][::-1]

    def reset(self):
        self._emotion_counts.clear()
        self._timeline.clear()
        self._recent.clear()
        self._total_faces = 0
