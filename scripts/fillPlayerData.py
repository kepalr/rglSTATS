import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from steamid_converter import Converter
import time
from datetime import datetime
import logging
import django
import os
import sys

# Add the parent directory of the current directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Add the rglSTATS folder to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'rglSTATS')))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rglSTATS.settings')
django.setup()

from leaderboards.models import Match, Player, Log, Stat, SeasonTotal, ScannedMatches
LOGS_API = 'http://logs.tf/api/v1/log'
RGL_API = 'https://api.rgl.gg/v0/'
GET_MATCH = 'matches/'
GET_TEAM = 'teams/'
GET_SEASON = 'seasons/'
GET_PLAYER = 'profile/'
GET_PLAYER_TEAMS = '/teams'
THREAD_POOL = 16




session = requests.Session()
session.mount(
    'https://',
    requests.adapters.HTTPAdapter(pool_maxsize=THREAD_POOL,
                                    max_retries=10,
                                    pool_block=True)
)

def get(url):
    timeout = 15  # maximum time to wait for a response in seconds
    retries = 10  # number of times to retry the request
    for i in range(retries):
        try:
            response = requests.get(url, timeout=timeout)
            logging.info("request was completed in %s seconds [%s]", response.elapsed.total_seconds(), response.url)
            if response.status_code != 200:
                logging.error("request failed, error code %s [%s]", response.status_code, response.url)
            if 500 <= response.status_code < 600:
                # server is overloaded lol
                logging.info("server overloaded after %s seconds [%s]", response.elapsed.total_seconds(), response.url)
                time.sleep(5)
            return response
        except requests.exceptions.Timeout:
            logging.warning("request timed out, retrying in 5 seconds [%s]", url)
            time.sleep(5)
    # all retries failed, raise an exception
    raise requests.exceptions.Timeout("maximum number of retries reached, could not get a response from {}".format(url))

async def post(url):
    timeout = 15  # maximum time to wait for a response in seconds
    retries = 10  # number of times to retry the request
    for i in range(retries):
        try:
            response =  await print(os.system(f"curl -X 'POST' \
                    '{url}' \
                    -H 'accept: */*' \
                    -H 'Content-Type: application/json' \
                    -d '{{}}'"))
            return response
        except:
            print('cURL no likey')
            return []

def flatten(l):
    return [item for sublist in l for item in sublist]

def datedMatch(matchDate, logDate):
    h = 3600
    return (matchDate- 5*h - (2*h)) <= (logDate - (6*h)) <= (matchDate- 5*h + (2*h))

# give match date - returns in epoch seconds
def matchDateEpoch(matchDate):
    date_obj = datetime.fromisoformat(matchDate[:-1])
    return date_obj.timestamp()
    # return matchDate.timestamp()

def verify_match_info(match_info):
    return (match_info.data['matchName'] is not None
        and len(match_info.data['maps']) > 0
        and 'BYE WEEK' not in [team['teamName'] for team in match_info.data['teams']]
        and len(match_info.data['teams']) == 2
        and match_info.data['isForfeit'] == False
        and 'winner' in match_info.data.keys()
        and ('divName' in match_info.data.keys() or 'divisionName' in match_info.data.keys())
        and match_info.data['matchDate'] is not None)

def playerThreshold(team1, team2, logPlayers):

    playerKeys = logPlayers['players'].keys()
    own_count = 0
    their_count = 0
    # print(team1)
    # print('========')
    # print(team2)
    # print('========')
    # print(playerKeys)

    for id in playerKeys:
        if Converter.to_steamID64(id) in team1:
            own_count += 1
        elif Converter.to_steamID64(id) in team2:
            their_count +=1

    if (their_count / 6 * 100) >= 50 and (own_count / 6 * 100) >= 50:
        return True
    return False 

def confirmScores(winScore, loseScore, logScore):
    if winScore == 5:
        return (int(winScore) == int(max(logScore)) or int(winScore + 1) == int(max(logScore))) and int(loseScore) == int(min(logScore))
    else:
        return (int(winScore) == int(max(logScore))) and int(loseScore) == int(min(logScore))

def write_log(log, match, log_data, bad=0):
    log = Log(
        log_id=log,
        match_id=match,
        data=log_data,
        no_log=bad
    )
    log.save()
    if bad == 0:
        print(f'Successfully paired log to match ({log} -> {match})')
    else:
        print(f'No Log for Match: {match}')

def verify_match_info(match_info):
    return (match_info.data['matchName'] is not None
        and len(match_info.data['maps']) > 0
        and 'BYE WEEK' not in [team['teamName'] for team in match_info.data['teams']]
        and len(match_info.data['teams']) == 2
        and match_info.data['isForfeit'] == False
        and 'winner' in match_info.data.keys()
        and ('divName' in match_info.data.keys() or 'divisionName' in match_info.data.keys())
        and match_info.data['matchDate'] is not None)


def getOfficialLogs(urls, matchDetails):
    print(f'attempting to get official logs from {len(urls)} logs')
    ### JEsus fucking christ admins posting match scores as different than offical posted log scores if team disbands, and then they are given 5-0, dumb
    with ThreadPoolExecutor(max_workers=THREAD_POOL) as executer:
        # wrap in list and wait for all requests to complete
        Official_Logs_responses = []
        Official_Logs_ids = []
        Score = [0, 0]
        try:
            winner = max(matchDetails.data['maps'][0]['homeScore'], matchDetails.data['maps'][0]['awayScore'])
            loser = min(matchDetails.data['maps'][0]['homeScore'], matchDetails.data['maps'][0]['awayScore'])
            team_ids = matchDetails.get_players(both=True)
            # print('the teamIds going into it:')
            # print(team_ids)
            # print('=====')
            team1 = [p['player_id'] for p in team_ids['team1']]
            team2 = [p['player_id'] for p in team_ids['team2']]
        except:
            print('eat shit')
            # print(winner)
            # print(loser)
            # print(team_ids)
            
        else:
            for response in list(executer.map(get, urls)): #for each potential log (could be log logs for 2 halves or 1 single log for full game)
                quit = 0
                while response.status_code != 200:
                    if quit == 100:
                        break
                    else:
                        quit += 1
                    time.sleep(1) #remove this?
                if response.status_code == 200:
                    if playerThreshold(team1, team2, response.json()):
                        print('player threshold passed')
                        Score[0] += response.json()['teams']['Red']['score']
                        Score[1] += response.json()['teams']['Blue']['score']
                        Official_Logs_responses.append(response.json())
                        Official_Logs_ids.append(response.url.rsplit('/', 1)[-1])
                        if confirmScores(winner, loser, Score):
                            print('scores confirmed working')
                            for idx in range(len(Official_Logs_ids)):
                                write_log(Official_Logs_ids[idx], matchDetails.data['matchId'], Official_Logs_responses[idx])
                            return True ## moving this out one block i think fixed only the first log for each match getting documented
                        elif len(Official_Logs_responses) > 1: 
                            print(f"LOG BOUNCED BC IMPROPER SCORES: {response.url}")
                            # this is for rare case where combined match log gets uploaded right after offical and is counted before the individual halves are added
                            Score[0] -= response.json()['teams']['Red']['score']
                            Score[1] -= response.json()['teams']['Blue']['score']
                            Official_Logs_responses.pop()
                            Official_Logs_ids.pop()
                        else:
                            print('player count good, number of logs returned good, scores were bad?')
                            print(f'Winner: {winner}\nLoser: {loser}\nScore: {Score}')
                    else:
                        print('player threshold failed')
        print(f"match had no log for matchId: {matchDetails.match_id}")
        return False

### IMPORTANT ###  in order for this to all work you need to fill the match table AND players table (matching players to their teams) completely, so that any time a player is looked up, the matches can be cross referenced
### SO YOU NEED TO RUN GET_MATCHES(SZN) AND GET_TEAMS(SZN) or combine them and run them

### player table needs to be filled because Match model has method get_players which needs the player table to be full as well
### when a log is confirmed, everyone needs to be checked to make sure they are the right number of players to verify the match.
def getMatchesPlayer(player_id):
    seasons = []
    matches = []
    teams = []
    try:
        past_teams = get(RGL_API + GET_PLAYER + player_id + GET_PLAYER_TEAMS).json()
    except:  
        print(f'getTeams failed to get teams for player: {player_id}')
    else:
        for team in past_teams:
            # print(team)
            if team['formatName'] == "Sixes":
                seasons.append(team['seasonId'])
                teams.append(team['teamId'])
                # match_list = Match.objects.all().filter(data__teams__contains=[{"teamId": team["teamId"]}]).values_list('match_id', flat=True)
                # if len(match_list) > 0:
                #     matches.append(match_list)
                match_list = Match.objects.all().filter(data__teams__contains=[{"teamId": team["teamId"]}])
                for match in match_list:
                    if verify_match_info(match):
                        matches.append(match.match_id)

    return matches

def getSeasonsPlayer(player_id):
    seasons = []
    teams = []
    try:
        past_teams = get(RGL_API + GET_PLAYER + player_id + GET_PLAYER_TEAMS).json()
    except:  
        print('getTeams failed to get teams - trying again')
    else:
        for team in past_teams:
            # print(team)
            if team['formatName'] == "Sixes":
                seasons.append(team['seasonId'])
                teams.append(team['teamId'])
                season_list = Match.objects.all().filter(data__teams__contains=[{"teamId": team["teamId"]}]).values_list('data__seasonId', flat=True)
                if len(season_list) > 0:
                    # season_list = set(season_list)
                    seasons.append(season_list[0])

    out = list(set(seasons))
    out.remove(139)
    return out

def get_logs(p_id, match_list):
    start=0
    total = len(match_list)
    for match in match_list:
        start+=1
        if (len(Log.objects.filter(match_id=match)) == 0):
            print(f'{start}/{total} Matches paired to Logs ({round(start/total*100)}% Complete)')
            error = False
            try:
                match_info = Match.objects.get(match_id=match)
            except:
                error = True
                print("No Match Found in Database")
            if error == False and verify_match_info(match_info) == True:
                if len(match_info.data['maps']) == 1: # only track regular season games for now
                    # player_list = match_info.get_players()
                    # quit=0
                    # cache = []
                    # for player in player_list:
                    # if len(player_list) - quit < 4: # with not enough players remaining to even meet the player threshold, stop looking for the log
                    #     write_log(0, match, {}, bad=1)
                    #     break
                    # else:
                    # quit+=1
                    # print("for player:", player["player_id"])
                    logs = f'{LOGS_API}?map={match_info.data["maps"][0]["mapName"]}&player={p_id}'
                    try:
                        THE_LOGS = get(logs).json()['logs'] # request to get all logs from a specified playerId on a specified map
                    except:
                        print('bad response - skipping')
                    else:
                        try:
                            THE_LOGS_THAT_DAY = [log for log in THE_LOGS if datedMatch(matchDateEpoch(match_info.data["matchDate"]), log['date'])]
                        except:
                            print('something went wrong - probably null matchDate')
                        else:
                            # if THE_LOGS_THAT_DAY not in cache:
                                # cache.append(THE_LOGS_THAT_DAY) # cache this log check so we dont have to check these same logs mutliple times
                            if getOfficialLogs([f'{LOGS_API}/{log["id"]}' for log in THE_LOGS_THAT_DAY], match_info) == True:
                                print('got logs')
                            else:
                                print('no logs rip')
        else:
            print('existing log')

def get_stats(p_id, matches):

    # stats are the tables containing all the relevent information from th log needed to crete the players total stats
    # season_id = models.IntegerField()
    # div_name = models.CharField(max_length=64)
    # match_id = models.IntegerField()
    # log_id = models.IntegerField()
    # team_id = models.IntegerField()
    # map = models.CharField(max_length=64)
    # player_id = models.CharField(max_length=50)
    # data = models.JSONField() 

    # for each log where no_log=0, get the match id and then get match info, then store the match info and log data for the player in stat
    # this is just for the purpose of filling logs to use as data, still need a way to append new data

    # this will need to be flipped around to get the matches first, then the logs
   
    start=0
    total = len(matches)
    fail = False

    for match in matches:
        log_list = Log.objects.filter(match_id=match).values()
        print(f'{start}/{total} matches checked for log stat entry ({round(start/total*100)}% Complete)')
        start+=1

        for log in log_list:
            if len(log['data'].keys()) > 0:
                try:
                    match_info = Match.objects.get(match_id=match)
                except:
                    print('non relevant match log')
                else:
                    # player_list = log['data']['players'].keys()
                    player_list = [Converter.to_steamID64(p) for p in log['data']['players'].keys()]
                    player_team_id = match_info.get_team(Converter.to_steamID64(p_id))
                    # teams = [team['teamId'] for team in match_info.data['teams']]
                    if p_id in player_list:
                        try:
                            stat = Stat(
                                season_id=match_info.data['seasonId'],
                                div_name=match_info.data['divName'],
                                match_id=match_info.data['matchId'],
                                log_id=log['log_id'],
                                team_id=player_team_id,
                                map=log['data']['info']['map'],
                                player_id=p_id,
                                data=log['data']['players'][Converter.to_steamID3(p_id)]
                            )
                        except:
                            stat = Stat(
                                season_id=match_info.data['seasonId'],
                                div_name=match_info.data['divisionName'],
                                match_id=match_info.data['matchId'],
                                log_id=log['log_id'],
                                team_id=player_team_id,
                                map=log['data']['info']['map'],
                                player_id=p_id,
                                data=log['data']['players'][Converter.to_steamID3(p_id)]
                            )
                        finally:
                            stat.save()

                    # for player in player_list:
                    #     try:
                    #         player_team_id = match_info.get_team(Converter.to_steamID64(player))
                    #     except:
                    #         fail=True
                    #         print("player_id: ", Converter.to_steamID64(player))
                    #         print("match_id: ", match_info.data['matchId'])
                    #         print("log_id: ", log['log_id'])

                    #     if player_team_id in teams:
                    #         try:
                    #             stat = Stat(
                    #                 season_id=match_info.data['seasonId'],
                    #                 div_name=match_info.data['divName'],
                    #                 match_id=match_info.data['matchId'],
                    #                 log_id=log['log_id'],
                    #                 team_id=player_team_id,
                    #                 map=log['data']['info']['map'],
                    #                 player_id=Converter.to_steamID64(player),
                    #                 data=log['data']['players'][player]
                    #             )
                    #         except:
                    #             stat = Stat(
                    #                 season_id=match_info.data['seasonId'],
                    #                 div_name=match_info.data['divisionName'],
                    #                 match_id=match_info.data['matchId'],
                    #                 log_id=log['log_id'],
                    #                 team_id=player_team_id,
                    #                 map=log['data']['info']['map'],
                    #                 player_id=Converter.to_steamID64(player),
                    #                 data=log['data']['players'][player]
                    #             )
                    #         finally:
                    #             stat.save()

def append_season_total(player, data, class_played=None, log_count=1):
    if data['games_played'] > 0:
        if class_played is None:
            player.games_played = player.games_played + data['games_played']
            player.time_played = player.time_played + data['total_time']
            player.kills = player.kills + data['kills']
            player.assists = player.assists + data['assists']
            player.deaths = player.deaths + data['deaths']
            player.dapm = ((player.dapm * (player.games_played - data['games_played'])) + (data['dapm'] / log_count)) / player.games_played #special (current dapm * current gp) + added dapm / new gp
            player.heal = player.heal + data['heal']
            player.ubers = player.ubers + data['ubers']
            player.drops = player.drops + data['drops']
            player.headshots = player.headshots + data['headshots']
            player.headshots_hit = player.headshots_hit + data['headshots_hit']
            player.backstabs = player.backstabs + data['backstabs']
        else:
            player.games_played = player.games_played + data['games_played']
            player.time_played = player.time_played + data['total_time']
            player.kills = player.kills + data['kills']
            player.assists = player.assists + data['assists']
            player.deaths = player.deaths + data['deaths']
            player.class_played = class_played
            player.dapm = ((player.dapm * (player.time_played - data['total_time'])/ 60) + (data['dmg'] / log_count)) / player.time_played *60

    player.save()

# on first entry, create blank profile for each class and class total, then if they never play as say spy, they wil just show 0s, else, show the individual class stats
# make method for getting player primary class by returning highest total time class for a season


def fill_season(p_id, matches):
    # players = Player.objects.filter(data__seasonId=szn)
    stat_list = ['total_time', 'kills', 'assists', 'deaths', 'dapm', 'heal', 'ubers', 'drops', 'headshots', 'headshots_hit', 'backstabs']
    stat_list_per_class = ['type', 'kills', 'assists', 'deaths', 'dmg', 'total_time']
    class_list = ['scout', 'soldier', 'pyro', 'demoman', 'heavyweapons', 'engineer', 'medic', 'sniper', 'spy']
    total = len(matches)
    start = 0
    for match in matches:
        match_info = Match.objects.get(match_id=match)
        start+=1
        print(f'{start}/{total} Logs checked for stat entry ({round(start/total*100)}% Complete)')
        db_data = {}
        gp = []
        try:
            the_player = SeasonTotal.objects.filter(player_id=p_id, div_name=match_info.data['divName'], class_played='all', season_id=match_info.data['seasonId']) #future reference we will need the season id as well
        except:
            the_player = SeasonTotal.objects.filter(player_id=p_id, div_name=match_info.data['divisionName'], class_played='all', season_id=match_info.data['seasonId'])
        if the_player.exists():
            the_player = the_player.first()
        else:
            try:
                the_player = SeasonTotal(
                    season_id = match_info.data['seasonId'],
                    div_name = match_info.data['divName'],
                    player_id = p_id,
                    games_played = 0,
                    time_played = 0,
                    kills = 0,
                    deaths = 0,
                    assists = 0,
                    dapm = 0,
                    heal = 0,
                    ubers = 0,
                    drops = 0,
                    headshots = 0,
                    headshots_hit = 0,
                    backstabs = 0,
                )
            except:
                the_player = SeasonTotal(
                    season_id = match_info.data['seasonId'],
                    div_name = match_info.data['divisionName'],
                    player_id = p_id,
                    games_played = 0,
                    time_played = 0,
                    kills = 0,
                    deaths = 0,
                    assists = 0,
                    dapm = 0,
                    heal = 0,
                    ubers = 0,
                    drops = 0,
                    headshots = 0,
                    headshots_hit = 0,
                    backstabs = 0,
                )
        try:
            player_stats = Stat.objects.filter(player_id=p_id, match_id=match, div_name=match_info.data['divName'], team_id=match_info.get_team(p_id), season_id=match_info.data['seasonId']) #filter by team so you dont get dupe stats when you revisit this player again bc two teams means 2 player entries
        except:
            player_stats = Stat.objects.filter(player_id=p_id, match_id=match, div_name=match_info.data['divisionName'], team_id=match_info.get_team(p_id), season_id=match_info.data['seasonId']) 
        
        for p_stat in player_stats:
            # gp.append(p_stat.match_id)
            for stat in stat_list:
                if stat == 'total_time':
                    time_played = sum([c['total_time'] for c in p_stat.data['class_stats']])
                    if stat in db_data.keys():
                        db_data[stat] = db_data[stat] + time_played
                    else:
                        db_data[stat] = time_played
                else:
                    if stat in db_data.keys():
                        db_data[stat] = db_data[stat] + p_stat.data[stat]
                    else:
                        db_data[stat] = p_stat.data[stat]
        
        #print('added new stats:', db_data)
        if len(player_stats) > 0:
            db_data['games_played'] = 1
            append_season_total(the_player, db_data, log_count=len(player_stats))
        for cp in class_list:
            db_data_st = {}
            gp_st = []
            for p_stat in player_stats:
                for cp_stat in p_stat.data['class_stats']:
                    if cp_stat['type'] == cp:
                        gp_st.append(p_stat.match_id)
                        for stat in stat_list_per_class:
                            if stat in db_data_st.keys():
                                db_data_st[stat] = db_data_st[stat] + cp_stat[stat]
                            else:
                                db_data_st[stat] = cp_stat[stat]
            db_data_st['games_played'] = len(gp_st)
            
            try:
                the_player = SeasonTotal.objects.filter(player_id=p_id, div_name=match_info.data['divName'], class_played=cp, season_id=match_info.data['seasonId']) #future reference we will need the season id as well
            except:
                the_player = SeasonTotal.objects.filter(player_id=p_id, div_name=match_info.data['divisionName'], class_played=cp, season_id=match_info.data['seasonId'])

            if the_player.exists():
                the_player = the_player.first()
            else:
                try:
                    the_player = SeasonTotal(
                        season_id = match_info.data['seasonId'],
                        div_name = match_info.data['divName'],
                        player_id = p_id,
                        games_played = 0,
                        time_played = 0,
                        kills = 0,
                        deaths = 0,
                        assists = 0,
                        dapm = 0,
                        heal = 0,
                        ubers = 0,
                        drops = 0,
                        headshots = 0,
                        headshots_hit = 0,
                        backstabs = 0,
                    )
                except:
                    the_player = SeasonTotal(
                        season_id = match_info.data['seasonId'],
                        div_name = match_info.data['divisionName'],
                        player_id = p_id,
                        games_played = 0,
                        time_played = 0,
                        kills = 0,
                        deaths = 0,
                        assists = 0,
                        dapm = 0,
                        heal = 0,
                        ubers = 0,
                        drops = 0,
                        headshots = 0,
                        headshots_hit = 0,
                        backstabs = 0,
                    )
            
            #print('added new stats:', db_data)
            if len(gp_st) > 0:
                append_season_total(the_player, db_data_st, cp)


def fetchNewStats(p_id):
    all_matches = getMatchesPlayer(p_id)
    try:
        scan_matches = ScannedMatches.objects.get(player_id=p_id)
    except:
        print('First time scan')
        matches_to_scan = all_matches
        scan_matches = ScannedMatches(player_id=p_id, scanned_matches=all_matches)
    else:
        print('This account has been scanned before')
        matches_to_scan = [item for item in all_matches if item not in scan_matches.scanned_matches]
        scan_matches.scanned_matches = all_matches
        
    if len(matches_to_scan) > 0:
        print('adding new player data')
        get_logs(p_id, matches_to_scan)
        get_stats(p_id, matches_to_scan)
        fill_season(p_id, matches_to_scan)
        scan_matches.save()
    else:
        print('No new data to scan')
    return 1



# p_id = '76561198041345724' # keplar
p_id = '76561198009091066' # achoo

# fetchNewStats(p_id)

# matches = getMatchesPlayer(p_id)

# print(getSeasonsPlayer(p_id))

# print(matches)

# get_logs(p_id, matches)
# get_stats(matches)
# fill_season(p_id, matches)