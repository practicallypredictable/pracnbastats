"""DataFrame of all current and historical NBA players.

"""

import collections
import numpy as np
import pandas as pd
from . import params
from .table import Table
from . import utils
from . import tqdm
import logging

log = logging.getLogger(__name__)

# Singleton module variable
_Data = None


class Player(collections.namedtuple('AllPlayersRowTuple', [
            'player_id',
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
    global _Data
    return _Data.copy()


def ids():
    """Iterator of all stats.nba.com player IDs."""
    global _Data
    return (int(player_id) for player_id in _Data['id'])


def as_tuples(index=False):
    """Iterator of namedtuples for all active and historical NBA players."""
    global _Data
    return utils.as_tuples(df=_Data, to_tuple=Player, index=index)


def select(index=False, **kwargs):
    """Single namedtuple containing data for an NBA player."""
    global _Data
    return utils.select_row_as_tuple(
                df=_Data, to_tuple=Player, index=index, **kwargs)


def active(index=False):
    """NBA players active as of the most recent season."""
    global _Data
    current_year = params.Season.current_start_year()
    rows = _Data[_Data['to_year'] >= current_year]
    return utils.as_tuples(df=rows, to_tuple=Player, index=index)


def historical(index=False):
    """NBA players no longer active as of the most recent season."""
    global _Data
    current_year = params.Season.current_start_year()
    rows = _Data[_Data['to_year'] < current_year]
    return utils.as_tuples(df=rows, to_tuple=Player, index=index)


def load(scraper):
    global _Data
    table = Table(store_name='allplayers')
    pipeline = [
        _scrape_all_players,
        _format_all_players,
        _join_player_info,
    ]
    _Data = scraper.load_pipeline(
        table=table,
        pipeline=pipeline
    )


def _scrape_all_players(session):
    api_params = params.Arguments(
        Season=params.Season.default(),
        IsOnlyCurrentSeason=0,
    )
    records = session.records(
        api_endpoint='commonallplayers',
        api_params=api_params,
    )
    return pd.DataFrame(records)


def _format_all_players(df, scraper):
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
        'person_id': 'player_id',
        'display_first_last': 'name',
        'playercode': 'code',
    })
    df['from_year'] = df['from_year'].astype(int)
    df['to_year'] = df['to_year'].astype(int)
    return df.reset_index(drop=True)


def _scrape_player_info(player_id, session):
    api_params = params.Arguments(PlayerID=player_id)
    return session.records(
        api_endpoint='commonplayerinfo',
        api_params=api_params,
    )


def _join_player_info(players, scraper):
    players = players.copy()
    info = []
    for player_id in tqdm(players['player_id']):
        player_info = _scrape_player_info(player_id, scraper)
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
        'person_id': 'player_id',
        'dleague_flag': 'dleague',
    })
    df['birthdate'] = pd.to_datetime(df['birthdate'])
    df['height'] = df['height'].apply(_convert_height)
    for col in ['position', 'school', 'country']:
        df[col] = df[col].apply(_clean_blanks)
    df = players.merge(df, on='player_id')
    return df.reset_index(drop=True)


def _clean_blanks(s):
    if not s:
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
