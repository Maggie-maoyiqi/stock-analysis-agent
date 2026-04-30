"""市场代码识别与转换工具。"""
from __future__ import annotations

import re


def detect_market(stock_code: str) -> str:
    """根据股票代码识别市场类型。"""
    code = (stock_code or "").strip()
    upper_code = code.upper()

    if code.startswith(("sh.", "sz.")):
        return "cn"
    if upper_code.endswith(".HK") or code.startswith("hk."):
        return "hk"
    if re.fullmatch(r"[A-Z][A-Z0-9.\-]{0,9}", upper_code):
        return "us"
    if re.fullmatch(r"\d{6}", code):
        return "cn"
    if re.fullmatch(r"\d{4,5}", code):
        return "hk"
    return "unknown"


def to_yfinance_ticker(stock_code: str) -> str:
    """转换为 Yahoo Finance 可识别的代码。"""
    code = (stock_code or "").strip()
    market = detect_market(code)

    if market == "cn":
        if code.startswith("sh."):
            return f"{code.split('.', 1)[1]}.SS"
        if code.startswith("sz."):
            return f"{code.split('.', 1)[1]}.SZ"
        return f"{code}.SS"

    if market == "hk":
        if code.startswith("hk."):
            digits = re.sub(r"\D", "", code.split(".", 1)[1])
        else:
            digits = re.sub(r"\D", "", code.replace(".HK", "").replace(".hk", ""))
        return f"{digits[-4:].zfill(4)}.HK"

    if market == "us":
        return code.upper()

    return code
