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

class CurrentTeam(namedtuple('CurrentTeamsRowTuple', [
        'id',
        'abbr',
        'code',
        'conference',
        'division',
        'city',
        'name',
        'since',
    ])):
    __slots__ = ()

def data():
    global Data
    return Data.copy()

def abbrs():
    global Data
    return (team_abbr for team_abbr in Data['abbr'])

def ids():
    global Data
    return (team_id for team_id in Data['id'])

def codes():
    global Data
    return (team_code for team_code in Data['code'])

def as_tuples(index=False):
    global Data
    return utils.as_tuples(df=Data, to_tuple=CurrentTeam, index=index)

def select(index=False, **kwargs):
    global Data
    return utils.select_row_as_tuple(df=Data, to_tuple=CurrentTeam, index=index, **kwargs)

def conference(conf, index=False):
    global Data
    rows = Data[Data['conference'] == conf]
    return utils.as_tuples(df=rows, to_tuple=CurrentTeam, index=index)

def division(div, index=False):
    global Data
    rows = Data[Data['division'] == div]
    return utils.as_tuples(df=rows, to_tuple=CurrentTeam, index=index)

def load(filehandler=None):
    global Data
    if filehandler:
        Data = filehandler.load(
            scraper=_get_data,
            tablename='currentteams')
    else:
        Data = _get_data()

def _get_data():
    df = _scrape_teams()
    formatted = _format_teams(df)
    return _join_team_info(formatted)

def _scrape_teams():
    endpoint = 'commonteamyears'
    args = params.Arguments()
    return pd.DataFrame(scrape.NBAStats.get(endpoint, args.for_request))

def _format_teams(df):
    df = df.copy()
    df = df.dropna()
    df.columns = df.columns.str.lower()
    df = df.drop(columns=['league_id', 'max_year',])
    df = df.rename(columns={
        'min_year': 'since',
        'abbreviation': 'team_abbr',
    })
    df = df[['team_id', 'since', 'team_abbr',]]
    df['team_id'] = df['team_id'].astype(int)
    df['since'] = df['since'].astype(int)
    df.columns = df.columns.str.replace('team_', '')
    return df.reset_index(drop=True)

def _get_summary_for_team(team_id):
    endpoint = 'teaminfocommon'
    args = params.Arguments(Season=params.Season.default(), TeamID=team_id)
    return scrape.NBAStats.get(endpoint, args.for_request)

def _join_team_info(teams):
    teams = teams.copy()
    info = []
    for team_id in tqdm(teams['id']):
        team_info = _get_summary_for_team(team_id)
        info.append(team_info)
    df = pd.DataFrame(info)
    keep_cols = [
        'TEAM_ID',
        'TEAM_CODE',
        'TEAM_CONFERENCE',
        'TEAM_DIVISION',
        'TEAM_CITY',
        'TEAM_NAME',
    ]
    df = df[keep_cols]
    df.columns = df.columns.str.lower().str.replace('team_', '')
    df = (teams
            .merge(df, on='id')
            .sort_values(by=['conference', 'division', 'code'])
    )
    cols = [col for col in df.columns if col != 'since']
    cols.append('since')
    df = df[cols]
    return df.reset_index(drop=True)
