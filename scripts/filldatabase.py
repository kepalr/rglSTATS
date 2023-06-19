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

from leaderboards.models import Match, Player, Log, Stat, SeasonTotal
LOGS_API = 'http://logs.tf/api/v1/log'
RGL_API = 'https://api.rgl.gg/v0/'
GET_MATCH = 'matches/'
GET_TEAM = 'teams/'
GET_SEASON = 'seasons/'
GET_PLAYER = 'profile/'
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

def datedMatch(matchDate, logDate):
    h = 3600
    return (matchDate- 5*h - (2*h)) <= (logDate - (6*h)) <= (matchDate- 5*h + (2*h))

# give match date - returns in epoch seconds
def matchDateEpoch(matchDate):
    date_obj = datetime.fromisoformat(matchDate[:-1])
    return date_obj.timestamp()
    # return matchDate.timestamp()

def playerThreshold(team1, team2, logPlayers):

    playerKeys = logPlayers['players'].keys()
    own_count = 0
    their_count = 0

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
    # print('attempting to get official logs')
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
                    time.sleep(1)
                if response.status_code == 200:
                    if playerThreshold(team1, team2, response.json()):
                        # print('player threshold passed')
                        Score[0] += response.json()['teams']['Red']['score']
                        Score[1] += response.json()['teams']['Blue']['score']
                        Official_Logs_responses.append(response.json())
                        Official_Logs_ids.append(response.url.rsplit('/', 1)[-1])
                        if confirmScores(winner, loser, Score):
                            # print('scores confirmed working')
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
                        # else:
                            # print('player count good, number of logs returned good, scores were bad?')
                            # print(f'Winner: {winner}\nLoser: {loser}\nScore: {Score}')
                    # else:
                    #     print('player threshold failed')
        print("fail")
        return False


def get_teams(szn):
    team_list = get(RGL_API+GET_SEASON+str(szn)).json()['participatingTeams']
    start=0
    total = len(team_list)

    i_fucked_up = 1
    for team_id in team_list:
        # if i_fucked_up < 68:
        #     print('u suck')
        #     i_fucked_up += 1
        #     start +=1
        # else:
        start+=1
        print(f'Scanning Team {start}/{total} ({round(start/total*100)}% Complete)')
        time.sleep(1)
        team_data = get(RGL_API+GET_TEAM+str(team_id)).json()
        try: 
            player_list = [player['steamId'] for player in team_data['players']]
        except:
            print('team aquisition failed, trying again')
            time.sleep(2)
            team_data = get(RGL_API+GET_TEAM+str(team_id)).json()
            time.sleep(1)
            player_list = [player['steamId'] for player in team_data['players']]
        finally:
            for player in set(player_list):
                p = Player(
                    player_id=player,
                    data=team_data
                )
                p.save()
                print(f'Successfully saved data for player: {player}')

def get_matches(szn, match_list=[]):
    if len(match_list) == 0:
        match_list = get(RGL_API+GET_SEASON+str(szn)).json()['matchesPlayedDuringSeason']
    
    start=0
    total = len(match_list)

    for match_id in match_list:
        start+=1
        print(f'Scanning Match {start}/{total} ({round(start/total*100)}% Complete)')
        #time.sleep(1)
        match_data = get(RGL_API+GET_MATCH+str(match_id))
        quit = 0
        while match_data.status_code != 200:
            quit += 1
            time.sleep(2)
            match_data = get(RGL_API+GET_MATCH+str(match_id))
            if quit > 25:
                break # we wont find it rip
        if match_data.status_code == 200:
            match = Match(
                match_id=match_data.json()['matchId'],
                data=match_data.json()
            )
            match.save()
            print(f'Successfully saved data for match: {match_id}')
        else:
            print(f'Match: {match_id} was never found')

def get_logs(szn):
    try:
        match_list = get(RGL_API+GET_SEASON+str(szn)).json()['matchesPlayedDuringSeason']
    except:
        print('give it a sec')
        time.sleep(2)
        match_list = get(RGL_API+GET_SEASON+str(szn)).json()['matchesPlayedDuringSeason']
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
                    player_list = match_info.get_players()
                    quit=0
                    cache = []
                    for player in player_list:
                        if len(player_list) - quit < 4: # with not enough players remaining to even meet the player threshold, stop looking for the log
                            write_log(0, match, {}, bad=1)
                            break
                        else:
                            quit+=1
                            print("for player:", player["player_id"])
                            logs = f'{LOGS_API}?map={match_info.data["maps"][0]["mapName"]}&player={player["player_id"]}'
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
                                    if THE_LOGS_THAT_DAY not in cache:
                                        cache.append(THE_LOGS_THAT_DAY) # cache this log check so we dont have to check these same logs mutliple times
                                        if getOfficialLogs([f'{LOGS_API}/{log["id"]}' for log in THE_LOGS_THAT_DAY], match_info) == True:
                                            break


def get_stats(szn):
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
    log_list = Log.objects.filter(no_log=0)
    start=0
    total = len(log_list)
    fail = False
    for log in log_list:
        start+=1
        print(f'{start}/{total} Logs checked for stat entry ({round(start/total*100)}% Complete)')
        if len(log.data.keys()) > 0:
            try:
                match_info = Match.objects.get(match_id=log.match_id, data__seasonId=szn)
            except:
                print('non relevant match log')
            else:
                player_list = log.data['players'].keys()
                teams = [team['teamId'] for team in match_info.data['teams']]
                for player in player_list:
                    try:
                        player_team_id = match_info.get_team(Converter.to_steamID64(player))
                    except:
                        fail=True
                        print("player_id: ", Converter.to_steamID64(player))
                        print("match_id: ", match_info.data['matchId'])
                        print("log_id: ", log.log_id)

                    if player_team_id in teams:
                        try:
                            stat = Stat(
                                season_id=match_info.data['seasonId'],
                                div_name=match_info.data['divName'],
                                match_id=match_info.data['matchId'],
                                log_id=log.log_id,
                                team_id=player_team_id,
                                map=log.data['info']['map'],
                                player_id=Converter.to_steamID64(player),
                                data=log.data['players'][player]
                            )
                        except:
                            stat = Stat(
                                season_id=match_info.data['seasonId'],
                                div_name=match_info.data['divisionName'],
                                match_id=match_info.data['matchId'],
                                log_id=log.log_id,
                                team_id=player_team_id,
                                map=log.data['info']['map'],
                                player_id=Converter.to_steamID64(player),
                                data=log.data['players'][player]
                            )
                        finally:
                            stat.save()

def append_season_total(player, data, class_played=None):
    if data['games_played'] > 0:
        if class_played is None:
            player.games_played = player.games_played + data['games_played']
            player.time_played = player.time_played + data['total_time']
            player.kills = player.kills + data['kills']
            player.assists = player.assists + data['assists']
            player.deaths = player.deaths + data['deaths']
            player.dapm = ((player.dapm * (player.games_played - data['games_played'])) + data['dapm']) / player.games_played #special (current dapm * current gp) + added dapm / new gp
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
            player.dapm = ((player.dapm * (player.time_played - data['total_time'])/ 60) + data['dmg']) / player.time_played *60

    player.save()

# on first entry, create blank profile for each class and class total, then if they never play as say spy, they wil just show 0s, else, show the individual class stats
# make method for getting player primary class by returning highest total time class for a season


def fill_season(szn):
    players = Player.objects.filter(data__seasonId=szn)
    stat_list = ['total_time', 'kills', 'assists', 'deaths', 'dapm', 'heal', 'ubers', 'drops', 'headshots', 'headshots_hit', 'backstabs']
    total = len(players)
    start = 0
    for player in players:
        start+=1
        print(f'{start}/{total} Logs checked for stat entry ({round(start/total*100)}% Complete)')
        db_data = {}
        gp = []
        the_player = SeasonTotal.objects.filter(player_id=player.player_id, div_name=player.data['divisionName'], class_played='all', season_id=szn) #future reference we will need the season id as well
        if the_player.exists():
            the_player = the_player.first()
        else:
            the_player = SeasonTotal(
                season_id = szn,
                div_name = player.data['divisionName'],
                player_id = player.player_id,
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
        player_stats = Stat.objects.filter(player_id=player.player_id, div_name=player.data['divisionName'], team_id=player.data['teamId']) #filter by team so you dont get dupe stats when you revisit this player again bc two teams means 2 player entries
        for p_stat in player_stats:
            gp.append(p_stat.match_id)
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
        db_data['games_played'] = len(gp)
        #print('added new stats:', db_data)
        append_season_total(the_player, db_data)

def fill_season_classes(szn):
    players = Player.objects.filter(data__seasonId=szn)
    stat_list = ['type', 'kills', 'assists', 'deaths', 'dmg', 'total_time']
    class_list = ['scout', 'soldier', 'pyro', 'demoman', 'heavyweapons', 'engineer', 'medic', 'sniper', 'spy']
    total = len(players)
    start = 0
    for player in players:
        start+=1
        print(f'{start}/{total} Logs checked for stat entry ({round(start/total*100)}% Complete)')


        player_stats = Stat.objects.filter(player_id=player.player_id, div_name=player.data['divisionName'], team_id=player.data['teamId']) #filter by team so you dont get dupe stats when you revisit this player again bc two teams means 2 player entries
        
        for cp in class_list:
            db_data = {}
            gp = []
            for p_stat in player_stats:
                for cp_stat in p_stat.data['class_stats']:
                    if cp_stat['type'] == cp:
                        gp.append(p_stat.match_id)
                        for stat in stat_list:
                            if stat in db_data.keys():
                                db_data[stat] = db_data[stat] + cp_stat[stat]
                            else:
                                db_data[stat] = cp_stat[stat]
            db_data['games_played'] = len(gp)
            
            the_player = SeasonTotal.objects.filter(player_id=player.player_id, div_name=player.data['divisionName'], class_played=cp) #future reference we will need the season id as well
            if the_player.exists():
                the_player = the_player.first()
            else:
                the_player = SeasonTotal(
                    season_id = szn,
                    div_name = player.data['divisionName'],
                    player_id = player.player_id,
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
            if len(gp) > 0:
                append_season_total(the_player, db_data, cp)


def fill_everything(szn):
    # get_teams(szn)
    # get_matches(szn)
    get_logs(szn)
    # the above functions are used to make aquiring the below functions fast
    # the above collect and store data about matches, and dont need to be truncated
    # players might need to be truncated, it is possible that players who leave and rejoin a team are counted twice, see h4ppy last season with 10gp
    get_stats(szn)
    fill_season(szn) # things to think about, make sure to only do unique entries only to prevent dupes like with the invite team guys
    fill_season_classes(szn)
    # fill_season and fill_season_classes should be combined into one at some point


#get_team()
#get_logs()
#get_matches()
# get_stats()
# fill_season() # things to think about, make sure to only do unique entries only to prevent dupes like with the invite team guys

# fill_season_classes()
# get_logs(129)
# fill_everything(133)

seasonNumbers = [53, 67, 72, 95, 105, 110, 120, 123, 127, 129, 133]

# fill_everything(133)

#fill_everything(int(sys.argv[1]))
get_teams(123)

# get_logs(53)
# for s in seasonNumbers:
#      fill_everything(s)

# season
# 1 - 53
# 2 - 67
# 3 - 72
# 4 - 95
# 5 - 105
# 6 - 110
# 7 - 120
# 8 - 123
# 9 - 127
# 10 - 129
# 11 - 133
# 12 - 

