# Retail_assistant_v2
帮助分析客流热度，表情统计等，并加入了语音输入输出，连接mysql，保存会话，将会话向量化根据语义相似度查询会话，调整了前端UI


# 智能零售分析系统

一个面向门店场景的智能零售分析项目，整合了货架热度分析、异常行为告警、顾客表情分析、本地语音唤醒、语音问答、会话记录、MySQL 持久化和查询历史向量召回。

## 项目介绍

系统主要包含以下能力：

- 零售视频分析：YOLO 行人检测 + ByteTrack 跟踪 + ROI 货架热度统计
- 异常行为分析：轨迹异常、绕过收银台、人群聚集等告警
- 人脸表情分析：入口摄像头人脸检测 + 表情识别 + SQLite/MySQL 记录
- 本地语音唤醒：sherpa-onnx KWS，支持“小零”等唤醒词
- 本地指令识别：唤醒后使用 sherpa-onnx 流式 ASR 识别指令
- 语音回复：edge-tts 服务端 TTS，手机端也可播放
- 自然语言问答：LangChain Agent + DeepSeek，支持流式回答
- 会话记录：新建、保存、切换、重命名、删除会话
- MySQL 持久化：表情、问答历史、会话、语音日志、TTS 缓存、视频记录、ROI 配置
- 向量召回：Qdrant 本地模式 + Ollama bge-small-zh-v1.5

## 技术栈

- Python 3.13
- FastAPI + Uvicorn + WebSocket
- Ultralytics YOLO26n + ByteTrack
- PyTorch + OpenCV
- sherpa-onnx：KWS 唤醒 + 流式中文 ASR
- edge-tts：服务端中文语音合成
- LangChain + DeepSeek：Agent 问答
- MySQL：业务数据持久化
- Qdrant + Ollama：查询历史向量召回
- HTML/CSS/JS：前端界面

## 目录结构

```text
.
├── agents/                  # LangChain Agent
├── api/                     # FastAPI 路由
├── config/                  # 全局配置与 ROI
├── cv_engine/               # YOLO、跟踪、表情、ROI
├── skills/                  # 热度、告警、表情技能
├── frontend/                # 前端页面
├── data/                    # SQLite、视频、日志
├── all_models/              # sherpa-onnx 语音模型
├── sherpa-onnx-kws-*        # KWS 唤醒词模型
├── yolo26n.pt               # YOLO 小模型
├── best.pt                  # 人脸检测模型
├── mobilenetv3_fer_best.pth # 表情识别模型
├── mysql_db.py              # MySQL 数据层
├── vector_memory.py         # Qdrant 向量召回
├── requirements.txt
└── run.py
```

## 环境安装

### 1. 创建 Python 环境

推荐使用 Conda：

```powershell
conda create -n py313 python=3.13 -y
conda activate py313
```

### 2. 安装依赖

在项目根目录执行：

```powershell
pip install -r requirements.txt
```

如果缺少 PyMySQL、qdrant-client、edge-tts，也可以单独安装：

```powershell
pip install PyMySQL qdrant-client edge-tts
```

### 3. 配置环境变量

#### DeepSeek API Key

```powershell
$env:dazuoye_api = "你的DeepSeek API Key"
```

#### MySQL

系统会自动创建 `Retail_assistant` 数据库，需要提供可建库的 MySQL 账号：

```powershell
$env:mysql_root = "你的MySQL密码"
$env:MYSQL_HOST = "127.0.0.1"
$env:MYSQL_PORT = "3306"
$env:MYSQL_USER = "root"
