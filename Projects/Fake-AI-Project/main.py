"""
Cyber Mentor v2.0.5 — 函数化重构版
每个功能一个函数，各司其职
"""
from datetime import datetime
import os

NAME = "刘焕玉"

# ==================== 函数区 ====================

def welcome():
    """显示欢迎语和身份"""
    print(f"👤 {NAME}，欢迎回到 Cyber Mentor")
    print("=" * 40)


def show_history():
    """读取 study_log.txt，显示最近 10 条记录"""
    print("\n📚 历史学习记录：")
    try:
        with open("study_log.txt", "r", encoding="utf-8") as f:
            log = f.read().strip()
            if log:
                lines = log.split("\n")
                recent = lines[-20:] if len(lines) > 20 else lines
                for line in recent:
                    print(f"  {line}")
                # 统计总记录数
                count = len([l for l in lines if l.startswith("[")])
                print(f"  ...共 {count} 条记录")
            else:
                print("  （暂无）")
    except FileNotFoundError:
        print("  （暂无）")


def save_study(study, mood):
    """保存学习内容到 study_log.txt"""
    now = datetime.now()
    time_str = now.strftime("%Y-%m-%d %H:%M:%S")
    with open("study_log.txt", "a", encoding="utf-8") as f:
        f.write(f"\n[{time_str}] 心情:{mood}/10\n")
        f.write(f"  {study}\n")


def update_diary(study, mood):
    """把今天的学习内容写入赛博日记"""
    today = datetime.now().strftime("%Y-%m-%d")
    diary_path = "../Notes/Cyber-Diary.md"

    # 检查今天是否已经写过
    already_written = False
    if os.path.exists(diary_path):
        with open(diary_path, "r", encoding="utf-8") as f:
            already_written = today in f.read()

    if not already_written:
        # 新建今天的日记
        with open(diary_path, "a", encoding="utf-8") as f:
            f.write(f"\n## {today}\n\n")
            f.write(f"- 😊 心情：{mood}/10\n")
            f.write(f"- 📖 学习：{study}\n")
        print("\n📝 赛博日记已更新！")
    else:
        # 追加到今天的条目
        with open(diary_path, "a", encoding="utf-8") as f:
            f.write(f"- 📖 补充学习：{study}\n")


# ==================== 主程序 ====================

def main():
    """总调度：按顺序调用各个功能"""
    welcome()           # 1. 打招呼
    show_history()      # 2. 看历史
    study = input("\n📖 今天学了什么：")
    mood = input("😊 心情如何（1-10）：")
    save_study(study, mood)      # 3. 保存
    update_diary(study, mood)    # 4. 写日记
    print("\n✅ 记录已保存。继续加油！")


# 只有直接运行时才执行，被 import 时不会跑
if __name__ == "__main__":
    main()
