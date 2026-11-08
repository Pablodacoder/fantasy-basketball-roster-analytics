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
        
class DummyManager(models.Model):
    id = models.PositiveIntegerField(primary_key=True)
    name = models.CharField(max_length=50)
    
    def __str__(self):
        return self.name
    
class Availability(models.TextChoices):
    FREE = "FREE"
    WAIVER = "WAIVER"
    TAKEN = "TAKEN"

class PlayerListManager(models.Manager):
    def createPlayer(self, id: Player, recruited: bool = False, manager: LeagueManager | None = None):
        p = self.create(id=id, 
                        recruited=recruited,
                        manager=manager)
        return p

    def get_player_by_id(self, player_id: int):
        p_id = Player.objects.get(id=player_id)
        p = self.get(id=p_id)
        return p

    def recruit_player_by_id(self, player_id: int, *, manager: DummyManager | None = None):
        p: PlayerList = self.get_player_by_id(player_id)
        p.add_to_roster(manager=manager)
        return p

class PlayerList(models.Model):
    id = models.OneToOneField("nba.Player", on_delete=models.CASCADE, primary_key=True)
    recruited = models.BooleanField(default=False)
    manager = models.ForeignKey(
        'DummyManager',
        on_delete=models.SET_DEFAULT, 
        default=None, 
        null=True, 
        blank=True
    ) 

    # Manager
    objects = PlayerListManager()
    
    @property
    def player_id(self):
        player: Player = self.id
        return player.id
    
    @property
    def name(self):
        player: Player = self.id
        return player.full_name
    
    @property
    def team(self):
        player: Player = self.id
        return player.team
    
    @property
    def positions(self):
        player: Player = self.id
        return f"{player.positions}"
    
    def manager_name(self):
        if not self.recruited or self.manager is None:
            return ""
        manager = self.manager
        return manager.name

    def __str__(self):
        return f"{self.name}"

    def get_status(self):
        return f"status: {self.recruited}{f" by {self.manager}" if self.manager is not None else ""}"

    def add_to_roster(self, *, manager: DummyManager | None = None):
        if not self.recruited:
            self.recruited = True
            self.manager = manager
            self.save()
        else:
            # TODO throw already taken error
            pass

    def toggle_status(self):
        self.recruited = not self.recruited
        
        if not self.recruited:
            self.manager = None
        
        self.save()