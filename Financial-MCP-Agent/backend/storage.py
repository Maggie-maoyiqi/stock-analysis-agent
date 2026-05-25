"""SQLite-backed storage for profiles, tasks, and generated briefs."""
from __future__ import annotations

import json
import os
import sqlite3
import threading
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
LEGACY_PROFILE_PATH = DATA_DIR / "user_profile.json"
DB_PATH = Path(os.getenv("APP_DB_PATH", str(DATA_DIR / "financial_agent.db")))

DEFAULT_PROFILE: Dict[str, Any] = {
    "risk_preference": "稳健",
    "recommendation_count": 5,
    "primary_market": "cn",
    "active_markets": ["cn", "hk", "us"],
    "delivery_schedule": {"morning": "09:00", "evening": "21:00"},
    "watchlist": [],
    "positions": [],
}

_LOCK = threading.Lock()


def _utcnow() -> str:
    return datetime.utcnow().isoformat()


def _connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    return connection


def _dump_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _load_json(value: Optional[str], fallback: Any) -> Any:
    if not value:
        return deepcopy(fallback)
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return deepcopy(fallback)


def init_db() -> None:
    """Create tables and bootstrap the default profile."""
    with _LOCK:
        connection = _connect()
        try:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS profiles (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    risk_preference TEXT NOT NULL,
                    recommendation_count INTEGER NOT NULL,
                    primary_market TEXT NOT NULL,
                    active_markets TEXT NOT NULL,
                    delivery_schedule TEXT NOT NULL,
                    watchlist TEXT NOT NULL,
                    positions TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS analysis_tasks (
                    task_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    query TEXT NOT NULL,
                    stock_code TEXT,
                    stock_name TEXT,
                    final_report TEXT,
                    report_file TEXT,
                    fundamental_analysis TEXT,
                    technical_analysis TEXT,
                    value_analysis TEXT,
                    news_analysis TEXT,
                    forecast_analysis TEXT,
                    error TEXT,
                    progress_percent REAL NOT NULL,
                    step_statuses TEXT NOT NULL,
                    step_progresses TEXT NOT NULL,
                    step_messages TEXT NOT NULL,
                    charts TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    execution_time REAL
                );

                CREATE TABLE IF NOT EXISTS briefs (
                    brief_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    session TEXT NOT NULL,
                    generated_at TEXT NOT NULL,
                    markdown TEXT NOT NULL,
                    markdown_file TEXT NOT NULL,
                    docx_file TEXT NOT NULL,
                    charts TEXT NOT NULL,
                    report_payload TEXT NOT NULL
                );
                """
            )

            row = connection.execute("SELECT id FROM profiles WHERE id = 1").fetchone()
            if row is None:
                profile = deepcopy(DEFAULT_PROFILE)
                if LEGACY_PROFILE_PATH.exists():
                    try:
                        legacy = json.loads(LEGACY_PROFILE_PATH.read_text(encoding="utf-8"))
                        profile.update({key: value for key, value in legacy.items() if value is not None})
                    except Exception:
                        pass
                now = _utcnow()
                connection.execute(
                    """
                    INSERT INTO profiles (
                        id, risk_preference, recommendation_count, primary_market,
                        active_markets, delivery_schedule, watchlist, positions,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        1,
                        profile["risk_preference"],
                        int(profile["recommendation_count"]),
                        profile["primary_market"],
                        _dump_json(profile["active_markets"]),
                        _dump_json(profile["delivery_schedule"]),
                        _dump_json(profile["watchlist"]),
                        _dump_json(profile["positions"]),
                        now,
                        now,
                    ),
                )
            connection.commit()
        finally:
            connection.close()


def load_profile() -> Dict[str, Any]:
    init_db()
    with _LOCK:
        connection = _connect()
        try:
            row = connection.execute("SELECT * FROM profiles WHERE id = 1").fetchone()
            if row is None:
                return deepcopy(DEFAULT_PROFILE)
            return {
                "risk_preference": row["risk_preference"],
                "recommendation_count": row["recommendation_count"],
                "primary_market": row["primary_market"],
                "active_markets": _load_json(row["active_markets"], DEFAULT_PROFILE["active_markets"]),
                "delivery_schedule": _load_json(row["delivery_schedule"], DEFAULT_PROFILE["delivery_schedule"]),
                "watchlist": _load_json(row["watchlist"], []),
                "positions": _load_json(row["positions"], []),
            }
        finally:
            connection.close()


def save_profile(profile: Dict[str, Any]) -> Dict[str, Any]:
    init_db()
    with _LOCK:
        connection = _connect()
        try:
            now = _utcnow()
            connection.execute(
                """
                UPDATE profiles
                SET risk_preference = ?, recommendation_count = ?, primary_market = ?,
                    active_markets = ?, delivery_schedule = ?, watchlist = ?, positions = ?,
                    updated_at = ?
                WHERE id = 1
                """,
                (
                    profile["risk_preference"],
                    int(profile["recommendation_count"]),
                    profile["primary_market"],
                    _dump_json(profile["active_markets"]),
                    _dump_json(profile["delivery_schedule"]),
                    _dump_json(profile["watchlist"]),
                    _dump_json(profile["positions"]),
                    now,
                ),
            )
            connection.commit()
        finally:
            connection.close()
    return profile


def create_task_record(record: Dict[str, Any]) -> Dict[str, Any]:
    init_db()
    with _LOCK:
        connection = _connect()
        try:
            connection.execute(
                """
                INSERT INTO analysis_tasks (
                    task_id, status, query, stock_code, stock_name, final_report, report_file,
                    fundamental_analysis, technical_analysis, value_analysis, news_analysis,
                    forecast_analysis, error, progress_percent, step_statuses, step_progresses,
                    step_messages, charts, created_at, updated_at, execution_time
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record["task_id"],
                    record["status"],
                    record["query"],
                    record.get("stock_code"),
                    record.get("stock_name"),
                    record.get("final_report"),
                    record.get("report_file"),
                    record.get("fundamental_analysis"),
                    record.get("technical_analysis"),
                    record.get("value_analysis"),
                    record.get("news_analysis"),
                    record.get("forecast_analysis"),
                    record.get("error"),
                    float(record.get("progress_percent", 0.0)),
                    _dump_json(record.get("step_statuses", {})),
                    _dump_json(record.get("step_progresses", {})),
                    _dump_json(record.get("step_messages", {})),
                    _dump_json(record.get("charts", [])),
                    record["created_at"],
                    record["updated_at"],
                    record.get("execution_time"),
                ),
            )
            connection.commit()
        finally:
            connection.close()
    return record


def update_task_record(task_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    init_db()
    columns = {
        "status",
        "query",
        "stock_code",
        "stock_name",
        "final_report",
        "report_file",
        "fundamental_analysis",
        "technical_analysis",
        "value_analysis",
        "news_analysis",
        "forecast_analysis",
        "error",
        "progress_percent",
        "step_statuses",
        "step_progresses",
        "step_messages",
        "charts",
        "created_at",
        "updated_at",
        "execution_time",
    }
    payload = {key: value for key, value in updates.items() if key in columns}
    if "step_statuses" in payload:
        payload["step_statuses"] = _dump_json(payload["step_statuses"])
    if "step_progresses" in payload:
        payload["step_progresses"] = _dump_json(payload["step_progresses"])
    if "step_messages" in payload:
        payload["step_messages"] = _dump_json(payload["step_messages"])
    if "charts" in payload:
        payload["charts"] = _dump_json(payload["charts"])

    assignments = ", ".join(f"{key} = ?" for key in payload)
    values = list(payload.values())
    values.append(task_id)

    with _LOCK:
        connection = _connect()
        try:
            if assignments:
                connection.execute(f"UPDATE analysis_tasks SET {assignments} WHERE task_id = ?", values)
                connection.commit()
            row = connection.execute("SELECT * FROM analysis_tasks WHERE task_id = ?", (task_id,)).fetchone()
            return _task_row_to_dict(row) if row else {}
        finally:
            connection.close()


def get_task_record(task_id: str) -> Optional[Dict[str, Any]]:
    init_db()
    with _LOCK:
        connection = _connect()
        try:
            row = connection.execute("SELECT * FROM analysis_tasks WHERE task_id = ?", (task_id,)).fetchone()
            return _task_row_to_dict(row) if row else None
        finally:
            connection.close()


def _task_row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "task_id": row["task_id"],
        "status": row["status"],
        "query": row["query"],
        "stock_code": row["stock_code"],
        "stock_name": row["stock_name"],
        "final_report": row["final_report"],
        "report_file": row["report_file"],
        "fundamental_analysis": row["fundamental_analysis"],
        "technical_analysis": row["technical_analysis"],
        "value_analysis": row["value_analysis"],
        "news_analysis": row["news_analysis"],
        "forecast_analysis": row["forecast_analysis"],
        "error": row["error"],
        "progress_percent": row["progress_percent"],
        "step_statuses": _load_json(row["step_statuses"], {}),
        "step_progresses": _load_json(row["step_progresses"], {}),
        "step_messages": _load_json(row["step_messages"], {}),
        "charts": _load_json(row["charts"], []),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "execution_time": row["execution_time"],
    }


def save_brief_record(brief_id: str, report: Dict[str, Any]) -> Dict[str, Any]:
    init_db()
    with _LOCK:
        connection = _connect()
        try:
            connection.execute(
                """
                INSERT OR REPLACE INTO briefs (
                    brief_id, title, session, generated_at, markdown, markdown_file,
                    docx_file, charts, report_payload
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    brief_id,
                    report["title"],
                    report["session"],
                    report["generated_at"],
                    report["markdown"],
                    report["markdown_file"],
                    report["docx_file"],
                    _dump_json(report.get("charts", [])),
                    _dump_json(report),
                ),
            )
            connection.commit()
        finally:
            connection.close()
    return report
