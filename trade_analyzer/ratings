def calculate_star_impact(stat_differential):
    """
    Maps raw statistical differentials into a 1-5 star impact rating tier.
    - 1 Star: Little to no impact
    - 2 Stars: Minor impact
    - 3 Stars: Moderate impact
    - 4 Stars: Significant impact
    - 5 Stars: Elite impact
    """
    abs_diff = abs(stat_differential)

    if abs_diff >= 5.0:
        return 5
    elif abs_diff >= 3.5:
        return 4
    elif abs_diff >= 2.0:
        return 3
    elif abs_diff >= 1.0:
        return 2
    else:
        return 1
