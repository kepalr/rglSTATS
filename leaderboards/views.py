from django.shortcuts import render
from django.views.generic import ListView
from django.http import HttpResponse
from django.template import loader
from decimal import Decimal
import collections, functools, operator
from steamid_converter import Converter

import time
from .models import Player, Stat, SeasonTotal, Log, Match
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
        fetchNewStats(p_id, get_more=False)
        return HttpResponseRedirect(f'/player/{p_id}')
    
    else:
        form = SearchPlayer()
        return render(request, 'leaderboards/lookup.html', {'form': form, 'player_id': form['player_id'].value()})

def id(request, player_id):
    return HttpResponse("You are viewing playerId: %s." % player_id)

def name(request, player_id):
    return HttpResponse("You are viewing player: %s." % player_id)

#get the stats for a specific log of a specific match from a specific player
def getStats(p_id, match_info, log):
    if len(log.data.keys()) > 0:
        player_list = [Converter.to_steamID64(p) for p in log.data['players'].keys()]
        player_team_id = match_info.get_team(p_id, string=True)
        if p_id in player_list:
            player_stat = {
                'season_id': match_info.data['seasonId'],
                'match_id': match_info.data['matchId'],
                'log_id': log.log_id,
                'team_id': player_team_id,
                'map': log.data['info']['map'],
                'player_id': p_id,
                'class_played': {c['type']: c['total_time'] for c in log.data['players'][Converter.to_steamID3(p_id)]['class_stats']}, 
                'data': log.data['players'][Converter.to_steamID3(p_id)]
            }
            try:
                player_stat['div_name'] = match_info.data['divName']    
            except:
                player_stat['div_name'] = match_info.data['divisionName']
            finally:
                return player_stat

#return the log stats data in a easy to digest form       
def formatStats(stats):
    stat_keys = ['total_time', 'kills', 'assists', 'deaths', 'damage', 'dapm', 'heal', 'ubers', 'drops', 'headshots', 'headshots_hit', 'backstabs']
    out = {key: stats.get(key) for key in stat_keys if key in stats}
    time_played = sum([s['total_time'] for s in stats.get('class_stats')])
    out['total_time'] = time_played
    return out

#combine matches with the same matchId
def combineLogs(dataset):
    stat_total = {}
    for data in dataset:
        for stat in data.keys():
            try:
                stat_total[stat] += data[stat]
            except:
                stat_total[stat] = data[stat]
    stat_total['dapm'] = int(stat_total['dapm'] / len(dataset))
    stat_total['heal'] = int(stat_total['heal'] / stat_total['total_time'] * 60)
    return stat_total


def seasonTotal(stats):
    season_total = {}
    for season in stats.keys():
        season_total[season] = {}

        for match_stats in stats[season]:
            for stat in match_stats['data']:
                try:
                    season_total[season][stat] += match_stats['data'][stat]
                except:
                    season_total[season][stat] = match_stats['data'][stat]

        season_total[season]['games_played'] = len(stats[season])
        season_total[season]['dapm'] = int(season_total[season]['dapm'] / season_total[season]['games_played'])
        season_total[season]['heal'] = int(season_total[season]['heal'] / season_total[season]['games_played'])
    return season_total

def getPlayerData(player_id):
    from scripts.fillPlayerData import getMatchesPlayer
    Top3 = {}
    matches_played = getMatchesPlayer(player_id)
    time.sleep(1)
    combined_match_logs = {}
    for match in matches_played:
        match_info = Match.objects.get(match_id=match) ## ideally have these make 50+ simueltaneous calls or all the calls in one go, idk
        match_logs = Log.objects.filter(match_id=match)
        formatted_logs = []
        for log in match_logs:
            if player_id in log.get_players():
                get_stat = getStats(player_id, match_info, log)
                formatted_logs.append(get_stat)
                for c, tp in get_stat['class_played'].items():
                    try:
                        Top3[c] += tp
                    except:
                        Top3[c] = tp
               
        if len(formatted_logs) > 0:
            final_log = formatted_logs[0] # initialize with all the data that matches between the same game
            final_log['data'] = combineLogs([formatStats(l['data']) for l in formatted_logs])
            try:
                combined_match_logs[str(match_info.get_season())].append(final_log)
            except:
                combined_match_logs[str(match_info.get_season())] = [final_log]
    
    return{'stats': combined_match_logs, 'main': Top3} 


def stat(request, player_id):
    response = "You are viewing the player's Stats:  %s."
    player = Player.objects.filter(player_id=player_id)
    data = getPlayerData(player_id)
    excluded_fields = ['id', 'player_id', 'class_played', 'games_played']
    context = { 
        'convert': conversionTable,
        'player': player[0].get_name(),
        'headers': ['Kills', 'Assists', 'Deaths', 'DPM', 'HPM', 'Ubers', 'Drops', 'Headshots', 'Headshots_hit', 'Backstabs', 'Time_played'],
        'stats': data['stats'],
        'seasons': seasonTotal(data['stats']),
        'exclude': excluded_fields,
        'main': sorted(data['main'].items(), key=lambda x:x[1], reverse=True)[0:3]

        }
    return render(request, 'leaderboards/stats.html', context)


def division(request, player_id):
    response = "You are viewing the player's Division  %s."
    return HttpResponse(response % player_id)



