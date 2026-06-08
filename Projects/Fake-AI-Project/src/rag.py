"""
Cyber RAG v0.2 — 检索增强问答
从你的日记/学习记录中检索相关内容 → 喂给 AI → 得到智能回答

用法：
  python rag.py              # 交互式问答
  python rag.py "我学了什么"  # 单次问答
"""
import os
import sys
from pathlib import Path

# Windows 终端编码修复
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# 尝试加载 .env，没装 python-dotenv 也不炸
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ─── 配置（优先环境变量，其次 .env）──────────────
API_KEY = os.getenv("API_KEY", "")
BASE_URL = os.getenv("BASE_URL", "https://api.deepseek.com")
MODEL = os.getenv("MODEL", "deepseek-chat")

# 文件路径
# rag.py 在 Fake-AI-Project/src/ 下
PROJECT_DIR = Path(__file__).resolve().parent.parent  # Fake-AI-Project/
BASE_DIR = PROJECT_DIR.parent.parent  # AI-system/
DIARY_PATH = BASE_DIR / "Notes" / "Cyber-Diary.md"

# 确保 src 在 path 中（独立运行时也能导入同目录模块）
_src = str(Path(__file__).resolve().parent)
if _src not in sys.path:
    sys.path.insert(0, _src)


# ═══════════════════════════════════════════════════
# 1. 检索模块（从 v0.1 保留）
# ═══════════════════════════════════════════════════

def load_diary():
    """加载赛博日记"""
    if not DIARY_PATH.exists():
        return ""
    return DIARY_PATH.read_text(encoding="utf-8")


def load_study_log():
    """从数据库加载学习记录"""
    try:
        from database import get_all_records
        records = get_all_records(limit=200)
        lines = []
        for r in reversed(records):
            lines.append(f"[{r['timestamp']}] 心情:{r['mood']}/10")
            lines.append(f"  {r['content']}")
        return "\n".join(lines)
    except ImportError:
        return ""


def search(query, top_n=5):
    """根据关键词从日记和记录中检索相关内容"""
    diary = load_diary()
    study_log = load_study_log()

    diary_sections = diary.split("\n## ")
    study_sections = study_log.split("\n[")

    results = []
    keywords = query.lower().split()

    for section in diary_sections:
        if not section.strip():
            continue
        score = sum(1 for kw in keywords if kw in section.lower())
        if score > 0:
            results.append((score, "📝 日记", section[:400]))

    for section in study_sections:
        if not section.strip():
            continue
        score = sum(1 for kw in keywords if kw in section.lower())
        if score > 0:
            results.append((score, "📖 学习记录", section[:300]))

    results.sort(key=lambda x: x[0], reverse=True)
    return results[:top_n]


def get_context(query):
    """获取与查询相关的上下文，用于喂给 AI"""
    hits = search(query)
    if not hits:
        return "（未在日记和学习记录中找到相关内容）"

    lines = []
    for score, source, content in hits:
        lines.append(f"[{source}] 匹配度: {score}")
        lines.append(content.strip())
        lines.append("---")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════
# 2. AI 问答模块（v0.2 新增）
# ═══════════════════════════════════════════════════

SYSTEM_PROMPT = """你是 Cyber Mentor，刘焕玉的学习伙伴。

你的知识来源是用户的学习日记和记录（会附在下方）。请你：
1. 基于这些记录回答问题
2. 如果记录中没有相关信息，诚实说"你的日记里还没提到这个"
3. 用温暖鼓励的语气，像朋友聊天一样
4. 适当提醒用户坚持学习
5. 用中文回答"""


def ask_ai(question, context):
    """
    把上下文 + 问题发给 AI，返回回答
    需要先配置 API_KEY！
    """
    if not API_KEY or API_KEY == "sk-your-api-key-here":
        return (
            "⚠️ 还没配置 API Key！\n\n"
            "1. 去 https://platform.deepseek.com/api_keys 注册获取 key\n"
            "2. 打开 .env 文件，把 API_KEY= 后面改成你的 key\n"
            "3. 重新运行\n\n"
            "（DeepSeek 很便宜，1块钱能用很久）"
        )

    try:
        from openai import OpenAI
    except ImportError:
        return (
            "⚠️ 缺少 openai 库！\n\n"
            "在终端运行：pip install openai python-dotenv"
        )

    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

    full_context = (
        f"以下是刘焕玉的学习日记和记录：\n\n{context}"
        if "未在" not in context
        else "用户目前的学习日记中内容还不多。"
    )

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "system", "content": full_context},
                {"role": "user", "content": question},
            ],
            temperature=0.7,
            max_tokens=1000,
        )
        return response.choices[0].message.content

    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg or "auth" in error_msg.lower():
            return "⚠️ API Key 无效，请检查 .env 中的 API_KEY"
        elif "timeout" in error_msg.lower():
            return "⚠️ 请求超时，检查网络或换一个 API 地址"
        else:
            return f"⚠️ AI 调用出错：{error_msg}"


# ═══════════════════════════════════════════════════
# 3. 交互入口
# ═══════════════════════════════════════════════════

def chat():
    """交互式问答循环"""
    print("🧠 Cyber Mentor 智能问答（输入 quit 退出）")
    print("=" * 45)
    print(f"📚 数据源：日记 + 数据库")
    if not API_KEY or API_KEY == "sk-your-api-key-here":
        print("⚠️  API 未配置（问答会提示错误）")
    print()

    while True:
        try:
            question = input("💬 你想问什么：").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 再见！")
            break

        if not question:
            continue
        if question.lower() in ("quit", "退出", "q"):
            print("👋 再见！")
            break

        print("🔍 检索记忆中...", end=" ")
        context = get_context(question)
        hit_count = len(search(question))
        print(f"找到 {hit_count} 条相关记录")

        print("🤖 AI 思考中...")
        answer = ask_ai(question, context)
        print(f"\n{answer}\n")
        print("-" * 45)


def main():
    """支持命令行参数或交互模式"""
    if len(sys.argv) > 1:
        # 命令行模式：python rag.py "我学了什么"
        question = " ".join(sys.argv[1:])
        context = get_context(question)
        print(f"🔍 检索到 {len(search(question))} 条记录\n")
        print(ask_ai(question, context))
    else:
        chat()


if __name__ == "__main__":
    main()
