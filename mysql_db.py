"""
MySQL 数据层 — Retail_assistant
连接信息通过环境变量配置，密码不写进代码。
"""
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import pymysql

from config.settings import PROJECT_ROOT, ROI_CONFIG_PATH, LOCAL_ROI_CONFIG_PATH

MYSQL_HOST = os.environ.get("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = int(os.environ.get("MYSQL_PORT", "3306"))
MYSQL_USER = os.environ.get("MYSQL_USER", "root")
MYSQL_PASSWORD = os.environ.get("mysql_root") or os.environ.get("MYSQL_PASSWORD", "")
MYSQL_DB = "Retail_assistant"


def mysql_available() -> bool:
    """是否配置了 MySQL 密码，用于决定优先写 MySQL。"""
    return bool(os.environ.get("mysql_root") or os.environ.get("MYSQL_PASSWORD"))


def get_connection(database: str = MYSQL_DB):
    """返回 MySQL 连接。"""
    return pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=database,
        charset="utf8mb4",
        autocommit=True,
        connect_timeout=10,
    )


def create_database():
    """创建 Retail_assistant 数据库。"""
    conn = pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        charset="utf8mb4",
        autocommit=True,
        connect_timeout=10,
    )
    with conn.cursor() as cur:
        cur.execute(
            "CREATE DATABASE IF NOT EXISTS `Retail_assistant` "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
    conn.close()


def init_schema():
    """创建项目当前可落库的 MySQL 表。"""
    create_database()
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS emotion_record (
            id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            camera_id VARCHAR(64) NOT NULL,
            capture_time DATETIME NOT NULL,
            emotion VARCHAR(32) NOT NULL,
            conf DECIMAL(6,4) NOT NULL DEFAULT 0,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_emotion_time_camera (capture_time, camera_id),
            INDEX idx_emotion_camera_id (camera_id, id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS retail_stats (
            id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            zone_id VARCHAR(64) NOT NULL,
            zone_type VARCHAR(32) NOT NULL,
            zone_label VARCHAR(128) NOT NULL,
            period_key VARCHAR(64) NOT NULL DEFAULT '',
            period_start DATETIME NOT NULL,
            period_end DATETIME NOT NULL,
            visit_count INT UNSIGNED NOT NULL DEFAULT 0,
            total_dwell_seconds DECIMAL(12,3) NOT NULL DEFAULT 0,
            heat_score DECIMAL(10,3) NOT NULL DEFAULT 0,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uq_retail_period_zone (period_key, zone_id),
            INDEX idx_retail_zone_time (zone_id, period_start, period_end)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS alert_record (
            id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            alert_type VARCHAR(64) NOT NULL,
            zone_id VARCHAR(64) NOT NULL DEFAULT '',
            person_id INT UNSIGNED NOT NULL DEFAULT 0,
            level VARCHAR(16) NOT NULL DEFAULT 'watch',
            score INT UNSIGNED NOT NULL DEFAULT 0,
            reason TEXT,
            frame_id BIGINT UNSIGNED NOT NULL DEFAULT 0,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_alert_time_level (created_at, level),
            INDEX idx_alert_zone_time (zone_id, created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS query_history (
            id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            session_id VARCHAR(128) NOT NULL,
            conversation_id BIGINT UNSIGNED NULL,
            seq_no BIGINT UNSIGNED NOT NULL DEFAULT 0,
            question TEXT NOT NULL,
            answer TEXT,
            intent VARCHAR(64) NOT NULL DEFAULT 'general',
            confidence DECIMAL(6,4) NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_query_session_time (session_id, created_at),
            INDEX idx_query_created_at (created_at),
            INDEX idx_query_conversation_seq (conversation_id, seq_no)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS voice_command_log (
            id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            session_id VARCHAR(128) NOT NULL,
            wake_word VARCHAR(64) NOT NULL DEFAULT '',
            raw_text TEXT,
            command VARCHAR(64) NOT NULL DEFAULT '',
            action VARCHAR(32) NOT NULL DEFAULT '',
            source VARCHAR(32) NOT NULL DEFAULT 'voice',
            status VARCHAR(16) NOT NULL DEFAULT 'ok',
            latency_ms INT UNSIGNED NOT NULL DEFAULT 0,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_voice_session_time (session_id, created_at),
            INDEX idx_voice_created_at (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS tts_cache (
            id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            text_hash CHAR(40) NOT NULL,
            text TEXT NOT NULL,
            audio MEDIUMBLOB NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uq_tts_text_hash (text_hash)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS roi_config (
            id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            zone_id VARCHAR(64) NOT NULL,
            zone_type VARCHAR(32) NOT NULL,
            zone_label VARCHAR(128) NOT NULL,
            polygon JSON NOT NULL,
            source VARCHAR(32) NOT NULL DEFAULT 'server',
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uq_roi_source_zone (source, zone_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS video_record (
            id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            filename VARCHAR(255) NOT NULL,
            file_path VARCHAR(500) NOT NULL,
            file_size BIGINT UNSIGNED NOT NULL DEFAULT 0,
            source VARCHAR(32) NOT NULL DEFAULT 'upload',
            status VARCHAR(32) NOT NULL DEFAULT 'uploaded',
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_video_created_at (created_at),
            INDEX idx_video_status (status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS chat_session (
            id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            session_id VARCHAR(128) NOT NULL,
            title VARCHAR(255) NOT NULL DEFAULT '新会话',
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uq_chat_session_id (session_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)

        cur.execute(
            "SELECT COUNT(*) FROM information_schema.columns "
            "WHERE table_schema=%s AND table_name='retail_stats' AND column_name='period_key'",
            (MYSQL_DB,),
        )
        if int(cur.fetchone()[0]) == 0:
            cur.execute(
                "ALTER TABLE retail_stats "
                "ADD COLUMN period_key VARCHAR(64) NOT NULL DEFAULT '' AFTER zone_label, "
                "ADD UNIQUE KEY uq_retail_period_zone (period_key, zone_id)"
            )

        cur.execute(
            "SELECT COUNT(*) FROM information_schema.columns "
            "WHERE table_schema=%s AND table_name='query_history' AND column_name='conversation_id'",
            (MYSQL_DB,),
        )
        if int(cur.fetchone()[0]) == 0:
            cur.execute(
                "ALTER TABLE query_history "
                "ADD COLUMN conversation_id BIGINT UNSIGNED NULL AFTER session_id, "
                "ADD COLUMN seq_no BIGINT UNSIGNED NOT NULL DEFAULT 0 AFTER conversation_id, "
                "ADD INDEX idx_query_conversation_seq (conversation_id, seq_no)"
            )

        cur.execute(
            "SELECT COUNT(*) FROM information_schema.columns "
            "WHERE table_schema=%s AND table_name='query_history' AND column_name='seq_no'",
            (MYSQL_DB,),
        )
        if int(cur.fetchone()[0]) == 0:
            cur.execute(
                "ALTER TABLE query_history "
                "ADD COLUMN seq_no BIGINT UNSIGNED NOT NULL DEFAULT 0 AFTER conversation_id, "
                "ADD INDEX idx_query_conversation_seq (conversation_id, seq_no)"
            )

        cur.execute(
            "INSERT IGNORE INTO chat_session(session_id, title) "
            "SELECT DISTINCT q.session_id, LEFT(q.question, 60) "
            "FROM query_history q "
            "WHERE NOT EXISTS (SELECT 1 FROM chat_session s WHERE s.session_id=q.session_id)"
        )
        cur.execute(
            "UPDATE query_history q "
            "JOIN chat_session s ON q.session_id=s.session_id "
            "SET q.conversation_id=s.id WHERE q.conversation_id IS NULL"
        )
        cur.execute(
            "UPDATE query_history q "
            "JOIN ("
            " SELECT id, ROW_NUMBER() OVER (PARTITION BY session_id ORDER BY id) rn "
            " FROM query_history"
            ") x ON q.id=x.id "
            "SET q.seq_no=x.rn WHERE q.seq_no=0"
        )
    conn.close()


def migrate_sqlite_emotion_records():
    """把 SQLite 中已有的表情记录迁移到 MySQL。"""
    sqlite_path = PROJECT_ROOT / "data" / "shop_emotion.db"
    if not sqlite_path.exists():
        return 0

    sqlite_conn = sqlite3.connect(str(sqlite_path))
    rows = sqlite_conn.execute(
        "SELECT id, camera_id, capture_time, emotion, conf "
        "FROM emotion_record ORDER BY id"
    ).fetchall()
    sqlite_conn.close()

    if not rows:
        return 0

    conn = get_connection()
    migrated = 0
    with conn.cursor() as cur:
        insert_rows = [
            (rid, camera_id, capture_time, emotion, conf)
            for rid, camera_id, capture_time, emotion, conf in rows
        ]
        if insert_rows:
            cur.executemany(
                "INSERT IGNORE INTO emotion_record "
                "(id, camera_id, capture_time, emotion, conf) "
                "VALUES (%s, %s, %s, %s, %s)",
                insert_rows,
            )
            migrated = cur.rowcount
    conn.close()
    return migrated


def import_roi_configs():
    """把当前 ROI YAML 配置同步到 MySQL。"""
    import json
    import yaml

    sources = [
        ("server", PROJECT_ROOT / ROI_CONFIG_PATH),
        ("local", PROJECT_ROOT / LOCAL_ROI_CONFIG_PATH),
    ]
    conn = get_connection()
    total = 0
    with conn.cursor() as cur:
        for source, path in sources:
            if not path.exists():
                continue
            with open(path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            for zone_id, info in (config or {}).get("zones", {}).items():
                cur.execute(
                    """
                    INSERT INTO roi_config
                    (zone_id, zone_type, zone_label, polygon, source)
                    VALUES (%s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        zone_type = VALUES(zone_type),
                        zone_label = VALUES(zone_label),
                        polygon = VALUES(polygon),
                        source = VALUES(source)
                    """,
                    (
                        zone_id,
                        info.get("type", "shelf"),
                        info.get("label", zone_id),
                        json.dumps(info.get("polygon", []), ensure_ascii=False),
                        source,
                    ),
                )
                total += cur.rowcount
    conn.close()
    return total


def insert_emotion_record(camera_id: str, emotion: str, conf: float):
    """写入一条表情识别记录。"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO emotion_record(camera_id, capture_time, emotion, conf) "
            "VALUES (%s, %s, %s, %s)",
            (camera_id, now, emotion, conf),
        )
    conn.close()


def insert_emotion_records(camera_id: str, records: list[tuple[str, float]]):
    """批量写入表情识别记录。"""
    if not records:
        return
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows = [(camera_id, now, emotion, conf) for emotion, conf in records]
    conn = get_connection()
    with conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO emotion_record(camera_id, capture_time, emotion, conf) "
            "VALUES (%s, %s, %s, %s)",
            rows,
        )
    conn.close()


def get_emotion_statistic(start_time: str, end_time: str, camera_id: str | None = None):
    """按时间段统计表情数量。"""
    conn = get_connection()
    with conn.cursor() as cur:
        if camera_id:
            cur.execute(
                """
                SELECT emotion, COUNT(*) FROM emotion_record
                WHERE capture_time BETWEEN %s AND %s AND camera_id=%s
                GROUP BY emotion
                """,
                (start_time, end_time, camera_id),
            )
        else:
            cur.execute(
                """
                SELECT emotion, COUNT(*) FROM emotion_record
                WHERE capture_time BETWEEN %s AND %s
                GROUP BY emotion
                """,
                (start_time, end_time),
            )
        result = cur.fetchall()
    conn.close()
    return result


def get_latest_emotion_records(camera_id: str | None = None, limit: int = 20):
    """查询最近表情记录，返回与 SQLite 相同的元组结构。"""
    conn = get_connection()
    with conn.cursor() as cur:
        if camera_id:
            cur.execute(
                """
                SELECT camera_id, capture_time, emotion, conf
                FROM emotion_record
                WHERE camera_id=%s
                ORDER BY id DESC LIMIT %s
                """,
                (camera_id, int(limit)),
            )
        else:
            cur.execute(
                """
                SELECT camera_id, capture_time, emotion, conf
                FROM emotion_record
                ORDER BY id DESC LIMIT %s
                """,
                (int(limit),),
            )
        result = cur.fetchall()
    conn.close()
    return result


def get_emotion_record_count(camera_id: str | None = None, hours: int = 24):
    """统计最近 N 小时表情记录数。"""
    end = datetime.now()
    start = end - timedelta(hours=hours)
    start_str = start.strftime("%Y-%m-%d %H:%M:%S")
    end_str = end.strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection()
    with conn.cursor() as cur:
        if camera_id:
            cur.execute(
                """
                SELECT COUNT(*) FROM emotion_record
                WHERE capture_time BETWEEN %s AND %s AND camera_id=%s
                """,
                (start_str, end_str, camera_id),
            )
        else:
            cur.execute(
                """
                SELECT COUNT(*) FROM emotion_record
                WHERE capture_time BETWEEN %s AND %s
                """,
                (start_str, end_str),
            )
        count = int(cur.fetchone()[0])
    conn.close()
    return count


def cleanup_emotion_records(days: int = 30):
    """删除超过 N 天的表情记录。"""
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM emotion_record WHERE capture_time < %s",
            (cutoff,),
        )
        deleted = cur.rowcount
    conn.close()
    return deleted


def save_query_history(
    session_id: str,
    question: str,
    answer: str | None,
    intent: str = "general",
    confidence: float | None = None,
):
    """保存自然语言查询历史。"""
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO chat_session(session_id, title)
            VALUES (%s, LEFT(%s, 60))
            ON DUPLICATE KEY UPDATE
                title=CASE WHEN title='新会话' THEN VALUES(title) ELSE title END,
                updated_at=CURRENT_TIMESTAMP
            """,
            (session_id, question.strip()),
        )
        cur.execute(
            "SELECT id FROM chat_session WHERE session_id=%s",
            (session_id,),
        )
        conversation_row = cur.fetchone()
        conversation_id = conversation_row[0] if conversation_row else None
        cur.execute(
            "SELECT COALESCE(MAX(seq_no), 0) + 1 FROM query_history WHERE session_id=%s",
            (session_id,),
        )
        seq_no = int(cur.fetchone()[0])
        cur.execute(
            """
            INSERT INTO query_history
            (session_id, conversation_id, seq_no, question, answer, intent, confidence)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (session_id, conversation_id, seq_no, question, answer, intent, confidence),
        )
        message_id = cur.lastrowid
    conn.close()
    return message_id, seq_no


def create_chat_session(session_id: str, title: str = "新会话"):
    """新建会话。"""
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(
            "INSERT IGNORE INTO chat_session(session_id, title) VALUES (%s, %s)",
            (session_id, title[:255]),
        )
    conn.close()


def save_chat_session(session_id: str, title: str | None = None):
    """保存会话标题并刷新更新时间。"""
    conn = get_connection()
    with conn.cursor() as cur:
        if title:
            cur.execute(
                "UPDATE chat_session SET title=%s, updated_at=CURRENT_TIMESTAMP "
                "WHERE session_id=%s",
                (title[:255], session_id),
            )
        else:
            cur.execute(
                "UPDATE chat_session SET updated_at=CURRENT_TIMESTAMP "
                "WHERE session_id=%s",
                (session_id,),
            )
    conn.close()


def list_chat_sessions():
    """列出全部会话及消息数。"""
    conn = get_connection()
    sessions = []
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT s.session_id, s.title, s.created_at, s.updated_at,
                   (SELECT COUNT(*) FROM query_history q WHERE q.session_id=s.session_id) AS message_count
            FROM chat_session s
            ORDER BY s.updated_at DESC, s.id DESC
            """
        )
        for row in cur.fetchall():
            sessions.append({
                "session_id": row[0],
                "title": row[1],
                "created_at": row[2].strftime("%Y-%m-%d %H:%M:%S") if row[2] else "",
                "updated_at": row[3].strftime("%Y-%m-%d %H:%M:%S") if row[3] else "",
                "message_count": row[4],
            })
    conn.close()
    return sessions


def get_chat_messages(session_id: str):
    """获取指定会话的消息列表。"""
    conn = get_connection()
    messages = []
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT seq_no, question, answer, intent, confidence, created_at
            FROM query_history
            WHERE session_id=%s
            ORDER BY seq_no, id
            """,
            (session_id,),
        )
        for row in cur.fetchall():
            messages.append({
                "seq_no": row[0],
                "question": row[1],
                "answer": row[2],
                "intent": row[3],
                "confidence": float(row[4]) if row[4] is not None else None,
                "created_at": row[5].strftime("%Y-%m-%d %H:%M:%S") if row[5] else "",
            })
    conn.close()
    return messages


def search_chat_messages(keyword: str):
    """搜索会话标题、问题或回答内容。"""
    if not keyword or not keyword.strip():
        return []
    pattern = f"%{keyword.strip()}%"
    conn = get_connection()
    results = []
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT q.session_id, s.title, q.seq_no, q.question, q.answer, q.created_at
            FROM query_history q
            JOIN chat_session s ON q.session_id = s.session_id
            WHERE q.question LIKE %s
               OR q.answer LIKE %s
               OR s.title LIKE %s
            ORDER BY q.created_at DESC
            LIMIT 50
            """,
            (pattern, pattern, pattern),
        )
        for row in cur.fetchall():
            results.append({
                "session_id": row[0],
                "title": row[1],
                "seq_no": row[2],
                "question": row[3],
                "answer": row[4],
                "created_at": row[5].strftime("%Y-%m-%d %H:%M:%S") if row[5] else "",
            })
    conn.close()
    return results


def get_all_query_history_records():
    """获取全部查询历史，用于向量库重建。"""
    conn = get_connection()
    records = []
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT q.id, q.session_id, q.seq_no, q.question, q.answer,
                   q.created_at, s.title
            FROM query_history q
            JOIN chat_session s ON q.session_id = s.session_id
            ORDER BY q.id
            """
        )
        for row in cur.fetchall():
            records.append({
                "message_id": row[0],
                "session_id": row[1],
                "seq_no": row[2],
                "question": row[3],
                "answer": row[4],
                "created_at": row[5].strftime("%Y-%m-%d %H:%M:%S") if row[5] else "",
                "title": row[6],
            })
    conn.close()
    return records


def search_chat_messages(keyword: str):
    """按关键词搜索会话标题、问题或回答。"""
    if not keyword or not keyword.strip():
        return []
    pattern = f"%{keyword.strip()}%"
    conn = get_connection()
    results = []
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT q.session_id, s.title, q.seq_no, q.question, q.answer, q.created_at
            FROM query_history q
            JOIN chat_session s ON q.session_id=s.session_id
            WHERE q.question LIKE %s
               OR q.answer LIKE %s
               OR s.title LIKE %s
            ORDER BY q.created_at DESC
            LIMIT 50
            """,
            (pattern, pattern, pattern),
        )
        for row in cur.fetchall():
            results.append({
                "session_id": row[0],
                "title": row[1],
                "seq_no": row[2],
                "question": row[3],
                "answer": row[4],
                "created_at": row[5].strftime("%Y-%m-%d %H:%M:%S") if row[5] else "",
            })
    conn.close()
    return results


def save_retail_stats(
    period_key: str,
    zones: dict,
    period_start: str | None = None,
    period_end: str | None = None,
):
    """保存零售热度统计快照，同一分钟同一区域只保留最新值。"""
    now = datetime.now()
    period_start = period_start or now.strftime("%Y-%m-%d %H:%M:%S")
    period_end = period_end or now.strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection()
    with conn.cursor() as cur:
        for zone_id, z in (zones or {}).items():
            cur.execute(
                """
                INSERT INTO retail_stats
                (period_key, zone_id, zone_type, zone_label,
                 period_start, period_end, visit_count,
                 total_dwell_seconds, heat_score)
                VALUES (%s, %s, 'shelf', %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    zone_label=VALUES(zone_label),
                    period_start=VALUES(period_start),
                    period_end=VALUES(period_end),
                    visit_count=VALUES(visit_count),
                    total_dwell_seconds=VALUES(total_dwell_seconds),
                    heat_score=VALUES(heat_score)
                """,
                (
                    period_key,
                    zone_id,
                    z.get("zone_label", zone_id),
                    period_start,
                    period_end,
                    z.get("visit_count", 0),
                    z.get("total_dwell_seconds", 0),
                    z.get("heat_score", 0),
                ),
            )
    conn.close()


def save_alert_record(
    alert_type: str,
    zone_id: str,
    person_id: int,
    level: str,
    score: int,
    reason: str,
    frame_id: int,
    created_at: str | None = None,
):
    """保存异常告警记录。"""
    created_at = created_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO alert_record
            (alert_type, zone_id, person_id, level, score, reason, frame_id, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                alert_type,
                zone_id,
                person_id,
                level,
                score,
                reason,
                frame_id,
                created_at,
            ),
        )
    conn.close()


def save_voice_command_log(
    session_id: str,
    raw_text: str,
    command: str,
    action: str,
    status: str = "ok",
    wake_word: str = "",
    source: str = "voice",
    latency_ms: int = 0,
):
    """保存语音指令日志。"""
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO voice_command_log
            (session_id, wake_word, raw_text, command, action, source, status, latency_ms)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (session_id, wake_word, raw_text, command, action, source, status, latency_ms),
        )
    conn.close()


def save_tts_cache(cache_key: str, text: str, audio: bytes):
    """保存 TTS 音频缓存。"""
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO tts_cache(text_hash, text, audio)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE text=VALUES(text), audio=VALUES(audio)
            """,
            (cache_key, text, audio),
        )
    conn.close()


def get_tts_cache(cache_key: str) -> bytes | None:
    """从 MySQL 读取 TTS 音频缓存。"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT audio FROM tts_cache WHERE text_hash=%s",
                (cache_key,),
            )
            row = cur.fetchone()
            return bytes(row[0]) if row else None
    finally:
        conn.close()


def save_video_record(
    filename: str,
    file_path: str,
    file_size: int,
    source: str = "upload",
    status: str = "uploaded",
):
    """保存视频上传记录。"""
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO video_record(filename, file_path, file_size, source, status)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (filename, file_path, file_size, source, status),
        )
    conn.close()


def upsert_roi_config(
    zone_id: str,
    zone_type: str,
    zone_label: str,
    polygon: list,
    source: str,
):
    """写入或更新 ROI 配置。"""
    import json

    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO roi_config(zone_id, zone_type, zone_label, polygon, source)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                zone_type=VALUES(zone_type),
                zone_label=VALUES(zone_label),
                polygon=VALUES(polygon),
                source=VALUES(source)
            """,
            (zone_id, zone_type, zone_label, json.dumps(polygon, ensure_ascii=False), source),
        )
    conn.close()


def delete_roi_config(zone_id: str, source: str = "server"):
    """删除 ROI 配置。"""
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM roi_config WHERE zone_id=%s AND source=%s",
            (zone_id, source),
        )
    conn.close()


def list_tables():
    """列出 Retail_assistant 数据库中的业务表。"""
    conn = get_connection()
    tables = []
    with conn.cursor() as cur:
        cur.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema=%s ORDER BY table_name",
            (MYSQL_DB,),
        )
        tables = [row[0] for row in cur.fetchall()]
    conn.close()
    return tables


def table_schema(table_name: str) -> list[dict]:
    """返回表字段信息。"""
    conn = get_connection()
    fields = []
    with conn.cursor() as cur:
        cur.execute(
            "SELECT column_name, column_type, is_nullable, column_default, extra "
            "FROM information_schema.columns "
            "WHERE table_schema=%s AND table_name=%s "
            "ORDER BY ordinal_position",
            (MYSQL_DB, table_name),
        )
        for row in cur.fetchall():
            fields.append({
                "column": row[0],
                "type": row[1],
                "nullable": row[2],
                "default": row[3],
                "extra": row[4],
            })
    conn.close()
    return fields


def row_counts() -> dict[str, int]:
    """返回各表当前记录数。"""
    conn = get_connection()
    counts = {}
    with conn.cursor() as cur:
        for table in list_tables():
            cur.execute(f"SELECT COUNT(*) FROM `{table}`")
            counts[table] = int(cur.fetchone()[0])
    conn.close()
    return counts


if __name__ == "__main__":
    init_schema()
    emotion_migrated = migrate_sqlite_emotion_records()
    roi_migrated = import_roi_configs()
    print("tables:", list_tables())
    print("counts:", row_counts())
    print("migrated_emotion:", emotion_migrated)
    print("migrated_roi:", roi_migrated)
