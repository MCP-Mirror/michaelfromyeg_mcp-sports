import asyncio

import mcp.server.stdio
import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from yfpy.query import YahooFantasySportsQuery

server = Server("yahoo")


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    List available tools.

    Each tool specifies its arguments using JSON Schema validation.
    """
    return [
        types.Tool(
            name="hello-world",
            description="Print hello world.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """
    Handle tool execution requests.

    Tools can fetch Yahoo Fantasy data.
    """
    if name == "hello-world":
        return [types.TextContent("Hello, world!")]
    else:
        raise ValueError(f"Unknown tool: {name}")


async def main():
    test_game_code = "nfl"
    test_game_id = 449
    test_league_id = "365083"

    query = YahooFantasySportsQuery(
        test_league_id,
        test_game_code,
        game_id=test_game_id,
        # yahoo_consumer_key=os.environ.get("YAHOO_CONSUMER_KEY"),
        # yahoo_consumer_secret=os.environ.get("YAHOO_CONSUMER_SECRET"),
        # yahoo_access_token_json=os.environ.get("YAHOO_ACCESS_TOKEN_JSON"),
        # env_file_location=project_dir,
        # save_token_data_to_env_file=True,
    )
    query.league_key = f"{test_game_id}.l.{test_league_id}"
    print(repr(query.get_all_yahoo_fantasy_game_keys()))

    # Run the server using stdin/stdout streams
    print("Running Yahoo MCP server...")
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="yahoo",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
