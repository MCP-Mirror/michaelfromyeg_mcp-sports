import asyncio
from datetime import date as Date
from datetime import datetime
from typing import Any

import httpx
import mcp.server.stdio
import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

from .formatters import (
    NHL_TEAM_ABBREVIATIONS,
    format_games,
    format_player_stats,
    format_roster,
    format_standings,
)

NHL_API_BASE = "https://api-web.nhle.com/v1"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

server = Server("nhl")


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    List available tools.
    Each tool specifies its arguments using JSON Schema validation.
    """
    return [
        types.Tool(
            name="get-nhl-schedule",
            description="Get NHL schedule for a date, and get the corresponding game information.",
            inputSchema={
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "The date in YYYY-MM-DD format.",
                    },
                },
                "required": ["date"],
            },
        ),
        types.Tool(
            name="get-nhl-game-play-by-play",
            description="Get NHL play by plays for a game. Get the game id from get-nhl-schedule tool.",
            inputSchema={
                "type": "object",
                "properties": {
                    "game_id": {
                        "type": "string",
                        "description": "Game ID. Example: 2024020451.",
                    },
                },
                "required": ["game_id"],
            },
        ),
        types.Tool(
            name="get-nhl-roster",
            description="Get NHL roster for a team",
            inputSchema={
                "type": "object",
                "properties": {
                    "team_abbreviation": {
                        "type": "string",
                        "description": "An NHL team abbreviation: one-of ANA (Mighty Ducks of Anaheim/Anaheim Ducks), BOS (Boston Bruins), BUF (Buffalo Sabres), CAR (Carolina Hurricanes), CBJ (Columbus Blue Jackets), CGY (Calgary Flames), CHI (Chicago Black Hawks/Blackhawks), COL (Colorado Avalanche), DAL (Dallas Stars), DET (Detroit Red Wings), EDM (Edmonton Oilers), FLA (Florida Panthers), LAK (Los Angeles Kings), MIN (Minnesota Wild), MTL (Montreal Canadiens), NJD (New Jersey Devils), NSH (Nashville Predators), NYI (New York Islanders), NYR (New York Rangers), OTT (Ottawa Senators), PHI (Philadelphia Flyers), PIT (Pittsburgh Penguins), SEA (Seattle Kraken), SJS (San Jose Sharks), STL (St. Louis Blues), TBL (Tampa Bay Lightning), TOR (Toronto Maple Leafs), UTA (Utah Hockey Club), VAN (Vancouver Canucks), VGK (Vegas Golden Knights), WPG (Winnipeg Jets), WSH (Washington Capitals)",
                    },
                },
            },
        ),
        types.Tool(
            name="get-nhl-player-stats",
            description="Get NHL player stats",
            inputSchema={
                "type": "object",
                "properties": {
                    "player_id": {
                        "type": "string",
                        "description": "An NHL player ID",
                    },
                },
            },
        ),
        # TODO(michaelfromyeg): fix NHL team stats endpoint
        # types.Tool(
        #     name="get-nhl-team-stats",
        #     description="Get NHL team stats",
        #     inputSchema={
        #         "type": "object",
        #         "properties": {
        #             "team_abbreviation": {
        #                 "type": "string",
        #                 "description": "An NHL team abbreviation",
        #             },
        #         },
        #     },
        # ),
    ]


async def make_nhl_request(
    client: httpx.AsyncClient, url: str
) -> dict[str, Any] | None:
    """
    Make a request to the NHL API with proper error handling, including following 307 redirects.
    """
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}

    try:
        response = await client.get(
            url, headers=headers, timeout=30.0, follow_redirects=True
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Request failed: {e}")
        return None


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """
    Handle tool execution requests.

    Tools can fetch NHL data and notify clients of changes.

    TODO(michaelfromyeg): clean this up.
    """
    if name == "get-nhl-schedule":
        if not arguments:
            raise ValueError("Missing arguments")

        date = arguments.get("date")
        if not date:
            raise ValueError("Missing state parameter")

        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Invalid date format. Please use YYYY-MM-DD.")

        async with httpx.AsyncClient() as client:
            schedule_url = f"{NHL_API_BASE}/schedule/{date}"
            schedule_data = await make_nhl_request(client, schedule_url)

            if not schedule_data:
                return [
                    types.TextContent(
                        type="text", text="Failed to retrieve alerts data"
                    )
                ]

            game_days = schedule_data.get("gameWeek", [])
            if not game_days:
                return [
                    types.TextContent(type="text", text=f"No active games for {date}")
                ]

            for game_day in game_days:
                if game_day.get("date", "") == date:
                    games = game_day.get("games", [])
                    return [types.TextContent(type="text", text=format_games(games))]

            return [types.TextContent(type="text", text=f"No active games for {date}")]
    if name == "get-nhl-game-play-by-play":
        game_id = arguments.get("game_id")

        schedule_url = f"{NHL_API_BASE}/gamecenter/{game_id}/play-by-play"
        async with httpx.AsyncClient() as client:
            data = await make_nhl_request(client, schedule_url)

        # Extract some key info
        game_id = data.get("id")
        away_team_info = data.get("awayTeam", {})
        home_team_info = data.get("homeTeam", {})

        away_name = away_team_info.get("commonName", {}).get("default", "Unknown")
        away_score = away_team_info.get("score", "N/A")
        home_name = home_team_info.get("commonName", {}).get("default", "Unknown")
        home_score = home_team_info.get("score", "N/A")

        output_str = ""
        output_str += f"Game ID: {game_id}\n"
        output_str += f"Away Team: {away_name} Score: {away_score}\n"
        output_str += f"Home Team: {home_name} Score: {home_score}\n"
        output_str += f"Game State: {data.get('gameState', 'N/A')}\n"
        output_str += f"Period: {data.get('displayPeriod', 'N/A')}\n"

        # Print a few plays for demonstration
        plays = data.get("plays", [])
        output_str += "All plays of the game:\n"
        for i, play in enumerate(plays, start=1):
            event_type = play.get("typeDescKey", "Unknown")
            time_in_period = play.get("timeInPeriod", "N/A")
            details = play.get("details", {})
            output_str += (
                f"Play {i}: {event_type} at {time_in_period}, details: {details}\n"
            )

        # Return as types.TextContent
        return [types.TextContent(type="text", text=output_str)]
    elif name == "get-nhl-roster":
        if not arguments:
            raise ValueError("Missing arguments")

        team_abbreviation = arguments.get("team_abbreviation")
        if not team_abbreviation:
            raise ValueError("Missing team_abbreviation")

        # validate team_abbreviation
        if team_abbreviation not in NHL_TEAM_ABBREVIATIONS:
            raise ValueError(f"Invalid team abbreviation: {team_abbreviation}")

        # current season id, i.e., 20242025
        today = Date.today()
        # NHL season starts in October, so if we're before October, use previous year
        season_start_year = today.year if today.month >= 10 else today.year - 1
        current_season_id = f"{season_start_year}{season_start_year + 1}"
        roster_url = f"{NHL_API_BASE}/roster/{team_abbreviation}/{current_season_id}"

        async with httpx.AsyncClient() as client:
            roster_data = await make_nhl_request(client, roster_url)

        if not roster_data:
            return [
                types.TextContent(type="text", text="Failed to retrieve roster data")
            ]

        return [types.TextContent(type="text", text=format_roster(roster_data))]
    elif name == "get-nhl-schedule-now":
        async with httpx.AsyncClient() as client:
            schedule_url = f"{NHL_API_BASE}/schedule/now"
            schedule_data = await make_nhl_request(client, schedule_url)

            if not schedule_data:
                return [
                    types.TextContent(
                        type="text", text="Failed to retrieve alerts data"
                    )
                ]

            game_days = schedule_data.get("gameWeek", [])
            if not game_days:
                return [types.TextContent(type="text", text="No active games")]

            for game_day in game_days:
                if game_day.get("date", "") == date:
                    games = game_day.get("games", [])
                    return [types.TextContent(type="text", text=format_games(games))]

            return [types.TextContent(type="text", text="No active games right now")]
    elif name == "get-nhl-standings":
        async with httpx.AsyncClient() as client:
            standings_url = (
                f"{NHL_API_BASE}/standings/{Date.today().strftime('%Y-%m-%d')}"
            )
            standings_data = await make_nhl_request(client, standings_url)

            if not standings_data:
                return [
                    types.TextContent(
                        type="text", text="Failed to retrieve standings data"
                    )
                ]

            return [
                types.TextContent(type="text", text=format_standings(standings_data))
            ]
    # elif name == "get-nhl-team-stats":
    #     # First, parse the arguments
    #     if not arguments:
    #         raise ValueError("Missing arguments")

    #     team_abbreviation = arguments.get("team_abbreviation")
    #     if not team_abbreviation:
    #         raise ValueError("Missing team_abbreviation")

    #     # validate team_abbreviation
    #     if team_abbreviation not in TEAM_ABBREVIATIONS:
    #         raise ValueError(f"Invalid team abbreviation: {team_abbreviation}")

    #     # current season id, i.e., 20242025
    #     today = Date.today()
    #     # NHL season starts in October, so if we're before October, use previous year
    #     season_start_year = today.year if today.month >= 10 else today.year - 1
    #     current_season_id = f"{season_start_year}{season_start_year + 1}"
    #     roster_url = f"{NHL_API_BASE}/roster/{team_abbreviation}/{current_season_id}"
    elif name == "get-nhl-player-stats":
        # validate args
        if not arguments:
            raise ValueError("Missing arguments")

        player_id = arguments.get("player_id")
        if not player_id:
            raise ValueError("Missing player_id")

        # query https://api-web.nhle.com/v1/player/8484145/landing

        async with httpx.AsyncClient() as client:
            player_url = f"{NHL_API_BASE}/player/{player_id}/landing"
            player_data = await make_nhl_request(client, player_url)

            if not player_data:
                return [
                    types.TextContent(
                        type="text", text="Failed to retrieve player data"
                    )
                ]

            return [
                types.TextContent(type="text", text=format_player_stats(player_data))
            ]
    else:
        raise ValueError(f"Unknown tool: {name}")


async def main():
    # Run the server using stdin/stdout streams
    print("Running NHL MCP server...")
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="nhl",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
