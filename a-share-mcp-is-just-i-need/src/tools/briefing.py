"""日报与推荐所需的结构化工具。"""
from __future__ import annotations

import json
import math
from datetime import datetime, timedelta
from typing import Any, Dict, List

import pandas as pd
import yfinance as yf

from ..data_source_factory import get_data_source
from ..market_utils import detect_market
from ..yfinance_data_source import YFinanceDataSource
from .forecasting import forecast_price_payload


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _load_history_frame(stock_code: str, days: int = 260) -> pd.DataFrame:
    end_date = datetime.utcnow().strftime("%Y-%m-%d")
    start_date = (datetime.utcnow() - timedelta(days=days * 2)).strftime("%Y-%m-%d")
    source = get_data_source(stock_code)
    try:
        rows = source.get_historical_k_data(stock_code, start_date, end_date, frequency="d", adjustflag="2")
    except Exception:
        rows = []
    if not rows:
        try:
            rows = YFinanceDataSource().get_historical_k_data(
                stock_code,
                start_date,
                end_date,
                frequency="d",
                adjustflag="2",
            )
        except Exception:
            rows = []
    if not rows:
        return pd.DataFrame()

    frame = pd.DataFrame(rows)
    for column in ["open", "high", "low", "close", "volume", "pctChg", "peTTM", "pbMRQ"]:
        if column not in frame.columns:
            frame[column] = 0
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame = frame.sort_values("date").dropna(subset=["date", "close"]).tail(days).reset_index(drop=True)
    return frame


def _rsi(close_series: pd.Series, window: int = 14) -> float:
    delta = close_series.diff()
    gain = delta.clip(lower=0).rolling(window).mean()
    loss = (-delta.clip(upper=0)).rolling(window).mean()
    rs = gain / (loss + 1e-8)
    value = 100 - (100 / (1 + rs))
    return _safe_float(value.iloc[-1])


def _macd(close_series: pd.Series) -> tuple[float, float]:
    ema_fast = close_series.ewm(span=12, adjust=False).mean()
    ema_slow = close_series.ewm(span=26, adjust=False).mean()
    macd = ema_fast - ema_slow
    signal = macd.ewm(span=9, adjust=False).mean()
    return _safe_float(macd.iloc[-1]), _safe_float(signal.iloc[-1])


def _score_band(value: float, low: float, high: float, cap: float = 100.0) -> float:
    if value <= low:
        return cap
    if value >= high:
        return max(0.0, cap * 0.2)
    ratio = (value - low) / (high - low)
    return max(0.0, cap * (1 - ratio * 0.8))


def _extract_news_items(stock_code: str, stock_name: str, top_k: int = 5) -> tuple[float, List[Dict[str, str]]]:
    source = get_data_source(stock_code)
    items = []
    if hasattr(source, "get_news"):
        try:
            items = source.get_news(stock_code, top_k=top_k)
        except Exception:
            items = []

    if not items:
        items = [
            {
                "title": f"{stock_name or stock_code} 业务进展平稳",
                "summary": "当前未接入高质量实时新闻源，系统使用中性兜底判断。",
                "url": "",
            }
        ]

    positive_keywords = ["增长", "超预期", "中标", "扩产", "回购", "增持", "利好", "创新高", "突破"]
    negative_keywords = ["减持", "下滑", "诉讼", "亏损", "处罚", "风险", "暴雷", "下修", "违约"]

    score = 50.0
    normalized_items: List[Dict[str, str]] = []
    for item in items[:top_k]:
        title = item.get("title", "")
        summary = item.get("summary", "")
        text = f"{title} {summary}"
        score += sum(6 for keyword in positive_keywords if keyword in text)
        score -= sum(8 for keyword in negative_keywords if keyword in text)
        normalized_items.append(
            {
                "title": title,
                "summary": summary,
                "url": item.get("url", ""),
            }
        )
    return max(0.0, min(100.0, score)), normalized_items


def _fundamental_bundle(stock_code: str) -> Dict[str, Any]:
    source = get_data_source(stock_code)
    current_year = datetime.utcnow().year
    year = max(current_year - 1, 2020)

    try:
        profit = source.get_profit_data(stock_code, year, 4)
    except Exception:
        profit = {}
    try:
        growth = source.get_growth_data(stock_code, year, 4)
    except Exception:
        growth = {}
    try:
        balance = source.get_balance_data(stock_code, year, 4)
    except Exception:
        balance = {}
    try:
        cashflow = source.get_cash_flow_data(stock_code, year, 4)
    except Exception:
        cashflow = {}
    return {
        "profit": profit,
        "growth": growth,
        "balance": balance,
        "cashflow": cashflow,
    }


def _reason_list(
    overall_score: float,
    technical_score: float,
    fundamental_score: float,
    valuation_score: float,
    news_score: float,
    forecast: Dict[str, Any],
) -> List[str]:
    reasons = []
    if fundamental_score >= 70:
        reasons.append("基本面质量较稳，盈利与成长指标在稳健阈值之上。")
    if valuation_score >= 65:
        reasons.append("估值压力相对可控，当前价格没有明显透支。")
    if technical_score >= 65:
        reasons.append("技术面保持偏强结构，均线和量价关系未出现明显破坏。")
    if news_score >= 60:
        reasons.append("近期消息面偏中性偏正，未看到显著风险事件。")
    if forecast.get("direction") == "上涨" and forecast.get("confidence", 0) >= 0.6:
        reasons.append("短期预测信号偏多，下一交易日方向概率略占优。")
    if overall_score < 50:
        reasons.append("综合分偏低，建议优先规避而不是尝试抄底。")
    return reasons[:4]


def get_stock_snapshot(stock_code: str, stock_name: str = "") -> str:
    """返回结构化个股快照，用于日报和推荐引擎。"""
    try:
        frame = _load_history_frame(stock_code)
        if frame.empty:
            raise ValueError("未获取到历史行情")

        source = get_data_source(stock_code)
        try:
            basic_info = source.get_stock_basic_info(stock_code)
        except Exception:
            basic_info = {}
        stock_name = stock_name or basic_info.get("name") or stock_code
        close = frame["close"]
        volume = frame["volume"].replace(0, pd.NA).ffill().fillna(0)

        latest_close = _safe_float(close.iloc[-1])
        return_1d = _safe_float((close.iloc[-1] / close.iloc[-2] - 1) * 100) if len(close) > 1 else 0.0
        return_5d = _safe_float((close.iloc[-1] / close.iloc[-6] - 1) * 100) if len(close) > 5 else 0.0
        return_20d = _safe_float((close.iloc[-1] / close.iloc[-21] - 1) * 100) if len(close) > 20 else 0.0
        volatility_20d = _safe_float(close.pct_change().rolling(20).std().iloc[-1] * math.sqrt(20) * 100)
        ma5 = _safe_float(close.rolling(5).mean().iloc[-1])
        ma20 = _safe_float(close.rolling(20).mean().iloc[-1])
        ma60 = _safe_float(close.rolling(60).mean().iloc[-1])
        rsi14 = _rsi(close)
        macd, macd_signal = _macd(close)
        volume_ratio = _safe_float(volume.iloc[-1] / (volume.tail(20).mean() + 1e-8))
        support_20d = _safe_float(frame["low"].tail(20).min())
        resistance_20d = _safe_float(frame["high"].tail(20).max())
        rolling_high_60d = _safe_float(frame["high"].tail(60).max())

        fundamentals = _fundamental_bundle(stock_code)
        profit = fundamentals["profit"]
        growth = fundamentals["growth"]
        balance = fundamentals["balance"]
        roe = _safe_float(profit.get("roe"))
        revenue_growth = _safe_float(growth.get("yoy_revenue"))
        net_profit_growth = _safe_float(growth.get("yoy_net_profit"))
        asset_debt_ratio = _safe_float(balance.get("asset_debt_ratio")) * 100

        pe_ttm = _safe_float(basic_info.get("pe_ttm"))
        pb_mrq = _safe_float(basic_info.get("pb_mrq"))

        fundamental_score = 0.0
        fundamental_score += min(35.0, max(0.0, roe * 1.8))
        fundamental_score += min(25.0, max(0.0, revenue_growth * 0.6))
        fundamental_score += min(25.0, max(0.0, net_profit_growth * 0.5))
        fundamental_score += max(0.0, 15.0 - max(0.0, asset_debt_ratio - 50) * 0.4)
        fundamental_score = max(15.0, min(100.0, fundamental_score))

        valuation_score = 55.0
        if pe_ttm > 0:
            valuation_score = _score_band(pe_ttm, 12, 40)
        if pb_mrq > 0:
            valuation_score = (valuation_score * 0.7) + (_score_band(pb_mrq, 1.2, 6.0) * 0.3)

        technical_score = 50.0
        technical_score += 15 if latest_close > ma20 > 0 else -5
        technical_score += 10 if ma20 > ma60 > 0 else -8
        technical_score += 12 if macd > macd_signal else -10
        technical_score += 8 if 45 <= rsi14 <= 68 else -6
        technical_score += 8 if volume_ratio >= 1.1 and return_5d > 0 else 0
        technical_score += 5 if latest_close >= support_20d and latest_close <= resistance_20d else 0
        technical_score = max(0.0, min(100.0, technical_score))

        news_score, news_items = _extract_news_items(stock_code, stock_name)
        flow_score = max(0.0, min(100.0, 45 + volume_ratio * 15 + max(0.0, return_5d) * 1.2))
        news_flow_score = max(0.0, min(100.0, news_score * 0.6 + flow_score * 0.4))

        forecast = forecast_price_payload(stock_code)
        overall_score = (
            fundamental_score * 0.4
            + valuation_score * 0.2
            + technical_score * 0.2
            + news_flow_score * 0.2
        )
        if forecast.get("direction") == "上涨":
            overall_score += 3
        elif forecast.get("direction") == "下跌":
            overall_score -= 4
        overall_score = max(0.0, min(100.0, overall_score))

        if overall_score >= 80:
            recommendation_label = "买入"
        elif overall_score >= 65:
            recommendation_label = "继续观察"
        elif overall_score >= 50:
            recommendation_label = "中性"
        else:
            recommendation_label = "回避"

        payload = {
            "stock_code": stock_code,
            "stock_name": stock_name,
            "market": detect_market(stock_code),
            "available": True,
            "current_price": round(latest_close, 4),
            "recent_change_pct_1d": round(return_1d, 2),
            "recent_change_pct_5d": round(return_5d, 2),
            "recent_change_pct_20d": round(return_20d, 2),
            "volatility_20d_pct": round(volatility_20d, 2),
            "ma5": round(ma5, 4),
            "ma20": round(ma20, 4),
            "ma60": round(ma60, 4),
            "rsi14": round(rsi14, 2),
            "macd": round(macd, 4),
            "macd_signal": round(macd_signal, 4),
            "volume_ratio": round(volume_ratio, 2),
            "support_20d": round(support_20d, 4),
            "resistance_20d": round(resistance_20d, 4),
            "rolling_high_60d": round(rolling_high_60d, 4),
            "pe_ttm": round(pe_ttm, 2) if pe_ttm else 0,
            "pb_mrq": round(pb_mrq, 2) if pb_mrq else 0,
            "roe": round(roe, 2),
            "revenue_growth_yoy": round(revenue_growth, 2),
            "net_profit_growth_yoy": round(net_profit_growth, 2),
            "asset_debt_ratio_pct": round(asset_debt_ratio, 2),
            "fundamental_score": round(fundamental_score, 2),
            "valuation_score": round(valuation_score, 2),
            "technical_score": round(technical_score, 2),
            "news_flow_score": round(news_flow_score, 2),
            "overall_score": round(overall_score, 2),
            "recommendation_label": recommendation_label,
            "forecast": forecast,
            "news_sentiment_score": round(news_score, 2),
            "news_headlines": news_items,
            "reasons": _reason_list(
                overall_score,
                technical_score,
                fundamental_score,
                valuation_score,
                news_flow_score,
                forecast,
            ),
        }
        return json.dumps(payload, ensure_ascii=False)
    except Exception as exc:
        payload = {
            "stock_code": stock_code,
            "stock_name": stock_name or stock_code,
            "market": detect_market(stock_code),
            "available": False,
            "error": str(exc),
            "recommendation_label": "数据不足",
            "reasons": ["当前数据源不可用，建议稍后重试或人工复核。"],
        }
        return json.dumps(payload, ensure_ascii=False)


def get_market_context(session: str = "morning") -> str:
    """返回结构化的市场环境摘要。"""
    tickers = {
        "标普500": "^GSPC",
        "纳斯达克": "^IXIC",
        "道琼斯": "^DJI",
        "VIX": "^VIX",
        "恒生科技": "^HSTECH",
        "美元兑离岸人民币": "CNH=X",
        "黄金": "GC=F",
        "原油": "CL=F",
    }

    items = []
    for label, ticker in tickers.items():
        try:
            history = yf.Ticker(ticker).history(period="5d", interval="1d", auto_adjust=False)
            history = history.dropna(subset=["Close"])
            if len(history) < 2:
                continue
            latest = float(history["Close"].iloc[-1])
            previous = float(history["Close"].iloc[-2])
            change_pct = ((latest - previous) / previous * 100) if previous else 0.0
            items.append(
                {
                    "label": label,
                    "ticker": ticker,
                    "latest": round(latest, 4),
                    "change_pct": round(change_pct, 2),
                }
            )
        except Exception:
            continue

    bias = "中性"
    if any(item["label"] == "纳斯达克" and item["change_pct"] >= 1.0 for item in items):
        bias = "偏多"
    elif any(item["label"] == "纳斯达克" and item["change_pct"] <= -1.0 for item in items):
        bias = "偏谨慎"

    payload = {
        "session": session,
        "generated_at": datetime.utcnow().isoformat(),
        "bias": bias,
        "items": items,
    }
    return json.dumps(payload, ensure_ascii=False)
