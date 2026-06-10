"""FastAPI backend entrypoint."""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

from backend.storage import init_db  # noqa: E402
from backend.schemas import (  # noqa: E402
    AnalysisCreateRequest,
    AnalysisCreateResponse,
    AnalysisTaskResponse,
    BriefGenerateRequest,
    BriefGenerateResponse,
    PositionItem,
    ProfileResponse,
    ProfileUpdateRequest,
    WatchlistItem,
)
from backend.task_manager import task_manager  # noqa: E402
from src.services.briefing_service import generate_daily_brief  # noqa: E402
from src.services.profile_service import (  # noqa: E402
    add_position,
    add_watchlist_item,
    load_profile,
    remove_position,
    remove_watchlist_item,
    update_profile,
)

app = FastAPI(
    title="Financial MCP Agent API",
    version="1.0.0",
    description="A股智能分析系统后端接口",
)
init_db()

frontend_origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_origin, "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health_check():
    """健康检查。"""
    return {"status": "ok"}


@app.post("/api/analysis", response_model=AnalysisCreateResponse)
async def create_analysis(request: AnalysisCreateRequest):
    """创建分析任务。"""
    record = task_manager.create_task(request.query)
    return AnalysisCreateResponse(
        task_id=record["task_id"],
        status=record["status"],
        message="分析任务已创建，前端可通过 SSE 实时订阅任务状态。",
    )


@app.get("/api/analysis/{task_id}", response_model=AnalysisTaskResponse)
async def get_analysis(task_id: str):
    """获取分析任务状态与结果。"""
    record = task_manager.get_task(task_id)
    if not record:
        raise HTTPException(status_code=404, detail="任务不存在")
    return AnalysisTaskResponse(**record)


@app.get("/api/analysis/{task_id}/stream")
async def stream_analysis(task_id: str):
    """通过 SSE 推送分析任务状态。"""
    record = task_manager.get_task(task_id)
    if not record:
        raise HTTPException(status_code=404, detail="任务不存在")
    return StreamingResponse(
        task_manager.stream(task_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/profile", response_model=ProfileResponse)
async def get_profile():
    """获取用户档案。"""
    return ProfileResponse(**load_profile())


@app.put("/api/profile", response_model=ProfileResponse)
async def put_profile(request: ProfileUpdateRequest):
    """更新用户档案顶层设置。"""
    profile = update_profile(request.model_dump(exclude_none=True))
    return ProfileResponse(**profile)


@app.post("/api/profile/watchlist", response_model=ProfileResponse)
async def create_watchlist_item(request: WatchlistItem):
    """新增或更新自选股。"""
    profile = add_watchlist_item(request.model_dump())
    return ProfileResponse(**profile)


@app.delete("/api/profile/watchlist/{stock_code}", response_model=ProfileResponse)
async def delete_watchlist_item(stock_code: str):
    """移除自选股。"""
    profile = remove_watchlist_item(stock_code)
    return ProfileResponse(**profile)


@app.post("/api/profile/positions", response_model=ProfileResponse)
async def create_position(request: PositionItem):
    """新增或更新持仓。"""
    profile = add_position(request.model_dump())
    return ProfileResponse(**profile)


@app.delete("/api/profile/positions/{stock_code}", response_model=ProfileResponse)
async def delete_position(stock_code: str):
    """移除持仓。"""
    profile = remove_position(stock_code)
    return ProfileResponse(**profile)


@app.post("/api/briefs/generate", response_model=BriefGenerateResponse)
async def create_daily_brief(request: BriefGenerateRequest):
    """生成早报或晚报。"""
    report = await generate_daily_brief(request.session)
    return BriefGenerateResponse(**report)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
