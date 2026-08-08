# Retail_assistant_v2
帮助分析客流热度，表情统计等，并加入了语音输入输出，连接mysql，保存会话，将会话向量化根据语义相似度查询会话，调整了前端UI

## 智能零售分析系统
一个面向门店场景的智能零售分析项目，整合了货架热度分析、异常行为告警、顾客表情分析、本地语音唤醒、语音问答、会话记录、MySQL 持久化和查询历史向量召回。

## 项目介绍
系统主要包含以下能力：

- **零售视频分析**：YOLO 行人检测 + ByteTrack 跟踪 + ROI 货架热度统计
- **异常行为分析**：轨迹异常、绕过收银台、人群聚集等告警
- **人脸表情分析**：入口摄像头人脸检测 + 表情识别 + MySQL 记录
- **本地语音唤醒**：sherpa‑onnx KWS，支持“小零”等唤醒词
- **本地指令识别**：唤醒后使用 sherpa‑onnx 流式 ASR 识别指令
- **语音回复**：edge‑tts 服务端 TTS，手机端也可播放音频
- **自然语言问答**：LangChain Agent + DeepSeek，支持流式回答输出
- **会话记录**：新建、保存、切换、重命名、删除会话
- **MySQL 持久化**：表情、问答历史、会话、语音日志、TTS 缓存、视频记录、ROI 配置
- **向量召回**：Qdrant 本地模式 + Ollama bge‑small‑zh‑v1.5，实现历史会话语义相似度检索

> ⚠️ **重要提示**
> 本仓库仅提交源码，**模型权重文件没有上传**（YOLO、人脸、表情、sherpa‑onnx语音模型体积较大）。
> 需要自行下载对应模型，放置到 `all_models/` 目录下，视频分析、语音唤醒识别功能才可以正常工作。

## 技术栈
- Python 3.13
- FastAPI + Uvicorn + WebSocket
- Ultralytics YOLO26n + ByteTrack
- PyTorch + OpenCV
- sherpa‑onnx：KWS 唤醒 + 流式中文 ASR
- edge‑tts：服务端中文语音合成
- LangChain + DeepSeek：Agent 智能问答
- MySQL：业务数据持久化存储
- Qdrant + Ollama：历史会话向量召回
- HTML/CSS/JS：前端交互界面

## 目录结构
```
.
├── agents/                  # LangChain Agent 智能代理模块
├── api/                     # FastAPI 接口路由
├── config/                  # 全局配置、ROI区域配置
├── cv_engine/               # YOLO检测、目标跟踪、表情识别、ROI热度计算
├── skills/                  # 热度统计、异常告警、表情分析业务技能
├── frontend/                # Web前端页面
├── data/                    # SQLite缓存、视频文件、运行日志
├── all_models/              # sherpa‑onnx语音模型（需要自行下载放入）
├── mysql_db.py              # MySQL数据库操作层
├── vector_memory.py         # Qdrant向量召回逻辑
├── requirements.txt         # Python依赖清单
└── run.py                   # 项目启动入口
```

## 环境安装
### 1. 创建 Python 虚拟环境
推荐 Conda：
```bash
conda create -n py313 python=3.13 -y
conda activate py313
```

### 2. 安装项目依赖
项目根目录执行：
```bash
pip install -r requirements.txt
```
如部分包缺失，可手动补充安装：
```bash
pip install PyMySQL qdrant-client edge-tts
```

### 3. 配置系统环境变量（Windows PowerShell示例）
```powershell
# DeepSeek API密钥
$env:dazuoye_api = "你的DeepSeek API Key"

# MySQL数据库配置，账号需要具备建库权限
$env:mysql_root = "你的MySQL密码"
$env:MYSQL_HOST = "127.0.0.1"
$env:MYSQL_PORT = "3306"
$env:MYSQL_USER = "root"
```
> 程序启动后会自动创建 `Retail_assistant` 数据库。

### 4. 准备模型文件
将 YOLO、人脸检测、表情识别、sherpa‑onnx语音模型，放到项目对应`all_models`文件夹。

### 5. 启动项目
```bash
python run.py
```
启动完成后访问前端页面即可使用整套零售分析系统。

---
你可以直接复制上面全部内容粘贴到GitHub的README.md编辑框。
需要我帮你再补充一份**故障排查小节**放到README末尾吗？方便作业演示的时候遇到报错快速查阅。
