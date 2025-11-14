"""
Custom Claude LLM adapter for LiveKit Agents
"""

from __future__ import annotations

import logging
from typing import Optional, AsyncIterator, Any
from livekit.agents import llm
from livekit.agents.llm import ChatContext, ChatRole, ChatMessage
from anthropic import Anthropic
import os

# Try to import FunctionContext, but use Any as fallback if it doesn't exist
try:
    from livekit.agents.llm import FunctionContext
except ImportError:
    FunctionContext = Any

logger = logging.getLogger("claude-llm")


class ClaudeLLM(llm.LLM):
    """Claude LLM adapter for LiveKit Agents"""
    
    def __init__(
        self,
        *,
        model: str = "claude-3-5-sonnet-20241022",
        api_key: Optional[str] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.model = model
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY is required. Set it in environment variables or pass it directly.")
        
        self.client = Anthropic(api_key=self.api_key)
        logger.info(f"✅ Claude LLM initialized with model: {model}")
    
    def chat(
        self,
        *,
        ctx: ChatContext,
        fnc_ctx: Optional[FunctionContext] = None,
    ) -> "ClaudeChat":
        return ClaudeChat(self, ctx=ctx, fnc_ctx=fnc_ctx)


class ClaudeChat(llm.Chat):
    """Claude chat implementation"""
    
    def __init__(
        self,
        llm: ClaudeLLM,
        *,
        ctx: ChatContext,
        fnc_ctx: Optional[FunctionContext] = None,
    ):
        super().__init__(llm=llm, ctx=ctx, fnc_ctx=fnc_ctx)
        self._llm = llm
        self._ctx = ctx
        self._fnc_ctx = fnc_ctx
    
    async def achat(
        self,
        *,
        message: Optional[str] = None,
        functions: Optional[list[llm.Function]] = None,
    ) -> "ClaudeStream":
        # Convert messages to Anthropic format
        messages = []
        system_message = None
        
        for msg in self._ctx.messages:
            if msg.role == ChatRole.SYSTEM:
                system_message = msg.content
            elif msg.role == ChatRole.USER:
                messages.append({
                    "role": "user",
                    "content": msg.content
                })
            elif msg.role == ChatRole.ASSISTANT:
                messages.append({
                    "role": "assistant",
                    "content": msg.content
                })
        
        # Add the new user message if provided
        if message:
            messages.append({
                "role": "user",
                "content": message
            })
        
        # Convert functions to Anthropic format
        tools = None
        if functions:
            tools = []
            for func in functions:
                tools.append({
                    "name": func.name,
                    "description": func.description,
                    "input_schema": func.parameters
                })
        
        # Prepare the request with streaming
        request_params = {
            "model": self._llm.model,
            "messages": messages,
            "max_tokens": 4096,
            "stream": True,  # Enable streaming
        }
        
        if system_message:
            request_params["system"] = system_message
        
        if tools:
            request_params["tools"] = tools
        
        # Create async stream
        stream = self._llm.client.messages.stream(**request_params)
        return ClaudeStream(stream)


class ClaudeStream(llm.Stream):
    """Claude stream implementation"""
    
    def __init__(self, stream):
        self._stream = stream
        self._content = ""
        self._function_calls = []
        self._finished = False
    
    async def aclose(self):
        self._finished = True
        if hasattr(self._stream, 'close'):
            await self._stream.close()
    
    def __aiter__(self) -> AsyncIterator[llm.StreamChunk]:
        return self._stream_chunks()
    
    async def _stream_chunks(self) -> AsyncIterator[llm.StreamChunk]:
        # Process streaming response from Anthropic
        async for event in self._stream:
            if event.type == "content_block_delta":
                if hasattr(event.delta, 'type'):
                    if event.delta.type == "text_delta":
                        chunk_text = event.delta.text
                        self._content += chunk_text
                        yield llm.StreamChunk(
                            choices=[
                                llm.Choice(
                                    delta=llm.ChoiceDelta(
                                        content=chunk_text,
                                        role=ChatRole.ASSISTANT,
                                    ),
                                    index=0,
                                )
                            ]
                        )
                    elif hasattr(event.delta, 'input') and event.delta.input:
                        # Accumulate tool use arguments
                        if self._function_calls:
                            self._function_calls[-1]["arguments"] += event.delta.input
            elif event.type == "content_block_start":
                if hasattr(event, 'content_block') and event.content_block.type == "tool_use":
                    # Start of a tool use block
                    self._function_calls.append({
                        "name": event.content_block.name,
                        "arguments": ""
                    })
            elif event.type == "message_stop":
                self._finished = True
                break
        
        self._finished = True
    
    @property
    def content(self) -> str:
        return self._content
    
    @property
    def function_calls(self) -> list[dict]:
        return self._function_calls

