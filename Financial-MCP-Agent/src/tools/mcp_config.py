"""MCP服务器配置。"""
import os
import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parents[1]
DEFAULT_MCP_PATH = (PROJECT_ROOT / "../a-share-mcp-is-just-i-need").resolve()


def _resolve_mcp_path() -> Path:
    configured = os.environ.get("A_SHARE_MCP_PATH")
    if not configured:
        return DEFAULT_MCP_PATH
    configured_path = Path(configured)
    if configured_path.is_absolute():
        return configured_path.resolve()
    return (PROJECT_ROOT / configured_path).resolve()


A_SHARE_MCP_PATH = _resolve_mcp_path()

SERVER_CONFIGS = {
    "a_share_mcp": {
        "command": sys.executable,
        "args": [str(A_SHARE_MCP_PATH / "mcp_server.py")],
        "transport": "stdio",
    }
}
