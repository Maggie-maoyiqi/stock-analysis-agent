"""基于 yfinance 的多市场数据源实现。"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
import yfinance as yf

from .data_source_interface import DataSourceError, FinancialDataSource
from .market_utils import to_yfinance_ticker


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    normalized = df.reset_index().copy()
    if "Date" not in normalized.columns:
        first_col = normalized.columns[0]
        normalized = normalized.rename(columns={first_col: "Date"})

    rename_map = {
        "Date": "date",
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Adj Close": "adj_close",
        "Volume": "volume",
    }
    normalized = normalized.rename(columns=rename_map)
    normalized["date"] = pd.to_datetime(normalized["date"]).dt.strftime("%Y-%m-%d")
    return normalized


def _find_row(frame: pd.DataFrame, candidates: List[str]) -> Optional[pd.Series]:
    if frame is None or frame.empty:
        return None

    lowered_index = {str(idx).lower(): idx for idx in frame.index}
    for candidate in candidates:
        for lowered, original in lowered_index.items():
            if candidate.lower() == lowered or candidate.lower() in lowered:
                return frame.loc[original]
    return None


def _latest_and_previous(row: Optional[pd.Series]) -> tuple[float, float]:
    if row is None:
        return 0.0, 0.0
    values = pd.to_numeric(row, errors="coerce").dropna().tolist()
    if not values:
        return 0.0, 0.0
    latest = float(values[0])
    previous = float(values[1]) if len(values) > 1 else 0.0
    return latest, previous


class YFinanceDataSource(FinancialDataSource):
    """yfinance 数据源，覆盖美股、港股和部分A股镜像行情。"""

    def _get_ticker(self, stock_code: str) -> yf.Ticker:
        return yf.Ticker(to_yfinance_ticker(stock_code))

    def _get_info_payload(self, ticker: yf.Ticker) -> Dict[str, Any]:
        """兼容不同 yfinance 版本的 info 读取方式。"""
        try:
            info = ticker.get_info()
            if info:
                return info
        except Exception:
            pass

        try:
            info = ticker.info
            if info:
                return info
        except Exception:
            pass

        return {}

    def get_historical_k_data(
        self,
        stock_code: str,
        start_date: str,
        end_date: str,
        frequency: str = "d",
        adjustflag: str = "2",
    ) -> List[Dict[str, Any]]:
        ticker = self._get_ticker(stock_code)
        interval_map = {"d": "1d", "w": "1wk", "m": "1mo"}
        history = ticker.history(
            start=start_date,
            end=end_date,
            interval=interval_map.get(frequency, "1d"),
            auto_adjust=False,
            repair=True,
            raise_errors=False,
        )
        normalized = _normalize_columns(history)
        if normalized.empty:
            raise DataSourceError(f"未获取到 {stock_code} 的历史行情数据")

        rows: List[Dict[str, Any]] = []
        previous_close = 0.0
        for _, row in normalized.iterrows():
            close = _safe_float(row.get("close"))
            pct = ((close - previous_close) / previous_close * 100) if previous_close else 0.0
            rows.append(
                {
                    "date": row.get("date", ""),
                    "code": to_yfinance_ticker(stock_code),
                    "open": row.get("open", ""),
                    "high": row.get("high", ""),
                    "low": row.get("low", ""),
                    "close": row.get("close", ""),
                    "preclose": previous_close,
                    "volume": row.get("volume", ""),
                    "amount": "",
                    "adjustflag": adjustflag,
                    "turn": "",
                    "tradestatus": "1",
                    "pctChg": f"{pct:.2f}",
                    "peTTM": "",
                    "pbMRQ": "",
                }
            )
            previous_close = close
        return rows

    def get_stock_basic_info(self, stock_code: str, fields: Optional[List[str]] = None) -> Dict[str, Any]:
        ticker = self._get_ticker(stock_code)
        info = self._get_info_payload(ticker)
        fast_info = dict(getattr(ticker, "fast_info", {}) or {})
        result = {
            "code": to_yfinance_ticker(stock_code),
            "name": info.get("longName") or info.get("shortName") or stock_code,
            "ipoDate": info.get("firstTradeDateEpochUtc", ""),
            "outDate": "",
            "type": info.get("quoteType", ""),
            "status": "ACTIVE",
            "exchange": info.get("exchange", ""),
            "currency": info.get("currency", ""),
            "market_cap": info.get("marketCap") or fast_info.get("marketCap", ""),
            "pe_ttm": info.get("trailingPE") or fast_info.get("trailingPE", ""),
            "pb_mrq": info.get("priceToBook", ""),
            "sector": info.get("sector", ""),
            "industry": info.get("industry", ""),
            "previous_close": fast_info.get("previousClose", info.get("previousClose", "")),
        }
        if fields:
            return {field: result.get(field, "") for field in fields}
        return result

    def get_profit_data(self, stock_code: str, year: int, quarter: int) -> Dict[str, Any]:
        ticker = self._get_ticker(stock_code)
        income_stmt = ticker.quarterly_income_stmt
        balance_sheet = ticker.quarterly_balance_sheet

        revenue_row = _find_row(income_stmt, ["Total Revenue", "Operating Revenue"])
        net_income_row = _find_row(income_stmt, ["Net Income", "Net Income Common Stockholders"])
        gross_profit_row = _find_row(income_stmt, ["Gross Profit"])
        equity_row = _find_row(balance_sheet, ["Stockholders Equity", "Common Stock Equity", "Total Equity Gross Minority Interest"])
        eps_row = _find_row(income_stmt, ["Diluted EPS", "Basic EPS"])

        revenue, _ = _latest_and_previous(revenue_row)
        net_income, _ = _latest_and_previous(net_income_row)
        gross_profit, _ = _latest_and_previous(gross_profit_row)
        equity, _ = _latest_and_previous(equity_row)
        eps, _ = _latest_and_previous(eps_row)

        return {
            "roe": round((net_income / equity * 100), 2) if equity else "",
            "net_profit_rate": round((net_income / revenue * 100), 2) if revenue else "",
            "gross_profit_rate": round((gross_profit / revenue * 100), 2) if revenue else "",
            "eps": round(eps, 4) if eps else "",
            "year": year,
            "quarter": quarter,
        }

    def get_growth_data(self, stock_code: str, year: int, quarter: int) -> Dict[str, Any]:
        ticker = self._get_ticker(stock_code)
        income_stmt = ticker.quarterly_income_stmt

        revenue_row = _find_row(income_stmt, ["Total Revenue", "Operating Revenue"])
        net_income_row = _find_row(income_stmt, ["Net Income", "Net Income Common Stockholders"])
        eps_row = _find_row(income_stmt, ["Diluted EPS", "Basic EPS"])

        revenue_latest, revenue_previous = _latest_and_previous(revenue_row)
        net_income_latest, net_income_previous = _latest_and_previous(net_income_row)
        eps_latest, eps_previous = _latest_and_previous(eps_row)

        def yoy(latest: float, previous: float) -> str:
            if previous == 0:
                return ""
            return round((latest - previous) / abs(previous) * 100, 2)

        return {
            "yoy_net_profit": yoy(net_income_latest, net_income_previous),
            "yoy_revenue": yoy(revenue_latest, revenue_previous),
            "yoy_eps": yoy(eps_latest, eps_previous),
            "year": year,
            "quarter": quarter,
        }

    def get_balance_data(self, stock_code: str, year: int, quarter: int) -> Dict[str, Any]:
        ticker = self._get_ticker(stock_code)
        balance_sheet = ticker.quarterly_balance_sheet

        total_assets_row = _find_row(balance_sheet, ["Total Assets"])
        total_liab_row = _find_row(balance_sheet, ["Total Liabilities Net Minority Interest", "Total Liabilities"])
        current_assets_row = _find_row(balance_sheet, ["Current Assets", "Total Current Assets"])
        current_liab_row = _find_row(balance_sheet, ["Current Liabilities", "Total Current Liabilities"])

        total_assets, _ = _latest_and_previous(total_assets_row)
        total_liab, _ = _latest_and_previous(total_liab_row)
        current_assets, _ = _latest_and_previous(current_assets_row)
        current_liab, _ = _latest_and_previous(current_liab_row)

        return {
            "asset_debt_ratio": total_liab / total_assets if total_assets else 0,
            "total_assets": total_assets,
            "total_liabilities": total_liab,
            "current_ratio": round(current_assets / current_liab, 2) if current_liab else 0,
            "year": year,
            "quarter": quarter,
        }

    def get_cash_flow_data(self, stock_code: str, year: int, quarter: int) -> Dict[str, Any]:
        ticker = self._get_ticker(stock_code)
        cashflow = ticker.quarterly_cashflow

        operating_row = _find_row(cashflow, ["Operating Cash Flow", "Cash Flow From Continuing Operating Activities"])
        free_cash_row = _find_row(cashflow, ["Free Cash Flow"])
        operating_cash_flow, _ = _latest_and_previous(operating_row)
        free_cash_flow, _ = _latest_and_previous(free_cash_row)

        return {
            "operating_cash_flow": operating_cash_flow,
            "free_cash_flow": free_cash_flow,
            "year": year,
            "quarter": quarter,
        }

    def get_dividend_data(self, stock_code: str, year: int) -> List[Dict[str, Any]]:
        ticker = self._get_ticker(stock_code)
        dividends = getattr(ticker, "dividends", None)
        if dividends is None or dividends.empty:
            return []

        year_mask = dividends.index.year == year
        filtered = dividends[year_mask]
        results = []
        for index, value in filtered.items():
            results.append(
                {
                    "year": str(index.year),
                    "dividend_per_share": round(float(value), 4),
                    "ex_dividend_date": index.strftime("%Y-%m-%d"),
                }
            )
        return results

    def get_hs300_stocks(self, date: Optional[str] = None) -> List[str]:
        return []

    def get_zz500_stocks(self, date: Optional[str] = None) -> List[str]:
        return []

    def get_sz50_stocks(self, date: Optional[str] = None) -> List[str]:
        return []

    def get_news(self, stock_code: str, top_k: int = 10) -> List[Dict[str, Any]]:
        ticker = self._get_ticker(stock_code)
        try:
            items = ticker.get_news(count=top_k)
        except Exception:
            try:
                items = ticker.news
            except Exception:
                items = []

        results = []
        for item in items[:top_k]:
            content = item.get("content", item)
            title = content.get("title") or item.get("title") or "未命名新闻"
            summary = (
                content.get("summary")
                or content.get("description")
                or item.get("summary")
                or "暂无摘要"
            )
            url = content.get("canonicalUrl", {}).get("url") or content.get("clickThroughUrl", {}).get("url") or item.get("link") or ""
            results.append(
                {
                    "title": title,
                    "summary": summary,
                    "url": url,
                    "publisher": content.get("provider", {}).get("displayName", ""),
                    "published_at": content.get("pubDate", ""),
                }
            )
        return results
