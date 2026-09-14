"""
mcp_server.py — MCP transport for Quantity Engine.
Authority is the engine (quantities.execute). This server is transport only:
no interpretation, no fallback, no hidden logic.
Compatible with mcp SDK v2.x (constructor-based handlers).
"""

import asyncio
import json
from pathlib import Path

import jsonschema
import mcp.server.stdio
from mcp import types
from mcp.server import Server, ServerRequestContext

from quantities import execute

HERE = Path(__file__).parent
TOOL_DEF = json.loads((HERE / "tool.json").read_text())


async def handle_list_tools(
    ctx: ServerRequestContext,
    params: types.PaginatedRequestParams | None,
) -> types.ListToolsResult:
    return types.ListToolsResult(
        tools=[
            types.Tool(
                name=TOOL_DEF["name"],
                description=TOOL_DEF["description"],
                input_schema=TOOL_DEF["input_schema"],
            )
        ]
    )


async def handle_call_tool(
    ctx: ServerRequestContext,
    params: types.CallToolRequestParams,
) -> types.CallToolResult:
    if params.name != TOOL_DEF["name"]:
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=json.dumps({
                "status": "ERROR",
                "error_code": "UNKNOWN_TOOL",
                "message": f"Unknown tool: {params.name}",
            }))],
            is_error=True,
        )

    arguments = params.arguments or {}

    try:
        jsonschema.validate(instance=arguments, schema=TOOL_DEF["input_schema"])
    except jsonschema.ValidationError as e:
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=json.dumps({
                "status": "ERROR",
                "error_code": "INVALID_INPUT",
                "message": e.message,
            }))],
            is_error=True,
        )

    result = execute(
        arguments["operations"],
        precision=arguments.get("precision"),
    )

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=json.dumps(result))],
        is_error=False,
    )


server = Server(
    "quantity-engine",
    on_list_tools=handle_list_tools,
    on_call_tool=handle_call_tool,
)


async def main():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        try:
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options(),
            )
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass