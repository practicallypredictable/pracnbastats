import collections
import pandas as pd
from . import params
from .table import Table
from . import utils
from . import tqdm
import logging

log = logging.getLogger(__name__)

# Singleton module variable
_Data = None


class CurrentTeam(collections.namedtuple('CurrentTeamsRowTuple', [
        'team_id',
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
    global _Data
    return _Data.copy()


def abbrs():
    global _Data
    return (team_abbr for team_abbr in _Data['abbr'])


def ids():
    global _Data
    return (team_id for team_id in _Data['team_id'])


def codes():
    global _Data
    return (team_code for team_code in _Data['code'])


def as_tuples(*, index=False):
    global _Data
    return utils.as_tuples(df=_Data, to_tuple=CurrentTeam, index=index)


def select(index=False, **kwargs):
    global _Data
    return utils.select_row_as_tuple(
        df=_Data, to_tuple=CurrentTeam, index=index, **kwargs)


def conference(conf, *, index=False):
    global _Data
    rows = _Data[_Data['conference'] == conf]
    return utils.as_tuples(df=rows, to_tuple=CurrentTeam, index=index)


def division(div, *, index=False):
    global _Data
    rows = _Data[_Data['division'] == div]
    return utils.as_tuples(df=rows, to_tuple=CurrentTeam, index=index)


def load(scraper):
    global _Data
    table = Table(store_name='currentteams')
    pipeline = [
        _scrape_teams,
        _format_teams,
        _join_team_info,
    ]
    _Data = scraper.load_pipeline(
        table=table,
        pipeline=pipeline,
    )


def _scrape_teams(session):
    records = session.records(
        api_endpoint='commonteamyears',
        api_params=params.Arguments(),
    )
    return pd.DataFrame(records)


def _format_teams(df, session):
    df = df.copy()
    df = df.dropna()
    df.columns = df.columns.str.lower()
    df = df.drop(columns=['league_id', 'max_year'])
    df = df.rename(columns={
        'min_year': 'since',
        'abbreviation': 'abbr',
    })
    df = df[['team_id', 'since', 'abbr']]
    df['team_id'] = df['team_id'].astype(int)
    df['since'] = df['since'].astype(int)
    return df.reset_index(drop=True)


def _get_summary_for_team(team_id, session):
    api_params = params.Arguments(
        Season=params.Season.default(),
        TeamID=team_id,
    )
    return session.records(
        api_endpoint='teaminfocommon',
        api_params=api_params,
    )


def _join_team_info(teams, session):
    teams = teams.copy()
    info = []
    for team_id in tqdm(teams['team_id']):
        team_info = _get_summary_for_team(team_id, session)
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
    df.columns = df.columns.str.lower()
    cols = (
        ['team_id', ] +
        [col.replace('team_', '') for col in df.columns if col != 'team_id']
    )
    df.columns = cols
    df = (
        teams
        .merge(df, on='team_id')
        .sort_values(by=['conference', 'division', 'code'])
    )
    cols = [col for col in df.columns if col != 'since']
    cols.append('since')
    df = df[cols]
    return df.reset_index(drop=True)
