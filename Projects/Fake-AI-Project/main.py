"""
Cyber Mentor v2.0 — 赛博导师
记录学习 + 心情 + 每日总结
"""
from datetime import datetime
import os

# ===== 身份 =====
NAME = "刘焕玉"
print(f"👤 {NAME}，欢迎回到 Cyber Mentor")
print("=" * 40)

# ===== 1. 显示历史学习记录 =====
print("\n📚 历史学习记录：")
try:
    with open("study_log.txt", "r", encoding="utf-8") as f:
        log = f.read().strip()
        if log:
            lines = log.split("\n")
            # 只显示最近的 10 条
            recent = lines[-20:] if len(lines) > 20 else lines
            for line in recent:
                print(f"  {line}")
            print(f"  ...共 {len([l for l in lines if l.startswith('[')])} 条记录")
        else:
            print("  （暂无）")
except FileNotFoundError:
    print("  （暂无）")

# ===== 2. 记录今日学习 =====
study = input("\n📖 今天学了什么：")
mood = input("😊 心情如何（1-10）：")

# 保存学习记录
now = datetime.now()
time_str = now.strftime("%Y-%m-%d %H:%M:%S")
with open("study_log.txt", "a", encoding="utf-8") as f:
    f.write(f"\n[{time_str}] 心情:{mood}/10\n")
    f.write(f"  {study}\n")

# ===== 3. 写入赛博日记 =====
today = now.strftime("%Y-%m-%d")
diary_path = "../Notes/Cyber-Diary.md"

# 检查今天是否已写过
already_written = False
if os.path.exists(diary_path):
    with open(diary_path, "r", encoding="utf-8") as f:
        already_written = today in f.read()

if not already_written:
    with open(diary_path, "a", encoding="utf-8") as f:
        f.write(f"\n## {today}\n\n")
        f.write(f"- 😊 心情：{mood}/10\n")
        f.write(f"- 📖 学习：{study}\n")
    print("\n📝 赛博日记已更新！")
else:
    # 追加到今天的条目
    with open(diary_path, "a", encoding="utf-8") as f:
        f.write(f"- 📖 补充学习：{study}\n")

print("\n✅ 记录已保存。继续加油！")
