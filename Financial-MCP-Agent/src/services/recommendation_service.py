"""自选股跟踪、持仓体检与推荐引擎。"""
from __future__ import annotations

from typing import Any, Dict, List

from ..tools.mcp_client import run_tool_json

CANDIDATE_POOL: List[Dict[str, str]] = [
    {"stock_code": "sh.600519", "stock_name": "贵州茅台", "sector": "消费白马", "theme": "高端消费"},
    {"stock_code": "sz.300750", "stock_name": "宁德时代", "sector": "新能源", "theme": "动力电池"},
    {"stock_code": "sh.601318", "stock_name": "中国平安", "sector": "金融", "theme": "保险龙头"},
    {"stock_code": "sh.600036", "stock_name": "招商银行", "sector": "金融", "theme": "银行龙头"},
    {"stock_code": "sz.002594", "stock_name": "比亚迪", "sector": "新能源", "theme": "整车龙头"},
    {"stock_code": "sh.600900", "stock_name": "长江电力", "sector": "公用事业", "theme": "高股息"},
    {"stock_code": "sz.000333", "stock_name": "美的集团", "sector": "家电", "theme": "家电白马"},
    {"stock_code": "sh.601899", "stock_name": "紫金矿业", "sector": "资源", "theme": "黄金铜矿"},
    {"stock_code": "sz.000858", "stock_name": "五粮液", "sector": "消费白马", "theme": "白酒"},
    {"stock_code": "sh.600276", "stock_name": "恒瑞医药", "sector": "医药", "theme": "创新药"},
    {"stock_code": "sh.688981", "stock_name": "中芯国际", "sector": "半导体", "theme": "晶圆制造"},
    {"stock_code": "sz.002415", "stock_name": "海康威视", "sector": "科技", "theme": "安防龙头"},
    {"stock_code": "sh.600887", "stock_name": "伊利股份", "sector": "消费白马", "theme": "乳业龙头"},
    {"stock_code": "sh.600309", "stock_name": "万华化学", "sector": "化工", "theme": "材料龙头"},
    {"stock_code": "sz.300760", "stock_name": "迈瑞医疗", "sector": "医药", "theme": "医疗器械"},
    {"stock_code": "sh.601668", "stock_name": "中国建筑", "sector": "基建", "theme": "央企高股息"},
    {"stock_code": "sz.002371", "stock_name": "北方华创", "sector": "半导体", "theme": "设备国产化"},
    {"stock_code": "sh.601088", "stock_name": "中国神华", "sector": "能源", "theme": "煤炭高股息"},
    {"stock_code": "sz.000651", "stock_name": "格力电器", "sector": "家电", "theme": "白马分红"},
    {"stock_code": "sh.600941", "stock_name": "中国移动", "sector": "通信", "theme": "央企红利"},
]


async def fetch_market_context(session: str) -> Dict[str, Any]:
    return await run_tool_json("market_context", {"session": session})


async def fetch_snapshot(stock_code: str, stock_name: str = "") -> Dict[str, Any]:
    return await run_tool_json("stock_snapshot", {"stock_code": stock_code, "stock_name": stock_name})


def _round(value: Any, digits: int = 2) -> float:
    try:
        return round(float(value), digits)
    except (TypeError, ValueError):
        return 0.0


def _safe_name(item: Dict[str, Any]) -> str:
    return item.get("stock_name") or item.get("stock_code", "")


def _watch_action(snapshot: Dict[str, Any]) -> str:
    score = float(snapshot.get("overall_score", 0) or 0)
    label = snapshot.get("recommendation_label", "观察")
    if label == "买入" and score >= 80:
        return "买入"
    if score >= 65:
        return "继续观察"
    if score >= 50:
        return "中性"
    return "回避"


def _position_action(position: Dict[str, Any], snapshot: Dict[str, Any]) -> Dict[str, Any]:
    current_price = float(snapshot.get("current_price", 0) or 0)
    buy_price = float(position.get("buy_price", 0) or 0)
    pnl_pct = ((current_price - buy_price) / buy_price * 100) if current_price and buy_price else 0.0
    recent_high = float(snapshot.get("rolling_high_60d", current_price) or current_price or 0)
    drawdown_pct = ((current_price - recent_high) / recent_high * 100) if recent_high else 0.0
    stop_loss_pct = float(position.get("stop_loss_pct", 8.0) or 8.0)
    take_profit_drawdown_pct = float(position.get("take_profit_drawdown_pct", 15.0) or 15.0)
    technical_score = float(snapshot.get("technical_score", 0) or 0)
    volume_ratio = float(snapshot.get("volume_ratio", 0) or 0)
    fundamental_score = float(snapshot.get("fundamental_score", 0) or 0)

    reasons: List[str] = []
    risk_tag = "🟢"
    action = "继续持有"

    if pnl_pct <= -abs(stop_loss_pct):
        action = "清仓"
        risk_tag = "🔴"
        reasons.append(f"浮亏达到 {pnl_pct:.2f}%，已触发 -{stop_loss_pct:.1f}% 硬止损。")
    elif drawdown_pct <= -abs(take_profit_drawdown_pct):
        action = "减仓"
        risk_tag = "🟡"
        reasons.append(f"距近 60 日高点回撤 {drawdown_pct:.2f}%，触发移动止盈。")
    elif technical_score < 45 and volume_ratio >= 1.2:
        action = "减仓"
        risk_tag = "🟡"
        reasons.append("技术面破位且量能放大，短线抛压增强。")
    elif fundamental_score < 45:
        action = "清仓"
        risk_tag = "🔴"
        reasons.append("基本面分数明显恶化，原持有逻辑弱化。")
    else:
        reasons.append("当前未触发硬止损、明显破位或基本面恶化条件。")
        if pnl_pct > 0:
            reasons.append(f"当前仍处于浮盈 {pnl_pct:.2f}% 状态，可继续观察趋势延续。")
        else:
            reasons.append(f"当前浮亏 {pnl_pct:.2f}%，但尚未触发纪律位。")

    if not reasons:
        reasons = snapshot.get("reasons", [])[:2] or ["当前暂无足够理由调整仓位。"]

    return {
        "stock_code": position["stock_code"],
        "stock_name": _safe_name(snapshot) or _safe_name(position),
        "current_price": _round(current_price, 4),
        "buy_price": _round(buy_price, 4),
        "quantity": int(position.get("quantity", 0) or 0),
        "pnl_pct": _round(pnl_pct),
        "drawdown_from_high_pct": _round(drawdown_pct),
        "action": action,
        "risk_tag": risk_tag,
        "reasons": reasons,
        "overall_score": _round(snapshot.get("overall_score", 0)),
        "recent_change_pct_5d": _round(snapshot.get("recent_change_pct_5d", 0)),
        "volatility_20d_pct": _round(snapshot.get("volatility_20d_pct", 0)),
    }


def _extract_focus_sectors(profile: Dict[str, Any]) -> List[str]:
    names = " ".join(
        [
            f"{item.get('stock_name', '')} {item.get('notes', '')}"
            for item in profile.get("watchlist", []) + profile.get("positions", [])
        ]
    )
    keyword_map = {
        "消费白马": ["茅台", "五粮液", "伊利", "消费", "白酒"],
        "新能源": ["宁德", "比亚迪", "新能源", "电池", "汽车"],
        "金融": ["招商银行", "平安", "银行", "保险"],
        "医药": ["恒瑞", "迈瑞", "医药", "器械"],
        "半导体": ["中芯", "北方华创", "半导体", "芯片"],
        "家电": ["美的", "格力", "家电"],
        "资源": ["紫金", "黄金", "铜", "资源"],
    }
    hits = []
    for sector, keywords in keyword_map.items():
        if any(keyword in names for keyword in keywords):
            hits.append(sector)
    return hits


def _strategy_tags(candidate: Dict[str, str], focus_sectors: List[str], snapshot: Dict[str, Any]) -> List[str]:
    tags = ["稳健候选池"]
    if candidate.get("sector") in focus_sectors:
        tags.append("板块联动")
    volume_ratio = float(snapshot.get("volume_ratio", 0) or 0)
    current_price = float(snapshot.get("current_price", 0) or 0)
    rolling_high_60d = float(snapshot.get("rolling_high_60d", 0) or 0)
    recent_change_5d = float(snapshot.get("recent_change_pct_5d", 0) or 0)
    if volume_ratio >= 1.3 and recent_change_5d > 3:
        tags.append("量能异常")
    if current_price >= rolling_high_60d * 0.985 and rolling_high_60d > 0:
        tags.append("突破年内平台")
    if float(snapshot.get("fundamental_score", 0) or 0) >= 72:
        tags.append("基本面筛选")
    return tags


def _analysis_text(candidate: Dict[str, str], snapshot: Dict[str, Any], tags: List[str]) -> str:
    reasons = snapshot.get("reasons", [])[:3]
    parts = [
        f"{candidate.get('sector', '行业龙头')}方向下的 {candidate.get('theme', '核心标的')}，当前综合分 {snapshot.get('overall_score', 0)} 分。",
        "；".join(reasons) if reasons else "当前信号以稳健偏多为主。",
    ]
    if tags:
        parts.append(f"策略标签：{'、'.join(tags)}。")
    return " ".join(parts)


async def build_watchlist_reviews(profile: Dict[str, Any]) -> List[Dict[str, Any]]:
    reviews: List[Dict[str, Any]] = []
    for item in profile.get("watchlist", []):
        snapshot = await fetch_snapshot(item["stock_code"], item.get("stock_name", ""))
        review = {
            "stock_code": item["stock_code"],
            "stock_name": _safe_name(snapshot) or item.get("stock_name") or item["stock_code"],
            "market": item.get("market", "cn"),
            "notes": item.get("notes", ""),
            "status": snapshot.get("recommendation_label", "观察"),
            "action": _watch_action(snapshot),
            "overall_score": _round(snapshot.get("overall_score", 0)),
            "fundamental_score": _round(snapshot.get("fundamental_score", 0)),
            "valuation_score": _round(snapshot.get("valuation_score", 0)),
            "technical_score": _round(snapshot.get("technical_score", 0)),
            "news_flow_score": _round(snapshot.get("news_flow_score", 0)),
            "current_price": _round(snapshot.get("current_price", 0), 4),
            "recent_change_pct_1d": _round(snapshot.get("recent_change_pct_1d", 0)),
            "recent_change_pct_5d": _round(snapshot.get("recent_change_pct_5d", 0)),
            "volatility_20d_pct": _round(snapshot.get("volatility_20d_pct", 0)),
            "pe_ttm": _round(snapshot.get("pe_ttm", 0)),
            "pb_mrq": _round(snapshot.get("pb_mrq", 0)),
            "forecast_direction": (snapshot.get("forecast") or {}).get("direction", "中性"),
            "forecast_return_pct": _round((snapshot.get("forecast") or {}).get("predicted_return_pct", 0)),
            "reasons": snapshot.get("reasons", [])[:3],
            "available": snapshot.get("available", False),
        }
        reviews.append(review)
    return reviews


async def build_position_reviews(profile: Dict[str, Any]) -> List[Dict[str, Any]]:
    reviews: List[Dict[str, Any]] = []
    for item in profile.get("positions", []):
        snapshot = await fetch_snapshot(item["stock_code"], item.get("stock_name", ""))
        reviews.append(_position_action(item, snapshot))
    return reviews


async def discover_recommendations(profile: Dict[str, Any]) -> List[Dict[str, Any]]:
    recommendation_count = int(profile.get("recommendation_count", 5) or 5)
    existing_codes = {item["stock_code"] for item in profile.get("watchlist", [])}
    existing_codes.update(item["stock_code"] for item in profile.get("positions", []))
    focus_sectors = _extract_focus_sectors(profile)

    scored: List[Dict[str, Any]] = []
    for candidate in CANDIDATE_POOL:
        if candidate["stock_code"] in existing_codes:
            continue
        snapshot = await fetch_snapshot(candidate["stock_code"], candidate["stock_name"])
        if not snapshot.get("available"):
            continue

        overall_score = float(snapshot.get("overall_score", 0) or 0)
        fundamental_score = float(snapshot.get("fundamental_score", 0) or 0)
        valuation_score = float(snapshot.get("valuation_score", 0) or 0)
        technical_score = float(snapshot.get("technical_score", 0) or 0)
        news_flow_score = float(snapshot.get("news_flow_score", 0) or 0)
        recent_change_5d = float(snapshot.get("recent_change_pct_5d", 0) or 0)
        volume_ratio = float(snapshot.get("volume_ratio", 0) or 0)
        price = float(snapshot.get("current_price", 0) or 0)
        rolling_high_60d = float(snapshot.get("rolling_high_60d", 0) or 0)

        if fundamental_score < 55 or technical_score < 48:
            continue

        strategy_tags = _strategy_tags(candidate, focus_sectors, snapshot)
        adjusted_score = overall_score
        if "板块联动" in strategy_tags:
            adjusted_score += 4
        if "量能异常" in strategy_tags:
            adjusted_score += 3
        if "突破年内平台" in strategy_tags:
            adjusted_score += 3
        if "基本面筛选" in strategy_tags:
            adjusted_score += 2
        if recent_change_5d > 12:
            adjusted_score -= 2
        if valuation_score < 45:
            adjusted_score -= 2
        adjusted_score = max(0.0, min(100.0, adjusted_score))

        buy_low = price * 0.985 if price else 0
        buy_high = min(rolling_high_60d, price * 1.02) if rolling_high_60d else price * 1.02
        risk_point = "若放量跌破20日均线或消息面明显转弱，需重新评估。"
        if volume_ratio >= 1.4 and price >= rolling_high_60d * 0.99 and rolling_high_60d > 0:
            risk_point = "短线已有异动，若次日不能站稳突破位，容易回吐。"

        scored.append(
            {
                "stock_code": candidate["stock_code"],
                "stock_name": candidate["stock_name"],
                "sector": candidate.get("sector", ""),
                "theme": candidate.get("theme", ""),
                "strategy_tags": strategy_tags,
                "current_price": _round(price, 4),
                "overall_score": _round(adjusted_score),
                "fundamental_score": _round(fundamental_score),
                "valuation_score": _round(valuation_score),
                "technical_score": _round(technical_score),
                "news_flow_score": _round(news_flow_score),
                "forecast_direction": (snapshot.get("forecast") or {}).get("direction", "中性"),
                "forecast_return_pct": _round((snapshot.get("forecast") or {}).get("predicted_return_pct", 0)),
                "buy_zone": f"{_round(buy_low, 2)} - {_round(buy_high, 2)}",
                "risk_point": risk_point,
                "analysis": _analysis_text(candidate, snapshot, strategy_tags),
            }
        )

    scored.sort(
        key=lambda item: (
            item["overall_score"],
            item["fundamental_score"],
            item["technical_score"],
            item["news_flow_score"],
        ),
        reverse=True,
    )
    return scored[:recommendation_count]
