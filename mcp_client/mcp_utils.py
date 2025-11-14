import inspect
import json
import logging
from collections.abc import Coroutine
from enum import Enum
from typing import Any, Callable, Optional

from livekit.agents import FunctionTool, function_tool
from mcp.types import CallToolResult, Tool as MCPTool
from pydantic import BaseModel, Field, create_model

logger = logging.getLogger(__name__)


def mcp_to_function_tool(
    tool: MCPTool,
    call_tool: Callable[[str, dict[str, Any]], Coroutine[Any, Any, CallToolResult]],
) -> FunctionTool:
    name = tool.name
    description = tool.description

    raw_schema = {
        "name": name,
        "description": description,
        "parameters": tool.inputSchema,
    }

    async def tool_impl(raw_arguments: dict[str, Any]) -> str:
        try:
            arguments = {k: str(v) for k, v in raw_arguments.items() if v is not None}
            result = await call_tool(name, arguments)

            logger.info(f"Called tool '{name}' with arguments: {arguments}")

            text_contents = [
                content.text for content in result.content if content.type == "text"
            ]
            text = json.dumps(text_contents)

            if result.isError:
                raise ValueError("Tool call failed with content: " + text)

            return text

        except Exception as e:
            logger.error(f"Error calling tool '{name}': {e}")
            return f"Error calling tool '{name}': {e}"

    return function_tool(tool_impl, raw_schema=raw_schema)


def create_pydantic_model_from_schema(
    schema: dict[str, Any], model_name: str
) -> type[BaseModel]:
    properties: dict[str, dict[str, Any]] = schema.get("properties", {})
    required: list[str] = schema.get("required", [])

    fields = {}

    for field_name, field_info in properties.items():
        field_type = field_info.get("type", "string")
        description = field_info.get("description", "")

        if field_type == "object":
            nested_model = create_pydantic_model_from_schema(
                field_info, model_name=f"{model_name}_{field_name.capitalize()}"
            )
            if field_name in required:
                fields[field_name] = (nested_model, Field(description=description))
            else:
                fields[field_name] = (
                    Optional[nested_model],
                    Field(default=None, description=description),
                )

        elif field_type == "array":
            items: dict[str, Any] = field_info.get("items", {})
            items_type = items.get("type", "string")

            if items_type == "object":
                item_model = create_pydantic_model_from_schema(
                    items, model_name=f"{model_name}_{field_name.capitalize()}Item"
                )
                if field_name in required:
                    fields[field_name] = (
                        list[item_model],
                        Field(description=description),
                    )
                else:
                    fields[field_name] = (
                        Optional[list[item_model]],
                        Field(default=None, description=description),
                    )
            else:
                item_python_type = TYPE_MAP.get(items_type, Any)
                enum = items.get("enum", [])
                if enum:
                    item_python_type = Enum(
                        f"{model_name}_{field_name.capitalize()}",
                        [(v, v) for v in enum],
                    )

                if field_name in required:
                    fields[field_name] = (
                        list[item_python_type],
                        Field(description=description),
                    )
                else:
                    fields[field_name] = (
                        Optional[list[item_python_type]],
                        Field(default=None, description=description),
                    )
        else:
            python_type = TYPE_MAP.get(field_type, Any)
            enum = field_info.get("enum", [])
            if enum:
                python_type = Enum(
                    f"{model_name}_{field_name.capitalize()}", [(v, v) for v in enum]
                )

            if field_name in required:
                fields[field_name] = (python_type, Field(description=description))
            else:
                fields[field_name] = (
                    Optional[python_type],
                    Field(default=None, description=description),
                )

    return create_model(model_name, **fields)


TYPE_MAP = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
    "array": list,
    "object": dict,
    "null": type(None),
}