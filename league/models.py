from django.conf import settings
from django.db import models

from nba.models import Player


class ScoringProfile(models.Model):
    class Type(models.TextChoices):
        POINTS = "points"
        CATEGORIES = "categories"

    class Preset(models.TextChoices):
        STANDARD_POINTS = "standard_points"
        EXPANDED_POINTS = "expanded_points"
        STANDARD_9CAT = "standard_9cat"
        CUSTOM = "custom"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="scoring_profiles")
    name = models.CharField(max_length=50)
    type = models.CharField(max_length=10, choices=Type.choices)
    preset = models.CharField(max_length=20, choices=Preset.choices, default=Preset.CUSTOM)
    weights = models.JSONField(default=dict, blank=True)
    categories = models.JSONField(default=list, blank=True)

    def __str__(self):
        return self.name


class Roster(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="rosters")
    name = models.CharField(max_length=50)
    scoring_profile = models.ForeignKey(ScoringProfile, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class RosterSlot(models.Model):
    class SlotType(models.TextChoices):
        PG = "PG"
        SG = "SG"
        SF = "SF"
        PF = "PF"
        C = "C"
        G = "G"
        F = "F"
        UTIL = "UTIL"
        BN = "BN"
        IR = "IR"

    roster = models.ForeignKey(Roster, on_delete=models.CASCADE, related_name="slots")
    slot_index = models.IntegerField()
    slot_type = models.CharField(max_length=4, choices=SlotType.choices)
    player = models.ForeignKey(Player, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ["slot_index"]
        constraints = [
            models.UniqueConstraint(fields=["roster", "slot_index"], name="unique_slot_per_roster"),
        ]


class LeagueManager(models.Model):
    roster = models.ForeignKey(Roster, on_delete=models.CASCADE, related_name="managers")
    name = models.CharField(max_length=50)
    players = models.ManyToManyField(Player, blank=True)

    def __str__(self):
        return self.name


class TakenPlayer(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    roster = models.ForeignKey(Roster, on_delete=models.CASCADE, null=True, blank=True, related_name="taken")
    location = models.CharField(max_length=50, default="taken")  # manager name, taken, waiver, or free

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["player", "roster"], name="unique_taken_player_per_roster"),
        ]