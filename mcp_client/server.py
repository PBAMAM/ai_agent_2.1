import asyncio
import logging
from contextlib import AbstractAsyncContextManager, AsyncExitStack
from typing import Any, Optional

from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream
from livekit.agents import FunctionTool
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client
from mcp.types import CallToolResult, JSONRPCMessage, Tool as MCPTool
from typing_extensions import NotRequired, TypedDict

from .mcp_utils import mcp_to_function_tool

logger = logging.getLogger()


class MCPServer:
    async def connect(self):
        raise NotImplementedError

    @property
    def connected(self) -> bool:
        raise NotImplementedError

    @property
    def name(self) -> str:
        raise NotImplementedError

    async def list_tools(self) -> list[MCPTool]:
        raise NotImplementedError

    async def call_tool(
        self, tool_name: str, arguments: Optional[dict[str, Any]] = None
    ) -> CallToolResult:
        raise NotImplementedError

    async def cleanup(self):
        raise NotImplementedError

    async def get_agent_tools(self) -> list[FunctionTool]:
        tools = await self.list_tools()
        return [mcp_to_function_tool(tool, self.call_tool) for tool in tools]


class _MCPServerWithClientSession(MCPServer):
    def __init__(self, cache_tools_list: bool):
        self.session: Optional[ClientSession] = None
        self.exit_stack: AsyncExitStack = AsyncExitStack()
        self._cleanup_lock: asyncio.Lock = asyncio.Lock()
        self.cache_tools_list = cache_tools_list

        self._cache_dirty = True
        self._tools_list: Optional[list[MCPTool]] = None
        self.logger = logging.getLogger(__name__)

    @property
    def connected(self) -> bool:
        return self.session is not None

    def create_streams(
        self,
    ) -> AbstractAsyncContextManager[
        tuple[
            MemoryObjectReceiveStream[JSONRPCMessage | Exception],
            MemoryObjectSendStream[JSONRPCMessage],
        ]
    ]:
        raise NotImplementedError

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.cleanup()

    def invalidate_tools_cache(self):
        self._cache_dirty = True

    async def connect(self):
        try:
            transport = await self.exit_stack.enter_async_context(self.create_streams())
            read, write = transport
            session = await self.exit_stack.enter_async_context(
                ClientSession(read, write)
            )
            await session.initialize()
            self.session = session
            self.logger.info(f"Connected to MCP server: {self.name}")
        except Exception as e:
            self.logger.error(f"Error initializing MCP server: {e}")
            await self.cleanup()
            raise

    async def list_tools(self) -> list[MCPTool]:
        if not self.session:
            raise RuntimeError(
                "Server not initialized. Make sure you call connect() first."
            )

        if self.cache_tools_list and not self._cache_dirty and self._tools_list:
            return self._tools_list

        self._cache_dirty = False

        try:
            result = await self.session.list_tools()
            self._tools_list = result.tools
            return self._tools_list
        except Exception as e:
            self.logger.error(f"Error listing tools: {e}")
            raise

    async def call_tool(
        self, tool_name: str, arguments: Optional[dict[str, Any]] = None
    ) -> CallToolResult:
        if not self.session:
            raise RuntimeError(
                "Server not initialized. Make sure you call connect() first."
            )

        arguments = arguments or {}
        try:
            return await self.session.call_tool(tool_name, arguments)
        except Exception as e:
            self.logger.error(f"Error calling tool {tool_name}: {e}")
            raise

    async def cleanup(self):
        async with self._cleanup_lock:
            try:
                await self.exit_stack.aclose()
                self.session = None
                self.logger.info(f"Cleaned up MCP server: {self.name}")
            except Exception as e:
                self.logger.error(f"Error cleaning up server: {e}")


class MCPServerSseParams(TypedDict):
    url: str
    headers: NotRequired[dict[str, Any]]
    timeout: NotRequired[float]
    sse_read_timeout: NotRequired[float]


class MCPServerSse(_MCPServerWithClientSession):
    def __init__(
        self,
        params: MCPServerSseParams,
        cache_tools_list: bool = False,
        name: Optional[str] = None,
    ):
        super().__init__(cache_tools_list)
        self.params = params
        self._name = name or f"SSE Server at {self.params.get('url', 'unknown')}"

    def create_streams(
        self,
    ) -> AbstractAsyncContextManager[
        tuple[
            MemoryObjectReceiveStream[JSONRPCMessage | Exception],
            MemoryObjectSendStream[JSONRPCMessage],
        ]
    ]:
        return sse_client(
            url=self.params["url"],
            headers=self.params.get("headers"),
            timeout=self.params.get("timeout", 5),
            sse_read_timeout=self.params.get("sse_read_timeout", 60 * 5),
        )

    @property
    def name(self) -> str:
        return self._name