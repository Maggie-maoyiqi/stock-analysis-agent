"""API schemas."""
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class AnalysisCreateRequest(BaseModel):
    """创建分析任务请求。"""

    query: str = Field(..., min_length=1, max_length=500, description="用户输入的股票分析问题")


class AnalysisCreateResponse(BaseModel):
    """创建分析任务响应。"""

    task_id: str
    status: Literal["queued", "running", "completed", "failed"]
    message: str


class AnalysisTaskResponse(BaseModel):
    """查询分析任务响应。"""

    task_id: str
    status: Literal["queued", "running", "completed", "failed"]
    query: str
    stock_code: Optional[str] = None
    stock_name: Optional[str] = None
    final_report: Optional[str] = None
    report_file: Optional[str] = None
    fundamental_analysis: Optional[str] = None
    technical_analysis: Optional[str] = None
    value_analysis: Optional[str] = None
    news_analysis: Optional[str] = None
    forecast_analysis: Optional[str] = None
    error: Optional[str] = None
    progress_percent: float = 0.0
    step_statuses: Dict[str, str] = Field(default_factory=dict)
    step_progresses: Dict[str, float] = Field(default_factory=dict)
    step_messages: Dict[str, str] = Field(default_factory=dict)
    created_at: str
    updated_at: str
    execution_time: Optional[float] = None


class WatchlistItem(BaseModel):
    """自选股条目。"""

    stock_code: str
    stock_name: Optional[str] = None
    market: Optional[str] = None
    notes: Optional[str] = ""


class PositionItem(BaseModel):
    """持仓条目。"""

    stock_code: str
    stock_name: Optional[str] = None
    buy_price: float
    quantity: int
    buy_date: str
    stop_loss_pct: float = 8.0
    take_profit_drawdown_pct: float = 15.0
    notes: Optional[str] = ""


class ProfileResponse(BaseModel):
    """用户档案响应。"""

    risk_preference: str
    recommendation_count: int
    primary_market: str
    active_markets: List[str]
    delivery_schedule: Dict[str, str]
    watchlist: List[Dict[str, Any]]
    positions: List[Dict[str, Any]]


class ProfileUpdateRequest(BaseModel):
    """更新用户档案。"""

    risk_preference: Optional[str] = None
    recommendation_count: Optional[int] = None
    primary_market: Optional[str] = None
    active_markets: Optional[List[str]] = None
    delivery_schedule: Optional[Dict[str, str]] = None


class BriefGenerateRequest(BaseModel):
    """生成简报请求。"""

    session: Literal["morning", "evening"] = "morning"


class BriefGenerateResponse(BaseModel):
    """生成简报响应。"""

    title: str
    generated_at: str
    session: Literal["morning", "evening"]
    markdown: str
    markdown_file: str
    docx_file: str
    watchlist_reviews: List[Dict[str, Any]]
    position_reviews: List[Dict[str, Any]]
    recommendations: List[Dict[str, Any]]
