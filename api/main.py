"""
FastAPI 主入口 — 整合零售视频分析 + 门店人脸表情分析双系统

启动方式:
    python run.py
    或
    python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
"""
import os
import sys
import threading
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import FastAPI, UploadFile, File as FastAPIFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import API_HOST, API_PORT, ensure_dirs


# ==================== 缓存清理线程 ====================

def _cleanup_worker():
    """后台线程：定期清理过期视频与数据库旧记录"""
    from config.settings import (
        CACHE_CLEAN_INTERVAL_SECONDS, CACHE_MAX_AGE_HOURS,
        DB_RECORD_KEEP_DAYS, VIDEO_OUTPUT_DIR,
    )
    from database import cleanup_old_records

    while True:
        time.sleep(CACHE_CLEAN_INTERVAL_SECONDS)
        try:
            now = datetime.now()
            cutoff = now - timedelta(hours=CACHE_MAX_AGE_HOURS)
            removed = 0
            if os.path.exists(VIDEO_OUTPUT_DIR):
                for fname in os.listdir(VIDEO_OUTPUT_DIR):
                    fpath = os.path.join(VIDEO_OUTPUT_DIR, fname)
                    if os.path.isfile(fpath):
                        mtime = datetime.fromtimestamp(os.path.getmtime(fpath))
                        if mtime < cutoff:
                            try:
                                os.remove(fpath)
                                removed += 1
                            except Exception:
                                pass
            deleted_db = cleanup_old_records(DB_RECORD_KEEP_DAYS)
            if removed or deleted_db:
                print(f"[清理] 删除过期视频 {removed} 个，清理数据库记录 {deleted_db} 条")
        except Exception as e:
            print(f"[清理] 异常: {e}")


# ==================== 应用生命周期 ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("=" * 60)
    print("  🏪 智能零售分析系统 (零售分析 + 表情分析) — 启动中...")
    print("=" * 60)

    ensure_dirs()

    # 初始化表情数据库
    try:
        from database import init_db
        init_db()
        from database import _mysql_enabled
        if _mysql_enabled():
            print("[OK] 数据写入: MySQL Retail_assistant")
        else:
            print("[WARN] 未检测到 mysql_root，当前回退到 SQLite")
    except Exception as e:
        print(f"[WARN] 表情数据库初始化失败: {e}")

    # 重建查询历史向量索引
    try:
        import vector_memory
        count = vector_memory.reindex_all()
        print(f"[OK] 查询历史向量索引完成: {count} 条")
    except Exception as e:
        print(f"[WARN] 查询历史向量索引失败: {e}")

    # 预热CV引擎
    try:
        from api.dependencies import get_detector, get_tracker, get_roi_manager
        detector = get_detector()
        tracker = get_tracker()
        roi_mgr = get_roi_manager()
        app.state.ready = True
        print(f"[OK] CV引擎初始化完成 (设备: {detector.device}, ROI区域: {len(roi_mgr.zones)}个)")
    except Exception as e:
        print(f"[WARN] CV引擎初始化警告: {e}")
        app.state.ready = False

    # 启动缓存清理线程
    t_cleanup = threading.Thread(target=_cleanup_worker, daemon=True)
    t_cleanup.start()

    print(f"[OK] API地址: http://{API_HOST}:{API_PORT}")
    print(f"[OK] 仪表盘: http://localhost:{API_PORT}")
    print(f"[OK] API文档: http://localhost:{API_PORT}/docs")
    print("=" * 60)

    yield

    print("[STOP] 系统关闭中...")
    app.state.ready = False


# ==================== FastAPI App ====================

app = FastAPI(
    title="智能零售分析系统",
    description="整合零售视频分析(货架摄像头) + 门店人脸表情分析(出入口摄像头)双系统",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def no_cache_static_files(request, call_next):
    """开发阶段避免浏览器缓存旧的 CSS/JS 导致页面看不到最新功能。"""
    response = await call_next(request)
    if request.url.path.startswith(("/css/", "/js/")):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    return response


# 注册路由
from api.routes.query import router as query_router
from api.routes.report import router as report_router
from api.routes.stream import router as stream_router
from api.routes.emotion_camera import router as emotion_camera_router
from api.routes.voice import router as voice_router
from api.routes.asr import router as asr_router
from api.routes.tts import router as tts_router
from api.routes.chat import router as chat_router

app.include_router(query_router, prefix="/api")
app.include_router(report_router, prefix="/api")
app.include_router(stream_router, prefix="/api")
app.include_router(emotion_camera_router, prefix="/api")
app.include_router(voice_router, prefix="/api")
app.include_router(asr_router, prefix="/api")
app.include_router(tts_router, prefix="/api")
app.include_router(chat_router, prefix="/api")

# 静态文件
frontend_dir = PROJECT_ROOT / "frontend"
if frontend_dir.exists():
    app.mount("/css", StaticFiles(directory=str(frontend_dir / "css")), name="css")
    app.mount("/js", StaticFiles(directory=str(frontend_dir / "js")), name="js")
    print(f"[OK] 前端静态文件: {frontend_dir}")


@app.get("/")
async def serve_index():
    """根路径返回前端页面"""
    index_path = PROJECT_ROOT / "frontend" / "index.html"
    if index_path.exists():
        return FileResponse(
            str(index_path),
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )
    return {"message": "前端文件未找到，请访问 /docs 查看API文档"}


@app.get("/api/health")
async def health():
    """健康检查"""
    import torch
    from api.dependencies import get_uptime_seconds
    return {
        "status": "ok",
        "gpu_available": torch.cuda.is_available(),
        "device": "cuda:0" if torch.cuda.is_available() else "cpu",
        "uptime_seconds": get_uptime_seconds(),
    }


@app.post("/api/video/upload-file")
async def upload_video_file(file: UploadFile = FastAPIFile(...)):
    """接收上传的视频文件"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="未选择文件")

    allowed_ext = {".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv", ".wmv"}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_ext:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型 '{ext}'，允许: {', '.join(allowed_ext)}")

    videos_dir = Path(__file__).resolve().parent.parent / "data" / "videos"
    videos_dir.mkdir(parents=True, exist_ok=True)
    save_path = videos_dir / file.filename

    content = await file.read()
    with open(save_path, "wb") as f:
        f.write(content)

    try:
        import mysql_db
        mysql_db.save_video_record(
            filename=file.filename,
            file_path=str(save_path.resolve()),
            file_size=len(content),
            source="upload",
            status="uploaded",
        )
    except Exception as e:
        print(f"[MySQL] 视频记录写入失败: {e}")

    file_size_mb = len(content) / (1024 * 1024)

    return {
        "status": "ok",
        "filename": file.filename,
        "path": str(save_path.resolve()),
        "size_mb": round(file_size_mb, 2),
        "message": f"文件已上传，可通过 WebSocket 发送播放指令",
        "ws_action": {
            "action": "start_file",
            "file_path": str(save_path.resolve()),
        },
    }


# ==================== ROI配置管理 ====================

@app.get("/api/zones")
async def get_zones():
    from api.dependencies import get_roi_manager
    roi_mgr = get_roi_manager()
    zones_data = {}
    for zid in roi_mgr.zones:
        zones_data[zid] = {
            "zone_id": zid,
            "type": roi_mgr.zone_type.get(zid, "shelf"),
            "label": roi_mgr.zone_label.get(zid, zid),
            "polygon": roi_mgr.zones[zid].tolist(),
        }
    return {"zones": zones_data}


@app.put("/api/zones")
async def update_zone(zone: dict):
    from api.dependencies import get_roi_manager
    roi_mgr = get_roi_manager()
    roi_mgr.add_zone(
        zone_id=zone["zone_id"],
        zone_type=zone.get("type", "shelf"),
        label=zone.get("label", zone["zone_id"]),
        polygon=zone["polygon"],
    )
    roi_mgr.save_to_yaml()
    try:
        import mysql_db
        mysql_db.upsert_roi_config(
            zone_id=zone["zone_id"],
            zone_type=zone.get("type", "shelf"),
            zone_label=zone.get("label", zone["zone_id"]),
            polygon=zone["polygon"],
            source="server",
        )
    except Exception as e:
        print(f"[MySQL] ROI 配置写入失败: {e}")
    return {"status": "ok", "message": f"区域 {zone['zone_id']} 已更新"}


@app.delete("/api/zones/{zone_id}")
async def delete_zone(zone_id: str):
    from api.dependencies import get_roi_manager
    roi_mgr = get_roi_manager()
    if roi_mgr.remove_zone(zone_id):
        roi_mgr.save_to_yaml()
        try:
            import mysql_db
            mysql_db.delete_roi_config(zone_id, source="server")
        except Exception as e:
            print(f"[MySQL] ROI 配置删除失败: {e}")
        return {"status": "ok", "message": f"区域 {zone_id} 已删除"}
    return {"status": "error", "message": f"区域 {zone_id} 不存在"}


# ==================== 零售模式表情端点 ====================

@app.get("/api/emotion/stats")
async def emotion_stats():
    from api.dependencies import get_emotion_skill
    return get_emotion_skill().get_stats()


@app.get("/api/emotion/trend")
async def emotion_trend():
    from api.dependencies import get_emotion_skill
    return get_emotion_skill().get_trend()


@app.get("/api/emotion/recent")
async def emotion_recent(limit: int = 20):
    from api.dependencies import get_emotion_skill
    return {"records": get_emotion_skill().get_recent(limit)}


@app.get("/api/cameras")
async def scan_cameras():
    """扫描服务器上可用的摄像头设备"""
    import cv2
    cameras = []
    for i in range(8):
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
        if cap.isOpened():
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cameras.append({"id": i, "resolution": f"{w}x{h}"})
            cap.release()
    return {"cameras": cameras, "default": 0 if cameras else None}


# ==================== 启动入口 ====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host=API_HOST,
        port=API_PORT,
        reload=True,
        log_level="info",
    )
