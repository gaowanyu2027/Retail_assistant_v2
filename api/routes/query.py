"""
POST /query — 自然语言查询接口（LangChain Agent 版）
"""
import time
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from api.schemas import QueryRequest, QueryResponse

router = APIRouter(prefix="/query", tags=["query"])

# ===== 会话级 Agent 缓存（按 session_id 复用，保持对话记忆） =====
_agent_cache: dict[str, "MasterAgent"] = {}     # type: ignore
_agent_last_used: dict[str, float] = {}
SESSION_TTL = 1800  # 30分钟不活动自动清理


def _get_agent(session_id: str):
    """获取或创建 Agent 实例（按 session_id 复用，保持 MemorySaver 记忆）"""
    global _agent_cache, _agent_last_used

    # 清理过期会话
    now = time.time()
    expired = [sid for sid, t in _agent_last_used.items() if now - t > SESSION_TTL]
    for sid in expired:
        _agent_cache.pop(sid, None)
        _agent_last_used.pop(sid, None)

    # 复用已有或新建
    if session_id in _agent_cache:
        _agent_last_used[session_id] = now
        return _agent_cache[session_id]

    from api.dependencies import get_popularity_skill, get_anomaly_skill, get_emotion_skill
    from agents.master_agent import MasterAgent

    pop_skill = get_popularity_skill()
    anom_skill = get_anomaly_skill()
    emo_skill = get_emotion_skill()

    agent = MasterAgent(popularity_skill=pop_skill, anomaly_skill=anom_skill, emotion_skill=emo_skill)
    _agent_cache[session_id] = agent
    _agent_last_used[session_id] = now
    return agent


def get_agent(session_id: str):
    """供语音等接口复用的 Agent 获取入口。"""
    return _get_agent(session_id)


def _persist_query_history(session_id: str, question: str, answer: str, intent: str = "general"):
    """写入 MySQL 查询历史，并同步到向量库。"""
    try:
        import mysql_db
        import vector_memory
        from datetime import datetime

        message_id, seq_no = mysql_db.save_query_history(
            session_id=session_id,
            question=question,
            answer=answer,
            intent=intent,
        )
        vector_memory.upsert_message(
            message_id=message_id,
            session_id=session_id,
            seq_no=seq_no,
            title=question.strip()[:60],
            question=question,
            answer=answer,
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
    except Exception as e:
        print(f"[Vector] 查询历史持久化失败: {e}")


@router.post("", response_model=QueryResponse)
async def handle_query(request: QueryRequest):
    """处理自然语言查询（非流式，保持兼容）"""
    try:
        agent = _get_agent(request.session_id)
        result = agent.handle_query(
            query=request.question,
            context=request.context,
            session_id=request.session_id,
        )
        _persist_query_history(
            session_id=request.session_id,
            question=request.question,
            answer=result.get("answer", ""),
            intent=result.get("intent", "general"),
        )
        return QueryResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询处理失败: {str(e)}")


@router.post("/stream")
async def handle_query_stream(request: QueryRequest):
    """处理自然语言查询 — SSE 流式输出

    前端使用 fetch + ReadableStream 逐 token 渲染，实现打字效果
    """
    try:
        agent = _get_agent(request.session_id)

        async def token_generator():
            full_answer = ""
            async for token in agent.handle_query_stream(
                query=request.question,
                session_id=request.session_id,
            ):
                # SSE 格式: data: <token>\n\n
                full_answer += token
                yield f"data: {token}\n\n"
            yield "data: [DONE]\n\n"
            _persist_query_history(
                session_id=request.session_id,
                question=request.question,
                answer=full_answer,
                intent="general",
            )

        return StreamingResponse(
            token_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"流式查询失败: {str(e)}")
