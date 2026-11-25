import logging
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

from django.db import transaction

from nba.models import BoxScore, Game, Injury, Player, Team

from .injuries import map_status, normalize_name

log = logging.getLogger(__name__)

STAT_FIELDS = ["pts", "reb", "ast", "stl", "blk", "tov", "fg3m", "fgm", "fga", "ftm", "fta", "plus_minus"]


@transaction.atomic
def save_teams(rows):
    for r in rows:
        rating = r.get("def_rating")
        Team.objects.update_or_create(
            id=r["id"],
            defaults={
                "abbreviation": r["abbreviation"],
                "name": r["name"],
                "def_rating": Decimal(str(rating)) if rating is not None else None,
            },
        )
    return len(rows)


@transaction.atomic
def save_players(rows, today):
    if not rows:
        raise RuntimeError("Got 0 active players from NBA.com, refusing to save")

    old_players = {p.id: p for p in Player.objects.only("id", "team_id", "team_changed_on")}
    active_ids = []

    for r in rows:
        old = old_players.get(r["id"])
        changed_on = old.team_changed_on if old else None
        if old and old.team_id and old.team_id != r["team_id"]:
            changed_on = today

        Player.objects.update_or_create(
            id=r["id"],
            defaults={
                "full_name": r["full_name"],
                "team_id": r["team_id"],
                "positions": r["positions"],
                "is_active": True,
                "team_changed_on": changed_on,
            },
        )
        active_ids.append(r["id"])

    newly_inactive = Player.objects.filter(is_active=True).exclude(id__in=active_ids).update(is_active=False)
    return len(active_ids), newly_inactive


@transaction.atomic
def ensure_box_score_players(rows):
    known = set(Player.objects.values_list("id", flat=True))
    known_teams = set(Team.objects.values_list("id", flat=True))
    new_players = {}
    for r in rows:
        if r["player_id"] not in known and r["player_id"] not in new_players:
            new_players[r["player_id"]] = Player(
                id=r["player_id"],
                full_name=r["player_name"],
                team_id=r["team_id"] if r["team_id"] in known_teams else None,
                positions=[],
                is_active=False,
            )
    Player.objects.bulk_create(new_players.values())
    return len(new_players)


@transaction.atomic
def save_games(rows):
    known_teams = set(Team.objects.values_list("id", flat=True))
    saved = 0
    for r in rows:
        if r["home_team_id"] not in known_teams or r["away_team_id"] not in known_teams:
            continue
        defaults = {
            "season": r["season"],
            "game_date": r["game_date"],
            "home_team_id": r["home_team_id"],
            "away_team_id": r["away_team_id"],
            "status": r["status"],
        }
        if r.get("tipoff_at"):
            defaults["tipoff_at"] = r["tipoff_at"]
        Game.objects.update_or_create(id=r["id"], defaults=defaults)
        saved += 1
    return saved


@transaction.atomic
def save_box_scores(rows):
    known_games = set(Game.objects.values_list("id", flat=True))
    saved = skipped = 0
    for r in rows:
        if r["game_id"] not in known_games:
            skipped += 1
            continue
        defaults = {field: r[field] for field in STAT_FIELDS}
        defaults["minutes"] = Decimal(str(round(r["minutes"], 2)))
        BoxScore.objects.update_or_create(player_id=r["player_id"], game_id=r["game_id"], defaults=defaults)
        saved += 1
    if skipped:
        log.warning("Skipped %d box score rows for games we don't have", skipped)
    return saved


@transaction.atomic
def mark_back_to_backs(season):
    games = list(Game.objects.filter(season=season))

    dates_played = defaultdict(set)
    for g in games:
        if g.status != Game.Status.POSTPONED:
            dates_played[g.home_team_id].add(g.game_date)
            dates_played[g.away_team_id].add(g.game_date)

    changed = []
    b2b_games = 0
    for g in games:
        yesterday = g.game_date - timedelta(days=1)
        if g.status == Game.Status.POSTPONED:
            home_b2b = away_b2b = False
        else:
            home_b2b = yesterday in dates_played[g.home_team_id]
            away_b2b = yesterday in dates_played[g.away_team_id]

        if home_b2b or away_b2b:
            b2b_games += 1
        if (home_b2b, away_b2b) != (g.home_b2b, g.away_b2b):
            g.home_b2b, g.away_b2b = home_b2b, away_b2b
            changed.append(g)

    Game.objects.bulk_update(changed, ["home_b2b", "away_b2b"])
    return b2b_games


def build_name_index():
    index = defaultdict(list)
    for player_id, name in Player.objects.filter(is_active=True).values_list("id", "full_name"):
        index[normalize_name(name)].append(player_id)
    return index


@transaction.atomic
def save_injuries(rows, source):
    if not rows:
        raise RuntimeError(f"Injury source '{source}' returned nothing, keeping old statuses")

    names = build_name_index()
    manual_ids = set(Injury.objects.filter(source="manual").values_list("player_id", flat=True))
    injured_ids = set()
    unmatched, unknown_status = [], set()

    for r in rows:
        status = map_status(r["raw_status"])
        if status is None:
            unknown_status.add(r["raw_status"])
            continue

        ids = names.get(normalize_name(r["player_name"]), [])
        if len(ids) != 1:
            unmatched.append(r["player_name"])
            continue

        player_id = ids[0]
        if player_id in manual_ids or status == Injury.Status.AVAILABLE:
            continue

        Injury.objects.update_or_create(
            player_id=player_id,
            defaults={
                "status": status,
                "note": r["note"],
                "reported_at": r["reported_at"],
                "source": source,
            },
        )
        injured_ids.add(player_id)

    # anyone no longer listed is healthy again (manual rows are left alone)
    cleared, _ = Injury.objects.exclude(source="manual").exclude(player_id__in=injured_ids).delete()

    if unmatched:
        log.warning("Couldn't match %d injured players: %s", len(unmatched), ", ".join(unmatched[:20]))
    if unknown_status:
        log.warning("Unknown injury statuses: %s", ", ".join(sorted(unknown_status)))

    return {"injured": len(injured_ids), "cleared": cleared, "unmatched": unmatched, "unknown_status": unknown_status}