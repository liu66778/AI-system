"""
数据库模块 — SQLite 存储
替掉 study_log.txt，支持结构化查询 + 标签分类
"""
import sqlite3
import shutil
from datetime import datetime
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent  # Fake-AI-Project/
DB_PATH = PROJECT_DIR / "data" / "cyber_mentor.db"

# 预设标签
PRESET_TAGS = [
    ("编程", "💻"), ("AI", "🤖"), ("理论", "📚"),
    ("工具", "🔧"), ("项目", "🚀"), ("数据", "📊"),
    ("阅读", "📖"), ("数学", "🧮"),
]


def get_conn():
    """获取数据库连接（自动建目录）"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")  # 并发写入优化
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """创建表（首次运行），含标签系统"""
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS study_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            content TEXT NOT NULL,
            mood INTEGER DEFAULT 5,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            emoji TEXT DEFAULT '🏷️'
        );

        CREATE TABLE IF NOT EXISTS study_log_tags (
            log_id INTEGER NOT NULL,
            tag_id INTEGER NOT NULL,
            PRIMARY KEY (log_id, tag_id),
            FOREIGN KEY (log_id) REFERENCES study_logs(id) ON DELETE CASCADE,
            FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON study_logs(timestamp);
        CREATE INDEX IF NOT EXISTS idx_tags_name ON tags(name);
    """)

    # 插入预设标签（已存在则跳过）
    for name, emoji in PRESET_TAGS:
        conn.execute(
            "INSERT OR IGNORE INTO tags (name, emoji) VALUES (?, ?)",
            (name, emoji)
        )

    conn.commit()
    conn.close()


def migrate_from_txt():
    """从 study_log.txt 迁移数据到数据库，迁移后备份原文件"""
    txt_path = PROJECT_DIR / "study_log.txt"
    if not txt_path.exists():
        init_db()
        return 0

    init_db()

    conn = get_conn()
    count = conn.execute("SELECT COUNT(*) FROM study_logs").fetchone()[0]
    if count > 0:
        conn.close()
        return 0

    text = txt_path.read_text(encoding="utf-8").strip()
    parts = text.split("\n[")
    migrated = 0

    for part in parts[1:]:
        lines = part.strip().split("\n", 1)
        if len(lines) < 2:
            continue

        header = lines[0].strip()
        content = lines[1].strip()

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

    shutil.move(str(txt_path), str(txt_path) + ".bak")
    return migrated


# ─── 增删改查 ──────────────────────────────

def add_record(content, mood=5, tag_ids=None):
    """新增一条学习记录，可选关联标签"""
    conn = get_conn()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor = conn.execute(
        "INSERT INTO study_logs (timestamp, content, mood) VALUES (?, ?, ?)",
        (now, content, mood)
    )
    log_id = cursor.lastrowid

    if tag_ids:
        for tid in tag_ids:
            conn.execute(
                "INSERT OR IGNORE INTO study_log_tags (log_id, tag_id) VALUES (?, ?)",
                (log_id, tid)
            )

    conn.commit()
    conn.close()
    return log_id


def get_all_records(limit=50, tag_id=None):
    """获取最近 N 条记录，可按标签过滤"""
    conn = get_conn()
    if tag_id:
        rows = conn.execute(
            """SELECT DISTINCT s.* FROM study_logs s
               JOIN study_log_tags st ON s.id = st.log_id
               WHERE st.tag_id = ?
               ORDER BY s.timestamp DESC LIMIT ?""",
            (tag_id, limit)
        ).fetchall()
    else:
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


def search_records_multi(keywords):
    """多关键词 OR 搜索"""
    if not keywords:
        return []
    conn = get_conn()
    conditions = " OR ".join(["content LIKE ?"] * len(keywords))
    params = [f"%{kw}%" for kw in keywords]
    rows = conn.execute(
        f"SELECT * FROM study_logs WHERE {conditions} ORDER BY timestamp DESC",
        params
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


# ─── 标签系统 ──────────────────────────────

def get_all_tags():
    """获取所有标签"""
    conn = get_conn()
    rows = conn.execute("SELECT * FROM tags ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_tags_for_record(log_id):
    """获取某条记录的标签"""
    conn = get_conn()
    rows = conn.execute(
        """SELECT t.* FROM tags t
           JOIN study_log_tags st ON t.id = st.tag_id
           WHERE st.log_id = ?""",
        (log_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_records_by_tag(tag_id, limit=50):
    """按标签查记录"""
    return get_all_records(limit=limit, tag_id=tag_id)


def get_tag_stats():
    """各标签使用次数统计"""
    conn = get_conn()
    rows = conn.execute(
        """SELECT t.name, t.emoji, COUNT(st.log_id) as cnt
           FROM tags t
           LEFT JOIN study_log_tags st ON t.id = st.tag_id
           GROUP BY t.id
           ORDER BY cnt DESC"""
    ).fetchall()
    conn.close()
    return [{"name": r["name"], "emoji": r["emoji"], "count": r["cnt"]} for r in rows]


def add_tag(name, emoji="🏷️"):
    """添加自定义标签"""
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO tags (name, emoji) VALUES (?, ?)",
            (name, emoji)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # 标签已存在
    finally:
        conn.close()


def get_all_records_full(limit=200):
    """获取所有记录（含标签），给 RAG 搜索用"""
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM study_logs ORDER BY timestamp DESC LIMIT ?",
        (limit,)
    ).fetchall()

    records = []
    for r in rows:
        rec = dict(r)
        rec["tags"] = get_tags_for_record(r["id"])
        records.append(rec)
    conn.close()
    return records
