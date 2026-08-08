"""
GET /report/* — 报表数据接口（无需LLM，直接返回结构化数据）
"""
from fastapi import APIRouter, Query, HTTPException
from api.schemas import (
    PopularityReportResponse, AnomalyReportResponse, DashboardSnapshot,
    ZoneStatsResponse,
)

router = APIRouter(prefix="/report", tags=["report"])


@router.get("/popularity")
async def get_popularity_report(
    zone_id: str | None = Query(default=None, description="指定区域ID，不传则返回全部"),
):
    """获取货架热度报表（三维评分版）"""
    from api.dependencies import get_popularity_skill

    try:
        skill = get_popularity_skill()
        stats = skill.get_stats()

        if zone_id:
            zone_data = stats["zones"].get(zone_id)
            if not zone_data:
                raise HTTPException(status_code=404, detail=f"区域 {zone_id} 不存在")
            stats["zones"] = {zone_id: zone_data}

        return stats

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取热度报表失败: {str(e)}")


@router.get("/anomaly", response_model=AnomalyReportResponse)
async def get_anomaly_report(
    level: str | None = Query(default=None, pattern=r"^(watch|high)$"),
    min_score: int | None = Query(default=None, ge=0, le=100),
):
    """获取异常行为报表

    快速模式：直接从Skill读取告警数据。
    """
    from api.dependencies import get_anomaly_skill

    try:
        skill = get_anomaly_skill()
        summary = skill.get_alert_summary()

        return AnomalyReportResponse(**summary)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取异常报表失败: {str(e)}")


@router.get("/dashboard", response_model=DashboardSnapshot)
async def get_dashboard():
    """获取仪表盘全局快照"""
    from api.dependencies import get_popularity_skill, get_anomaly_skill
    from agents.master_agent import build_dashboard_snapshot

    try:
        snapshot = build_dashboard_snapshot(
            get_popularity_skill(),
            get_anomaly_skill(),
        )
        return DashboardSnapshot(**snapshot)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取仪表盘数据失败: {str(e)}")


@router.get("/health")
async def health_check():
    """健康检查"""
    import torch
    from api.dependencies import get_uptime_seconds

    return {
        "status": "ok",
        "gpu_available": torch.cuda.is_available(),
        "device": "cuda:0" if torch.cuda.is_available() else "cpu",
        "uptime_seconds": get_uptime_seconds(),
    }
