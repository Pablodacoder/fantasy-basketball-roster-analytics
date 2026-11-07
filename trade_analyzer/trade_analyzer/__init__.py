"""
trade_analyzer/engine.py
Pure statistical calculation engine for multi-season baselines,
Per-36 normalizations, and rolling game window analytics.
"""

STAT_FIELDS = ["pts", "reb", "ast", "stl", "blk", "tov", "fg3m", "fgm", "fga", "ftm", "fta"]

def calculate_per_game_averages(box_scores):
    """
    Computes standard per-game averages from a list of box score dictionaries or model objects.
    """
    if not box_scores:
        return {field: 0.0 for field in STAT_FIELDS}, 0

    totals = {field: 0.0 for field in STAT_FIELDS}
    games_played = len(box_scores)

    for box in box_scores:
        # Handle dict or object access safely
        get_val = box.get if isinstance(box, dict) else lambda f: getattr(box, f, 0.0)
        for field in STAT_FIELDS:
            totals[field] += float(get_val(field) or 0.0)

    averages = {field: round(totals[field] / games_played, 2) for field in STAT_FIELDS}
    return averages, games_played


def calculate_per_36_rates(box_scores):
    """
    Normalizes box score metrics to a Per-36 minute baseline.
    Formula: (Stat Total / Total Minutes Played) * 36
    """
    if not box_scores:
        return {field: 0.0 for field in STAT_FIELDS}

    totals = {field: 0.0 for field in STAT_FIELDS}
    total_minutes = 0.0

    for box in box_scores:
        get_val = box.get if isinstance(box, dict) else lambda f: getattr(box, f, 0.0)
        mins = float(get_val("minutes") or 0.0)
        if mins <= 0:
            continue
        total_minutes += mins
        for field in STAT_FIELDS:
            totals[field] += float(get_val(field) or 0.0)

    if total_minutes <= 0:
        return {field: 0.0 for field in STAT_FIELDS}

    per_36 = {field: round((totals[field] / total_minutes) * 36.0, 2) for field in STAT_FIELDS}
    return per_36


def get_blended_baseline(last_season_boxes, current_season_boxes, season_mode="both"):
    """
    Computes player baselines based on user filter selection:
      - 'last': Strictly last season's stats
      - 'current': Strictly current season's stats
      - 'both': Dynamic sample-size weighting (games / games + 15)
    """
    last_avg, last_gp = calculate_per_game_averages(last_season_boxes)
    curr_avg, curr_gp = calculate_per_game_averages(current_season_boxes)

    last_p36 = calculate_per_36_rates(last_season_boxes)
    curr_p36 = calculate_per_36_rates(current_season_boxes)

    if season_mode == "last":
        return {"per_game": last_avg, "per_36": last_p36, "games_played": last_gp, "mode": "last"}
    elif season_mode == "current":
        return {"per_game": curr_avg, "per_36": curr_p36, "games_played": curr_gp, "mode": "current"}

    # Default 'both' (Dynamic Weighting Blending)
    if curr_gp == 0:
        return {"per_game": last_avg, "per_36": last_p36, "games_played": last_gp, "mode": "last_fallback"}

    curr_weight = curr_gp / (curr_gp + 15.0)
    last_weight = 1.0 - curr_weight

    blended_pg = {}
    blended_p36 = {}

    for field in STAT_FIELDS:
        blended_pg[field] = round((curr_avg[field] * curr_weight) + (last_avg[field] * last_weight), 2)
        blended_p36[field] = round((curr_p36[field] * curr_weight) + (last_p36[field] * last_weight), 2)

    return {
        "per_game": blended_pg,
        "per_36": blended_p36,
        "games_played": curr_gp + last_gp,
        "mode": "both",
        "weights": {"current": round(curr_weight, 2), "last": round(last_weight, 2)}
    }
