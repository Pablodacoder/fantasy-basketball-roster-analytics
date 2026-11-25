import time
import traceback

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from nba.data import fetch, injuries, load
from nba.models import BoxScore, ProjectionRun

MODEL_VERSION = "m1-data-only"
PAST_SEASONS = 2  # last season and the season before that


class Command(BaseCommand):
    help = "Pull NBA data into the database (teams, players, schedule, box scores, injuries)."

    def add_arguments(self, parser):
        parser.add_argument("--full", action="store_true",
                            help="Reload past seasons' box scores even if we already have them.")
        parser.add_argument("--skip-injuries", action="store_true",
                            help="Don't pull injuries.")

    def log(self, message):
        self.stdout.write(f"[{timezone.localtime():%H:%M:%S}] {message}")

    def handle(self, *args, **options):
        run = ProjectionRun.objects.create(status=ProjectionRun.Status.RUNNING, model_version=MODEL_VERSION)
        started = time.monotonic()
        self.log(f"Started run #{run.id}")

        try:
            self.pull_everything(options)
            run.status = ProjectionRun.Status.SUCCESS
        except Exception as exc:
            run.status = ProjectionRun.Status.FAILED
            run.error = traceback.format_exc()
            raise CommandError(f"refresh_data failed: {exc}") from exc
        finally:
            run.finished_at = timezone.now()
            run.save()
            self.log(f"Run #{run.id} finished: {run.status} ({time.monotonic() - started:.0f}s)")

    def pull_everything(self, options):
        today = timezone.localdate()
        start_year = fetch.season_start_year(today)
        this_season = fetch.season_string(start_year)
        past_seasons = [fetch.season_string(start_year - n) for n in range(1, PAST_SEASONS + 1)]
        self.log(f"Seasons: {this_season} (current), past: {', '.join(past_seasons)}")

        teams = fetch.fetch_teams(this_season)
        self.log(f"Teams saved: {load.save_teams(teams)}")

        players = fetch.fetch_active_players(this_season, [t["id"] for t in teams])
        active, newly_inactive = load.save_players(players, today)
        self.log(f"Active players: {active} ({newly_inactive} newly inactive)")

        schedule = fetch.fetch_schedule(this_season)
        self.log(f"{this_season} games saved: {load.save_games(schedule)}")

        for season in past_seasons:
            already_have = BoxScore.objects.filter(game__season=season).exists()
            if options["full"] or not already_have:
                past_games = fetch.fetch_past_games(season)
                self.log(f"{season} games saved: {load.save_games(past_games)}")
                past_box = fetch.fetch_box_scores(season)
                self.log(f"Players added from old box scores: {load.ensure_box_score_players(past_box)}")
                self.log(f"{season} box scores saved: {load.save_box_scores(past_box)}")
            else:
                self.log(f"{season} already loaded, skipping (use --full to reload)")

        box = fetch.fetch_box_scores(this_season)
        load.ensure_box_score_players(box)
        self.log(f"{this_season} box scores saved: {load.save_box_scores(box)}")

        for season in [this_season] + past_seasons:
            self.log(f"{season} back-to-back games: {load.mark_back_to_backs(season)}")

        if options["skip_injuries"]:
            self.log("Skipping injuries")
        else:
            source = settings.INJURY_SOURCE
            result = load.save_injuries(injuries.fetch_injuries(source), source)
            self.log(f"Injuries from {source}: {result['injured']} injured, "
                     f"{result['cleared']} cleared, {len(result['unmatched'])} unmatched names")