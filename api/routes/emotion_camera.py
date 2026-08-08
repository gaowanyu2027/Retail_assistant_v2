"""
门店出入口摄像头 — 表情分析 REST API
来自 final_work，适配双系统整合
"""
import time
from datetime import datetime, timedelta
from fastapi import APIRouter

from database import (
    init_db, get_statistic, get_latest_records,
    get_record_count, cleanup_old_records,
)
from api.routes.stream import get_emotion_camera_status, stop_emotion_camera

router = APIRouter(prefix="/emotion_camera", tags=["emotion_camera"])


@router.get("/start")
async def start_emotion_camera():
    """启动门店出入口摄像头（标记开始时间，实际视频流通过WebSocket控制）"""
    status = get_emotion_camera_status()
    if status["running"]:
        return {"code": 1, "msg": "门店出入口摄像头已在运行"}
    # 初始化数据库
    init_db()
    return {"code": 0, "msg": "门店出入口摄像头已就绪，请通过画面区域启动视频流"}


@router.get("/stop")
async def stop_emotion_camera_api():
    """停止门店出入口摄像头，返回前后半段表情对比分析"""
    result = stop_emotion_camera()
    return result


@router.get("/status")
async def emotion_camera_status():
    """查询门店出入口摄像头运行状态"""
    status = get_emotion_camera_status()
    return {
        "running": status["running"],
        "status": "运行中" if status["running"] else "已关闭",
        "start_time": status["start_time"],
    }


@router.get("/stat")
async def emotion_stat(start: str, end: str, camera_id: str = None):
    """查询指定时间段表情分布"""
    all_data = {}
    if not camera_id:
        all_data["出入口摄像头"] = get_statistic(start, end, "camera_entrance")
        all_data["本机摄像头"] = get_statistic(start, end, "camera_local")
    else:
        all_data["指定摄像头统计"] = get_statistic(start, end, camera_id)
    return all_data


@router.get("/latest")
async def emotion_latest(camera_id: str = "camera_entrance", limit: int = 20):
    """查询最近 N 条表情识别记录"""
    records = get_latest_records(camera_id, limit)
    return {
        "records": [
            {"camera_id": r[0], "time": r[1], "emotion": r[2], "conf": r[3]}
            for r in records
        ]
    }


@router.get("/summary")
async def emotion_summary(camera_id: str = "camera_entrance", hours: int = 1):
    """查询最近 N 小时内的记录总数与分布"""
    end = datetime.now()
    start = end - timedelta(hours=hours)
    start_str = start.strftime("%Y-%m-%d %H:%M:%S")
    end_str = end.strftime("%Y-%m-%d %H:%M:%S")
    stats = get_statistic(start_str, end_str, camera_id)
    total = sum(count for _, count in stats)
    return {"total": total, "distribution": stats}
