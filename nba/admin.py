from django.contrib import admin

from .models import BoxScore, Game, Injury, Player, ProjectionRun, Team


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("abbreviation", "name", "def_rating", "updated_at")


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ("full_name", "team", "positions", "is_active", "team_changed_on")
    list_filter = ("is_active", "team")
    search_fields = ("full_name",)


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ("id", "game_date", "away_team", "home_team", "away_b2b", "home_b2b", "status")
    list_filter = ("season", "status")


@admin.register(BoxScore)
class BoxScoreAdmin(admin.ModelAdmin):
    list_display = ("player", "game", "minutes", "pts", "reb", "ast")
    search_fields = ("player__full_name",)


@admin.register(Injury)
class InjuryAdmin(admin.ModelAdmin):
    list_display = ("player", "status", "note", "source", "reported_at")
    list_filter = ("status", "source")
    search_fields = ("player__full_name",)
    autocomplete_fields = ("player",)

    def save_model(self, request, obj, form, change):
        # hand edits are marked manual so the nightly job leaves them alone
        obj.source = "manual"
        super().save_model(request, obj, form, change)


@admin.register(ProjectionRun)
class ProjectionRunAdmin(admin.ModelAdmin):
    list_display = ("id", "started_at", "finished_at", "status", "model_version")
    list_filter = ("status",)
    readonly_fields = ("started_at", "finished_at", "status", "model_version", "error")