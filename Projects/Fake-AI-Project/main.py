"""
Cyber Mentor v4.1 — 数据库版 + 标签分类 + TF-IDF 语义搜索
SQLite 存储 + 学习仪表盘 + 自动 Git 提交 + 标签系统
"""
from datetime import datetime
import os
import sys

# Windows 终端编码修复
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from database import (
    init_db, migrate_from_txt, add_record, get_all_records,
    has_today_record, get_all_tags, get_tag_stats,
    get_records_by_tag, search_records_multi
)
from stats import print_dashboard
from git_auto import auto_commit

NAME = "刘焕玉"

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(os.path.dirname(PROJECT_DIR))
DIARY_PATH = os.path.join(BASE_DIR, "Notes", "Cyber-Diary.md")


# ═══════════════════════════════════════════════════
# 功能函数
# ═══════════════════════════════════════════════════

def welcome():
    print(f"\n👤 {NAME}，欢迎回到 Cyber Mentor v4.1")
    print("=" * 40)


def show_history():
    """从数据库读取最近记录（含标签）"""
    print("\n📚 最近学习记录：")
    records = get_all_records(limit=20)
    if not records:
        print("  （暂无）")
        return

    from database import get_tags_for_record
    for r in reversed(records):
        mood_icon = {1:"😫", 2:"😣", 3:"😐", 4:"🙂", 5:"😊",
                     6:"😄", 7:"🤩", 8:"🎉", 9:"🔥", 10:"💯"}.get(r["mood"], "😊")
        tags = get_tags_for_record(r["id"])
        tag_str = ""
        if tags:
            tag_str = " " + " ".join(f"{t['emoji']}{t['name']}" for t in tags)
        print(f"  [{r['timestamp']}] {mood_icon}{tag_str} {r['content'][:60]}")

    total = len(get_all_records(limit=9999))
    print(f"  ...共 {total} 条记录")


def pick_tags():
    """让用户选择标签"""
    tags = get_all_tags()
    if not tags:
        return []

    print("\n🏷️  选择标签（输入编号，多个用空格分隔，回车跳过）：")
    for i, t in enumerate(tags, 1):
        print(f"  {i}. {t['emoji']} {t['name']}")

    choice = input("👉 标签：").strip()
    if not choice:
        return []

    selected = []
    for part in choice.split():
        try:
            idx = int(part) - 1
            if 0 <= idx < len(tags):
                selected.append(tags[idx]["id"])
        except ValueError:
            pass
    return selected


def update_diary(content, mood, tags=None):
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
            if tags:
                tag_names = [t["name"] for t in get_all_tags() if t["id"] in tags]
                f.write(f"- 🏷️  标签：{'、'.join(tag_names)}\n")
            f.write(f"- 📖 学习：{content}\n")
    else:
        with open(diary_path, "a", encoding="utf-8") as f:
            f.write(f"- 📖 补充学习：{content}\n")


def do_record():
    """记录今天的学习（含标签选择）"""
    today_already = has_today_record()
    if today_already:
        print("\n📌 你今天已经记录过了，可以追加")

    study = input("\n📖 今天学了什么：")
    if not study.strip():
        print("⚠️ 内容不能为空")
        return

    tags = pick_tags()

    mood = input("😊 心情如何（1-10）：")
    try:
        mood = int(mood)
        if mood < 1 or mood > 10:
            mood = 5
    except ValueError:
        mood = 5

    add_record(study, mood, tag_ids=tags if tags else None)
    update_diary(study, mood, tags if tags else None)

    if tags:
        tag_names = [t["name"] for t in get_all_tags() if t["id"] in tags]
        print(f"\n✅ 记录已保存！标签：{'、'.join(tag_names)}")
    else:
        print("\n✅ 记录已保存！")

    print("📤 自动提交到 GitHub...", end=" ")
    ok, msg = auto_commit()
    print(msg)


def do_search():
    """搜索记忆（支持标签筛选 + TF-IDF）"""
    print("\n🔍 搜索方式：")
    print("  1. 关键词搜索（模糊匹配）")
    print("  2. 按标签筛选")
    print("  3. AI 语义搜索（TF-IDF + DeepSeek）")
    mode = input("👉 选 (1-3，回车默认1)：").strip() or "1"

    if mode == "2":
        tags = get_all_tags()
        if not tags:
            print("⚠️ 暂无标签")
            return
        print()
        for i, t in enumerate(tags, 1):
            print(f"  {i}. {t['emoji']} {t['name']}")
        choice = input("\n👉 选标签编号：").strip()
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(tags):
                records = get_records_by_tag(tags[idx]["id"])
                if not records:
                    print(f"\n📭 {tags[idx]['emoji']}{tags[idx]['name']} 标签下暂无记录")
                    return
                print(f"\n🏷️  {tags[idx]['emoji']}{tags[idx]['name']} 相关记录：")
                for r in reversed(records):
                    mood_icon = {1:"😫", 2:"😣", 3:"😐", 4:"🙂", 5:"😊",
                                 6:"😄", 7:"🤩", 8:"🎉", 9:"🔥", 10:"💯"}.get(r["mood"], "😊")
                    print(f"  [{r['timestamp']}] {mood_icon} {r['content'][:80]}")
            else:
                print("⚠️ 无效编号")
        except ValueError:
            print("⚠️ 请输入数字")

    elif mode == "3":
        print()
        try:
            from rag import search as rag_search
            query = input("💬 输入查询：")
            results = rag_search(query)
            if not results:
                print("\n📭 没找到相关记录")
                return
            print(f"\n🔍 找到 {len(results)} 条相关记录：\n")
            for score, source, content in results:
                print(f"  [{source}] 匹配度:{score:.2f}")
                print(f"  {content.strip()[:200]}")
                print(f"  ---")
        except ImportError:
            print("\n⚠️ rag.py 未找到")

    else:
        keywords = input("\n🔍 输入关键词（空格分隔）：").strip()
        if not keywords:
            return
        kws = keywords.split()
        records = search_records_multi(kws)
        if not records:
            print(f"\n📭 未找到与 '{keywords}' 相关的记录")
            return
        print(f"\n🔍 关键词 '{keywords}' 匹配到 {len(records)} 条记录：")
        from database import get_tags_for_record
        for r in reversed(records):
            tags = get_tags_for_record(r["id"])
            tag_str = " ".join(f"{t['emoji']}{t['name']}" for t in tags) if tags else ""
            print(f"  [{r['timestamp']}] {r['content'][:80]}{'  '+tag_str if tag_str else ''}")


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


def main():
    migrated = migrate_from_txt()
    if migrated > 0:
        print(f"📦 已从旧文件迁移 {migrated} 条记录到数据库")

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
