from typing import Any
import asyncio
import httpx
from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
import mcp.server.stdio
from datetime import datetime, date as Date

NHL_API_BASE = "https://api-web.nhle.com/v1"
# TODO(michaelfromyeg): make this legit!
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# "sports", eventually actually make it sports
server = Server("sports")

TEAM_ABBREVIATIONS = [
    "ANA",
    "BOS",
    "BUF",
    "CAR",
    "CBJ",
    "CGY",
    "CHI",
    "COL",
    "DAL",
    "DET",
    "EDM",
    "FLA",
    "LAK",
    "MIN",
    "MTL",
    "NJD",
    "NSH",
    "NYI",
    "NYR",
    "OTT",
    "PHI",
    "PIT",
    "SEA",
    "SJS",
    "STL",
    "TBL",
    "TOR",
    "UTA",
    "VAN",
    "VGK",
    "WPG",
    "WSH",
]

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    List available tools.
    Each tool specifies its arguments using JSON Schema validation.
    """
    return [
        types.Tool(
            name="get-nhl-schedule",
            description="Get NHL schedule for a date",
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
            name="get-nhl-standings",
            description="Get NHL standings",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
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
        )
    ]

async def make_nhl_request(client: httpx.AsyncClient, url: str) -> dict[str, Any] | None:
    """Make a request to the NHL API with proper error handling."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json"
    }

    try:
        response = await client.get(url, headers=headers, timeout=30.0)
        response.raise_for_status()
        return response.json()
    except Exception:
        return None

def format_games(games: list[dict]) -> str:
    """Format a list of games into a concise string."""
    games_str = ""

    for game in games:
        home_team = game.get('homeTeam', {}).get('commonName', {}).get("default", "")
        away_team = game.get('awayTeam', {}).get('commonName', {}).get("default", "")
        venue = game.get('venue', {}).get('default', "")
        games_str += f"{home_team} vs {away_team} at {venue}\n"
    
    return games_str

def format_standings(standings: dict) -> str:
    """Format NHL standings into a concise string."""
    standings_str = ""
    
    # Sort standings by points and goal differential as tiebreaker
    sorted_standings = sorted(
        standings.get("standings", []),
        key=lambda x: (x.get("points", 0), x.get("goalDifferential", 0)),
        reverse=True
    )

    for team in sorted_standings:
        team_name = team.get("teamCommonName", {}).get("default", "")
        points = team.get("points", 0)
        wins = team.get("wins", 0)
        losses = team.get("losses", 0)
        ot_losses = team.get("otLosses", 0)
        goal_diff = team.get("goalDifferential", 0)
        
        standings_str += f"{team_name}: {points}pts ({wins}-{losses}-{ot_losses}) GD: {goal_diff:+d}\n"
    return standings_str

def format_roster(roster: dict) -> str:
    """Format NHL roster into a concise string."""
    roster_str = ""
    # Process forwards
    roster_str += "FORWARDS:\n"
    for player in roster.get("forwards", []):
        first_name = player.get("firstName", {}).get("default", "")
        last_name = player.get("lastName", {}).get("default", "")
        number = player.get("sweaterNumber", "")
        roster_str += f"#{number} {first_name} {last_name}\n"

    # Process defensemen 
    roster_str += "\nDEFENSEMEN:\n"
    for player in roster.get("defensemen", []):
        first_name = player.get("firstName", {}).get("default", "")
        last_name = player.get("lastName", {}).get("default", "")
        number = player.get("sweaterNumber", "")
        roster_str += f"#{number} {first_name} {last_name}\n"

    # Process goalies
    roster_str += "\nGOALIES:\n" 
    for player in roster.get("goalies", []):
        first_name = player.get("firstName", {}).get("default", "")
        last_name = player.get("lastName", {}).get("default", "")
        number = player.get("sweaterNumber", "")
        roster_str += f"#{number} {first_name} {last_name}\n"
    return roster_str

@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """
    Handle tool execution requests.
    Tools can fetch sports data and notify clients of changes.
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
                return [types.TextContent(type="text", text="Failed to retrieve alerts data")]

            game_days = schedule_data.get("gameWeek", [])
            if not game_days:
                return [types.TextContent(type="text", text=f"No active games for {date}")]

            for game_day in game_days:
                if game_day.get("date", "") == date:
                    games = game_day.get("games", [])
                    return [
                        types.TextContent(
                            type="text",
                            text=format_games(games)
                        )
                    ]

            return [
                types.TextContent(
                    type="text",
                    text=f"No active games for {date}"
                )
            ]
    elif name == "get-nhl-roster":
        if not arguments:
            raise ValueError("Missing arguments")

        team_abbreviation = arguments.get("team_abbreviation")
        if not team_abbreviation:
            raise ValueError("Missing team_abbreviation")

        # validate team_abbreviation
        if team_abbreviation not in TEAM_ABBREVIATIONS:
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
            return [types.TextContent(type="text", text="Failed to retrieve roster data")]
        
        return [
            types.TextContent(
                type="text",
                text=format_roster(roster_data)
            )
        ]
    elif name == "get-nhl-standings":
        async with httpx.AsyncClient() as client:
            standings_url = f"{NHL_API_BASE}/standings/{Date.today().strftime('%Y-%m-%d')}"
            standings_data = await make_nhl_request(client, standings_url)

            if not standings_data:
                return [types.TextContent(type="text", text="Failed to retrieve standings data")]

            return [
                types.TextContent(
                    type="text",
                    text=format_standings(standings_data)
                )
            ]
    else:
        raise ValueError(f"Unknown tool: {name}")

async def main():
    # Run the server using stdin/stdout streams
    print("Running sports MCP server...")
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="sports",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())
