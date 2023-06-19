from django.contrib import admin

from .models import Match, Player, Log, Stat, SeasonTotal, ScannedMatches

admin.site.register(Match)
admin.site.register(Player)
admin.site.register(Log)
admin.site.register(Stat)
admin.site.register(SeasonTotal)
admin.site.register(ScannedMatches)

# Register your models here.
