"""
数据库模块 — SQLite 存储
替掉 study_log.txt，支持结构化查询
"""
import sqlite3
import shutil
from datetime import datetime
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent  # Fake-AI-Project/
DB_PATH = PROJECT_DIR / "data" / "cyber_mentor.db"


def get_conn():
    """获取数据库连接（自动建目录）"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """创建表（首次运行）"""
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS study_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            content TEXT NOT NULL,
            mood INTEGER DEFAULT 5,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        )
    """)
    conn.commit()
    conn.close()


def migrate_from_txt():
    """从 study_log.txt 迁移数据到数据库，迁移后备份原文件"""
    txt_path = PROJECT_DIR / "study_log.txt"
    if not txt_path.exists():
        init_db()
        return 0

    init_db()

    # 已经迁移过则跳过
    conn = get_conn()
    count = conn.execute("SELECT COUNT(*) FROM study_logs").fetchone()[0]
    if count > 0:
        conn.close()
        return 0

    # 解析 txt
    text = txt_path.read_text(encoding="utf-8").strip()
    parts = text.split("\n[")
    migrated = 0

    for part in parts[1:]:  # 跳过第一个块（关键词行）
        lines = part.strip().split("\n", 1)
        if len(lines) < 2:
            continue

        header = lines[0].strip()
        content = lines[1].strip()

        # 解析时间戳和心情：2026-05-31 18:28:01] 心情:7/10
        timestamp = header.split("]")[0].strip()
        mood = 5
        if "心情:" in header:
            try:
                mood_part = header.split("心情:")[1].split("/")[0].strip()
                mood = int(mood_part)
            except (ValueError, IndexError):
                pass

        conn.execute(
            "INSERT INTO study_logs (timestamp, content, mood) VALUES (?, ?, ?)",
            (timestamp, content, mood)
        )
        migrated += 1

    conn.commit()
    conn.close()

    # 备份原文件
    shutil.move(str(txt_path), str(txt_path) + ".bak")
    return migrated


# ─── 增删改查 ──────────────────────────────

def add_record(content, mood=5):
    """新增一条学习记录"""
    conn = get_conn()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        "INSERT INTO study_logs (timestamp, content, mood) VALUES (?, ?, ?)",
        (now, content, mood)
    )
    conn.commit()
    conn.close()


def get_all_records(limit=50):
    """获取最近 N 条记录"""
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM study_logs ORDER BY timestamp DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_today_records():
    """获取今天的记录"""
    conn = get_conn()
    today = datetime.now().strftime("%Y-%m-%d")
    rows = conn.execute(
        "SELECT * FROM study_logs WHERE timestamp LIKE ? ORDER BY timestamp DESC",
        (f"{today}%",)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def search_records(keyword):
    """按关键词搜索"""
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM study_logs WHERE content LIKE ? ORDER BY timestamp DESC",
        (f"%{keyword}%",)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_distinct_dates():
    """获取所有学习过的日期"""
    conn = get_conn()
    rows = conn.execute(
        "SELECT DISTINCT substr(timestamp, 1, 10) as date FROM study_logs ORDER BY date"
    ).fetchall()
    conn.close()
    return [r["date"] for r in rows]


def get_total_count():
    """总记录数"""
    conn = get_conn()
    count = conn.execute("SELECT COUNT(*) FROM study_logs").fetchone()[0]
    conn.close()
    return count


def get_mood_stats():
    """每天的平均心情"""
    conn = get_conn()
    rows = conn.execute(
        """SELECT substr(timestamp, 1, 10) as date,
                  ROUND(AVG(mood), 1) as avg_mood
           FROM study_logs GROUP BY date ORDER BY date"""
    ).fetchall()
    conn.close()
    return [(r["date"], r["avg_mood"]) for r in rows]


def has_today_record():
    """今天是否已经记录过"""
    return len(get_today_records()) > 0
