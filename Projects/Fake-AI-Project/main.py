"""
Cyber Mentor v3.0 — 菜单交互版
支持：记录学习 | 查看历史 | 搜索记忆 | AI问答
"""
from datetime import datetime
import os
import sys

# Windows 终端编码修复
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# 把 src 目录加到路径，方便 import rag
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

NAME = "刘焕玉"

# 文件路径
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))  # Fake-AI-Project/
LOG_FILE = os.path.join(PROJECT_DIR, "study_log.txt")
BASE_DIR = os.path.dirname(os.path.dirname(PROJECT_DIR))  # AI-system/
DIARY_PATH = os.path.join(BASE_DIR, "Notes", "Cyber-Diary.md")


# ═══════════════════════════════════════════════════
# 功能函数
# ═══════════════════════════════════════════════════

def welcome():
    """显示欢迎语"""
    print(f"\n👤 {NAME}，欢迎回到 Cyber Mentor")
    print("=" * 40)


def show_history():
    """显示最近学习记录"""
    print("\n📚 历史学习记录：")
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            log = f.read().strip()
            if log:
                lines = log.split("\n")
                recent = lines[-20:] if len(lines) > 20 else lines
                for line in recent:
                    print(f"  {line}")
                count = len([l for l in lines if l.startswith("[")])
                print(f"  ...共 {count} 条记录")
            else:
                print("  （暂无）")
    except FileNotFoundError:
        print("  （暂无）")


def save_study(study, mood):
    """保存学习内容"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"\n[{now}] 心情:{mood}/10\n")
        f.write(f"  {study}\n")


def update_diary(study, mood):
    """写入赛博日记（按日期归档）"""
    today = datetime.now().strftime("%Y-%m-%d")
    diary_path = os.path.normpath(DIARY_PATH)

    already_written = False
    if os.path.exists(diary_path):
        with open(diary_path, "r", encoding="utf-8") as f:
            already_written = today in f.read()

    os.makedirs(os.path.dirname(diary_path), exist_ok=True)

    if not already_written:
        with open(diary_path, "a", encoding="utf-8") as f:
            f.write(f"\n## {today}\n\n")
            f.write(f"- 😊 心情：{mood}/10\n")
            f.write(f"- 📖 学习：{study}\n")
    else:
        with open(diary_path, "a", encoding="utf-8") as f:
            f.write(f"- 📖 补充学习：{study}\n")


def do_record():
    """记录今天的学习"""
    study = input("\n📖 今天学了什么：")
    mood = input("😊 心情如何（1-10）：")
    save_study(study, mood)
    update_diary(study, mood)
    print("\n✅ 记录已保存。继续加油！")


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
        print("\n⚠️ rag.py 未找到，请检查 src/ 目录")


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
        print("\n⚠️ rag.py 未找到，请检查 src/ 目录")


# ═══════════════════════════════════════════════════
# 菜单
# ═══════════════════════════════════════════════════

MENU = {
    "1": ("📖 记录学习", do_record),
    "2": ("📚 查看历史", show_history),
    "3": ("🔍 搜索记忆", do_search),
    "4": ("🤖 AI 问答", do_ask),
    "5": ("👋 退出", None),
}


def show_menu():
    print("\n" + "─" * 30)
    for key, (label, _) in MENU.items():
        print(f"  {key}. {label}")
    print("─" * 30)


def main():
    welcome()
    show_history()

    while True:
        show_menu()
        choice = input("👉 选择 (1-5)：").strip()

        if choice == "5":
            print("\n👋 再见，记得今天也学点什么！")
            break

        if choice in MENU and MENU[choice][1] is not None:
            MENU[choice][1]()
        else:
            print("\n⚠️ 请输入 1-5")


if __name__ == "__main__":
    main()
