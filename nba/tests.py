from datetime import date
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from nba.data import load
from nba.data.fetch import parse_positions
from nba.data.injuries import normalize_name
from nba.models import BoxScore, Game, Injury, Player, ProjectionRun, Team

BOS, NYK = 1610612738, 1610612752
TODAY = date(2026, 11, 5)

TEAMS = [
    {"id": BOS, "abbreviation": "BOS", "name": "Boston Celtics", "def_rating": 110.5},
    {"id": NYK, "abbreviation": "NYK", "name": "New York Knicks", "def_rating": 112.0},
]
PLAYERS = [
    {"id": 1, "full_name": "Jalen Brunson", "team_id": NYK, "positions": ["PG", "SG"]},
    {"id": 2, "full_name": "Jayson Tatum", "team_id": BOS, "positions": ["SF", "PF"]},
    {"id": 3, "full_name": "Nikola Jokić", "team_id": BOS, "positions": ["C"]},
]


def make_game(game_id, day, home=BOS, away=NYK):
    return {"id": game_id, "season": "2026-27", "game_date": date(2026, 11, day), "tipoff_at": None,
            "home_team_id": home, "away_team_id": away, "status": "final"}


def make_box(player_id, game_id, pts=20):
    return {"player_id": player_id, "player_name": f"Player {player_id}", "team_id": BOS,
            "game_id": game_id, "minutes": 34.5, "pts": pts, "reb": 5, "ast": 4, "stl": 1,
            "blk": 0, "tov": 2, "fg3m": 2, "fgm": 8, "fga": 16, "ftm": 2, "fta": 3, "plus_minus": 4}


def injury(name, status):
    return {"player_name": name, "team": "x", "raw_status": status, "note": "Ankle", "reported_at": None}


GAMES = [make_game("0022600001", 1), make_game("0022600002", 2, home=NYK, away=BOS), make_game("0022600003", 4)]
BOX = [make_box(1, "0022600001"), make_box(2, "0022600001"), make_box(1, "0022600002")]


def load_everything():
    load.save_teams(TEAMS)
    load.save_players(PLAYERS, TODAY)
    load.save_games(GAMES)
    load.save_box_scores(BOX)


class HelperTests(TestCase):
    def test_parse_positions(self):
        self.assertEqual(parse_positions("F-C"), ["SF", "PF", "C"])

    def test_normalize_name(self):
        self.assertEqual(normalize_name("P.J. Washington Jr."), "pj washington")


class LoaderTests(TestCase):
    def test_running_twice_does_not_duplicate(self):
        load_everything()
        load_everything()
        self.assertEqual(Player.objects.count(), 3)
        self.assertEqual(Game.objects.count(), 3)
        self.assertEqual(BoxScore.objects.count(), 3)

    def test_back_to_backs(self):
        load_everything()
        load.mark_back_to_backs("2026-27")
        nov1, nov2, nov4 = Game.objects.order_by("game_date")
        self.assertFalse(nov1.home_b2b or nov1.away_b2b)
        self.assertTrue(nov2.home_b2b and nov2.away_b2b)
        self.assertFalse(nov4.home_b2b or nov4.away_b2b)

    def test_team_change_sets_date(self):
        load_everything()
        load.save_players([dict(PLAYERS[0], team_id=BOS)] + PLAYERS[1:], TODAY)
        self.assertEqual(Player.objects.get(id=1).team_changed_on, TODAY)

    def test_zero_players_refuses_to_save(self):
        load_everything()
        with self.assertRaises(RuntimeError):
            load.save_players([], TODAY)


class InjuryTests(TestCase):
    def setUp(self):
        load_everything()

    def test_matches_accented_names(self):
        load.save_injuries([injury("Nikola Jokic", "Out")], "espn")
        self.assertEqual(Injury.objects.get(player_id=3).status, "out")

    def test_recovered_player_loses_row(self):
        load.save_injuries([injury("Jayson Tatum", "Out")], "espn")
        load.save_injuries([injury("Jalen Brunson", "Doubtful")], "espn")
        self.assertFalse(Injury.objects.filter(player_id=2).exists())

    def test_manual_fix_not_overwritten(self):
        Injury.objects.create(player_id=2, status="out", source="manual")
        load.save_injuries([injury("Jayson Tatum", "Probable")], "espn")
        self.assertEqual(Injury.objects.get(player_id=2).status, "out")


FAKE_FETCH = {
    "nba.data.fetch.fetch_teams": TEAMS,
    "nba.data.fetch.fetch_active_players": PLAYERS,
    "nba.data.fetch.fetch_schedule": GAMES,
    "nba.data.fetch.fetch_past_games": [],
    "nba.data.fetch.fetch_box_scores": BOX,
    "nba.data.injuries.fetch_injuries": [injury("Jayson Tatum", "Out")],
}


class RefreshDataCommandTests(TestCase):
    def run_command(self):
        patchers = [patch(target, return_value=value) for target, value in FAKE_FETCH.items()]
        for p in patchers:
            p.start()
        try:
            call_command("refresh_data", stdout=StringIO())
        finally:
            for p in patchers:
                p.stop()

    def test_two_runs_succeed_without_duplicates(self):
        self.run_command()
        self.run_command()
        self.assertEqual(ProjectionRun.objects.filter(status="success").count(), 2)
        self.assertEqual(BoxScore.objects.count(), 3)
        self.assertEqual(Injury.objects.count(), 1)

    def test_failed_run_is_recorded(self):
        with patch("nba.data.fetch.fetch_teams", side_effect=RuntimeError("blocked by NBA.com")):
            with self.assertRaises(CommandError):
                call_command("refresh_data", stdout=StringIO())
        run = ProjectionRun.objects.get()
        self.assertEqual(run.status, "failed")
        self.assertIn("blocked by NBA.com", run.error)