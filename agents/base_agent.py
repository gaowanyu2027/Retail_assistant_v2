"""
Agent 基础设施 — LangChain 方案
使用 ChatOpenAI + create_agent，参考 travel_agent 架构
"""
import os
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from config.settings import LLM_PROVIDER, LLM_MODEL, LLM_BASE_URL


def create_llm(temperature: float = 0.3) -> ChatOpenAI:
    """创建 LLM 实例 — 通过 ChatOpenAI 对接 DeepSeek

    Args:
        temperature: 生成温度（0=确定，1=随机）

    Returns:
        ChatOpenAI 实例
    """
    api_key = os.environ.get("dazuoye_api", "")
    return ChatOpenAI(
        api_key=api_key,
        base_url=LLM_BASE_URL,
        model=LLM_MODEL,
        temperature=temperature,
    )


def create_memory() -> MemorySaver:
    """创建内存级对话状态持久化

    Returns:
        MemorySaver 实例 — 按 thread_id 隔离多轮对话上下文
    """
    return MemorySaver()
