"""MCP客户端。"""
import asyncio
import json
import logging
from contextlib import AsyncExitStack
from typing import Iterable, List, Sequence, Tuple

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from .mcp_config import SERVER_CONFIGS

logger = logging.getLogger(__name__)


class MCPClient:
    """MCP客户端管理器。"""

    def __init__(self):
        self.session = None
        self.exit_stack = AsyncExitStack()
        self._tools = None
        self._connected_server = None

    async def connect(self, server_name: str = "a_share_mcp"):
        """连接到MCP服务器。"""
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
        """调用MCP工具。"""
        if not self.session:
            raise RuntimeError("未连接到MCP服务器")

        result = await self.session.call_tool(tool_name, arguments=arguments)
        if result.content:
            return "\n".join(getattr(item, "text", str(item)) for item in result.content)
        return ""

    async def close(self):
        """关闭连接。"""
        await self.exit_stack.aclose()
        self.session = None
        self._tools = None
        self._connected_server = None
        logger.info("MCP客户端连接已关闭")


_client_lock = asyncio.Lock()


async def get_mcp_tools():
    """获取MCP工具列表。"""
    client = MCPClient()
    try:
        return await client.connect()
    finally:
        await client.close()


async def run_tools(tool_calls: Sequence[Tuple[str, dict]]) -> str:
    """串行调用一组工具并汇总结果。"""
    async with _client_lock:
        client = MCPClient()
        try:
            await client.connect()
            outputs: List[str] = []
            for tool_name, arguments in tool_calls:
                result = await client.call_tool(tool_name, arguments)
                outputs.append(f"## 工具: {tool_name}\n参数: {arguments}\n结果:\n{result}\n")
            return "\n".join(outputs)
        finally:
            await client.close()


async def run_tool(tool_name: str, arguments: dict | None = None) -> str:
    """调用单个工具并返回文本。"""
    async with _client_lock:
        client = MCPClient()
        try:
            await client.connect()
            return await client.call_tool(tool_name, arguments or {})
        finally:
            await client.close()


async def run_tool_json(tool_name: str, arguments: dict | None = None) -> dict:
    """调用单个工具并解析 JSON。"""
    result = await run_tool(tool_name, arguments)
    try:
        return json.loads(result)
    except json.JSONDecodeError as exc:
        raise ValueError(f"工具 {tool_name} 返回的不是合法 JSON: {result[:200]}") from exc


def print_tool_details(tools: Iterable):
    """打印工具详细信息（调试用）。"""
    logger.info("工具详细信息:")
    for index, tool in enumerate(tools, 1):
        logger.info("  %s. 工具名称: %s", index, tool.name)
        logger.info("     描述: %s", tool.description)
