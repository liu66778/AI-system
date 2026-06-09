"""
统计分析模块 — 学习仪表盘
从数据库提取数据，算连续天数/心情趋势/高频主题/标签分布
"""
from datetime import datetime, timedelta
from collections import Counter
import re
from database import (
    get_distinct_dates, get_mood_stats, get_all_records,
    get_total_count, has_today_record, get_tag_stats
)


def get_total_days():
    return len(get_distinct_dates())


def get_current_streak():
    """连续学习天数（从今天往回数）"""
    dates = set(get_distinct_dates())
    if not dates:
        return 0
    today = datetime.now().strftime("%Y-%m-%d")
    check = datetime.now() if today in dates else datetime.now() - timedelta(days=1)
    streak = 0
    while check.strftime("%Y-%m-%d") in dates:
        streak += 1
        check -= timedelta(days=1)
    return streak


def get_longest_streak():
    """历史最长连续天数"""
    dates = sorted(set(get_distinct_dates()))
    if not dates:
        return 0
    longest = 1
    current = 1
    for i in range(1, len(dates)):
        prev = datetime.strptime(dates[i-1], "%Y-%m-%d")
        curr = datetime.strptime(dates[i], "%Y-%m-%d")
        if (curr - prev).days == 1:
            current += 1
            longest = max(longest, current)
        else:
            current = 1
    return longest


def get_avg_mood():
    data = get_mood_stats()
    if not data:
        return 0
    return round(sum(m[1] for m in data) / len(data), 1)


def get_top_themes(n=5):
    """高频学习主题（简易中文分词）"""
    records = get_all_records(limit=200)
    stopwords = {
        '的','了','在','是','我','有','和','就','不','人','都','一',
        '一个','上','也','很','到','说','要','去','你','会','着',
        '没有','看','好','自己','这','那','些','什么','怎么','哪',
        '为什么','还','但','吧','啊','呢','今天','学了','然后','学'
    }
    words = []
    for r in records:
        text = re.sub(r'[^\u4e00-\u9fff\w]', ' ', r['content'])
        for w in text.split():
            if len(w) >= 2 and w not in stopwords:
                words.append(w)
    return Counter(words).most_common(n)


def get_weekly_summary():
    """本周概览"""
    today = datetime.now()
    week_start = today - timedelta(days=today.weekday())
    dates = get_distinct_dates()
    week_dates = [d for d in dates if d >= week_start.strftime("%Y-%m-%d")]

    return {
        "today_studied": has_today_record(),
        "week_days": len(week_dates),
        "total_days": len(dates),
        "streak": get_current_streak(),
        "longest_streak": get_longest_streak(),
        "avg_mood": get_avg_mood(),
        "total_records": get_total_count(),
        "top_themes": get_top_themes(5),
        "tag_stats": get_tag_stats(),
        "mood_trend": get_mood_stats(),
    }


def mood_bar(value):
    """心情可视化条"""
    filled = "█" * int(value)
    empty = "░" * (10 - int(value))
    return f"{filled}{empty} {value}/10"


def print_dashboard():
    """终端仪表盘（含标签分布）"""
    s = get_weekly_summary()
    today_tag = "✅ 已记录" if s["today_studied"] else "❌ 还没记录"

    print(f"""
╔══════════════════════════════════╗
║     📊 Cyber Mentor 学习仪表盘     ║
╠══════════════════════════════════╣
║  📅 今天：{today_tag:<14}        ║
║  🔥 连续：{s['streak']} 天                       ║
║  🏆 最长连续：{s['longest_streak']} 天                   ║
║  📚 累计学习：{s['total_days']} 天                   ║
║  📝 累计记录：{s['total_records']} 条                   ║
║  😊 平均心情：{mood_bar(s['avg_mood'])}  ║""")

    # 标签分布
    if s["tag_stats"]:
        print("╠══════════════════════════════════╣")
        print("║  🏷️  标签分布                       ║")
        for tag in s["tag_stats"]:
            bar_len = min(tag["count"], 10)
            bar = "█" * bar_len + "░" * (10 - bar_len)
            print(f"║  {tag['emoji']} {tag['name']:<6} {bar} {tag['count']:>3}次    ║")

    # 高频主题
    if s["top_themes"]:
        print("╠══════════════════════════════════╣")
        print("║  📈 高频主题                       ║")
        for theme, count in s["top_themes"]:
            bar = "█" * min(count, 15)
            print(f"║    {theme:<10} {bar} {count}次{'':<8}║")

    # 心情趋势
    if s["mood_trend"]:
        print("╠══════════════════════════════════╣")
        print("║  📈 心情趋势                       ║")
        for date, mood in s["mood_trend"][-7:]:
            tag = " ←今天" if date == datetime.now().strftime("%Y-%m-%d") else ""
            bar = "█" * int(mood) + "░" * (10 - int(mood))
            print(f"║  {date[-5:]} {bar} {mood}{tag:<8}║")

    print("╚══════════════════════════════════╝")
