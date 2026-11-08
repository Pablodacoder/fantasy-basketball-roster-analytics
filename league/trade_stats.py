"""
Connects the trade page to the real NBA data.
Box scores -> per-game averages -> side totals -> stars -> Helps/Hurts verdict.
"""

from nba.models import BoxScore
from trade_analyzer.engine import(
    STAT_FIELDS,
    calculate_advanced_metrics,
    get_blended_baseline,
    get_rolling_window_baseline,
)

LAST_SEASON = "2025-26"
CURRENT_SEASON = "2026-27"

#KEYS MATCH STAR THRESHOLDS; values shown on the page
CATEGORY_LABELS = {
    "pts": "Points",
    "reb": "Rebounds",
    "ast": "Assists",
    "stl": "Steals",
    "blk": "Blocks",
    "3pm": "3-pointers made",
    "fg_pct": "FG%",
    "ft_pct": "FT%",
    "tov": "Turnovers",
    "ts_pct": "True shooting %",
    "prf": "Points responsible for"
}


class NotEnoughGames(Exception):
    """Player hasn't played enough games for the 'last N games' filter."""
    pass


def season_boxes(player, season):
    # Oldest first: Joshua's engine takes the newest games from the end.
    return list(BoxScore.objects
                .filter(player=player, game__season=season)
                .order_by("game__game_date"))


def player_per_game(player, season_mode, last_n):
    """One player's per-game averages, using Joshua's season and game filters."""
    last = season_boxes(player, LAST_SEASON)
    current = season_boxes(player, CURRENT_SEASON)

    if last_n:
        if season_mode == "last":
            result = get_rolling_window_baseline(last, [], last_n,
                                                 allow_cross_season_fallback=False)
        else:
            # "both" fills missing games from last season; "current" rejects instead.
            result = get_rolling_window_baseline(current, last, last_n,
                                                 allow_cross_season_fallback=(season_mode == "both"))
        if "error" in result:
            raise NotEnoughGames(f"{player.full_name}: {result['message']}")
    else:
        result = get_blended_baseline(last, current, season_mode)

    return result["per_game"]


def side_baseline(players, season_mode, last_n, categories):
    """Adds up one side of the trade, in the format Joshua's star function expects."""
    total = dict.fromkeys(STAT_FIELDS, 0.0)
    for p in players:
        per_game = player_per_game(p, season_mode, last_n)
        for f in STAT_FIELDS:
            total[f] += per_game[f]

    advanced = calculate_advanced_metrics(total)

    # FG% and FT% use total makes/attempts, times 100 to match Joshua's thresholds.
    all_stats = {
        "pts": total["pts"],
        "reb": total["reb"],
        "ast": total["ast"],
        "stl": total["stl"],
        "blk": total["blk"],
        "tov": total["tov"],
        "3pm": total["fg3m"],
        "fg_pct": 100 * total["fgm"] / total["fga"] if total["fga"] else 0.0,
        "ft_pct": 100 * total["ftm"] / total["fta"] if total["fta"] else 0.0,
        "ts_pct": advanced["ts_pct"],
        "prf": advanced["prf"],
    }

    # Only the categories the user checked.
    return {"per_game": {c: all_stats[c] for c in categories}}


def build_results(result, categories):
    """
    Joshua's stars show how big each difference is.
    This adds which side wins, for the Helps/Hurts labels and overall verdict.
    """
    rows, helps, hurts = [], 0, 0

    for c in categories:
        diff = result["differentials"][c]
        stars = result["star_ratings"][c]
        gain = -diff if c == "tov" else diff  # fewer turnovers is better

        if stars == 1:
            direction = "Even"  # difference too small to matter
        elif gain > 0:
            direction = "Helps"
            helps += 1
        else:
            direction = "Hurts"
            hurts += 1

        rows.append({"label": CATEGORY_LABELS[c], "diff": diff,
                     "stars": stars, "direction": direction})

    if helps > hurts:
        verdict = "▲ Helps your team"
    elif hurts > helps:
        verdict = "▼ Hurts your team"
    else:
        verdict = "≈ Roughly even"

    return {"rows": rows, "overall": result["composite_mean"], "verdict": verdict}