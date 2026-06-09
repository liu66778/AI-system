"""
Gate.io 行情数据源 — 替代 yfinance 获取 crypto OHLCV + 技术指标

Gate.io 公开 API 无需 Key，不墙，数据准。
BTC_USDT → 日线 OHLCV → 兼容 TradingAgents 内部格式
"""
import logging
from datetime import datetime, timedelta
import urllib.request
import urllib.error
import json
import time
import pandas as pd

logger = logging.getLogger(__name__)

GATE_BASE = "https://api.gateio.ws/api/v4"
CACHE = {}  # 简单内存缓存: {ticker_key: (timestamp, DataFrame)}
CACHE_TTL = 120  # 缓存 2 分钟

# Gate.io 合约格式: BTC_USDT, ETH_USDT
CRYPTO_TO_GATE = {
    "BTC": "BTC_USDT",
    "ETH": "ETH_USDT",
    "SOL": "SOL_USDT",
    "XRP": "XRP_USDT",
    "ADA": "ADA_USDT",
    "DOGE": "DOGE_USDT",
    "LTC": "LTC_USDT",
    "BCH": "BCH_USDT",
    "DOT": "DOT_USDT",
    "AVAX": "AVAX_USDT",
    "LINK": "LINK_USDT",
}


def _resolve_pair(symbol: str) -> str:
    """把 TradingAgents 符号转成 Gate.io 交易对"""
    # 已经是 Gate 格式就直接用
    if "_" in symbol and symbol.upper() == symbol:
        return symbol

    clean = symbol.strip().upper().replace("-", "_")
    # BTC-USD → BTC_USDT
    if clean.endswith("_USD"):
        clean = clean[:-4] + "_USDT"
    # BTCUSD → BTC_USDT
    elif clean.endswith("USD") and "_" not in clean:
        base = clean[:-3]
        if base in CRYPTO_TO_GATE:
            return CRYPTO_TO_GATE[base]
        clean = base + "_USDT"

    return clean


def _fetch_candles(pair: str, interval: str = "1d", limit: int = 365) -> pd.DataFrame:
    """从 Gate.io 拉 K 线数据"""
    url = f"{GATE_BASE}/spot/candlesticks?currency_pair={pair}&interval={interval}&limit={limit}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        logger.warning("Gate.io HTTP %s for %s: %s", e.code, pair, e.reason)
        raise
    except Exception as e:
        logger.warning("Gate.io fetch error for %s: %s", pair, e)
        raise

    if not data:
        logger.warning("Gate.io returned empty data for %s", pair)
        return pd.DataFrame()

    rows = []
    for candle in data:
        ts = int(candle[0])
        rows.append({
            "Date": datetime.fromtimestamp(ts),
            "Open": float(candle[5]),
            "High": float(candle[3]),
            "Low": float(candle[4]),
            "Close": float(candle[2]),
            "Volume": float(candle[1]),
        })

    df = pd.DataFrame(rows)
    df.set_index("Date", inplace=True)
    df.sort_index(inplace=True)
    return df


def get_YFin_data_online(symbol: str, start_date: str, end_date: str) -> str:
    """
    Gate.io 版 get_stock_data——返回和 yfinance 同样格式的 CSV 字符串

    Args:
        symbol: 如 'BTC-USD' 或 'BTCUSD' 或 'BTC_USDT'
        start_date: 'yyyy-mm-dd'
        end_date: 'yyyy-mm-dd'
    """
    pair = _resolve_pair(symbol)
    cache_key = f"candles_{pair}"

    # 缓存检查
    now = time.time()
    if cache_key in CACHE and now - CACHE[cache_key][0] < CACHE_TTL:
        df = CACHE[cache_key][1].copy()
        logger.debug("Gate.io cache hit for %s", pair)
    else:
        df = _fetch_candles(pair, limit=365)
        CACHE[cache_key] = (now, df.copy())
        logger.info("Gate.io fetched %d candles for %s", len(df), pair)

    if df.empty:
        from .symbol_utils import NoMarketDataError
        raise NoMarketDataError(symbol, canonical=pair,
                               detail=f"Gate.io returned no data for {pair}")

    # 裁剪到请求日期范围
    try:
        start = pd.Timestamp(start_date)
        end = pd.Timestamp(end_date)
        df = df[(df.index >= start) & (df.index <= end)]
    except Exception:
        pass

    if df.empty:
        from .symbol_utils import NoMarketDataError
        raise NoMarketDataError(
            symbol, canonical=pair,
            detail=f"No data in range {start_date}→{end_date} for {pair}")

    return df.to_csv()


def get_stock_stats_indicators_window(symbol: str, start_date: str, end_date: str) -> str:
    """
    Gate.io 版技术指标——yfinance 返回格式兼容

    从 Gate.io 拉 1 年 K 线（确保长周期指标有足够数据），
    计算全部指标，再裁剪到请求的日期范围。
    """
    pair = _resolve_pair(symbol)
    cache_key = f"indicators_{pair}"

    now = time.time()
    if cache_key in CACHE and now - CACHE[cache_key][0] < CACHE_TTL:
        df = CACHE[cache_key][1].copy()
    else:
        df = _fetch_candles(pair, limit=365)
        if df.empty:
            from .symbol_utils import NoMarketDataError
            raise NoMarketDataError(symbol, canonical=pair,
                                   detail=f"Gate.io returned no data for {pair}")

        # 按时间正序算指标
        df = df.sort_index(ascending=True)
        close = df["Close"]

        # SMA
        df["sma_10"] = close.rolling(10).mean()
        df["sma_50"] = close.rolling(50).mean()
        df["sma_200"] = close.rolling(200).mean()

        # EMA
        df["ema_10"] = close.ewm(span=10, adjust=False).mean()
        df["ema_50"] = close.ewm(span=50, adjust=False).mean()

        # RSI (14)
        delta = close.diff()
        gain = delta.clip(lower=0)
        loss = (-delta).clip(lower=0)
        avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
        rs = avg_gain / avg_loss.replace(0, 1)
        df["rsi_14"] = 100 - (100 / (1 + rs))

        # MACD
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        df["macd"] = ema12 - ema26
        df["macds"] = df["macd"].ewm(span=9, adjust=False).mean()
        df["macdh"] = df["macd"] - df["macds"]

        # 成交量 SMA
        df["volume_sma_20"] = df["Volume"].rolling(20).mean()

        # ATR (14)
        high_low = df["High"] - df["Low"]
        high_close = (df["High"] - close.shift()).abs()
        low_close = (df["Low"] - close.shift()).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df["atr_14"] = tr.ewm(alpha=1/14, adjust=False).mean()

        CACHE[cache_key] = (now, df.copy())

    # 裁剪到请求日期
    try:
        start = pd.Timestamp(start_date)
        end = pd.Timestamp(end_date)
        df = df[(df.index >= start) & (df.index <= end)]
    except Exception:
        pass

    if df.empty:
        from .symbol_utils import NoMarketDataError
        raise NoMarketDataError(symbol, canonical=pair,
                               detail=f"No indicators for {start_date} to {end_date}")

    # 反转日期（匹配 yfinance 格式：最新在前）
    df = df.sort_index(ascending=False)

    # 只删除核心指标为 NaN 的行
    core_cols = ["sma_10", "sma_50", "ema_10", "rsi_14", "macd"]
    existing = [c for c in core_cols if c in df.columns]
    if existing:
        df = df.dropna(subset=existing)

    return df.to_csv()


def get_fundamentals(symbol, *args, **kwargs):
    """Gate.io 不支持基本面数据（crypto 无财报），返回空"""
    return ""


def get_balance_sheet(symbol, *args, **kwargs):
    return ""


def get_cashflow(symbol, *args, **kwargs):
    return ""


def get_income_statement(symbol, *args, **kwargs):
    return ""


def get_insider_transactions(symbol, *args, **kwargs):
    return ""


def get_news(symbol, *args, **kwargs):
    return ""


def get_global_news(*args, **kwargs):
    return ""
