from django.contrib import admin

from .models import LeagueManager, Roster, RosterSlot, ScoringProfile, TakenPlayer

admin.site.register(ScoringProfile)
admin.site.register(Roster)
admin.site.register(RosterSlot)
admin.site.register(LeagueManager)
admin.site.register(TakenPlayer)
