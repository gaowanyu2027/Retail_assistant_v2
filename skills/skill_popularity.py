"""
SKII-1：货架热度分析（三维评分 + 店员判定）

三维热度 = 到访人次 × w1 + 总停留时长 × w2 + 深度兴趣人数 × w3
店员判定 = 单次连续停留 > 15分钟 → 标记为"疑似店员"，不计入热度
"""
from collections import OrderedDict, defaultdict
from dataclasses import dataclass, field
from typing import Any

from cv_engine.tracker import TrackState
from cv_engine.roi_manager import ROIManager


@dataclass
class ZoneStats:
    """单个区域的三维统计"""
    zone_id: str
    zone_label: str
    visit_count: int = 0                     # ① 到访人次（进入并离开=1次）
    total_dwell_seconds: float = 0.0         # ② 总停留秒数（所有人累加）
    deep_interest_count: int = 0             # ③ 深度兴趣人数（停留>阈值）
    current_visitors: int = 0                # 当前在区域内人数
    staff_count: int = 0                     # 疑似店员人数（不计入热度）
    dwell_count: int = 0
    dwell_total: float = 0.0
    dwell_min: float = 0.0
    dwell_max: float = 0.0
    hourly_visits: dict[int, int] = field(default_factory=dict)
    hourly_dwell: dict[int, float] = field(default_factory=dict)


class PopularitySkill:
    """货架热度分析（三维评分版）

    输出维度：
    - visit_count: 进入-离开为一次到访
    - total_dwell_seconds: 所有人在该区域停留的总秒数
    - deep_interest_count: 停留超过 dwell_threshold 的人数
    - staff_count: 被判定为店员的轨迹数
    - heat_score: 加权综合热度分

    店员判定：
    - 单次连续停留 > staff_threshold_seconds（默认 900s=15分钟）
    - 或累计停留 > staff_cumulative_seconds / 小时
    """

    # 热度评分权重（可调）
    HEAT_WEIGHTS = {
        "visit": 0.2,       # 人次权重
        "dwell": 0.5,       # 总时长权重（最重要）
        "deep": 0.3,        # 深度兴趣权重
    }

    def __init__(
        self,
        roi_manager: ROIManager,
        dwell_threshold: float = 30.0,          # 深度兴趣阈值（秒）
        staff_threshold: float = 900.0,          # 店员判定阈值（秒，默认15分钟）
        staff_cumulative: float = 1800.0,        # 每小时累计 > 30分钟 → 店员
        min_track_hits: int = 3,
    ):
        self.roi_manager = roi_manager
        self.dwell_threshold = dwell_threshold
        self.staff_threshold = staff_threshold
        self.staff_cumulative = staff_cumulative
        self.min_track_hits = min_track_hits

        self.zone_stats: dict[str, ZoneStats] = {}
        self._init_zone_stats()

        # 去重
        self._counted_visits: OrderedDict[tuple[int, str], None] = OrderedDict()
        self._counted_deep: OrderedDict[tuple[int, str], None] = OrderedDict()
        self._staff_ids: set[int] = set()                     # 已确认店员 track_id
        self._max_tracked = 5000

    @staticmethod
    def _remember(cache: OrderedDict, key: tuple[int, str], max_size: int):
        """有界记录：超限时淘汰最旧记录，保持 O(1) 均摊复杂度。"""
        if key not in cache:
            cache[key] = None
            if len(cache) > max_size:
                cache.popitem(last=False)

    def _init_zone_stats(self):
        for zone_id in self.roi_manager.get_shelf_zones():
            self.zone_stats[zone_id] = ZoneStats(
                zone_id=zone_id,
                zone_label=self.roi_manager.zone_label.get(zone_id, zone_id),
            )

    def process(
        self,
        tracks: list[TrackState],
        frame_id: int,
        fps: float,
        current_hour: int | None = None,
    ) -> dict[str, Any]:
        if fps <= 0:
            fps = 15.0

        events = []
        active_per_zone: dict[str, int] = defaultdict(int)

        for track in tracks:
            if track.hit_times < self.min_track_hits:
                continue

            zone_id = self.roi_manager.get_zone(track.center)

            if zone_id and self.roi_manager.is_shelf_zone(zone_id):
                active_per_zone[zone_id] += 1

                # 初始化访问记录
                record = track.visited_zones.get(zone_id)
                if record is None:
                    track.visited_zones[zone_id] = {
                        "enter_frame": frame_id,
                        "dwell_frames": 0,
                        "counted_visit": False,
                        "counted_deep": False,
                        "counted_staff": False,
                        "exit_frame": None,
                    }
                    record = track.visited_zones[zone_id]

                record["dwell_frames"] += 1
                dwell_sec = record["dwell_frames"] / fps

                # ---- 店员判定 ----
                if (
                    not record.get("counted_staff")
                    and dwell_sec >= self.staff_threshold
                    and track.track_id not in self._staff_ids
                ):
                    track.is_staff = True
                    track.staff_confidence = min(
                        1.0, dwell_sec / self.staff_threshold
                    )
                    self._staff_ids.add(track.track_id)
                    record["counted_staff"] = True
                    self.zone_stats[zone_id].staff_count += 1
                    events.append({
                        "type": "staff_detected",
                        "track_id": track.track_id,
                        "zone_id": zone_id,
                        "dwell_seconds": round(dwell_sec, 1),
                        "frame_id": frame_id,
                    })

                # 店员不计入热度统计
                if track.is_staff:
                    continue

                # ---- ① 到访人次（进入→离开计1次） ----
                if (
                    not record.get("counted_visit")
                    and (track.track_id, zone_id) not in self._counted_visits
                ):
                    self._remember(
                        self._counted_visits,
                        (track.track_id, zone_id),
                        self._max_tracked,
                    )
                    record["counted_visit"] = True
                    self.zone_stats[zone_id].visit_count += 1
                    if current_hour is not None:
                        self.zone_stats[zone_id].hourly_visits[current_hour] = (
                            self.zone_stats[zone_id].hourly_visits.get(current_hour, 0) + 1
                        )

                # ---- ③ 深度兴趣 ----
                if (
                    not record.get("counted_deep")
                    and dwell_sec >= self.dwell_threshold
                    and (track.track_id, zone_id) not in self._counted_deep
                ):
                    self._remember(
                        self._counted_deep,
                        (track.track_id, zone_id),
                        self._max_tracked,
                    )
                    record["counted_deep"] = True
                    self.zone_stats[zone_id].deep_interest_count += 1
                    events.append({
                        "type": "deep_interest",
                        "track_id": track.track_id,
                        "zone_id": zone_id,
                        "zone_label": self.roi_manager.zone_label.get(zone_id, zone_id),
                        "dwell_seconds": round(dwell_sec, 1),
                        "frame_id": frame_id,
                    })

            # ---- ② 总停留时长（每帧实时累加，不依赖离开事件） ----
            if zone_id and self.roi_manager.is_shelf_zone(zone_id):
                if zone_id in self.zone_stats and not track.is_staff:
                    dwell_add = 1.0 / fps
                    self.zone_stats[zone_id].total_dwell_seconds += dwell_add

            # 离开 zone 时标记退出 + 记录完整dwell
            for zid, rec in track.visited_zones.items():
                if zid != zone_id and rec.get("exit_frame") is None:
                    rec["exit_frame"] = frame_id
                    dwell = rec["dwell_frames"] / fps
                    if zid in self.zone_stats and not track.is_staff:
                        stats = self.zone_stats[zid]
                        stats.dwell_count += 1
                        stats.dwell_total += dwell
                        if stats.dwell_count == 1:
                            stats.dwell_min = dwell
                            stats.dwell_max = dwell
                        else:
                            stats.dwell_min = min(stats.dwell_min, dwell)
                            stats.dwell_max = max(stats.dwell_max, dwell)
                        if current_hour is not None:
                            self.zone_stats[zid].hourly_dwell[current_hour] = (
                                self.zone_stats[zid].hourly_dwell.get(current_hour, 0.0) + dwell
                            )

        # 当前活跃人数
        for zid in self.zone_stats:
            self.zone_stats[zid].current_visitors = active_per_zone.get(zid, 0)

        return {"events": events, "active_zones": dict(active_per_zone)}

    def get_stats(self) -> dict[str, Any]:
        """获取三维热度报告"""
        from datetime import datetime

        zones_data = {}
        for zid, stats in self.zone_stats.items():
            # 加权综合热度分（归一化到0-100）
            heat_score = 0.0
            if stats.visit_count > 0:
                # 以所有 zone 中的最大值为基准归一化
                pass  # 在下面统一计算

            zones_data[zid] = {
                "zone_id": zid,
                "zone_label": stats.zone_label,
                "visit_count": stats.visit_count,
                "total_dwell_seconds": round(stats.total_dwell_seconds, 1),
                "deep_interest_count": stats.deep_interest_count,
                "current_visitors": stats.current_visitors,
                "staff_count": stats.staff_count,
                "avg_dwell_seconds": (
                    round(stats.dwell_total / stats.dwell_count, 1)
                    if stats.dwell_count else 0
                ),
                "max_dwell_seconds": round(stats.dwell_max, 1) if stats.dwell_count else 0,
                "hourly_visits": stats.hourly_visits,
                "hourly_dwell": stats.hourly_dwell,
            }

        # 计算归一化热度分
        max_visit = max((z["visit_count"] for z in zones_data.values()), default=1)
        max_dwell = max((z["total_dwell_seconds"] for z in zones_data.values()), default=1)
        max_deep = max((z["deep_interest_count"] for z in zones_data.values()), default=1)

        for zid, zdata in zones_data.items():
            visit_norm = zdata["visit_count"] / max_visit if max_visit > 0 else 0
            dwell_norm = zdata["total_dwell_seconds"] / max_dwell if max_dwell > 0 else 0
            deep_norm = zdata["deep_interest_count"] / max_deep if max_deep > 0 else 0

            w = self.HEAT_WEIGHTS
            zdata["heat_score"] = round(
                (visit_norm * w["visit"] + dwell_norm * w["dwell"] + deep_norm * w["deep"]) * 100, 1
            )

        # 找最热区域
        top_zone = max(zones_data, key=lambda z: zones_data[z]["heat_score"]) if zones_data else None

        return {
            "zones": zones_data,
            "top_zone": top_zone,
            "total_visitors": sum(z.deep_interest_count for z in self.zone_stats.values()),
            "total_visits": sum(z.visit_count for z in self.zone_stats.values()),
            "total_staff": sum(z.staff_count for z in self.zone_stats.values()),
            "timestamp": datetime.now().isoformat(),
        }

    def get_zone_ranking(self) -> list[dict]:
        stats = self.get_stats()
        zones = list(stats["zones"].values())
        zones.sort(key=lambda z: z["heat_score"], reverse=True)
        return zones

    def get_staff_list(self) -> list[int]:
        """获取已判定的店员 track_id 列表"""
        return list(self._staff_ids)

    def reset(self):
        self._init_zone_stats()
        self._counted_visits.clear()
        self._counted_deep.clear()
        self._staff_ids.clear()
