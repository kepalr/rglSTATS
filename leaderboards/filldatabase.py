import requests
import time
import logging
import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rglSTATS.settings')
django.setup()

from models import Match, Player
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
    response = session.get(url)
    logging.info("request was completed in %s seconds [%s]", response.elapsed.total_seconds(), response.url)
    if response.status_code != 200:
        logging.error("request failed, error code %s [%s]", response.status_code, response.url)
    if 500 <= response.status_code < 600:
        # server is overloaded lol
        logging.info("server overloaded after %s seconds [%s]", response.elapsed.total_seconds(), response.url)
        time.sleep(5)
    return response

team_list = get(RGL_API+GET_SEASON+str(133)).json()['participatingTeams']

start=0
total = len(team_list)

for team_id in team_list:
    start+=1
    print(f'Scanning Team {start}/{total} ({round(start/total*100)}% Complete)')
    time.sleep(2)
    team_data = get(RGL_API+GET_TEAM+str(team_id)).json()
    player_list = [player['steamId'] for player in team_data['players']]
    for player in player_list:
        p = Player(
            player_id=player,
            data=team_data
        )
        p.save()
        print(f'Successfully saved data for player: {player}')

