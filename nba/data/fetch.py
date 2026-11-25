from datetime import date, datetime
from zoneinfo import ZoneInfo

from nba_api.stats.endpoints import (
    commonteamroster,
    leaguedashteamstats,
    leaguegamelog,
    scheduleleaguev2,
)
from nba_api.stats.static import teams as static_teams

from .nba_client import call_nba

EASTERN = ZoneInfo("America/New_York")


def season_start_year(today=None):
    today = today or date.today()
    return today.year if today.month >= 9 else today.year - 1


def season_string(start_year):
    return f"{start_year}-{str(start_year + 1)[-2:]}"  # 2026 -> "2026-27"


def _num(value, default=0):
    """Turn None/NaN into a default."""
    if value is None:
        return default
    try:
        if value != value:  # only NaN isn't equal to itself
            return default
    except TypeError:
        return default
    return value


def _parse_date(value):
    return date.fromisoformat(str(value)[:10])


def _parse_eastern(value):
    # schedule times end in "Z" but are really Eastern
    try:
        return datetime.fromisoformat(str(value)[:19]).replace(tzinfo=EASTERN)
    except ValueError:
        return None


POSITION_MAP = {
    "G": ["PG", "SG"],
    "F": ["SF", "PF"],
    "C": ["C"],
}


def parse_positions(raw):
    positions = []
    for part in (raw or "").split("-"):
        for pos in POSITION_MAP.get(part.strip().upper(), []):
            if pos not in positions:
                positions.append(pos)
    return positions


def fetch_teams(season):
    teams = {}
    for t in static_teams.get_teams():
        teams[t["id"]] = {
            "id": t["id"],
            "abbreviation": t["abbreviation"],
            "name": t["full_name"],
            "def_rating": None,
        }

    frames = call_nba(
        leaguedashteamstats.LeagueDashTeamStats,
        season=season,
        measure_type_detailed_defense="Advanced",
    )
    for _, row in frames[0].iterrows():
        team_id = int(row["TEAM_ID"])
        if team_id in teams:
            rating = _num(row["DEF_RATING"], None)
            teams[team_id]["def_rating"] = round(float(rating), 1) if rating is not None else None

    return list(teams.values())


def fetch_active_players(season, team_ids):
    players = {}
    for team_id in team_ids:
        frames = call_nba(commonteamroster.CommonTeamRoster, team_id=team_id, season=season)
        for _, row in frames[0].iterrows():
            player_id = int(row["PLAYER_ID"])
            players[player_id] = {
                "id": player_id,
                "full_name": row["PLAYER"],
                "team_id": team_id,
                "positions": parse_positions(row["POSITION"]),
            }
    return list(players.values())


def fetch_schedule(season):
    frames = call_nba(scheduleleaguev2.ScheduleLeagueV2, season=season)
    games = []
    for _, row in frames[0].iterrows():
        game_id = str(row["gameId"])
        if not game_id.startswith("002"):  # regular season only
            continue

        home = int(_num(row["homeTeam_teamId"]))
        away = int(_num(row["awayTeam_teamId"]))
        if not home or not away:
            continue

        status_code = int(_num(row["gameStatus"], 1))
        status_text = str(row.get("gameStatusText", "")).upper()
        if status_code == 3:
            status = "final"
        elif "PPD" in status_text or "POSTPONED" in status_text:
            status = "postponed"
        else:
            status = "scheduled"

        games.append({
            "id": game_id,
            "season": season,
            "game_date": _parse_date(row["gameDateEst"]),
            "tipoff_at": _parse_eastern(row["gameDateTimeEst"]),
            "home_team_id": home,
            "away_team_id": away,
            "status": status,
        })
    return games


def fetch_past_games(season):
    frames = call_nba(
        leaguegamelog.LeagueGameLog,
        season=season,
        player_or_team_abbreviation="T",
        season_type_all_star="Regular Season",
    )
    games = {}
    for _, row in frames[0].iterrows():
        game_id = str(row["GAME_ID"])
        game = games.setdefault(game_id, {
            "id": game_id,
            "season": season,
            "game_date": _parse_date(row["GAME_DATE"]),
            "tipoff_at": None,
            "home_team_id": None,
            "away_team_id": None,
            "status": "final",
        })
        if " vs. " in row["MATCHUP"]:  # "BOS vs. NYK" = BOS home
            game["home_team_id"] = int(row["TEAM_ID"])
        else:                          # "BOS @ NYK" = BOS away
            game["away_team_id"] = int(row["TEAM_ID"])

    return [g for g in games.values() if g["home_team_id"] and g["away_team_id"]]


def fetch_box_scores(season):
    frames = call_nba(
        leaguegamelog.LeagueGameLog,
        season=season,
        player_or_team_abbreviation="P",
        season_type_all_star="Regular Season",
    )
    rows = []
    for _, r in frames[0].iterrows():
        plus_minus = _num(r["PLUS_MINUS"], None)
        rows.append({
            "player_id": int(r["PLAYER_ID"]),
            "player_name": r["PLAYER_NAME"],
            "team_id": int(r["TEAM_ID"]),
            "game_id": str(r["GAME_ID"]),
            "minutes": float(_num(r["MIN"])),
            "pts": int(_num(r["PTS"])),
            "reb": int(_num(r["REB"])),
            "ast": int(_num(r["AST"])),
            "stl": int(_num(r["STL"])),
            "blk": int(_num(r["BLK"])),
            "tov": int(_num(r["TOV"])),
            "fg3m": int(_num(r["FG3M"])),
            "fgm": int(_num(r["FGM"])),
            "fga": int(_num(r["FGA"])),
            "ftm": int(_num(r["FTM"])),
            "fta": int(_num(r["FTA"])),
            "plus_minus": None if plus_minus is None else int(plus_minus),
        })
    return rows