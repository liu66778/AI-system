"""
Cyber Mentor v4.0 — 数据库版
SQLite 存储 + 学习仪表盘 + 自动 Git 提交
"""
from datetime import datetime
import os
import sys

# Windows 终端编码修复
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# 把 src 加到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from database import init_db, migrate_from_txt, add_record, get_all_records, has_today_record
from stats import print_dashboard
from git_auto import auto_commit

NAME = "刘焕玉"

# 文件路径
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(os.path.dirname(PROJECT_DIR))
DIARY_PATH = os.path.join(BASE_DIR, "Notes", "Cyber-Diary.md")


# ═══════════════════════════════════════════════════
# 功能函数
# ═══════════════════════════════════════════════════

def welcome():
    print(f"\n👤 {NAME}，欢迎回到 Cyber Mentor")
    print("=" * 40)


def show_history():
    """从数据库读取最近记录"""
    print("\n📚 历史学习记录：")
    records = get_all_records(limit=20)
    if not records:
        print("  （暂无）")
        return

    for r in reversed(records):
        mood_icon = {1:"😫", 2:"😣", 3:"😐", 4:"🙂", 5:"😊",
                     6:"😄", 7:"🤩", 8:"🎉", 9:"🔥", 10:"💯"}.get(r["mood"], "😊")
        print(f"  [{r['timestamp']}] {mood_icon} {r['content'][:60]}")

    total = len(get_all_records(limit=9999))
    print(f"  ...共 {total} 条记录")


def update_diary(content, mood):
    """写入赛博日记（按日期归档）"""
    today = datetime.now().strftime("%Y-%m-%d")
    diary_path = os.path.normpath(DIARY_PATH)
    os.makedirs(os.path.dirname(diary_path), exist_ok=True)

    already_written = False
    if os.path.exists(diary_path):
        with open(diary_path, "r", encoding="utf-8") as f:
            already_written = today in f.read()

    if not already_written:
        with open(diary_path, "a", encoding="utf-8") as f:
            f.write(f"\n## {today}\n\n")
            f.write(f"- 😊 心情：{mood}/10\n")
            f.write(f"- 📖 学习：{content}\n")
    else:
        with open(diary_path, "a", encoding="utf-8") as f:
            f.write(f"- 📖 补充学习：{content}\n")


def do_record():
    """记录今天的学习"""
    today_already = has_today_record()
    if today_already:
        print("\n📌 你今天已经记录过了，可以追加")

    study = input("\n📖 今天学了什么：")
    if not study.strip():
        print("⚠️ 内容不能为空")
        return

    mood = input("😊 心情如何（1-10）：")
    try:
        mood = int(mood)
        if mood < 1 or mood > 10:
            mood = 5
    except ValueError:
        mood = 5

    add_record(study, mood)
    update_diary(study, mood)
    print("\n✅ 记录已保存！")

    # 自动 Git 提交
    print("📤 自动提交到 GitHub...", end=" ")
    ok, msg = auto_commit()
    print(msg)


def do_search():
    """搜索记忆"""
    try:
        from rag import search as rag_search
        query = input("\n🔍 搜索关键词：")
        results = rag_search(query)
        if not results:
            print("\n📭 没找到相关记录")
            return
        print(f"\n找到 {len(results)} 条相关记录：\n")
        for score, source, content in results:
            print(f"  [{source}] 匹配度:{score}")
            print(f"  {content.strip()[:200]}")
            print(f"  ---")
    except ImportError:
        print("\n⚠️ rag.py 未找到")


def do_ask():
    """AI 问答"""
    try:
        from rag import ask_ai, get_context, search as rag_search
        question = input("\n💬 向 Cyber Mentor 提问：")
        context = get_context(question)
        hit_count = len(rag_search(question))
        print(f"\n🔍 检索到 {hit_count} 条相关记录")
        print("🤖 AI 思考中...\n")
        answer = ask_ai(question, context)
        print(answer)
    except ImportError:
        print("\n⚠️ rag.py 未找到")


def do_stats():
    """学习仪表盘"""
    print_dashboard()


# ═══════════════════════════════════════════════════
# 菜单
# ═══════════════════════════════════════════════════

MENU = {
    "1": ("📖 记录学习", do_record),
    "2": ("📚 查看历史", show_history),
    "3": ("🔍 搜索记忆", do_search),
    "4": ("🤖 AI 问答",   do_ask),
    "5": ("📊 学习统计", do_stats),
    "6": ("👋 退出",     None),
}


def show_menu():
    print("\n" + "─" * 30)
    for key, (label, _) in MENU.items():
        print(f"  {key}. {label}")
    print("─" * 30)


# ═══════════════════════════════════════════════════
# 入口
# ═══════════════════════════════════════════════════

def main():
    # 启动时迁移旧数据
    migrated = migrate_from_txt()
    if migrated > 0:
        print(f"📦 已从旧文件迁移 {migrated} 条记录到数据库")

    # 确保数据库就绪
    init_db()

    welcome()
    show_history()

    while True:
        show_menu()
        choice = input("👉 选择 (1-6)：").strip()

        if choice == "6":
            print("\n👋 再见，记得今天也学点什么！")
            break

        if choice in MENU and MENU[choice][1] is not None:
            MENU[choice][1]()
        else:
            print("\n⚠️ 请输入 1-6")


if __name__ == "__main__":
    main()
