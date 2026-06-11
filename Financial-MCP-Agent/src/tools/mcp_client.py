"""MCP client with a shared persistent stdio session."""
from __future__ import annotations

import asyncio
import json
import logging
from contextlib import AsyncExitStack, asynccontextmanager
from contextvars import ContextVar
from typing import Iterable, List, Sequence, Tuple

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from .mcp_config import SERVER_CONFIGS

logger = logging.getLogger(__name__)


class ToolRequestCache:
    """Per-analysis MCP tool cache with in-flight request deduplication."""

    def __init__(self):
        self.results: dict[str, str] = {}
        self.inflight: dict[str, asyncio.Task[str]] = {}

    @staticmethod
    def make_key(tool_name: str, arguments: dict) -> str:
        return json.dumps(
            {"tool_name": tool_name, "arguments": arguments},
            ensure_ascii=False,
            sort_keys=True,
        )


_tool_cache_var: ContextVar[ToolRequestCache | None] = ContextVar("tool_request_cache", default=None)


class MCPClient:
    """Manage a single MCP stdio session."""

    def __init__(self):
        self.session = None
        self.exit_stack = AsyncExitStack()
        self._tools = None
        self._connected_server = None
        self._connect_lock = asyncio.Lock()

    async def connect(self, server_name: str = "a_share_mcp"):
        """Connect to the MCP server once and reuse the session."""
        async with self._connect_lock:
            if self.session and self._connected_server == server_name:
                return self._tools or []

            config = SERVER_CONFIGS.get(server_name)
            if not config:
                raise ValueError(f"未找到服务器配置: {server_name}")

            server_params = StdioServerParameters(command=config["command"], args=config["args"])
            stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
            self.stdio, self.write = stdio_transport
            self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
            await self.session.initialize()
            self._connected_server = server_name
            response = await self.session.list_tools()
            self._tools = response.tools
            logger.info("已连接到MCP服务器: %s，工具数: %s", server_name, len(self._tools))
            return self._tools

    async def call_tool(self, tool_name: str, arguments: dict) -> str:
        """Call a tool on the active session."""
        if not self.session:
            await self.connect()

        result = await self.session.call_tool(tool_name, arguments=arguments)
        if result.content:
            return "\n".join(getattr(item, "text", str(item)) for item in result.content)
        return ""

    async def reset(self):
        """Close the current session so it can be rebuilt."""
        await self.exit_stack.aclose()
        self.exit_stack = AsyncExitStack()
        self.session = None
        self._tools = None
        self._connected_server = None


_shared_client = MCPClient()
_client_lock = asyncio.Lock()


async def get_mcp_tools():
    """Return the list of registered tools."""
    async with _client_lock:
        return await _shared_client.connect()


async def _call_with_retry(tool_name: str, arguments: dict) -> str:
    await _shared_client.connect()
    try:
        return await _shared_client.call_tool(tool_name, arguments)
    except Exception:
        logger.warning("MCP工具调用失败，尝试重建会话: %s", tool_name, exc_info=True)
        await _shared_client.reset()
        await _shared_client.connect()
        return await _shared_client.call_tool(tool_name, arguments)


async def _run_tool_uncached(tool_name: str, arguments: dict) -> str:
    async with _client_lock:
        return await _call_with_retry(tool_name, arguments)


@asynccontextmanager
async def analysis_tool_cache():
    """Cache repeated tool calls for a single analysis run."""
    token = _tool_cache_var.set(ToolRequestCache())
    try:
        yield
    finally:
        _tool_cache_var.reset(token)


async def run_tools(tool_calls: Sequence[Tuple[str, dict]]) -> str:
    """Call multiple tools sequentially and join the outputs."""
    outputs: List[str] = []
    for tool_name, arguments in tool_calls:
        result = await run_tool(tool_name, arguments)
        outputs.append(f"## 工具: {tool_name}\n参数: {arguments}\n结果:\n{result}\n")
    return "\n".join(outputs)


async def run_tool(tool_name: str, arguments: dict | None = None) -> str:
    """Call a single tool and return plain text."""
    resolved_arguments = arguments or {}
    cache = _tool_cache_var.get()
    if not cache:
        return await _run_tool_uncached(tool_name, resolved_arguments)

    cache_key = cache.make_key(tool_name, resolved_arguments)
    if cache_key in cache.results:
        return cache.results[cache_key]

    task = cache.inflight.get(cache_key)
    if task is None:
        task = asyncio.create_task(_run_tool_uncached(tool_name, resolved_arguments))
        cache.inflight[cache_key] = task

    try:
        result = await task
        cache.results[cache_key] = result
        return result
    finally:
        if cache.inflight.get(cache_key) is task:
            cache.inflight.pop(cache_key, None)


async def run_tool_json(tool_name: str, arguments: dict | None = None) -> dict:
    """Call a single tool and parse JSON output."""
    result = await run_tool(tool_name, arguments)
    try:
        return json.loads(result)
    except json.JSONDecodeError as exc:
        raise ValueError(f"工具 {tool_name} 返回的不是合法 JSON: {result[:200]}") from exc


def print_tool_details(tools: Iterable):
    """Print tool metadata for debugging."""
    logger.info("工具详细信息:")
    for index, tool in enumerate(tools, 1):
        logger.info("  %s. 工具名称: %s", index, tool.name)
        logger.info("     描述: %s", tool.description)
