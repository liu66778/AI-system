"""
Cyber RAG v0.3 — 语义检索增强问答
TF-IDF + 中文分词 → 检索更准 → 喂给 AI → 智能回答

用法：
  python rag.py              # 交互式问答
  python rag.py "我学了什么"  # 单次问答
"""
import os
import sys
import re
from math import log
from pathlib import Path
from collections import Counter

# Windows 终端编码修复
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# jieba 可选——没装就回退到简单分词
try:
    import jieba
    JIEBA_OK = True
except ImportError:
    JIEBA_OK = False

# ─── 配置 ──────────────────────────────────
API_KEY = os.getenv("API_KEY", "")
BASE_URL = os.getenv("BASE_URL", "https://api.deepseek.com")
MODEL = os.getenv("MODEL", "deepseek-chat")

PROJECT_DIR = Path(__file__).resolve().parent.parent
BASE_DIR = PROJECT_DIR.parent.parent
DIARY_PATH = BASE_DIR / "Notes" / "Cyber-Diary.md"

_src = str(Path(__file__).resolve().parent)
if _src not in sys.path:
    sys.path.insert(0, _src)


# ═══════════════════════════════════════════════════
# 1. 中文分词 + TF-IDF 检索
# ═══════════════════════════════════════════════════

# 中文停用词
STOPWORDS = set(
    "的 了 在 是 我 有 和 就 不 人 都 一 一个 上 也 很 到 说 要 去 "
    "你 会 着 没有 看 好 自己 这 那 些 什么 怎么 哪 为什么 还 "
    "但 吧 啊 呢 今天 学了 然后 学 可以 把 被 让 从 对 给 用 "
    "所以 因为 如果 虽然 但是 不过 而且 或者 已经 正在 没有 可能 "
    "应该 需要 能够 知道 觉得 希望 开始 继续 完成 之后 之前 以内 "
    "之外 之间 之中 以上 以下 左右 前后 上下".split()
)


def tokenize(text):
    """中文分词"""
    if not text:
        return []
    # 清理标点和空白
    text = re.sub(r'[^\u4e00-\u9fff\w]', ' ', text)
    if JIEBA_OK:
        words = jieba.cut(text)
    else:
        # 回退：直接按空格和字符边界切
        words = []
        for w in text.split():
            w = w.strip()
            if len(w) >= 2:
                words.append(w)
            # 英文词直接加入
            elif len(w) == 1 and w.isascii():
                continue
    return [w.strip() for w in words if len(w.strip()) >= 2 and w.strip().lower() not in STOPWORDS]


def load_diary():
    """加载赛博日记"""
    if not DIARY_PATH.exists():
        return ""
    return DIARY_PATH.read_text(encoding="utf-8")


def load_study_log():
    """从数据库加载学习记录（含标签）"""
    try:
        from database import get_all_records_full
        records = get_all_records_full(limit=200)
        if not records:
            return ""
        lines = []
        for r in records:
            tags_str = ""
            if r.get("tags"):
                tags_str = " [" + ", ".join(f"{t['emoji']}{t['name']}" for t in r["tags"]) + "]"
            lines.append(f"[{r['timestamp']}] 心情:{r['mood']}/10{tags_str}")
            lines.append(f"  {r['content']}")
        return "\n".join(lines)
    except ImportError:
        return ""


def _split_into_docs(text):
    """把文本按段落切分成文档列表"""
    paras = text.split("\n\n")
    docs = []
    for p in paras:
        p = p.strip()
        if p and len(p) > 10:
            docs.append(p)
    return docs


def _build_tfidf(docs):
    """对文档集合构建 TF-IDF 向量

    返回 (doc_vectors, idf_scores, vocabulary)
    """
    if not docs:
        return [], {}, {}

    N = len(docs)
    doc_tokens = [tokenize(d) for d in docs]

    # 文档频率 DF
    df = Counter()
    for tokens in doc_tokens:
        unique = set(tokens)
        for word in unique:
            df[word] += 1

    # IDF
    idf = {}
    for word, cnt in df.items():
        idf[word] = log((N + 1) / (cnt + 1)) + 1  # 平滑

    # TF-IDF 向量
    vectors = []
    for tokens in doc_tokens:
        tf = Counter(tokens)
        vec = {}
        for word, cnt in tf.items():
            if word in idf:
                vec[word] = cnt * idf[word]
        vectors.append(vec)

    return vectors, idf, set(df.keys())


def _cosine_similarity(vec1, vec2):
    """两个稀疏向量的余弦相似度"""
    if not vec1 or not vec2:
        return 0
    dot = sum(vec1.get(k, 0) * vec2.get(k, 0) for k in set(vec1) | set(vec2))
    norm1 = sum(v ** 2 for v in vec1.values()) ** 0.5
    norm2 = sum(v ** 2 for v in vec2.values()) ** 0.5
    if norm1 == 0 or norm2 == 0:
        return 0
    return dot / (norm1 * norm2)


def search(query, top_n=5):
    """TF-IDF 语义检索——主入口"""
    diary = load_diary()
    study_log = load_study_log()

    if not diary and not study_log:
        return []

    # 合并所有来源的文档
    diary_docs = _split_into_docs(diary)
    log_docs = _split_into_docs(study_log)

    all_docs = diary_docs + log_docs
    sources = ["📝 日记"] * len(diary_docs) + ["📖 学习记录"] * len(log_docs)

    if not all_docs:
        return []

    # 构建 TF-IDF
    vectors, _, _ = _build_tfidf(all_docs)

    # 查询向量
    query_tokens = tokenize(query)
    if not query_tokens:
        return []

    q_tf = Counter(query_tokens)

    # 计算 IDF（复用文档集的 IDF）
    N = len(all_docs)
    df = Counter()
    for tokens in [tokenize(d) for d in all_docs]:
        for w in set(tokens):
            df[w] += 1

    q_vec = {}
    for word, cnt in q_tf.items():
        if word in df:
            q_vec[word] = cnt * (log((N + 1) / (df[word] + 1)) + 1)

    # 计算相似度并排序
    scored = []
    for i, doc_vec in enumerate(vectors):
        score = _cosine_similarity(q_vec, doc_vec)
        if score > 0:
            # 同时做关键词兜底，防止语义搜索遗漏精准匹配
            kw_bonus = sum(1 for kw in query_tokens if kw.lower() in all_docs[i].lower())
            score += kw_bonus * 0.3
            scored.append((score, sources[i], all_docs[i][:500]))

    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:top_n]


def get_context(query):
    """获取与查询相关的上下文"""
    hits = search(query)
    if not hits:
        return "（未在日记和学习记录中找到相关内容）"

    lines = []
    for score, source, content in hits:
        lines.append(f"[{source}] 匹配度: {score:.2f}")
        lines.append(content.strip())
        lines.append("---")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════
# 2. AI 问答模块
# ═══════════════════════════════════════════════════

SYSTEM_PROMPT = """你是 Cyber Mentor，刘焕玉的学习伙伴。

你的知识来源是用户的学习日记和记录（会附在下方）。请你：
1. 基于这些记录回答问题
2. 如果记录中没有相关信息，诚实说"你的日记里还没提到这个"
3. 用温暖鼓励的语气，像朋友聊天一样
4. 适当提醒用户坚持学习
5. 用中文回答"""


def ask_ai(question, context):
    """把上下文 + 问题发给 AI"""
    if not API_KEY or API_KEY == "sk-your-api-key-here":
        return (
            "⚠️ 还没配置 API Key！\n\n"
            "1. 去 https://platform.deepseek.com/api_keys 注册获取 key\n"
            "2. 打开 .env 文件，把 API_KEY=你的key\n"
            "3. 重新运行\n\n"
            "（DeepSeek 很便宜，1块钱能用很久）"
        )

    try:
        from openai import OpenAI
    except ImportError:
        return "⚠️ 缺少 openai 库！\n\n在终端运行：pip install openai python-dotenv"

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
    print(f"📚 数据源：日记 + 数据库标签")
    if JIEBA_OK:
        print("🔍 搜索引擎：TF-IDF + jieba 分词")
    else:
        print("🔍 搜索引擎：TF-IDF（建议 pip install jieba 提升分词精度）")
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

        print("🔍 TF-IDF 检索中...", end=" ")
        hits = search(question)
        print(f"找到 {len(hits)} 条相关记录")

        if hits:
            print()  # 空行让输出更干净

        context = get_context(question)

        print("🤖 AI 思考中...")
        answer = ask_ai(question, context)
        print(f"\n{answer}\n")
        print("-" * 45)


def main():
    """支持命令行参数或交互模式"""
    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
        context = get_context(question)
        hits = search(question)
        print(f"🔍 TF-IDF 检索到 {len(hits)} 条记录\n")
        if hits:
            # 显示检索摘要
            for score, source, content in hits[:3]:
                preview = content[:100].replace('\n', ' ')
                print(f"  [{source}] {preview}...")
            print()
        print(ask_ai(question, context))
    else:
        chat()


if __name__ == "__main__":
    main()
