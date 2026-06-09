"""
Cyber Quant v2.0 — 多智能体 AI 量化分析平台
部署版：Streamlit Cloud 直接可跑
"""
import streamlit as st
import pandas as pd
import json
from pathlib import Path
from datetime import datetime
import urllib.request

# 本地 Gate.io 数据模块（从 TradingAgents 提取）
from gate_io import _fetch_candles, _resolve_pair

st.set_page_config(page_title="Cyber Quant", page_icon="🚀", layout="wide")

LOGS_DIR = Path(__file__).parent / "logs"
RATING_SCORE = {"Buy": 3, "Overweight": 1, "Hold": 0, "Underweight": -1, "Sell": -3}
RATING_EMOJI = {"Buy": "🟢", "Overweight": "🟡", "Hold": "⚪", "Underweight": "🟠", "Sell": "🔴"}

# ─── 数据 ──────────────────────────────────────

@st.cache_data(ttl=60, show_spinner=False)
def get_live_prices():
    """Gate.io 实时价格"""
    prices = {}
    for pair, ticker in [("BTC_USDT", "BTC"), ("ETH_USDT", "ETH"), ("SOL_USDT", "SOL")]:
        try:
            url = f"https://api.gateio.ws/api/v4/spot/tickers?currency_pair={pair}"
            resp = urllib.request.urlopen(url, timeout=5)
            data = json.loads(resp.read().decode())[0]
            prices[ticker] = {
                "price": float(data["last"]),
                "change": float(data["change_percentage"]),
                "high": float(data["high_24h"]),
                "low": float(data["low_24h"]),
                "volume": float(data["quote_volume"]),
            }
        except Exception:
            prices[ticker] = None
    return prices


@st.cache_data(ttl=300, show_spinner="加载历史记录...")
def load_history():
    """解析所有历史分析日志"""
    records = []
    if not LOGS_DIR.exists():
        return records

    for log_file in sorted(LOGS_DIR.rglob("full_states_log_*.json")):
        try:
            ticker = log_file.parent.parent.name
            date_str = log_file.stem.replace("full_states_log_", "")
            data = json.loads(log_file.read_text(encoding="utf-8"))

            decision = data.get("final_trade_decision", "")
            rating = "Unknown"
            for r in ["Buy", "Overweight", "Hold", "Underweight", "Sell"]:
                if r in decision:
                    rating = r
                    break

            records.append({
                "date": date_str,
                "ticker": ticker.replace("USD", ""),
                "rating": rating,
                "score": RATING_SCORE.get(rating, 0),
                "result": "⏳",
                "market": data.get("market_report", ""),
                "sentiment": data.get("sentiment_report", ""),
                "news": data.get("news_report", ""),
                "fundamentals": data.get("fundamentals_report", ""),
                "investment_plan": data.get("investment_plan", ""),
                "trader_plan": data.get("trader_investment_decision", ""),
                "decision": data.get("final_trade_decision", ""),
                "invest_debate": data.get("investment_debate_state", {}),
                "risk_debate": data.get("risk_debate_state", {}),
            })
        except Exception:
            continue

    records.sort(key=lambda x: x["date"])
    evaluate_results(records)
    return records


def evaluate_results(records):
    """用 Gate.io 真实价格验证信号"""
    price_cache = {}
    for rec in records:
        pair = _resolve_pair("BTCUSD" if rec["ticker"] == "BTC" else "ETHUSD")
        if pair not in price_cache:
            try:
                df = _fetch_candles(pair, limit=365)
                price_cache[pair] = df
            except Exception:
                continue

        df = price_cache[pair]
        entry_date = pd.Timestamp(rec["date"])
        exit_date = entry_date + pd.Timedelta(days=7)
        subset = df[(df.index >= entry_date) & (df.index <= exit_date)]
        if len(subset) >= 2:
            entry_price = float(subset["Close"].iloc[0])
            exit_price = float(subset["Close"].iloc[-1])
            direction = "UP" if exit_price > entry_price else "DOWN"
            rec["entry_price"] = entry_price
            rec["exit_price"] = exit_price
            rec["direction"] = direction
            rec["change_pct"] = (exit_price - entry_price) / entry_price * 100

            if rec["score"] > 0 and direction == "UP":
                rec["result"] = "✅"; rec["correct"] = True
            elif rec["score"] < 0 and direction == "DOWN":
                rec["result"] = "✅"; rec["correct"] = True
            elif rec["score"] == 0:
                rec["result"] = "➖"
            else:
                rec["result"] = "❌"; rec["correct"] = False


# ─── UI 组件 ────────────────────────────────────

def show_debate_dialog(bull_args, bear_args, judge=""):
    """多空辩论"""
    if not bull_args and not bear_args:
        return
    for i in range(max(len(bull_args), len(bear_args))):
        cols = st.columns(2)
        with cols[0]:
            if i < len(bull_args):
                text = bull_args[i][:600]
                st.markdown(f"🐂 **多头** 第{i+1}轮\n\n{text}")
        with cols[1]:
            if i < len(bear_args):
                text = bear_args[i][:600]
                st.markdown(f"🐻 **空头** 第{i+1}轮\n\n{text}")
        st.divider()
    if judge:
        with st.expander("⚖️ 裁判裁决", expanded=False):
            st.markdown(judge[:2000])


def show_risk_debate(debate_state):
    """风控三方辩论"""
    history = debate_state.get("history", [])
    aggressive, conservative, neutral = [], [], []
    for msg in history:
        content = msg.get("content", "") if isinstance(msg, dict) else str(msg)
        name = msg.get("name", "") if isinstance(msg, dict) else ""
        if "aggressive" in name.lower() or "激进" in name:
            aggressive.append(content)
        elif "conservative" in name.lower() or "保守" in name:
            conservative.append(content)
        else:
            neutral.append(content)

    for i in range(max(len(aggressive), len(conservative), len(neutral))):
        cols = st.columns(3)
        with cols[0]:
            if i < len(aggressive):
                text = aggressive[i][:400]
                st.markdown(f"🟢 **激进派**\n\n{text}")
        with cols[1]:
            if i < len(neutral):
                text = neutral[i][:400]
                st.markdown(f"🟡 **中立派**\n\n{text}")
        with cols[2]:
            if i < len(conservative):
                text = conservative[i][:400]
                st.markdown(f"🔴 **保守派**\n\n{text}")
        st.divider()

    judge = debate_state.get("judge_decision", "")
    if judge:
        with st.expander("⚖️ 风控经理裁决", expanded=False):
            st.markdown(judge[:2000])


# ─── 侧边栏 ────────────────────────────────────

with st.sidebar:
    st.title("🚀 Cyber Quant")
    st.caption("多智能体 AI 量化平台")
    st.caption("[GitHub](https://github.com/liu66778/cyber-quant)")
    page = st.radio("导航", ["📊 仪表盘", "📚 历史记录", "📖 分析详情"])

# ═══════════════════════════════════════════════
# 仪表盘
# ═══════════════════════════════════════════════
if page == "📊 仪表盘":
    st.title("📊 交易仪表盘")

    prices = get_live_prices()
    history = load_history()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        btc = prices.get("BTC")
        delta_str = f"{btc['change']:+.2f}%" if btc else "—"
        st.metric("BTC/USDT", f"${btc['price']:,.0f}" if btc else "—", delta_str)
    with col2:
        eth = prices.get("ETH")
        delta_str = f"{eth['change']:+.2f}%" if eth else "—"
        st.metric("ETH/USDT", f"${eth['price']:,.0f}" if eth else "—", delta_str)
    with col3:
        sol = prices.get("SOL")
        delta_str = f"{sol['change']:+.2f}%" if sol else "—"
        st.metric("SOL/USDT", f"${sol['price']:,.2f}" if sol else "—", delta_str)
    with col4:
        correct = sum(1 for r in history if r.get("correct"))
        calls = sum(1 for r in history if r["score"] != 0)
        win_rate = f"{correct}/{calls}" if calls else "—"
        st.metric("方向胜率", win_rate, f"{len(history)} 次")

    st.divider()

    if prices:
        st.subheader("📈 24h 行情")
        cols2 = st.columns(3)
        for i, key in enumerate(["BTC", "ETH", "SOL"]):
            data = prices.get(key)
            if data:
                with cols2[i]:
                    st.markdown(
                        f"**{key}**  "
                        f"高: ${data['high']:,.0f} | "
                        f"低: ${data['low']:,.0f} | "
                        f"量: ${data['volume']:,.0f}"
                    )

    st.divider()

    if history:
        latest = history[-1]
        st.subheader(f"📡 最新信号：{latest['ticker']} {latest['date']}")
        emoji = RATING_EMOJI.get(latest["rating"], "❓")
        st.info(f"{emoji} **{latest['rating']}**\n\n{latest['decision'][:400]}...")

        st.subheader("📉 信号历史")
        df = pd.DataFrame([{
            "日期": r["date"], "币种": r["ticker"], "评级": r["rating"],
            "入场": f"${r.get('entry_price',0):,.0f}" if r.get("entry_price") else "—",
            "7天后": f"${r.get('exit_price',0):,.0f}" if r.get("exit_price") else "—",
            "涨跌": f"{r.get('change_pct',0):+.1f}%" if r.get("change_pct") else "—",
            "结果": r["result"],
        } for r in reversed(history[-10:])])
        st.dataframe(df, use_container_width=True, hide_index=True)

# ═══════════════════════════════════════════════
# 历史记录
# ═══════════════════════════════════════════════
elif page == "📚 历史记录":
    st.title("📚 历史分析记录")

    history = load_history()
    if not history:
        st.warning("暂无分析记录")
    else:
        df = pd.DataFrame([{
            "日期": r["date"], "币种": r["ticker"], "评级": r["rating"],
            "入场": f"${r.get('entry_price',0):,.0f}" if r.get("entry_price") else "—",
            "7天后": f"${r.get('exit_price',0):,.0f}" if r.get("exit_price") else "—",
            "涨跌": f"{r.get('change_pct',0):+.1f}%" if r.get("change_pct") else "—",
            "结果": r["result"],
        } for r in reversed(history)])
        st.dataframe(df, use_container_width=True, hide_index=True)

# ═══════════════════════════════════════════════
# 分析详情
# ═══════════════════════════════════════════════
elif page == "📖 分析详情":
    st.title("📖 分析详情")

    history = load_history()
    if not history:
        st.warning("暂无记录")
    else:
        options = [f"{r['date']} {r['ticker']} — {r['rating']} {r['result']}" for r in reversed(history)]
        selected = st.selectbox("选择一条记录", options)
        idx = options.index(selected)
        rec = list(reversed(history))[idx]

        emoji = RATING_EMOJI.get(rec["rating"], "❓")

        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("日期", rec["date"])
        with col2:
            st.metric("币种", rec["ticker"])
        with col3:
            st.metric("评级", f"{emoji} {rec['rating']}")
        with col4:
            if rec.get("entry_price"):
                st.metric("入场", f"${rec['entry_price']:,.0f}")
        with col5:
            if rec.get("change_pct") is not None:
                st.metric("7天后", f"${rec['exit_price']:,.0f}", delta=f"{rec['change_pct']:+.1f}%")

        st.divider()

        tabs = st.tabs([
            "📈 技术分析", "💬 市场情绪", "📰 新闻分析",
            "📊 基本面", "🐂🐻 多空辩论", "🛡️ 风控辩论", "💰 最终决策"
        ])

        with tabs[0]:
            st.markdown(rec.get("market", "—")[:12000] or "暂无")

        with tabs[1]:
            st.markdown(rec.get("sentiment", "—")[:12000] or "暂无")

        with tabs[2]:
            st.markdown(rec.get("news", "—")[:12000] or "暂无")

        with tabs[3]:
            st.markdown(rec.get("fundamentals", "—")[:8000] or "暂无")

        with tabs[4]:
            debate = rec.get("invest_debate", {})
            if debate:
                bull = debate.get("bull_history", [])
                bear = debate.get("bear_history", [])
                bull_texts = [m.get("content", str(m)) if isinstance(m, dict) else str(m)
                              for m in bull if len(str(m)) > 20]
                bear_texts = [m.get("content", str(m)) if isinstance(m, dict) else str(m)
                              for m in bear if len(str(m)) > 20]
                show_debate_dialog(
                    bull_texts, bear_texts,
                    debate.get("judge_decision", rec.get("investment_plan", ""))
                )
            else:
                st.info("无辩论数据")

        with tabs[5]:
            risk = rec.get("risk_debate", {})
            if risk:
                show_risk_debate(risk)
            else:
                st.info("无风控辩论数据")

        with tabs[6]:
            st.subheader("🎯 最终决策")
            st.markdown(rec.get("decision", "—")[:10000])
