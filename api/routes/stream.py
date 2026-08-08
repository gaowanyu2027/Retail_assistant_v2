"""
WS /ws/stream — 实时视频流 WebSocket 端点（双模式：零售分析 / 表情分析）

架构：后台线程处理视频 -> WebSocket 仅负责推帧
- 零售模式(retail): YOLO26l+ByteTrack -> 轨迹 -> ROI -> 热度/异常/表情技能
- 表情模式(emotion): YOLOv8n-face -> MobileNetV3表情 -> 十帧表决 -> 批量入库SQLite
"""
import asyncio
import base64
import json
import threading
import time as _time
import os
from collections import deque
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

# ==================== 全局线程安全状态 ====================

_lock = threading.Lock()
_active: dict[str, Any] = {
    "running": False,
    "paused": False,
    "source": None,
    "camera_id": 0,
    "current_frame": 0,
    "target_fps": 15.0,
    "mode": "retail",  # "retail" | "emotion"
}

_latest_result: dict | None = None
_latest_frame_b64: str | None = None

# 客户端帧队列
_client_frames: deque = deque(maxlen=3)
_client_frame_lock = threading.Lock()

# 表情模式专用状态
_emo_state = {
    "running": False,
    "start_time": 0.0,
    "sample_buffer": deque(maxlen=10),
    "batch_records": [],
    "camera_id": "camera_entrance",
}
_emo_lock = threading.Lock()


def inject_client_frame(frame_b64: str):
    """注入客户端帧（浏览器摄像头 -> WebSocket -> 服务端处理）"""
    try:
        img_bytes = base64.b64decode(frame_b64)
        inject_client_frame_bytes(img_bytes)
    except Exception:
        pass


def inject_client_frame_bytes(frame_bytes: bytes):
    """注入客户端 JPEG 二进制帧"""
    try:
        arr = np.frombuffer(frame_bytes, dtype=np.uint8)
        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if frame is not None:
            h, w = frame.shape[:2]
            if w != 640 or h != 480:
                frame = cv2.resize(frame, (640, 480), interpolation=cv2.INTER_AREA)
            with _client_frame_lock:
                _client_frames.append(frame)
    except Exception:
        pass


def get_client_frame():
    """获取最新客户端帧"""
    with _client_frame_lock:
        if _client_frames:
            return _client_frames.popleft()
        return None


def get_stream_status() -> dict:
    with _lock:
        return {
            "running": _active["running"],
            "source": _active["source"],
            "paused": _active["paused"],
            "current_frame": _active["current_frame"],
            "target_fps": _active.get("target_fps", 15.0),
            "mode": _active["mode"],
        }


def get_emotion_camera_status() -> dict:
    """获取表情摄像头状态"""
    with _emo_lock:
        return {
            "running": _emo_state["running"],
            "start_time": _emo_state["start_time"],
        }


def stop_emotion_camera() -> dict:
    """停止表情摄像头并返回分段分析"""
    from datetime import datetime
    from database import get_statistic, generate_emotion_analysis

    with _emo_lock:
        if not _emo_state["running"]:
            return {"code": 1, "msg": "表情摄像头当前未运行"}

        end_time = _time.time()
        total_duration = end_time - _emo_state["start_time"]
        mid_time = _emo_state["start_time"] + total_duration / 2

        start_str = datetime.fromtimestamp(_emo_state["start_time"]).strftime("%Y-%m-%d %H:%M:%S")
        mid_str = datetime.fromtimestamp(mid_time).strftime("%Y-%m-%d %H:%M:%S")
        end_str = datetime.fromtimestamp(end_time).strftime("%Y-%m-%d %H:%M:%S")

        cam_id = _emo_state["camera_id"]
        early_data = get_statistic(start_str, mid_str, cam_id)
        late_data = get_statistic(mid_str, end_str, cam_id)
        analysis_text = generate_emotion_analysis(early_data, late_data)

        # 批量入库剩余记录
        if _emo_state["batch_records"]:
            from database import insert_batch_records
            insert_batch_records(cam_id, _emo_state["batch_records"])
            _emo_state["batch_records"].clear()

        _emo_state["running"] = False
        _emo_state["start_time"] = 0.0
        _emo_state["sample_buffer"].clear()

    return {
        "code": 0,
        "msg": "门店出入口摄像头已关闭",
        "segment_analysis": {
            "前半段(采集前期)": early_data,
            "后半段(采集后期)": late_data,
            "分析结论": analysis_text
        }
    }


def _stop_internal():
    """内部停止"""
    global _latest_result, _latest_frame_b64
    with _lock:
        _active["running"] = False
        _active["source"] = None
    _latest_result = None
    _latest_frame_b64 = None


def _adaptive_fps_wait(frame_start: float):
    """根据上一帧处理耗时自动调整目标帧率，并控制处理线程节奏。"""
    from config.settings import VIDEO_MIN_FPS, VIDEO_MAX_FPS, VIDEO_FPS

    elapsed = _time.time() - frame_start
    with _lock:
        target_fps = _active.get("target_fps", VIDEO_FPS)
        target_interval = 1.0 / max(target_fps, 0.1)

        if elapsed > target_interval * 1.2:
            target_fps = max(VIDEO_MIN_FPS, target_fps * 0.8)
        elif elapsed < target_interval * 0.6 and target_fps < VIDEO_MAX_FPS:
            target_fps = min(VIDEO_MAX_FPS, target_fps * 1.1)

        _active["target_fps"] = round(target_fps, 1)
        interval = 1.0 / max(target_fps, 0.1)

    sleep_time = interval - elapsed
    if sleep_time > 0:
        _time.sleep(sleep_time)


# ==================== 表情模式处理线程 ====================

def _processing_thread_emotion(cap_source, face_emotion):
    """表情模式后台线程：仅做人脸检测+表情识别+SQLite入库"""
    global _latest_result, _latest_frame_b64
    from database import insert_batch_records, majority_vote
    from config.settings import (
        LOCAL_SAMPLE_FRAMES,
        LOCAL_BATCH_SAVE,
        VIDEO_OUTPUT_WIDTH,
        EMOTION_JPEG_QUALITY,
    )

    frame_id = 0
    while True:
        with _lock:
            if not _active["running"]:
                break
            paused = _active["paused"]

        if paused:
            _time.sleep(0.05)
            continue

        # 读帧
        if cap_source is None:
            frame = get_client_frame()
            if frame is None:
                _time.sleep(0.05)
                continue
        elif isinstance(cap_source, cv2.VideoCapture):
            ret, frame = cap_source.read()
            if not ret:
                _latest_result = {"type": "finished"}
                break
        else:
            break

        if frame is None:
            continue

        frame_start = _time.time()
        frame_id += 1
        if frame_id == 1:
            print(f"[WS] 表情源帧尺寸: {frame.shape[1]}x{frame.shape[0]}")
        with _lock:
            _active["current_frame"] = frame_id

        annotated = frame.copy()
        current_emotions = []

        # 人脸检测 + 表情识别
        faces = face_emotion.detect(frame)
        for face in faces:
            x1, y1, x2, y2 = face["bbox"]
            emotion = face["emotion"]
            conf = face["conf"]
            current_emotions.append(emotion)

            # 绘制人脸框
            color = (0, 255, 0) if emotion in ("happy", "neutral") else (0, 100, 255)
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            text = f"{face.get('emotion_cn', emotion)} {conf:.2f}"
            (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            cv2.rectangle(annotated, (x1, y1 - th - 10), (x1 + tw, y1), color, -1)
            cv2.putText(annotated, text, (x1, y1 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        # 十帧多数表决 + 批量入库
        with _emo_lock:
            if current_emotions:
                _emo_state["sample_buffer"].extend(current_emotions)

            if len(_emo_state["sample_buffer"]) >= LOCAL_SAMPLE_FRAMES:
                voted = majority_vote(list(_emo_state["sample_buffer"]))
                _emo_state["sample_buffer"].clear()
                if voted:
                    _emo_state["batch_records"].append((voted, 1.0))

                if len(_emo_state["batch_records"]) >= LOCAL_BATCH_SAVE:
                    insert_batch_records(_emo_state["camera_id"], _emo_state["batch_records"])
                    _emo_state["batch_records"].clear()

        # 画面标注
        cv2.putText(annotated, f"Mode: Emotion  Frame:{frame_id}  Faces:{len(faces)}",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

        # 编码帧：统一宽度为 VIDEO_OUTPUT_WIDTH，保留原始宽高比
        h, w = annotated.shape[:2]
        if w != VIDEO_OUTPUT_WIDTH:
            scale = VIDEO_OUTPUT_WIDTH / w
            annotated = cv2.resize(annotated, (VIDEO_OUTPUT_WIDTH, max(1, int(h * scale))))
        _, buffer = cv2.imencode('.jpg', annotated, [cv2.IMWRITE_JPEG_QUALITY, EMOTION_JPEG_QUALITY])
        _latest_frame_b64 = base64.b64encode(buffer).decode()

        _latest_result = {
            "frame_id": frame_id,
            "timestamp": _time.time(),
            "tracks": [],
            "events": [],
            "active_suspicious": [],
            "faces": [{"emotion": f["emotion"], "emotion_cn": f.get("emotion_cn", f["emotion"]),
                        "conf": f["conf"]} for f in faces],
        }
        _adaptive_fps_wait(frame_start)


# ==================== 零售模式处理线程 ====================

def _processing_thread_retail(cap_source, processor, pop_skill, anom_skill, emo_skill, event_detector):
    """零售模式后台线程：完整推理管线"""
    global _latest_result, _latest_frame_b64
    from config.settings import VIDEO_OUTPUT_WIDTH, VIDEO_JPEG_QUALITY

    while True:
        with _lock:
            if not _active["running"]:
                break
            paused = _active["paused"]

        if paused:
            _time.sleep(0.05)
            continue

        if cap_source is None:
            frame = get_client_frame()
            if frame is None:
                _time.sleep(0.05)
                continue
        elif isinstance(cap_source, cv2.VideoCapture):
            ret, frame = cap_source.read()
            if not ret:
                _latest_result = {"type": "finished"}
                break
        else:
            break

        if frame is None:
            continue

        frame_start = _time.time()
        if _active.get("current_frame", 0) == 0:
            print(f"[WS] 零售源帧尺寸: {frame.shape[1]}x{frame.shape[0]}")

        result = processor.process_frame(frame)
        with _lock:
            _active["current_frame"] = result.frame_id

        pop_skill.process(result.tracks, result.frame_id, processor.fps)
        anom_result = anom_skill.process(result.tracks, result.frame_id, processor.fps)
        emo_skill.process(result.tracks, result.timestamp)

        if result.frame_id % 75 == 0:
            try:
                from datetime import datetime
                import mysql_db
                stats = pop_skill.get_stats()
                mysql_db.save_retail_stats(
                    datetime.now().strftime("%Y%m%d%H%M"),
                    stats.get("zones", {}),
                )
            except Exception as e:
                print(f"[MySQL] 零售热度快照写入失败: {e}")

        for alert in anom_result.get("new_alerts", []):
            try:
                import mysql_db
                mysql_db.save_alert_record(
                    alert_type="anomaly",
                    zone_id=(alert.get("zone_visited") or [""])[0],
                    person_id=alert.get("person_id", 0),
                    level=alert.get("level", "watch"),
                    score=alert.get("score", 0),
                    reason="；".join(alert.get("reasons", [])),
                    frame_id=alert.get("frame_id", 0),
                    created_at=alert.get("timestamp") or None,
                )
            except Exception as e:
                print(f"[MySQL] 告警记录写入失败: {e}")

        if result.frame_id % 200 == 0 and isinstance(cap_source, cv2.VideoCapture):
            for _ in range(5):
                cap_source.grab()

        events = event_detector.detect(
            result.tracks, result.frame_id, processor.fps, result.timestamp)

        is_detection_frame = (result.frame_id % processor.frame_skip == 0)
        if is_detection_frame or _latest_frame_b64 is None:
            display_frame = result.annotated_frame
            h, w = display_frame.shape[:2]
            if w != VIDEO_OUTPUT_WIDTH:
                scale = VIDEO_OUTPUT_WIDTH / w
                display_frame = cv2.resize(display_frame, (VIDEO_OUTPUT_WIDTH, max(1, int(h * scale))))
            _, buffer = cv2.imencode('.jpg', display_frame, [cv2.IMWRITE_JPEG_QUALITY, VIDEO_JPEG_QUALITY])
            _latest_frame_b64 = base64.b64encode(buffer).decode()

        _latest_result = {
            "frame_id": result.frame_id,
            "timestamp": result.timestamp,
            "tracks": [{"track_id": t.track_id, "center": list(t.center),
                         "is_staff": t.is_staff, "anomaly_score": t.anomaly_score}
                        for t in result.tracks],
            "events": [{"type": e.event_type, "zone_id": e.zone_id,
                        "track_id": e.track_id, "detail": e.detail}
                       for e in events],
            "active_suspicious": [
                {"track_id": t.track_id, "score": t.anomaly_score}
                for t in result.tracks if t.anomaly_score >= 50
            ],
        }
        _adaptive_fps_wait(frame_start)


# ==================== WebSocket 端点 ====================

@router.websocket("/ws/client")
async def client_camera_stream(websocket: WebSocket):
    """接收浏览器本机摄像头 JPEG 二进制帧，交给主处理线程消费。"""
    await websocket.accept()
    print("[WS] 本机摄像头二进制流已连接")
    await websocket.send_json({"event": "ready"})

    try:
        while True:
            frame_bytes = await websocket.receive_bytes()
            if not frame_bytes:
                continue
            inject_client_frame_bytes(frame_bytes)
    except WebSocketDisconnect:
        pass
    finally:
        print("[WS] 本机摄像头二进制流已断开")


@router.websocket("/ws/stream")
async def video_stream(websocket: WebSocket):
    global _latest_result, _latest_frame_b64

    await websocket.accept()
    print("[WS] 客户端已连接")

    _latest_result = None
    _latest_frame_b64 = None

    from api.dependencies import (
        get_detector, get_roi_manager, reset_tracker,
        get_popularity_skill, get_anomaly_skill, get_emotion_skill,
        get_face_emotion,
    )
    from api.events import VideoEventDetector
    from cv_engine.tracker import TrackStateManager
    from cv_engine.video_processor import VideoProcessor

    # 零售模式组件（懒加载）
    detector = get_detector()
    roi_mgr = get_roi_manager()
    pop_skill = get_popularity_skill()
    anom_skill = get_anomaly_skill()
    emo_skill = get_emotion_skill()

    # 表情检测器（两种模式共用）
    face_emotion = None
    try:
        face_emotion = get_face_emotion()
    except Exception as e:
        print(f"[WS] 表情分析模块加载失败: {e}")

    track_mgr = TrackStateManager()
    processor = VideoProcessor(detector, track_mgr, roi_mgr, frame_skip=2,
                               face_emotion=face_emotion)
    event_detector = VideoEventDetector(roi_mgr)

    from config.settings import LOCAL_ROI_CONFIG_PATH, PROJECT_ROOT
    from cv_engine.roi_manager import ROIManager
    local_roi_mgr = ROIManager(str(PROJECT_ROOT / LOCAL_ROI_CONFIG_PATH))
    local_processor = VideoProcessor(detector, track_mgr, local_roi_mgr, frame_skip=2,
                                     face_emotion=face_emotion)
    local_event_detector = VideoEventDetector(local_roi_mgr)

    bg_thread: threading.Thread | None = None
    cap: cv2.VideoCapture | None = None
    _last_pushed_frame_id = -1

    def start_processing(cap_source, mode="retail", use_processor=None, use_event_detector=None):
        """启动后台处理线程"""
        nonlocal bg_thread
        target_processor = use_processor or processor
        target_event_detector = use_event_detector or event_detector
        _stop_internal()
        if bg_thread and bg_thread.is_alive():
            bg_thread.join(timeout=1.0)

        with _lock:
            _active["running"] = True
            _active["paused"] = False
            _active["mode"] = mode
            _active["target_fps"] = 15.0

        nonlocal _last_pushed_frame_id
        global _latest_result, _latest_frame_b64
        _latest_result = None
        _latest_frame_b64 = None
        _last_pushed_frame_id = -1

        if mode == "retail":
            reset_tracker()
            target_event_detector.reset()
            pop_skill.reset()
            anom_skill.reset()
            emo_skill.reset()
            target_processor.reset()
            bg_thread = threading.Thread(
                target=_processing_thread_retail,
                args=(cap_source, target_processor, pop_skill, anom_skill, emo_skill, target_event_detector),
                daemon=True,
            )
        else:
            # 表情模式
            from database import init_db
            init_db()
            with _emo_lock:
                _emo_state["running"] = True
                _emo_state["start_time"] = _time.time()
                _emo_state["sample_buffer"].clear()
                _emo_state["batch_records"].clear()
            bg_thread = threading.Thread(
                target=_processing_thread_emotion,
                args=(cap_source, face_emotion),
                daemon=True,
            )
        bg_thread.start()

    try:
        while True:
            try:
                raw = await asyncio.wait_for(websocket.receive_text(), timeout=0.1)
                msg = json.loads(raw)
                action = msg.get("action", "")
                mode = msg.get("mode", "retail")

                if action == "ping":
                    await websocket.send_json({"type": "pong", "ts": msg.get("ts", 0)})
                    continue

                if action == "client_frame":
                    inject_client_frame(msg.get("frame", ""))
                    continue

                if action == "start_webcam":
                    camera_id = msg.get("camera_id", 0)
                    if cap:
                        cap.release()
                    cap = cv2.VideoCapture(camera_id, cv2.CAP_DSHOW)
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 480)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 360)
                    with _lock:
                        _active["source"] = "webcam"
                        _active["camera_id"] = camera_id
                    start_processing(cap, mode)
                    print(f"[WS] 摄像头 #{camera_id} 已启动 (模式: {mode})")

                elif action == "start_file":
                    file_path = msg.get("file_path", "")
                    if cap:
                        cap.release()
                    cap = cv2.VideoCapture(file_path)
                    with _lock:
                        _active["source"] = "file"
                    start_processing(cap, mode)
                    print(f"[WS] 视频文件: {file_path} (模式: {mode})")

                elif action == "start_client_camera":
                    if cap:
                        cap.release()
                        cap = None
                    with _client_frame_lock:
                        _client_frames.clear()
                    with _lock:
                        _active["source"] = "client"
                    start_processing(None, mode, local_processor, local_event_detector)
                    print(f"[WS] 浏览器摄像头模式已启动 (模式: {mode})")

                elif action == "pause":
                    with _lock:
                        _active["paused"] = True

                elif action == "resume":
                    with _lock:
                        _active["paused"] = False

                elif action == "stop":
                    # 如果是表情模式，先停止表情摄像头
                    with _emo_lock:
                        if _emo_state["running"]:
                            _emo_state["running"] = False
                            # 批量入库剩余记录
                            if _emo_state["batch_records"]:
                                from database import insert_batch_records
                                insert_batch_records(_emo_state["camera_id"], _emo_state["batch_records"])
                                _emo_state["batch_records"].clear()

                    _stop_internal()
                    if bg_thread and bg_thread.is_alive():
                        bg_thread.join(timeout=1.0)
                    if cap:
                        cap.release()
                        cap = None
                    _latest_result = None
                    _latest_frame_b64 = None
                    await websocket.send_json({
                        "type": "status",
                        "status": "stopped",
                        "message": "视频已停止，WebSocket 保持连接",
                    })
                    print("[WS] 视频已停止")

            except asyncio.TimeoutError:
                pass

            # 推送最新帧
            frame_b64 = _latest_frame_b64
            result_to_send = _latest_result

            if frame_b64 is None or result_to_send is None:
                if _last_pushed_frame_id >= 0:
                    await websocket.send_json({
                        "type": "status", "status": "stopped",
                        "message": "视频流已停止",
                    })
                    _last_pushed_frame_id = -1
                await asyncio.sleep(0.01)
                continue

            if result_to_send.get("type") == "finished":
                await websocket.send_json({
                    "type": "status", "status": "finished",
                    "message": "视频播放完毕",
                })
                _stop_internal()
                _latest_result = None
                _latest_frame_b64 = None
                continue

            new_frame_id = result_to_send.get("frame_id", -1)
            if new_frame_id <= _last_pushed_frame_id:
                await asyncio.sleep(0.01)
                continue
            _last_pushed_frame_id = new_frame_id

            msg_to_send = {
                "type": "frame",
                "frame": frame_b64,
                "frame_id": result_to_send["frame_id"],
                "timestamp": result_to_send.get("timestamp", 0),
                "tracks": result_to_send.get("tracks", []),
                "events": result_to_send.get("events", []),
                "active_suspicious": result_to_send.get("active_suspicious", []),
                "mode": _active.get("mode", "retail"),
            }
            # 表情模式额外推送人脸信息
            if "faces" in result_to_send:
                msg_to_send["faces"] = result_to_send["faces"]

            await websocket.send_json(msg_to_send)
            await asyncio.sleep(0.005)

    except WebSocketDisconnect:
        print("[WS] 客户端断开连接")
    except Exception as e:
        print(f"[WS] 错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        _stop_internal()
        with _emo_lock:
            _emo_state["running"] = False
        if bg_thread and bg_thread.is_alive():
            bg_thread.join(timeout=1.0)
        if cap:
            cap.release()
        print("[WS] 连接关闭")
