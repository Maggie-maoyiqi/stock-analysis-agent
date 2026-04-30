"""用户档案读写服务。"""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
PROFILE_PATH = DATA_DIR / "user_profile.json"

DEFAULT_PROFILE: Dict[str, Any] = {
    "risk_preference": "稳健",
    "recommendation_count": 5,
    "primary_market": "cn",
    "active_markets": ["cn", "hk", "us"],
    "delivery_schedule": {"morning": "09:00", "evening": "21:00"},
    "watchlist": [],
    "positions": [],
}


def _detect_market(stock_code: str) -> str:
    code = (stock_code or "").upper()
    if code.startswith(("SH.", "SZ.")) or len(code) == 6 and code.isdigit():
        return "cn"
    if code.endswith(".HK"):
        return "hk"
    return "us"


def _ensure_profile_file():
    DATA_DIR.mkdir(exist_ok=True)
    if not PROFILE_PATH.exists():
        PROFILE_PATH.write_text(json.dumps(DEFAULT_PROFILE, ensure_ascii=False, indent=2), encoding="utf-8")


def load_profile() -> Dict[str, Any]:
    """读取用户档案，不存在时自动创建默认档案。"""
    _ensure_profile_file()
    return json.loads(PROFILE_PATH.read_text(encoding="utf-8"))


def save_profile(profile: Dict[str, Any]) -> Dict[str, Any]:
    """保存用户档案。"""
    DATA_DIR.mkdir(exist_ok=True)
    PROFILE_PATH.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
    return profile


def update_profile(partial: Dict[str, Any]) -> Dict[str, Any]:
    """更新用户档案的顶层字段。"""
    profile = load_profile()
    merged = deepcopy(profile)
    for key, value in partial.items():
        if value is not None:
            merged[key] = value
    return save_profile(merged)


def add_watchlist_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """新增或更新自选股。"""
    profile = load_profile()
    normalized = {
        "stock_code": item["stock_code"],
        "stock_name": item.get("stock_name") or item["stock_code"],
        "market": item.get("market") or _detect_market(item["stock_code"]),
        "notes": item.get("notes", ""),
    }
    watchlist = [entry for entry in profile["watchlist"] if entry["stock_code"] != normalized["stock_code"]]
    watchlist.append(normalized)
    profile["watchlist"] = sorted(watchlist, key=lambda row: row["stock_code"])
    return save_profile(profile)


def remove_watchlist_item(stock_code: str) -> Dict[str, Any]:
    """移除自选股。"""
    profile = load_profile()
    profile["watchlist"] = [entry for entry in profile["watchlist"] if entry["stock_code"] != stock_code]
    return save_profile(profile)


def add_position(item: Dict[str, Any]) -> Dict[str, Any]:
    """新增或更新持仓，并同步加入自选股。"""
    profile = load_profile()
    normalized = {
        "stock_code": item["stock_code"],
        "stock_name": item.get("stock_name") or item["stock_code"],
        "buy_price": float(item["buy_price"]),
        "quantity": int(item["quantity"]),
        "buy_date": item["buy_date"],
        "stop_loss_pct": float(item.get("stop_loss_pct", 8.0)),
        "take_profit_drawdown_pct": float(item.get("take_profit_drawdown_pct", 15.0)),
        "notes": item.get("notes", ""),
    }
    positions = [entry for entry in profile["positions"] if entry["stock_code"] != normalized["stock_code"]]
    positions.append(normalized)
    profile["positions"] = sorted(positions, key=lambda row: row["stock_code"])
    save_profile(profile)
    return add_watchlist_item(
        {
            "stock_code": normalized["stock_code"],
            "stock_name": normalized["stock_name"],
            "market": _detect_market(normalized["stock_code"]),
            "notes": normalized["notes"],
        }
    )


def remove_position(stock_code: str) -> Dict[str, Any]:
    """移除持仓。"""
    profile = load_profile()
    profile["positions"] = [entry for entry in profile["positions"] if entry["stock_code"] != stock_code]
    return save_profile(profile)
