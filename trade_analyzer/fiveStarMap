"""
trade_analyzer/ratings.py
Maps raw statistical differentials into 1-5 star impact ratings
across both basic box score categories and advanced efficiency metrics.
"""

# Custom thresholds for star ratings based on per-game stat differences (Player A minus Player B)
STAR_THRESHOLDS = {
    # Basic Stats
    "pts":  [1.5, 4.0, 7.5, 12.0],  # 1: <1.5, 2: 1.5-4, 3: 4-7.5, 4: 7.5-12, 5: >12
    "reb":  [1.0, 2.5, 4.5, 7.0],
    "ast":  [1.0, 2.5, 4.5, 7.0],
    "stl":  [0.5, 1.0, 1.8, 2.5],
    "blk":  [0.4, 0.9, 1.5, 2.3],
    "3pm":  [0.5, 1.2, 2.2, 3.5],
    "fg_pct": [1.0, 2.5, 4.5, 7.0],
    "ft_pct": [1.0, 2.5, 4.5, 7.0],
    "tov":  [0.5, 1.2, 2.0, 3.0],   # Turnovers (fewer difference is evaluated)

    # Advanced Metrics
    "ts_pct": [1.5, 3.5, 6.0, 9.0], # True Shooting % thresholds
    "prf":  [2.0, 5.0, 9.0, 15.0],  # Points Responsible For thresholds
}

def calculate_category_stars(diff, stat_name):
    """
    Converts a numerical stat difference (delta) into a 1-5 star rating.
    """
    abs_diff = abs(diff)
    thresholds = STAR_THRESHOLDS.get(stat_name, [1.0, 2.0, 3.5, 5.0])

    if abs_diff < thresholds[0]:
        return 1
    elif abs_diff < thresholds[1]:
        return 2
    elif abs_diff < thresholds[2]:
        return 3
    elif abs_diff < thresholds[3]:
        return 4
    else:
        return 5


def evaluate_trade_differential(baseline_a, baseline_b):
    """
    Computes direct stat differentials (Player A minus Player B) across
    both per_game stats and advanced metrics, assigning star ratings for each.
    """
    # Extract basic per-game stats
    stats_a = baseline_a.get("per_game", {})
    stats_b = baseline_b.get("per_game", {})

    # Extract advanced metrics if present
    advanced_a = baseline_a.get("advanced", {})
    advanced_b = baseline_b.get("advanced", {})

    differentials = {}
    star_ratings = {}

    # Combine standard and advanced dictionaries for full evaluation
    combined_a = {**stats_a, **advanced_a}
    combined_b = {**stats_b, **advanced_b}

    for stat in combined_a.keys():
        val_a = combined_a.get(stat, 0.0)
        val_b = combined_b.get(stat, 0.0)

        # Ensure values are numeric before subtracting
        try:
            diff = round(float(val_a) - float(val_b), 2)
        except (TypeError, ValueError):
            diff = 0.0

        differentials[stat] = diff
        star_ratings[stat] = calculate_category_stars(diff, stat)

    # Calculate overall composite star rating mean if ratings exist
    if star_ratings:
        composite_mean = round(sum(star_ratings.values()) / len(star_ratings), 2)
    else:
        composite_mean = 1.0

    return {
        "differentials": differentials,
        "star_ratings": star_ratings,
        "composite_mean": composite_mean
    }
