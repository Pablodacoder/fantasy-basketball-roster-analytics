from django.db import models
from django.utils import timezone


class Team(models.Model):
    id = models.IntegerField(primary_key=True)  # NBA team id
    abbreviation = models.CharField(max_length=3)
    name = models.CharField(max_length=50)
    def_rating = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.abbreviation


class Player(models.Model):
    id = models.IntegerField(primary_key=True)  # NBA person id
    full_name = models.CharField(max_length=100, db_index=True)
    team = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True, related_name="players")
    positions = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)
    team_changed_on = models.DateField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.full_name


class Game(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = "scheduled"
        FINAL = "final"
        POSTPONED = "postponed"

    id = models.CharField(max_length=12, primary_key=True)  # NBA game id
    season = models.CharField(max_length=7, db_index=True)  # e.g. 2026-27
    game_date = models.DateField(db_index=True)
    tipoff_at = models.DateTimeField(null=True, blank=True)
    home_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="home_games")
    away_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="away_games")
    home_b2b = models.BooleanField(default=False)
    away_b2b = models.BooleanField(default=False)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.SCHEDULED)

    def __str__(self):
        return f"{self.away_team} @ {self.home_team} ({self.game_date})"


class BoxScore(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="box_scores")
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="box_scores")
    minutes = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    pts = models.IntegerField(default=0)
    reb = models.IntegerField(default=0)
    ast = models.IntegerField(default=0)
    stl = models.IntegerField(default=0)
    blk = models.IntegerField(default=0)
    tov = models.IntegerField(default=0)
    fg3m = models.IntegerField(default=0)
    fgm = models.IntegerField(default=0)
    fga = models.IntegerField(default=0)
    ftm = models.IntegerField(default=0)
    fta = models.IntegerField(default=0)
    plus_minus = models.IntegerField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["player", "game"], name="one_box_score_per_player_per_game"),
        ]


class Injury(models.Model):
    # No row at all = Available
    class Status(models.TextChoices):
        AVAILABLE = "available"
        PROBABLE = "probable"
        QUESTIONABLE = "questionable"
        DOUBTFUL = "doubtful"
        OUT = "out"

    player = models.OneToOneField(Player, on_delete=models.CASCADE, related_name="injury")
    status = models.CharField(max_length=12, choices=Status.choices)
    note = models.CharField(max_length=200, blank=True)
    reported_at = models.DateTimeField(null=True, blank=True)
    source = models.CharField(max_length=30)  # source name, or "manual"

    class Meta:
        verbose_name_plural = "injuries"

    def __str__(self):
        return f"{self.player}: {self.status}"


class ProjectionRun(models.Model):
    class Status(models.TextChoices):
        RUNNING = "running"
        SUCCESS = "success"
        FAILED = "failed"

    started_at = models.DateTimeField(default=timezone.now)
    finished_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.RUNNING)
    model_version = models.CharField(max_length=30, blank=True)
    error = models.TextField(blank=True)

    def __str__(self):
        return f"Run {self.id} ({self.status})"


class Projection(models.Model):
    # Not filled until Milestone 2, but the plan wants every table in the first migration
    class Confidence(models.TextChoices):
        LOW = "low"
        MEDIUM = "medium"
        HIGH = "high"

    run = models.ForeignKey(ProjectionRun, on_delete=models.CASCADE, related_name="projections")
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="projections")
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="projections")
    minutes = models.FloatField(default=0)
    pts = models.FloatField(default=0)
    reb = models.FloatField(default=0)
    ast = models.FloatField(default=0)
    stl = models.FloatField(default=0)
    blk = models.FloatField(default=0)
    tov = models.FloatField(default=0)
    fg3m = models.FloatField(default=0)
    fgm = models.FloatField(default=0)
    fga = models.FloatField(default=0)
    ftm = models.FloatField(default=0)
    fta = models.FloatField(default=0)
    play_prob = models.FloatField(default=1.0)
    confidence = models.CharField(max_length=6, choices=Confidence.choices, default=Confidence.MEDIUM)
    factors = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["run", "player", "game"], name="one_projection_per_run_player_game"),
        ]

#Team: the 30 NBA teams. def_rating is used in Milestone 2 to adjust for tough or easy opponents.
#Player: every player. id is NBA.com’s own id, which is what stops duplicates when the job runs twice. positions is a list like ["PG", "SG"].
#Game: every game, past and future. home_b2b and away_b2b mark back-to-backs.
#BoxScore: one player’s stats from one game. The UniqueConstraint makes duplicates impossible.
#Injury: a player’s current status. No row means they’re healthy.
#ProjectionRun: one row every time the nightly job runs, saying whether it worked.
#Projection: projected stats for future games. It stays empty until Milestone 2, but the plan wants the table created now.