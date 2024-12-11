"""
Functions which wrap NHL API responses and turn into LLM-friendly strings.
"""

NHL_TEAM_ABBREVIATIONS: list[str] = [
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


def format_games(games: list[dict]) -> str:
    """
    Format a list of games into a detailed string including venue, game state,
    scores, team info, clock, outcome, and goals.
    """
    games_str = ""

    for game in games:
        # Basic info
        game_id = game.get("id", "N/A")
        game_state = game.get("gameState", "N/A")

        # Venue
        venue = game.get("venue", {}).get("default", "Unknown Venue")

        # Teams and Scores
        home_team = game.get("homeTeam", {})
        away_team = game.get("awayTeam", {})
        home_team_name = home_team.get("name", {}).get("default", "Unknown Team")
        away_team_name = away_team.get("name", {}).get("default", "Unknown Team")
        home_team_score = home_team.get("score", "N/A")
        away_team_score = away_team.get("score", "N/A")
        home_team_id = home_team.get("id", "N/A")
        away_team_id = away_team.get("id", "N/A")
        home_team_logo = home_team.get("logo", "")
        away_team_logo = away_team.get("logo", "")

        # Clock
        clock = game.get("clock", {})
        time_remaining = clock.get("timeRemaining", "N/A")
        period = game.get("period", "N/A")
        in_intermission = clock.get("inIntermission", False)

        # Game outcome
        game_outcome = game.get("gameOutcome", {})
        last_period_type = game_outcome.get("lastPeriodType", "N/A")
        ot_periods = game_outcome.get("otPeriods", 0)

        # Goals
        goals = game.get("goals", [])
        goals_str = ""
        for g in goals:
            scorer_name = g.get("name", {}).get("default", "Unknown Player")
            period_num = g.get("periodDescriptor", {}).get("number", "N/A")
            period_type = g.get("periodDescriptor", {}).get("periodType", "N/A")
            goal_time = g.get("timeInPeriod", "N/A")
            goal_team = g.get("teamAbbrev", "N/A")
            goal_strength = g.get("strength", "N/A")
            away_score_during_goal = g.get("awayScore", "N/A")
            home_score_during_goal = g.get("homeScore", "N/A")
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
    """
    Format NHL standings into a concise string.
    """
    standings_str = ""

    sorted_standings = sorted(
        standings.get("standings", []),
        key=lambda x: (x.get("points", 0), x.get("goalDifferential", 0)),
        reverse=True,
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
    """
    Format NHL roster into a concise string.
    """
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


def format_player_stats(player_data: dict) -> str:
    """
    Format NHL player stats into a concise string.

    TODO(michaelfromyeg): fix-up.
    """
    return str(player_data)

    # Get basic player info
    name = f"{player_data.get('firstName', {}).get('default', '')} {player_data.get('lastName', {}).get('default', '')}"
    team = player_data.get("teamCommonName", {}).get("default", "")
    position = player_data.get("position", "")
    number = player_data.get("sweaterNumber", "")

    # Get current season stats
    current_season = (
        player_data.get("featuredStats", {})
        .get("regularSeason", {})
        .get("subSeason", {})
    )
    games = current_season.get("gamesPlayed", 0)
    goals = current_season.get("goals", 0)
    assists = current_season.get("assists", 0)
    points = current_season.get("points", 0)
    plus_minus = current_season.get("plusMinus", 0)

    # Format output
    stats = f"#{number} {name} ({position}) - {team}\n"
    stats += "2024-25 Season Stats:\n"
    stats += f"Games: {games}, Goals: {goals}, Assists: {assists}, Points: {points}, +/-: {plus_minus}\n\n"

    # Add last 5 games
    stats += "Last 5 Games:\n"
    for game in player_data.get("last5Games", [])[:5]:
        date = game.get("gameDate", "")
        opp = game.get("opponentAbbrev", "")
        g = game.get("goals", 0)
        a = game.get("assists", 0)
        p = game.get("points", 0)
        pm = game.get("plusMinus", 0)
        stats += f"{date} vs {opp}: {g}G, {a}A, {p}P, {pm:+d}\n"

    return stats
