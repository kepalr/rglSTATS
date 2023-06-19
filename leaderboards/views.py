from django.shortcuts import render
from django.views.generic import ListView
from django.http import HttpResponse
from django.template import loader
from decimal import Decimal
import collections, functools, operator

from .models import Player, Stat, SeasonTotal
# from .tables import SeasonTable
from django.db.models import F, Case, When, ExpressionWrapper, FloatField
from django.db import models
from .forms import SearchPlayer
from django.http import HttpResponseRedirect


szn = 72

conversionTable = {
    '53': 'Season 1',
    '67': 'Season 2',
    '72': 'Season 3',
    '95': 'Season 4',
    '105': 'Season 5',
    '110': 'Season 6',
    '120': 'Season 7',
    '123': 'Season 8',
    '127': 'Season 9',
    '129': 'Season 10',
    '133': 'Season 11',
    'games_played': 'Games Played'
}

# class SeasonListView(ListView):
#     div = 'Amateur'
#     model = SeasonTotal
#     template_name='index.html'
#     table_class=SeasonTable
#     context_object_name = 'season_totals'
#     # queryset = SeasonTable.objects.filter(season_id=133, div_name=div, games_played__gt=1)
#     def get_queryset(self):
#         print(SeasonTotal.objects.filter(season_id=szn, div_name=self.div, games_played__gt=2))
#         return SeasonTotal.objects.filter(season_id=szn, div_name=self.div, games_played__gt=2)

    
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         context['division'] = self.div
#         return context
    
def sum_time_played(data):
    result = {}
    for item in data:
        class_played = item['class_played']
        time_played = item['time_played']
        if class_played in result:
            result[class_played] += time_played
        else:
            result[class_played] = time_played
    
    # Convert the dictionary to a list of dictionaries
    return [{'class_played': key, 'time_played': value} for key, value in result.items()]

def index(request, div='Invite', c='all'):

    season = szn
    ## below can be done better
    ## also make a stat for market gardener kills

    context = {"stats": {}}
    if c == 'all':
        stats = ['games_played', 'kills', 'assists', 'deaths', 'dapm', 'headshots', 'headshots_hit', 'backstabs']
    else:
        stats = ['games_played', 'kills', 'assists', 'deaths', 'dapm', 'time_played']

    for s in stats:
        context['stats'][s] = SeasonTotal.objects.filter(season_id=season, div_name=div, games_played__gt=2, class_played=c).order_by(f'-{s}')[:10]
    
    if c == 'medic':
        context['stats']['heal'] = SeasonTotal.objects.filter(season_id=season, div_name=div, games_played__gt=2, class_played='all').annotate(
                hpm=ExpressionWrapper(
                    Case(
                        When(time_played=0, then=0),
                        default= F('heal')/ F('time_played'),
                        output_field=FloatField()
                    ),
                    output_field=FloatField()
                )
            ).order_by(f'-hpm')[:10]
        for extra_stat in ['ubers', 'drops']:
            context['stats'][extra_stat] = SeasonTotal.objects.filter(season_id=season, div_name=div, games_played__gt=2, class_played='all').order_by(f'-{extra_stat}')[:10]

    if c == 'sniper':
        for extra_stat in ['headshots_hit', 'headshots']:
            context['stats'][extra_stat] = SeasonTotal.objects.filter(season_id=season, div_name=div, games_played__gt=2, class_played='all').order_by(f'-{extra_stat}')[:10]

    context['stat30'] = ['kills', 'assists', 'deaths', 'ubers', 'headshots', 'headshots_hit']
    context['div'] = div
    context['c'] = c
    template = loader.get_template('leaderboards/index.html')

    return HttpResponse(template.render(context, request))

def lookup(request):
    if request.method == 'POST' and 'fetch_data' in request.POST:
        from scripts.fillPlayerData import fetchNewStats
        print('POST')
        print(request)
        form = SearchPlayer(request.POST)
        p_id = form['player_id'].value()
        print(p_id)
        fetchNewStats(p_id)
        # return stat(request, p_id)
        return HttpResponseRedirect(f'/leaderboards/player/{p_id}')
    
    else:
        form = SearchPlayer()
        return render(request, 'leaderboards/lookup.html', {'form': form, 'player_id': form['player_id'].value()})

def id(request, player_id):
    return HttpResponse("You are viewing playerId: %s." % player_id)

def name(request, player_id):
    return HttpResponse("You are viewing player: %s." % player_id)

def stat(request, player_id):
    response = "You are viewing the player's Stats:  %s."
    player = Player.objects.filter(player_id=player_id)
    seasons_played = [s['data']['seasonId'] for s in player.values('data')]
    seasons_played.sort()
    stats = {s:Stat.objects.filter(player_id=player_id, season_id=s) for s in seasons_played}
    # stats = Stat.objects.filter(player_id=player_id)
    #each_stat = [stat.player_stats for stat in stats]
    excluded_fields = ['id', 'player_id', 'class_played']
    season = SeasonTotal.objects.filter(player_id=player_id, class_played='all').values()[0]
    seasons = SeasonTotal.objects.filter(player_id=player_id, class_played='all').values().order_by('-season_id')
    primary_classes = SeasonTotal.objects.filter(player_id=player_id).exclude(class_played='all').values('class_played', 'time_played').order_by('-time_played') #1 index because 0 wuld be 'all'
    top3 = sum_time_played(primary_classes)[:3]
    context = { 
        'convert': conversionTable,
        'player': player[0].get_name,
        'headers': ['Kills', 'Assists', 'Deaths', 'DPM', 'HPM', 'Ubers', 'Drops', 'Headshots', 'Headshots_hit', 'Backstabs', 'Time_played'],
        'SP': seasons_played,
        'stats': stats,
        'season': season,
        'seasons': seasons,
        'exclude': excluded_fields,
        'main': top3
        }
    return render(request, 'leaderboards/stats.html', context)
    #return HttpResponse(response % player_id)

def division(request, player_id):
    response = "You are viewing the player's Division  %s."
    return HttpResponse(response % player_id)



