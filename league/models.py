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
        
class RosterList(models.Model):
    #owner = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    PG = models.ForeignKey(Player, related_name="roster_PG", on_delete=models.SET_DEFAULT, null=True, default=None)
    SG = models.ForeignKey(Player, related_name="roster_SG", on_delete=models.SET_DEFAULT, null=True, default=None)
    SF = models.ForeignKey(Player, related_name="roster_SF", on_delete=models.SET_DEFAULT, null=True, default=None)
    PF = models.ForeignKey(Player, related_name="roster_PF", on_delete=models.SET_DEFAULT, null=True, default=None)
    C = models.ForeignKey(Player, related_name="roster_C", on_delete=models.SET_DEFAULT, null=True, default=None)
    G = models.ForeignKey(Player, related_name="roster_G", on_delete=models.SET_DEFAULT, null=True, default=None)
    F = models.ForeignKey(Player, related_name="roster_F", on_delete=models.SET_DEFAULT, null=True, default=None)
    UTIL = models.ForeignKey(Player, related_name="roster_UTIL", on_delete=models.SET_DEFAULT, null=True, default=None)
    BN = models.ForeignKey(Player, related_name="roster_BN", on_delete=models.SET_DEFAULT, null=True, default=None)
    IR = models.ForeignKey(Player, related_name="roster_IR", on_delete=models.SET_DEFAULT, null=True, default=None)
    
    def __str__(self):
        return f"{self.name}: "
    
    def to_dict(self):
        return {"PG": self.PG, "SG": self.SG, "SF": self.SF, "PF": self.PF, "C": self.C, "G": self.G, "F": self.F, "UTIL": self.UTIL, "BN": self.BN, "IR": self.IR}
    
    def to_name_dict(self):
        return {"PG": self.PG.full_name, "SG": self.SG.full_name, "SF": self.SF.full_name, "PF": self.PF.full_name, "C": self.C.full_name, "G": self.G.full_name, "F": self.F.full_name, "UTIL": self.UTIL.full_name, "BN": self.BN.full_name, "IR": self.IR.full_name}
    
    def to_list(self):
        return [self.PG, self.SG, self.SF, self.PF, self.C, self.G, self.F, self.UTIL, self.BN, self.IR]
    
    def add_to_roster(self, player: Player | int, position: str):
        # Returns 0 if success
        # Returns 1 if fail
        if type(player) is int:
            player = Player.objects.get(player)
        match position:
            case "PG":
                if self.PG is None:
                    self.PG = player
                    self.save()
                    return 0
            case "SG":
                if self.SG is None:
                    self.SG = player
                    self.save()
                    return 0
            case "SF":
                if self.SF is None:
                    self.SF = player
                    self.save()
                    return 0
            case "PF":
                if self.PF is None:
                    self.PF = player
                    self.save()
                    return 0
            case "C":
                if self.C is None:
                    self.C = player
                    self.save()
                    return 0
            case "G":
                if self.G is None:
                    self.G = player
                    self.save()
                    return 0
            case "F":
                if self.F is None:
                    self.F = player
                    self.save()
                    return 0
            case "UTIL":
                if self.UTIL is None:
                    self.UTIL = player
                    self.save()
                    return 0
            case "BN":
                if self.BN is None:
                    self.BN = player
                    self.save()
                    return 0
            case "IR":
                if self.IR is None:
                    self.IR = player
                    self.save()
                    return 0
            case _:
                print("Invalid position") # TODO add exception
        return 1       
        
    def remove_from_roster(self, p_id: int):
        print(f"Attempting to remove {p_id}")
        if self.PG is not None:
            if self.PG.id == p_id:
                self.PG = None
                
        if self.SG is not None:
            if self.SG.id == p_id:
                self.SG = None
                
        if self.SF is not None:
            if self.SF.id == p_id:
                self.SF = None
                
        if self.PF is not None:
            if self.PF.id == p_id:
                self.PF = None
                
        if self.C is not None:
            if self.C.id == p_id:
                self.C = None
                
        if self.G is not None:
            if self.G.id == p_id:
                self.G = None
                
        if self.F is not None:
            if self.F.id == p_id:
                self.F = None
                
        if self.UTIL is not None:
            if self.UTIL.id == p_id:
                self.UTIL = None
                
        if self.BN is not None:
            if self.BN.id == p_id:
                self.BN = None
                
        if self.IR is not None:
            if self.IR.id == p_id:
                self.IR = None
        
        self.save()

    def remove_slot(self, slot: str):
        slots = ["PG", "SG", "SF", "PF", "C", "G", "F", "UTIL", "BN", "IR"]
        if slot not in slots:
            print("Tried to remove a slot that does not exist") # TODO change to exception
            return
        setattr(self, slot, None)
        self.save()
        
        
    def clear_roster(self):
        self.PG = None
        self.SG = None
        self.SF = None
        self.PF = None
        self.C = None
        self.G = None
        self.F = None
        self.UTIL = None
        self.BN = None
        self.IR = None
        self.save()
    
class Availability(models.TextChoices):
    FREE = "FREE"
    WAIVER = "WAIVER"
    TAKEN = "TAKEN"

class PlayerListManager(models.Manager):
    def createPlayer(self, id: Player, recruited: bool = False):
        p = self.create(id=id, 
                        recruited=recruited)
        return p

    def get_player_by_id(self, player_id: int):
        p_id = Player.objects.get(id=player_id)
        p = self.get(id=p_id)
        return p

    def recruit_player_by_id(self, player_id: int):
        p: PlayerList = self.get_player_by_id(player_id)
        return p

class PlayerList(models.Model):
    id = models.OneToOneField("nba.Player", on_delete=models.CASCADE, primary_key=True)
    recruited = models.BooleanField(default=False)

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
        return player.positions
    

    def __str__(self):
        return f"{self.name}"

    def get_status(self):
        return f"status: {self.recruited}{f" by {self.manager}" if self.manager is not None else ""}"

    def add_to_roster(self):
        if not self.recruited:
            self.recruited = True
            self.save()
        else:
            # TODO throw already taken error
            pass

    def toggle_status(self):
        self.recruited = not self.recruited
        
        if not self.recruited:
            self.manager = None
        
        self.save()