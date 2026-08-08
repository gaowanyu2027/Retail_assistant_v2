"""
查询历史向量召回
使用 Qdrant 本地模式 + Ollama bge-small-zh-v1.5
"""
import threading
import atexit
from pathlib import Path

import httpx
from qdrant_client import QdrantClient, models

from config.settings import PROJECT_ROOT

COLLECTION_NAME = "query_history_vectors"
EMBED_MODEL = "qllama/bge-small-zh-v1.5"
OLLAMA_EMBED_URL = "http://127.0.0.1:11434/api/embeddings"
VECTOR_SIZE = 512

_client: QdrantClient | None = None
_client_lock = threading.Lock()


def _close_client():
    global _client
    if _client is not None:
        try:
            _client.close()
        except Exception:
            pass
        _client = None


atexit.register(_close_client)


def _embed(text: str) -> list[float]:
    clean_text = (text or "").strip()
    if not clean_text:
        clean_text = "空"
    resp = httpx.post(
        OLLAMA_EMBED_URL,
        json={"model": EMBED_MODEL, "prompt": clean_text[:1000]},
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    embedding = data.get("embedding")
    if not embedding and isinstance(data.get("data"), list) and data["data"]:
        embedding = data["data"][0].get("embedding")
    if not embedding:
        raise RuntimeError("Ollama embedding 返回为空")
    return embedding


def _get_client() -> QdrantClient:
    global _client
    with _client_lock:
        if _client is None:
            data_dir = Path(PROJECT_ROOT) / "qdrant_data"
            data_dir.mkdir(parents=True, exist_ok=True)
            _client = QdrantClient(path=str(data_dir))
        if not _client.collection_exists(COLLECTION_NAME):
            _client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=models.VectorParams(
                    size=VECTOR_SIZE,
                    distance=models.Distance.COSINE,
                ),
            )
        return _client


def upsert_message(
    message_id: int,
    session_id: str,
    seq_no: int,
    title: str,
    question: str,
    answer: str,
    created_at: str,
):
    """将一条查询历史写入向量库。"""
    vector = _embed(f"{title}\n{question}\n{answer}")
    client = _get_client()
    with _client_lock:
        client.upsert(
            collection_name=COLLECTION_NAME,
            points=[
                models.PointStruct(
                    id=int(message_id),
                    vector=vector,
                    payload={
                        "message_id": int(message_id),
                        "session_id": session_id,
                        "seq_no": int(seq_no or 0),
                        "title": title,
                        "question": question,
                        "answer": answer or "",
                        "created_at": created_at,
                    },
                )
            ],
        )


def delete_message(message_id: int):
    """从向量库删除一条消息。"""
    client = _get_client()
    with _client_lock:
        client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=models.PointIdsList(points=[int(message_id)]),
        )


def search_messages(query: str, limit: int = 10):
    """按语义相似度搜索查询历史。"""
    query = (query or "").strip()
    if not query:
        return []
    vector = _embed(query)
    client = _get_client()
    with _client_lock:
        response = client.query_points(
            collection_name=COLLECTION_NAME,
            query=vector,
            limit=limit,
            with_payload=True,
        )
        hits = response.points if response else []
    results = []
    for hit in hits:
        payload = hit.payload or {}
        results.append({
            "session_id": payload.get("session_id", ""),
            "title": payload.get("title", ""),
            "seq_no": payload.get("seq_no", 0),
            "question": payload.get("question", ""),
            "answer": payload.get("answer", ""),
            "created_at": payload.get("created_at", ""),
            "score": round(float(hit.score), 4),
        })
    return results


def reindex_all() -> int:
    """把 MySQL 中全部查询历史重建到向量库。"""
    import mysql_db
    records = mysql_db.get_all_query_history_records()
    count = 0
    for record in records:
        upsert_message(
            message_id=record["message_id"],
            session_id=record["session_id"],
            seq_no=record["seq_no"],
            title=record.get("title", ""),
            question=record["question"],
            answer=record.get("answer", ""),
            created_at=record.get("created_at", ""),
        )
        count += 1
    return count
