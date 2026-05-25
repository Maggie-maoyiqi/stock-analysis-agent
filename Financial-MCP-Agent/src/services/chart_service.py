"""Build structured chart payloads for reports and briefs."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List

from ..tools.mcp_client import run_tool_json


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _round(value: Any, digits: int = 2) -> float:
    return round(_safe_float(value), digits)


def _moving_average(values: List[float], window: int) -> List[float | None]:
    result: List[float | None] = []
    for index in range(len(values)):
        if index + 1 < window:
            result.append(None)
            continue
        subset = values[index - window + 1:index + 1]
        result.append(round(sum(subset) / window, 4))
    return result


def _drawdown_series(values: List[float]) -> List[float]:
    running_high = 0.0
    drawdowns = []
    for value in values:
        running_high = max(running_high, value)
        drawdown = ((value - running_high) / running_high * 100) if running_high else 0.0
        drawdowns.append(round(drawdown, 2))
    return drawdowns


def _cumulative_return(values: List[float]) -> List[float]:
    if not values:
        return []
    start = values[0] or 1.0
    return [round((value / start - 1) * 100, 2) if start else 0.0 for value in values]


async def build_analysis_charts(stock_code: str, stock_name: str) -> List[Dict[str, Any]]:
    end_date = datetime.utcnow().strftime("%Y-%m-%d")
    start_date = (datetime.utcnow() - timedelta(days=220)).strftime("%Y-%m-%d")
    history = await run_tool_json(
        "historical_k_data_json",
        {
            "stock_code": stock_code,
            "start_date": start_date,
            "end_date": end_date,
            "frequency": "d",
            "adjustflag": "2",
        },
    )
    snapshot = await run_tool_json("stock_snapshot", {"stock_code": stock_code, "stock_name": stock_name})
    rows = history.get("items", [])[-90:]
    labels = [item.get("date", "") for item in rows]
    opens = [_safe_float(item.get("open")) for item in rows]
    highs = [_safe_float(item.get("high")) for item in rows]
    lows = [_safe_float(item.get("low")) for item in rows]
    closes = [_safe_float(item.get("close")) for item in rows]
    ma5 = _moving_average(closes, 5)
    ma20 = _moving_average(closes, 20)
    ma60 = _moving_average(closes, 60)

    return [
        {
            "id": "price_structure",
            "type": "candlestick",
            "title": f"{stock_name} K线与均线",
            "labels": labels,
            "candles": [
                {"open": round(o, 4), "high": round(h, 4), "low": round(l, 4), "close": round(c, 4)}
                for o, h, l, c in zip(opens, highs, lows, closes)
            ],
            "lines": [
                {"name": "MA5", "color": "#0f766e", "values": ma5},
                {"name": "MA20", "color": "#d97706", "values": ma20},
                {"name": "MA60", "color": "#7c3aed", "values": ma60},
            ],
        },
        {
            "id": "drawdown_curve",
            "type": "line",
            "title": f"{stock_name} 回撤曲线",
            "labels": labels,
            "series": [{"name": "回撤%", "color": "#dc2626", "values": _drawdown_series(closes)}],
        },
        {
            "id": "return_curve",
            "type": "line",
            "title": f"{stock_name} 收益曲线",
            "labels": labels,
            "series": [{"name": "累计收益%", "color": "#2563eb", "values": _cumulative_return(closes)}],
        },
        {
            "id": "score_radar",
            "type": "radar",
            "title": f"{stock_name} 推荐分数雷达图",
            "indicators": ["基本面", "估值", "技术面", "新闻流", "综合"],
            "values": [
                _round(snapshot.get("fundamental_score")),
                _round(snapshot.get("valuation_score")),
                _round(snapshot.get("technical_score")),
                _round(snapshot.get("news_flow_score")),
                _round(snapshot.get("overall_score")),
            ],
        },
    ]


def build_portfolio_distribution_chart(positions: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    labels: List[str] = []
    values: List[float] = []
    for item in positions:
        quantity = _safe_float(item.get("quantity"))
        price = _safe_float(item.get("current_price") or item.get("buy_price"))
        labels.append(item.get("stock_name") or item.get("stock_code", ""))
        values.append(round(quantity * price, 2))
    return {
        "id": "position_distribution",
        "type": "bar",
        "title": "仓位分布",
        "labels": labels,
        "series": [{"name": "持仓市值", "color": "#0f766e", "values": values}],
    }


def build_recommendation_radar_charts(recommendations: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    charts: List[Dict[str, Any]] = []
    for item in list(recommendations)[:3]:
        charts.append(
            {
                "id": f"recommendation_radar_{item['stock_code']}",
                "type": "radar",
                "title": f"{item['stock_name']} 推荐雷达图",
                "indicators": ["基本面", "估值", "技术面", "新闻流", "综合"],
                "values": [
                    _round(item.get("fundamental_score")),
                    _round(item.get("valuation_score")),
                    _round(item.get("technical_score")),
                    _round(item.get("news_flow_score")),
                    _round(item.get("overall_score")),
                ],
            }
        )
    return charts


def build_watchlist_bar_chart(items: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    rows = list(items)
    return {
        "id": "watchlist_scores",
        "type": "bar",
        "title": "自选股综合评分",
        "labels": [item.get("stock_name") or item.get("stock_code", "") for item in rows],
        "series": [{"name": "综合分", "color": "#2563eb", "values": [_round(item.get("overall_score")) for item in rows]}],
    }
