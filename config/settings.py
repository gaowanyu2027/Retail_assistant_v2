"""
全局配置模块 — 统一管理路径、设备、模型参数等
整合零售视频分析 + 门店人脸表情分析双系统
"""
import os
from pathlib import Path

# ==================== 项目根目录 ====================
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
DATA_DIR = PROJECT_ROOT / "data"

# ==================== 设备配置 ====================
try:
    import torch
    DEVICE = "cuda:0" if torch.cuda.is_available() else "cpu"
    USE_FP16 = True if DEVICE != "cpu" else False
except ImportError:
    DEVICE = "cpu"
    USE_FP16 = False

# ==================== 模型路径（相对路径，使用时需基于 PROJECT_ROOT 解析） ====================
YOLO_MODEL_PATH = "yolo26n.pt"
FACE_MODEL_PATH = "best.pt"
EMOTION_MODEL_PATH = "mobilenetv3_fer_best.pth"

# ==================== 视频源配置 ====================
DEFAULT_VIDEO_SOURCE = str(PROJECT_ROOT / "data" / "MOT16" / "train" / "MOT16-04" / "img1")
FRAME_SAVE_DIR = str(DATA_DIR / "frames")
OUTPUT_VIDEO_PATH = str(DATA_DIR / "tracking_result.mp4")

# ==================== ROI配置文件 ====================
ROI_CONFIG_PATH = "config/roi_zones.yaml"
LOCAL_ROI_CONFIG_PATH = "config/roi_zones_local.yaml"
THRESHOLDS_CONFIG_PATH = "config/thresholds.yaml"

# ==================== DeepSORT 超参 ====================
MAX_AGE = 50
MIN_HITS = 3
IOU_THRESH = 0.4
MAHAL_THRESH = 9.4877
COS_THRESH = 0.15
FEAT_BANK_MAX = 150

# ==================== YOLO 检测参数 ====================
YOLO_CONF = 0.25
YOLO_IOU = 0.45
YOLO_IMGSZ = 640
PERSON_CLASS_ID = 0

# ==================== ID回收池参数 ====================
RECYCLE_MAX_LOST = 60
RECYCLE_COS_THRESH = 0.12

# ==================== 视频输出参数 ====================
VIDEO_FPS = 15
VIDEO_MIN_FPS = 5
VIDEO_MAX_FPS = 30
VIDEO_OUTPUT_WIDTH = 960
VIDEO_JPEG_QUALITY = 65
EMOTION_JPEG_QUALITY = 70

# ==================== API配置 ====================
API_HOST = "0.0.0.0"
API_PORT = 8000

# ==================== LLM配置（Agent层） ====================
LLM_PROVIDER = "openai"
LLM_MODEL = "deepseek-chat"
LLM_API_KEY = os.environ.get("dazuoye_api", "")
LLM_BASE_URL = "https://api.deepseek.com"

# ==================== 表情分析数据库配置（来自 final_work） ====================
EMOTION_DB_PATH = str(DATA_DIR / "shop_emotion.db")
VIDEO_OUTPUT_DIR = str(DATA_DIR / "videos")

# ==================== 本地语音唤醒模型配置 ====================
SHERPA_ONNX_PROVIDER = os.environ.get("SHERPA_ONNX_PROVIDER", "cpu")
KWS_MODEL_DIR = PROJECT_ROOT / "sherpa-onnx-kws-zipformer-wenetspeech-3.3M-2024-01-01"
KWS_KEYWORDS_FILE = KWS_MODEL_DIR / "keywords.txt"
KWS_SAMPLE_RATE = 16000
KWS_THRESHOLD = 0.25
KWS_SCORE = 2.0
KWS_ENERGY_THRESHOLD = 0.01
KWS_SILENCE_SECONDS = 0.35
KWS_TAIL_PADDING_SECONDS = 0.4
KWS_MAX_SEGMENT_SECONDS = 2.0
KWS_KEYWORD = (
    "x i\u01ceo l \u00edng :2.0 #0.15 @\u5c0f\u96f6/"
    "x i\u01ceo n \u00edng @\u5c0f\u5b81/"
    "x i\u01ceo l \u00edn @\u5c0f\u6797/"
    "x i\u01ceo m \u00edng @\u5c0f\u660e/"
    "x i\u01ceo x \u012bng @\u5c0f\u661f/"
    "x i\u01ceo q \u012bng @\u5c0f\u6e05/"
    "x i\u01ceo y \u012bng @\u5c0f\u82f1/"
    "x i\u01ceo b \u012bng @\u5c0f\u51b0/"
    "x i\u01ceo p \u00edng @\u5c0f\u5e73/"
    "x i\u01ceo x \u012bn @\u5c0f\u5fc3/"
    "x i\u01ceo j \u012bn @\u5c0f\u91d1/"
)

# ==================== 本地流式中文识别模型配置（临时麦克风测试） ====================
ASR_MODEL_DIR = PROJECT_ROOT / "all_models" / "sherpa-onnx-streaming-zipformer-zh-14M-2023-02-23"
ASR_SAMPLE_RATE = 16000
ASR_ENERGY_THRESHOLD = 0.01
ASR_TAIL_PADDING_SECONDS = 0.4
ASR_MAX_SEGMENT_SECONDS = 5.0
ASR_TARGET_RMS = 0.1
ASR_MAX_GAIN = 5.0

# 表情分析降采样配置
LOCAL_SAMPLE_FRAMES = 10   # 每10帧做一次多数表决
LOCAL_BATCH_SAVE = 100     # 每100条表决记录批量写入数据库
LOCAL_VIDEO_FPS = 10       # 保存视频的帧率
LOCAL_VIDEO_MAX_SECONDS = 300  # 单个视频最长 5 分钟

# 缓存清理配置
CACHE_CLEAN_INTERVAL_SECONDS = 600
CACHE_MAX_AGE_HOURS = 24
DB_RECORD_KEEP_DAYS = 30


def ensure_dirs():
    """确保所有运行时目录存在"""
    for d in [DATA_DIR, DATA_DIR / "logs", DATA_DIR / "snapshots",
              FRAME_SAVE_DIR, DATA_DIR / "videos"]:
        os.makedirs(d, exist_ok=True)
