"""Run local smoke checks without calling market data or an LLM."""
from __future__ import annotations

import compileall
import os
import subprocess
import sys
from pathlib import Path

from dotenv import dotenv_values


ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = ROOT / "Financial-MCP-Agent"
MCP_ROOT = ROOT / "a-share-mcp-is-just-i-need"


def check(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)
    print(f"[ok] {message}")


def main() -> None:
    check(sys.version_info >= (3, 10), "Python version is 3.10+")
    check((MCP_ROOT / "mcp_server.py").is_file(), "MCP server path exists")
    check(compileall.compile_dir(APP_ROOT, quiet=1), "Financial-MCP-Agent compiles")
    check(compileall.compile_dir(MCP_ROOT, quiet=1), "MCP service compiles")

    env = os.environ.copy()
    env["PYTHONPATH"] = str(APP_ROOT)
    backend = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from fastapi.testclient import TestClient;"
                "from backend.main import app;"
                "r=TestClient(app).get('/api/health');"
                "assert r.status_code == 200 and r.json() == {'status': 'ok'}"
            ),
        ],
        cwd=APP_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    check(backend.returncode == 0, f"backend health check passes{': ' + backend.stderr.strip() if backend.stderr else ''}")

    mcp = subprocess.run(
        [sys.executable, "-c", "import mcp_server; assert len(mcp_server.mcp._tool_manager.list_tools()) >= 20"],
        cwd=MCP_ROOT,
        capture_output=True,
        text=True,
    )
    check(mcp.returncode == 0, f"MCP server imports and registers tools{': ' + mcp.stderr.strip() if mcp.stderr else ''}")

    key = os.getenv("OPENAI_COMPATIBLE_API_KEY") or dotenv_values(APP_ROOT / ".env").get("OPENAI_COMPATIBLE_API_KEY", "")
    if not key:
        print("[warn] OPENAI_COMPATIBLE_API_KEY is not set; LLM analysis will not run")
    print("\nSmoke test passed.")


if __name__ == "__main__":
    main()
