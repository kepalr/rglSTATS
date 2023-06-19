import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from steamid_converter import Converter
import time
from datetime import datetime
import logging
import django
import os
import sys
import asyncio
from filldatabase import get_teams, get_matches

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
GET_MATCH_PAGES = 'matches/paged'
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

def post(url, params):
    timeout = 15  # maximum time to wait for a response in seconds
    retries = 10  # number of times to retry the request
    for i in range(retries):
        try:
            # response =  requests.post(f"curl -X 'POST' \
            #         '{url}' \
            #         -H 'accept: */*' \
            #         -H 'Content-Type: application/json' \
            #         -d '{{}}'")
            
            headers = {
                'accept': '*/*',
                # Already added when you pass json=
                # 'Content-Type': 'application/json',
            }

            json_data = {}

            response = requests.post(url, params=params, headers=headers, json=json_data)
            return response
        except:
            print('cURL no likey')
            return []

def GET_MATCH_PAGE_PARAMS(first_match, num_matches):
    return {
        'take': num_matches,
        'skip': first_match
    }


# async def getAllMatchDetails(first_match):
#     print(f'first match: {first_match}')
#     offset = int(first_match * .90)
#     print(f'offset value: {offset}')
#     offset_off_by = await post(GET_MATCH_PAGES(offset, 1))
#     print(offset_off_by)

def getAllMatchDetails(first_match, all_season_matches):
    offset = int(first_match * .85)
    time.sleep(1)
    try:
        blanket_matches = post(RGL_API + GET_MATCH_PAGES, GET_MATCH_PAGE_PARAMS(offset, 1000)).json()
        time.sleep(4)
        blanket_matches += post(RGL_API + GET_MATCH_PAGES, GET_MATCH_PAGE_PARAMS(offset + 1000 , 500)).json()

    except:
        print('eat shit once')
        time.sleep(15)
        blanket_matches = post(RGL_API + GET_MATCH_PAGES, GET_MATCH_PAGE_PARAMS(offset, 1000)).json()
        time.sleep(4)
        blanket_matches += post(RGL_API + GET_MATCH_PAGES, GET_MATCH_PAGE_PARAMS(offset + 1000 , 500)).json()
    
    trimmed_match_list = []
    if len(blanket_matches) < len(all_season_matches):
        print(blanket_matches)
    else:
        print(len(blanket_matches))
    for match in blanket_matches:
        if (match['matchId'] in all_season_matches) and ("Week" in match['matchName']):
            trimmed_match_list.append(match['matchId'])
    return trimmed_match_list



seasonNumbers = [53, 67, 72, 95, 105, 110, 120, 123, 127, 129, 133]

for szn in seasonNumbers:

    match_list = get(RGL_API+GET_SEASON+str(szn)).json()['matchesPlayedDuringSeason']
    first_id = match_list[0]
    t_m = getAllMatchDetails(first_id, match_list)
    get_matches(szn, t_m)
    get_teams(szn)




