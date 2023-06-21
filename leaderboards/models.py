from django.db import models
from datetime import datetime
from django.contrib.postgres.fields import ArrayField
from steamid_converter import Converter

# foreign keys (matches -> player, logs -> match)
# https://docs.djangoproject.com/en/1.11/ref/contrib/postgres/fields/
# so ur just gonna use json fields for everything bc its way easier

class Match(models.Model):
    match_id = models.IntegerField()
    data = models.JSONField()

    # returns the players that are on the roster for each team
    def get_players(self, both=False): # returns a list of players from the winning team, used to find logs for this match
        if both == False:
            winning_team = self.data.get('winner')
            return Player.objects.filter(data__teamId=winning_team).values()
        else:
            both_teams = {}
            teams = self.data.get('teams')
            team1 = teams[0]['teamId']
            both_teams['team1'] = Player.objects.filter(data__teamId=team1).values()
            team2 = teams[1]['teamId']
            both_teams['team2'] = Player.objects.filter(data__teamId=team2).values()
            return both_teams
    
    def get_team(self, player_id, string=False): # given a player id, figure out which team from this match that player plays for
        both_teams = {}
        teams = self.data.get('teams')
        both_teams['team1'] = Player.objects.filter(data__teamId=teams[0]['teamId']).values()
        both_teams['team2'] = Player.objects.filter(data__teamId=teams[1]['teamId']).values()
        # team1 = [p['steamId'] for p in both_teams['team1']['data']['players']]
        team1 = [p['player_id'] for p in both_teams['team1']]
        team2 = [p['player_id'] for p in both_teams['team2']]
        if player_id in team1 and player_id not in team2:
            if string:
                return  teams[0]['teamName']
            return teams[0]['teamId']
        elif player_id in team2 and player_id not in team1:
            if string:
                return  teams[1]['teamName']
            return teams[1]['teamId']
        elif player_id in team1 and player_id in team2:
            t1 = Player.objects.get(player_id=player_id, data__teamId=teams[0]['teamId'])
            t1 = [p['joinedAt'] for p in t1.data['players'] if p['steamId'] == player_id][0]
            # t1 = [p['joinedAt'] for p in both_teams['team1']['data']['players'] if p['steamId'] == player_id][0]
            t1 = datetime.fromisoformat(t1[:-1]).timestamp()

            t2 = Player.objects.get(player_id=player_id, data__teamId=teams[1]['teamId'])
            t2 = [p['joinedAt'] for p in t2.data['players'] if p['steamId'] == player_id][0]
            # t2 = [p['joinedAt'] for p in both_teams['team2']['data']['players'] if p['steamId'] == player_id][0]
            t2 = datetime.fromisoformat(t2[:-1]).timestamp()
            if t1 > t2:
                if string:
                    return  teams[0]['teamName']
                return teams[0]['teamId']
            else:
                if string:
                    return  teams[1]['teamName']
                return teams[1]['teamId']
        else:
            try:
                return f'Ringer - {self.data["divisionName"]}'
            except:
                return f'Ringer - {self.data["divName"]}'
    
    # returns what season this match was for
    def get_season(self):
        return self.data['seasonId']
            


class Player(models.Model):
    player_id = models.CharField(max_length=20)
    data = models.JSONField()
    
    def get_name(self):
        return [p['name'] for p in self.data['players'] if p['steamId'] == self.player_id][0]

    def get_team(self):
        return self.data['name']
    
    def get_team_abv(self):
        return self.data['tag']

class Log(models.Model):
    log_id = models.IntegerField()
    match_id = models.IntegerField()
    data = models.JSONField()
    no_log = models.IntegerField(default=0) # 0 - log found, 1 - no log found, 2 - log manually added

    # returns the players from the log
    def get_players(self):
        return [Converter.to_steamID64(p) for p in self.data['players'].keys()]


class Stat(models.Model):
    season_id = models.IntegerField()
    div_name = models.CharField(max_length=64)
    match_id = models.IntegerField()
    log_id = models.IntegerField()
    team_id = models.IntegerField()
    map = models.CharField(max_length=64)
    player_id = models.CharField(max_length=50)
    data = models.JSONField() # json from log table where player key is steamid64 converted playerid

    def player_stats(self):
        stats = self.data
        stat_keys = ['total_time', 'kills', 'assists', 'deaths', 'damage', 'dapm', 'heal', 'ubers', 'drops', 'headshots', 'headshots_hit', 'backstabs']
        out = {key: stats.get(key) for key in stat_keys if key in stats}
        time_played = sum([s['total_time'] for s in stats.get('class_stats')])
        out['total_time'] = time_played
        return out
    
    def class_stats(self, class_name=None): # return class stats for specified class_name, if class_name is none return array of all class specific stats
        stats = self.data
        if class_name is not None:
            classes_played = [s['type'] for s in stats.get('class_stats')]
            if class_name in classes_played:
                return stats.get('class_stats')[classes_played.index(class_name)]
            else:
                return {}
        else:
            return stats.get('class_stats')
    
    def get_team(self):
        return Player.objects.filter(data__teamId=self.team_id).first().get_team()
    def get_team_abv(self):
        return Player.objects.filter(player_id=self.player_id).first().get_team_abv()
    # def season_total(self):
    #     stats = Stat.objects.filter(player_id=self.player_id, div_name=self.div_name)
    #     stat_keys = ['kills', 'assists', 'deaths', 'dapm', 'heal', 'ubers', 'drops', 'headshots', 'headshots_hit', 'backstabs']
    #     # each_stat = [stat[key] for stat in stats]
    #     return {key: sum(d.data[key] for d in stats) for key in stat_keys}



class SeasonTotal(models.Model):
    season_id = models.IntegerField()
    div_name = models.CharField(max_length=64)
    player_id = models.CharField(max_length=50)
    class_played = models.CharField(max_length=32, default='all')
    games_played = models.IntegerField()
    time_played = models.IntegerField()
    kills = models.IntegerField()
    deaths = models.IntegerField()
    assists = models.IntegerField()
    dapm = models.IntegerField()
    heal = models.IntegerField()
    ubers = models.IntegerField()
    drops = models.IntegerField()
    headshots = models.IntegerField()
    headshots_hit = models.IntegerField()
    backstabs = models.IntegerField()

    # objects = models.Manager()

    def get_main(self):
        return SeasonTotal.objects.filter(player_id=self.player_id).values('class_played').order_by('-time_played')[1]
    def get_name(self):
        return Player.objects.filter(player_id=self.player_id).first().get_name()
    
    ## these below will show a players current team for all past seasons, may have to add the matching data__teamId so it gets the right one, rather than the first one that appears
    def get_team(self):
        return Player.objects.filter(player_id=self.player_id).first().get_team()
    def get_team_abv(self):
        return Player.objects.filter(player_id=self.player_id).first().get_team_abv()
    def get_stat_30m(self, stat):
        return round(stat / self.time_played * 1800, 2)

class ScannedMatches(models.Model):
    player_id = models.CharField(max_length=50)
    scanned_matches = ArrayField(models.IntegerField())