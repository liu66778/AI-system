"""
Cyber RAG v0.1 — 简易检索系统
读取日记和学习记录，按关键词匹配，返回相关内容
"""
import os

# 文件路径
DIARY_PATH = r"C:\Users\Administrator\Desktop\AI-system\Notes\Cyber-Diary.md"
STUDY_LOG_PATH = r"C:\Users\Administrator\Desktop\AI-system\Projects\Fake-AI-Project\study_log.txt"


def load_diary():
    """加载赛博日记"""
    if not os.path.exists(DIARY_PATH):
        return ""
    with open(DIARY_PATH, "r", encoding="utf-8") as f:
        return f.read()


def load_study_log():
    """加载学习记录"""
    if not os.path.exists(STUDY_LOG_PATH):
        return ""
    with open(STUDY_LOG_PATH, "r", encoding="utf-8") as f:
        return f.read()


def search(query, top_n=5):
    """根据关键词从日记和记录中检索相关内容"""
    diary = load_diary()
    study_log = load_study_log()

    # 把日记按日期拆成段落
    diary_sections = diary.split("\n## ")
    # 把学习记录按时间戳拆成段落
    study_sections = study_log.split("\n[")

    results = []

    keywords = query.lower().split()

    # 检索日记
    for section in diary_sections:
        if not section.strip():
            continue
        score = sum(1 for kw in keywords if kw in section.lower())
        if score > 0:
            results.append((score, "📝 日记", section[:300]))

    # 检索学习记录
    for section in study_sections:
        if not section.strip():
            continue
        score = sum(1 for kw in keywords if kw in section.lower())
        if score > 0:
            results.append((score, "📖 学习", section[:200]))

    # 按匹配度排序，取 Top N
    results.sort(key=lambda x: x[0], reverse=True)
    return results[:top_n]


def get_context(query):
    """获取与查询相关的上下文，用于喂给模型"""
    hits = search(query)
    if not hits:
        return "（未找到相关记录）"

    lines = []
    for score, source, content in hits:
        lines.append(f"[{source}] 匹配度:{score}")
        lines.append(content.strip())
        lines.append("---")
    return "\n".join(lines)


# ===== 命令行测试 =====
if __name__ == "__main__":
    query = input("🔍 搜索你的记忆库：")
    print("\n" + "=" * 50)
    print(get_context(query))
    print("=" * 50)
