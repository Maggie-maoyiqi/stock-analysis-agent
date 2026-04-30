"""LangGraph状态定义。"""
import operator
from typing import Annotated, List, Optional, TypedDict


class AgentState(TypedDict):
    """Agent工作流状态。"""

    user_query: str
    stock_code: str
    stock_name: str
    fundamental_analysis: Optional[str]
    technical_analysis: Optional[str]
    value_analysis: Optional[str]
    news_analysis: Optional[str]
    forecast_analysis: Optional[str]
    final_report: Optional[str]
    report_file: Optional[str]
    current_date: str
    execution_time: float
    errors: Annotated[List[str], operator.add]
