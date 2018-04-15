"""DataFrame of all current and historical NBA players.

"""

from collections import namedtuple
import numpy as np
import pandas as pd
from . import params
from . import store
from . import scrape
from . import utils

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(*args, **kwargs):
        if args:
            return args[0]
        return kwargs.get('iterable', None)

# Singleton module variable
Data = None

class Player(namedtuple('AllPlayersRowTuple', [
        'id',
        'name',
        'first_name',
        'last_name',
        'code',
        'from_year',
        'to_year',
    ])):
    __slots__ = ()

    @property
    def seasons(self):
        start_year = max(params.MIN_YEAR, self.from_year)
        end_year = params.Season.current_start_year()
        return range(start_year, end_year+1)

def data():
    global Data
    return Data.copy()

def ids():
    """Iterator of all stats.nba.com player IDs."""
    global Data
    return (int(player_id) for player_id in Data['id'])

def as_tuples(index=False):
    """Iterator of namedtuples containing all active and historical NBA players."""
    global Data
    return utils.as_tuples(df=Data, to_tuple=Player, index=index)

def select(index=False, **kwargs):
    """Single namedtuple containing data for an NBA player."""
    global Data
    return utils.select_row_as_tuple(df=Data, to_tuple=Player, index=index, **kwargs)

def active(index=False):
    """NBA players active as of the most recent season."""
    global Data
    current_year = params.Season.current_start_year()
    rows = Data[Data['to_year'] >= current_year]
    return utils.as_tuples(df=rows, to_tuple=Player, index=index)

def historical(index=False):
    """NBA players no longer active as of the most recent season."""
    global Data
    current_year = params.Season.current_start_year()
    rows = Data[Data['to_year'] < current_year]
    return utils.as_tuples(df=rows, to_tuple=Player, index=index)

def load(filehandler=None):
    global Data
    if filehandler:
        Data = filehandler.load(
            scraper=_get_data,
            tablename='allplayers')
    else:
        Data = _get_data()

def _get_data():
    df = _scrape_all_players()
    formatted = _format_all_players(df)
    return _join_player_info(formatted)

def _scrape_all_players():
    endpoint = 'commonallplayers'
    args = params.Arguments(Season=params.Season.default(), IsOnlyCurrentSeason=0)
    return pd.DataFrame(scrape.NBAStats.get(endpoint, args.for_request))

def _format_all_players(df):
    df = df.copy()
    df.columns = df.columns.str.lower()
    keep_cols = [
        'person_id',
        'display_first_last',
        'display_last_comma_first',
        'playercode',
        'from_year',
        'to_year',
    ]
    df = df[keep_cols]
    df['last_name'], df['first_name'] = (
        df['display_last_comma_first'].str.split(',', 1).str
    )
    df['first_name'] = df['first_name'].str.lstrip(' ')
    df = df.drop(columns=['display_last_comma_first'])
    df = df.rename(columns={
        'person_id': 'id',
        'display_first_last': 'name',
        'playercode': 'code',
    })
    df['from_year'] = df['from_year'].astype(int)
    df['to_year'] = df['to_year'].astype(int)
    return df.reset_index(drop=True)

def _scrape_player_info(player_id):
    endpoint = 'commonplayerinfo'
    args = params.Arguments(PlayerID=player_id)
    return scrape.NBAStats.get(endpoint, args.for_request)

def _join_player_info(players):
    players = players.copy()
    info = []
    for player_id in tqdm(players['id']):
        player_info = _scrape_player_info(player_id)
        if isinstance(player_info, list):
            # For some reason, some players have more than one JSON row
            # In my experience, these are duplicates
            # This only keeps the first row
            player_info = player_info[0]
        info.append(player_info)
    df = pd.DataFrame(info)
    keep_cols = [
        'PERSON_ID',
        'POSITION',
        'BIRTHDATE',
        'HEIGHT',
        'SCHOOL',
        'COUNTRY',
        'DLEAGUE_FLAG',
        'DRAFT_YEAR',
        'DRAFT_ROUND',
        'DRAFT_NUMBER',
    ]
    df = df[keep_cols]
    df.columns = df.columns.str.lower()
    df = df.rename(columns={
        'person_id': 'id',
        'dleague_flag': 'dleague',
    })
    df['birthdate'] = pd.to_datetime(df['birthdate'])
    df['height'] = df['height'].apply(_convert_height)
    for col in ['position', 'school', 'country']:
        df[col] = df[col].apply(_clean_blanks)
    df = players.merge(df, on='id')
    return df.reset_index(drop=True)

def _clean_blanks(s):
    if s == None:
        return np.nan
    elif isinstance(s, str) and s.strip() == '':
        return np.nan
    else:
        return s

def _convert_height(s):
    if '-' in s:
        feet, inches = s.split('-')
        return float(feet) + float(inches)/12
    else:
        return np.nan
