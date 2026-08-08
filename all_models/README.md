---
license: Apache License 2.0
language:
- zh
- en
- ja
- ko
- yue
- fr
- de
- es
- ru
- vi
- th
- pt
tags:
- speech-recognition
- asr
- sherpa-onnx
- sensevoice
- funasr
- paraformer
- whisper
- zipformer
- conformer
- onnx
- real-time
- on-device
- offline
- streaming
frameworks:
- onnxruntime
model-type:
- transducer
- ctc
- paraformer
- whisper
- sense-voice
domain:
- audio
pipeline_tag: automatic-speech-recognition
---

<div align="center">

# 🎙️ Sherpa-ONNX ASR Models Mirror

**GitHub 模型国内镜像 | China Mirror for sherpa-onnx ASR Models**

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![ONNX](https://img.shields.io/badge/ONNX-Runtime-green.svg)](https://onnxruntime.ai/)
[![Models](https://img.shields.io/badge/Models-160+-purple.svg)](#模型列表)
[![Platform](https://img.shields.io/badge/Platform-Cross--Platform-orange.svg)](#支持平台)

[English](#english) | [中文](#中文)

<br>

**⚡ 国内高速下载 | 🔒 完全离线运行 | 📱 全平台支持**

</div>

---

## 中文

### 📖 简介

本仓库是 [k2-fsa/sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx) 官方 ASR 模型的**国内镜像**，解决 GitHub Releases 下载缓慢的问题。

**sherpa-onnx** 是新一代 Kaldi 团队开发的跨平台语音识别推理框架，基于 ONNX Runtime，支持在各种设备上进行高效的**离线语音识别**，无需网络连接。

### 🌟 特色

- 🚀 **国内高速下载**：托管于 ModelScope，国内用户下载速度可达 10MB/s+
- 📦 **完整镜像**：包含 160+ 个官方模型，覆盖主流语音识别架构
- 🔄 **持续同步**：定期从 GitHub 同步最新模型
- 📝 **详细文档**：提供完整的使用示例和模型选择指南

---

### 📋 模型列表

#### 🇨🇳 中文模型（推荐）

| 模型 | 类型 | 大小 | 特点 | 推荐场景 |
|------|------|------|------|----------|
| `sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17` | SenseVoice | ~230MB | 多语言、情感识别 | 通用场景 |
| `sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17` | SenseVoice | ~60MB | INT8 量化版 | 移动端/边缘设备 |
| `sherpa-onnx-paraformer-zh-2024-03-09` | Paraformer | ~220MB | 中文识别最佳 | 纯中文场景 |
| `sherpa-onnx-paraformer-zh-small-2024-03-09` | Paraformer | ~30MB | 轻量版 | 资源受限设备 |
| `sherpa-onnx-streaming-zipformer-zh-2025-06-30` | Zipformer | ~80MB | 流式识别 | 实时转录 |
| `sherpa-onnx-streaming-paraformer-bilingual-zh-en` | Paraformer | ~220MB | 中英双语流式 | 中英混合实时 |

#### 🌍 多语言模型

| 模型 | 支持语言 | 大小 | 特点 |
|------|----------|------|------|
| `sherpa-onnx-whisper-large-v3` | 99+ 语言 | ~3GB | 最高准确率 |
| `sherpa-onnx-whisper-turbo` | 99+ 语言 | ~1.5GB | 速度优化版 |
| `sherpa-onnx-whisper-medium` | 99+ 语言 | ~1.5GB | 平衡之选 |
| `sherpa-onnx-whisper-small` | 99+ 语言 | ~460MB | 轻量版 |
| `sherpa-onnx-whisper-tiny` | 99+ 语言 | ~75MB | 最小版本 |

#### 🇬🇧 英文模型

| 模型 | 类型 | 大小 | 特点 |
|------|------|------|------|
| `sherpa-onnx-zipformer-en-2023-06-26` | Zipformer | ~70MB | 英文通用 |
| `sherpa-onnx-streaming-zipformer-en-2023-06-26` | Zipformer | ~20MB | 流式英文 |
| `sherpa-onnx-conformer-en-2023-03-18` | Conformer | ~120MB | 高准确率 |
| `sherpa-onnx-nemo-fast-conformer-ctc-en-24500` | NeMo | ~120MB | NVIDIA NeMo |

#### 🌏 其他语言

| 语言 | 推荐模型 | 大小 |
|------|----------|------|
| 日语 | `sherpa-onnx-zipformer-ja-reazonspeech-2024-08-01` | ~70MB |
| 韩语 | `sherpa-onnx-zipformer-korean-2024-06-24` | ~70MB |
| 粤语 | `sherpa-onnx-zipformer-cantonese-2024-03-13` | ~70MB |
| 俄语 | `sherpa-onnx-zipformer-ru-2024-09-18` | ~70MB |
| 法语 | `sherpa-onnx-streaming-zipformer-fr-2023-04-14` | ~20MB |
| 德语 | `sherpa-onnx-streaming-zipformer-de-kroko-2025-08-06` | ~20MB |
| 西班牙语 | `sherpa-onnx-streaming-zipformer-es-kroko-2025-08-06` | ~20MB |
| 越南语 | `sherpa-onnx-zipformer-vi-2025-04-20` | ~70MB |
| 泰语 | `sherpa-onnx-zipformer-thai-2024-06-20` | ~70MB |

#### 📱 移动端优化模型

| 模型 | 大小 | 特点 |
|------|------|------|
| `sherpa-onnx-streaming-zipformer-zh-14M-2023-02-23-mobile` | ~14MB | 中文流式，超轻量 |
| `sherpa-onnx-streaming-zipformer-en-20M-2023-02-17-mobile` | ~20MB | 英文流式，超轻量 |
| `sherpa-onnx-streaming-zipformer-bilingual-zh-en-2023-02-20-mobile` | ~30MB | 中英双语流式 |
| `sherpa-onnx-moonshine-tiny-en-int8` | ~30MB | 英文，极致压缩 |

---

### 🚀 快速开始

#### 方式一：直接下载（推荐）

```bash
# 下载压缩包（以 SenseVoice 为例）
curl -LO https://modelscope.cn/models/zhaochaoqun/sherpa-onnx-asr-models/resolve/master/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17.tar.bz2

# 解压
tar -xjf sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17.tar.bz2
```

#### 方式二：ModelScope SDK

```bash
pip install modelscope
```

```python
from modelscope import snapshot_download

# 下载指定模型
model_dir = snapshot_download(
    'zhaochaoqun/sherpa-onnx-asr-models',
    allow_patterns=['sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17.tar.bz2']
)
```

#### 方式三：Git Clone（下载全部）

```bash
# 安装 Git LFS
git lfs install

# 克隆仓库（警告：总大小超过 50GB）
GIT_LFS_SKIP_SMUDGE=1 git clone https://www.modelscope.cn/zhaochaoqun/sherpa-onnx-asr-models.git

# 下载指定文件
cd sherpa-onnx-asr-models
git lfs pull --include="sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17.tar.bz2"
```

---

### 💻 使用示例

#### Python

```python
import sherpa_onnx

# 非流式识别（适合录音文件）
recognizer = sherpa_onnx.OfflineRecognizer.from_sense_voice(
    model="sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17/model.int8.onnx",
    tokens="sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17/tokens.txt",
    num_threads=4,
    use_itn=True,
)

stream = recognizer.create_stream()
stream.accept_wave_file("test.wav")
recognizer.decode_stream(stream)
print(stream.result.text)
```

#### 流式识别

```python
import sherpa_onnx

# 流式识别（适合实时转录）
recognizer = sherpa_onnx.OnlineRecognizer.from_transducer(
    encoder="sherpa-onnx-streaming-zipformer-zh-2025-06-30/encoder-epoch-99-avg-1.onnx",
    decoder="sherpa-onnx-streaming-zipformer-zh-2025-06-30/decoder-epoch-99-avg-1.onnx",
    joiner="sherpa-onnx-streaming-zipformer-zh-2025-06-30/joiner-epoch-99-avg-1.onnx",
    tokens="sherpa-onnx-streaming-zipformer-zh-2025-06-30/tokens.txt",
    num_threads=4,
)

stream = recognizer.create_stream()
# 实时送入音频数据...
```

#### Swift (iOS/macOS)

```swift
import SherpaOnnx

let config = sherpaOnnxOfflineRecognizerConfig(
    modelConfig: sherpaOnnxOfflineModelConfig(
        senseVoice: sherpaOnnxOfflineSenseVoiceModelConfig(
            model: "model.int8.onnx",
            useItn: true
        ),
        tokens: "tokens.txt",
        numThreads: 4
    )
)

let recognizer = SherpaOnnxOfflineRecognizer(config: &config)
```

#### Android (Kotlin)

```kotlin
val config = OfflineRecognizerConfig(
    modelConfig = OfflineModelConfig(
        senseVoice = OfflineSenseVoiceModelConfig(
            model = "model.int8.onnx",
            useItn = true
        ),
        tokens = "tokens.txt",
        numThreads = 4
    )
)

val recognizer = OfflineRecognizer(config)
```

---

### 📊 模型架构说明

| 架构 | 类型 | 特点 | 适用场景 |
|------|------|------|----------|
| **SenseVoice** | 非流式 | 多语言、情感识别、高准确率 | 通用语音识别 |
| **Paraformer** | 非流式 | 中文优化、速度快 | 中文语音识别 |
| **Whisper** | 非流式 | 99+ 语言、最广泛支持 | 多语言场景 |
| **Zipformer** | 流式/非流式 | 轻量、低延迟 | 实时转录 |
| **Conformer** | 流式/非流式 | 高准确率 | 对准确率要求高 |
| **NeMo** | 非流式 | NVIDIA 优化 | GPU 部署 |

---

### 🖥️ 支持平台

| 平台 | 架构 | 状态 | 备注 |
|------|------|------|------|
| **macOS** | arm64 (M1/M2/M3/M4) | ✅ | 原生支持 |
| **macOS** | x86_64 (Intel) | ✅ | 原生支持 |
| **iOS** | arm64 | ✅ | 支持 iPhone/iPad |
| **Android** | arm64-v8a | ✅ | 支持大部分设备 |
| **Android** | armeabi-v7a | ✅ | 支持旧设备 |
| **Linux** | x86_64 | ✅ | 原生支持 |
| **Linux** | aarch64 | ✅ | 支持树莓派等 |
| **Windows** | x64 | ✅ | 原生支持 |
| **Windows** | x86 | ✅ | 32 位支持 |
| **WebAssembly** | wasm32 | ✅ | 浏览器运行 |

---

### 📈 性能参考

在 Apple M1 MacBook Pro 上的测试结果：

| 模型 | 加载时间 | RTF | 内存占用 |
|------|----------|-----|----------|
| SenseVoice INT8 | ~1s | 0.05 | ~200MB |
| Paraformer | ~2s | 0.08 | ~300MB |
| Whisper Small | ~3s | 0.15 | ~500MB |
| Streaming Zipformer | ~0.5s | 实时 | ~100MB |

> RTF (Real-Time Factor): < 1.0 表示比实时更快

---

### 🔗 相关资源

- **sherpa-onnx 官方仓库**: https://github.com/k2-fsa/sherpa-onnx
- **官方文档**: https://k2-fsa.github.io/sherpa/onnx/
- **原始模型下载**: https://github.com/k2-fsa/sherpa-onnx/releases/tag/asr-models
- **FunASR**: https://github.com/alibaba-damo-academy/FunASR
- **SenseVoice**: https://github.com/FunAudioLLM/SenseVoice
- **Whisper**: https://github.com/openai/whisper

---

### 📜 许可证

本仓库中的模型遵循各自的开源协议，大部分为 [Apache License 2.0](https://opensource.org/licenses/Apache-2.0)。

---

## English

### 📖 Introduction

This repository is a **China mirror** of the official ASR models from [k2-fsa/sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx), providing faster download speeds for users in China.

**sherpa-onnx** is a cross-platform speech recognition inference framework developed by the Next-gen Kaldi team, based on ONNX Runtime. It enables efficient **offline speech recognition** on various devices without network connectivity.

### 🌟 Features

- 🚀 **Fast Download in China**: Hosted on ModelScope, download speeds can reach 10MB/s+
- 📦 **Complete Mirror**: Contains 160+ official models covering mainstream ASR architectures
- 🔄 **Regular Sync**: Periodically synchronized from GitHub
- 📝 **Detailed Documentation**: Complete usage examples and model selection guide

---

### 📋 Model Categories

#### Recommended Models

| Model | Type | Size | Features |
|-------|------|------|----------|
| `sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-*` | SenseVoice | ~60MB | Multi-language, INT8 quantized |
| `sherpa-onnx-whisper-turbo` | Whisper | ~1.5GB | 99+ languages, speed optimized |
| `sherpa-onnx-streaming-zipformer-*` | Zipformer | ~20MB | Real-time streaming |

#### By Language

- **Chinese**: Paraformer, SenseVoice, Streaming Zipformer
- **English**: Zipformer, Conformer, NeMo, Whisper
- **Japanese**: Zipformer ReazonSpeech
- **Korean**: Zipformer
- **Multi-language**: Whisper, SenseVoice

---

### 🚀 Quick Start

```bash
# Download model
curl -LO https://modelscope.cn/models/zhaochaoqun/sherpa-onnx-asr-models/resolve/master/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17.tar.bz2

# Extract
tar -xjf sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17.tar.bz2
```

### 💻 Usage Example

```python
import sherpa_onnx

recognizer = sherpa_onnx.OfflineRecognizer.from_sense_voice(
    model="sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17/model.int8.onnx",
    tokens="sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17/tokens.txt",
    num_threads=4,
)

stream = recognizer.create_stream()
stream.accept_wave_file("test.wav")
recognizer.decode_stream(stream)
print(stream.result.text)
```

---

### 📜 License

Models in this repository follow their respective open-source licenses, mostly [Apache License 2.0](https://opensource.org/licenses/Apache-2.0).

---

<div align="center">

**🎙️ 让语音识别更简单 | Making Speech Recognition Easier**

<br>

如有问题或建议，欢迎提交 Issue | For issues or suggestions, please submit an Issue

<br>

[![GitHub](https://img.shields.io/badge/GitHub-k2--fsa%2Fsherpa--onnx-black?logo=github)](https://github.com/k2-fsa/sherpa-onnx)
[![ModelScope](https://img.shields.io/badge/ModelScope-Mirror-blue)](https://modelscope.cn/models/zhaochaoqun/sherpa-onnx-asr-models)

</div>
