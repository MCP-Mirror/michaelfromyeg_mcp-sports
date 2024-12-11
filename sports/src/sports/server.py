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

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    List available tools.
    Each tool specifies its arguments using JSON Schema validation.
    """
    return [
        types.Tool(
            name="get-nhl-schedule",
            description="Get NHL schedule for a date, and get the corresponding game IDs",
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
    ]

async def make_nhl_request(client: httpx.AsyncClient, url: str) -> dict[str, Any] | None:
    """Make a request to the NHL API with proper error handling, including following 307 redirects."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json"
    }

    try:
        # Enable following of redirects
        response = await client.get(url, headers=headers, timeout=30.0, follow_redirects=True)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Request failed: {e}")
        return None


def format_games(games: list[dict]) -> str:
    """Format a list of games into a detailed string including venue, game state, scores, team info, clock, outcome, and goals."""
    games_str = ""

    for game in games:
        # Basic info
        game_id = game.get('id', 'N/A')
        game_state = game.get('gameState', 'N/A')

        # Venue
        venue = game.get('venue', {}).get('default', 'Unknown Venue')

        # Teams and Scores
        home_team = game.get('homeTeam', {})
        away_team = game.get('awayTeam', {})
        home_team_name = home_team.get('name', {}).get('default', 'Unknown Team')
        away_team_name = away_team.get('name', {}).get('default', 'Unknown Team')
        home_team_score = home_team.get('score', 'N/A')
        away_team_score = away_team.get('score', 'N/A')
        home_team_id = home_team.get('id', 'N/A')
        away_team_id = away_team.get('id', 'N/A')
        home_team_logo = home_team.get('logo', '')
        away_team_logo = away_team.get('logo', '')

        # Clock
        clock = game.get('clock', {})
        time_remaining = clock.get('timeRemaining', 'N/A')
        period = game.get('period', 'N/A')
        in_intermission = clock.get('inIntermission', False)

        # Game outcome
        game_outcome = game.get('gameOutcome', {})
        last_period_type = game_outcome.get('lastPeriodType', 'N/A')
        ot_periods = game_outcome.get('otPeriods', 0)

        # Goals
        goals = game.get('goals', [])
        goals_str = ""
        for g in goals:
            scorer_name = g.get('name', {}).get('default', 'Unknown Player')
            period_num = g.get('periodDescriptor', {}).get('number', 'N/A')
            period_type = g.get('periodDescriptor', {}).get('periodType', 'N/A')
            goal_time = g.get('timeInPeriod', 'N/A')
            goal_team = g.get('teamAbbrev', 'N/A')
            goal_strength = g.get('strength', 'N/A')
            away_score_during_goal = g.get('awayScore', 'N/A')
            home_score_during_goal = g.get('homeScore', 'N/A')
            goals_str += (
                f" - {scorer_name} scored for {goal_team} in Period {period_num} "
                f"({period_type}) at {goal_time} [{goal_strength}] "
                f"(Score at that time: {away_score_during_goal}-{home_score_during_goal})\n"
            )

        # Construct the formatted string for each game
        games_str += f"Game ID: {game_id}\n"
        games_str += f"State: {game_state}\n"
        games_str += f"Venue: {venue}\n"
        games_str += f"Home Team: {home_team_name} (ID: {home_team_id}, Score: {home_team_score}, Logo: {home_team_logo})\n"
        games_str += f"Away Team: {away_team_name} (ID: {away_team_id}, Score: {away_team_score}, Logo: {away_team_logo})\n"
        games_str += f"Time Remaining: {time_remaining}, Period: {period}, In Intermission: {in_intermission}\n"
        games_str += f"Game Outcome: Last Period Type: {last_period_type}, OT Periods: {ot_periods}\n"
        if goals_str:
            games_str += "Goals:\n" + goals_str
        games_str += "\n"

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
    elif name == "get-nhl-schedule-now":
        async with httpx.AsyncClient() as client:
            schedule_url = f"{NHL_API_BASE}/schedule/now"
            schedule_data = await make_nhl_request(client, schedule_url)

            if not schedule_data:
                return [types.TextContent(type="text", text="Failed to retrieve alerts data")]

            game_days = schedule_data.get("gameWeek", [])
            if not game_days:
                return [types.TextContent(type="text", text=f"No active games")]

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
                    text=f"No active games right now"
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
