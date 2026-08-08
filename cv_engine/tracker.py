"""
轨迹状态管理（轻量） — ByteTrack 已内置在 detector 中完成跟踪
本模块仅维护每条轨迹的元数据：访问区域、异常评分、店员标记等
"""
from typing import Any


class TrackState:
    """单条轨迹的元数据

    ByteTrack 负责 bbox + track_id 的持续关联，
    本类只存业务层关心的状态——区域访问记录、异常评分、店员判定。
    """

    __slots__ = (
        "track_id", "visited_zones", "anomaly_score",
        "is_near_exit", "is_staff", "staff_confidence",
        "last_center", "hit_times", "lost_times",
        "emotion", "emotion_conf",  # 表情标签 + 置信度
    )

    def __init__(self, track_id: int, center: tuple[float, float]):
        self.track_id = track_id

        # 区域访问: {zone_id: {"enter_frame": N, "dwell_frames": 0, "counted": False}}
        self.visited_zones: dict[str, dict[str, Any]] = {}

        # 异常 & 店员
        self.anomaly_score: int = 0
        self.is_near_exit: bool = False
        self.is_staff: bool = False          # 是否疑似店员
        self.staff_confidence: float = 0.0   # 店员判定置信度

        # 位置追踪
        self.last_center: tuple[float, float] = center
        self.hit_times: int = 1
        self.lost_times: int = 0

        # 表情（SKII-3）
        self.emotion: str = "unknown"
        self.emotion_conf: float = 0.0

    @property
    def center(self) -> tuple[float, float]:
        return self.last_center

    def update_position(self, bbox: list[int]):
        """更新最近位置"""
        x1, y1, x2, y2 = bbox
        self.last_center = ((x1 + x2) / 2, (y1 + y2) / 2)
        self.hit_times += 1
        self.lost_times = 0

    def mark_lost(self):
        """标记一帧未匹配"""
        self.lost_times += 1


class TrackStateManager:
    """轨迹状态管理器

    维护 track_id → TrackState 的映射，自动清理过期轨迹。
    与 ByteTrack 的 persist=True 配合使用。
    """

    def __init__(self, max_lost: int = 30):
        self._tracks: dict[int, TrackState] = {}
        self.max_lost = max_lost

    def get_or_create(self, track_id: int, bbox: list[int]) -> TrackState:
        """获取或创建轨迹状态"""
        cx, cy = (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2
        if track_id not in self._tracks:
            self._tracks[track_id] = TrackState(track_id, (cx, cy))
        else:
            self._tracks[track_id].update_position(bbox)
        return self._tracks[track_id]

    def get(self, track_id: int) -> TrackState | None:
        return self._tracks.get(track_id)

    def mark_all_lost(self):
        """标记所有轨迹一帧未匹配"""
        for t in self._tracks.values():
            t.mark_lost()

    def cleanup(self):
        """清理长期未匹配的轨迹"""
        stale = [
            tid for tid, t in self._tracks.items()
            if t.lost_times > self.max_lost
        ]
        for tid in stale:
            del self._tracks[tid]

    def get_active(self) -> list[TrackState]:
        """获取活跃轨迹（最近有匹配）"""
        self.cleanup()
        return [t for t in self._tracks.values() if t.lost_times == 0]

    def get_all(self) -> list[TrackState]:
        return list(self._tracks.values())

    @property
    def active_count(self) -> int:
        return len(self.get_active())

    def reset(self):
        self._tracks.clear()
