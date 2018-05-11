import collections
import pandas as pd
from . import params
from . import exceptions
from .table import Table
from . import team
from . import utils
from . import tqdm
import logging

log = logging.getLogger(__name__)

# Singleton module variable
_Data = None


class HistoricalTeam(collections.namedtuple('HistoricalTeamsRowTuple', [
        'season',
        'team_id',
        'abbr',
        'city',
        'name',
        'wins',
        'losses',
        'conf_rank',
        'div_rank',
        'playoff_wins',
        'playoff_losses',
        'finals',
])):
    __slots__ = ()


def data():
    global _Data
    return _Data.copy()


def seasons():
    global _Data
    return (season for season in _Data['season'].unique())


def seasons_for_id(team_id):
    global _Data
    return (
        season for season in _Data.loc[_Data['team_id'] == team_id, 'season']
    )


def seasons_for_abbr(team_abbr):
    global _Data
    return (
        season for season in _Data.loc[_Data['abbr'] == team_abbr, 'season']
    )


def abbrs():
    global _Data
    return (team_abbr for team_abbr in _Data['abbr'].unique())


def ids():
    global _Data
    return (team_id for team_id in _Data['team_id'].unique())


def data_for_id(team_id):
    global _Data
    return (
        _Data[_Data['team_id'] == team_id]
    )


def id_for_abbr(team_abbr):
    global _Data
    team_ids = _Data.loc[
        _Data['abbr'] == team_abbr,
        'team_id',
    ].unique().tolist()
    assert len(team_ids) == 1
    return team_ids[0]


def abbrs_for_season(season):
    global _Data
    return _Data.loc[_Data['season'] == season, 'abbr'].tolist()


def ids_for_season(season):
    global _Data
    return _Data.loc[_Data['season'] == season, 'team_id'].tolist()


def abbr_for_id_season(team_id, season):
    global _Data
    abbrs = _Data.loc[
        (_Data['team_id'] == team_id) & (_Data['season'] == season),
        'abbr',
    ]
    abbrs = abbrs.unique().tolist()
    assert len(abbrs) == 1
    return abbrs[0]


def as_tuples(index=False):
    global _Data
    return utils.as_tuples(df=_Data, to_tuple=HistoricalTeam, index=index)


def select(*, season, index=False, **kwargs):
    global _Data
    df = _Data[_Data['season'] == season]
    return utils.select_row_as_tuple(
        df=df, to_tuple=HistoricalTeam, index=index, **kwargs)


def load(scraper, *, fix_hornets):
    global _Data
    table = Table(store_name='historicalteams')
    if (not scraper.force_reload
            and scraper.store and table.exists(scraper.store)):
        _Data = table.load(scraper.store)
    else:
        _Data = _scrape_teams(scraper)
        if scraper.store:
            table.save(
                store=scraper.store,
                data=_Data,
                archive=scraper.archive
            )
    if fix_hornets:
        pelicans_id = id_for_abbr('NOP')
        _Data.loc[_Data['abbr'] == 'CHH', 'team_id'] = pelicans_id


def _unique_teams_for_season(df):
    df = (
        df[['season', 'team_id', 'team_abbr']]
        .drop_duplicates()
        .rename(columns={
            'team_abbr': 'abbr',
        })
        .reset_index(drop=True)
    )
    df['team_id'] = df['team_id'].astype(int)
    df['season'] = df['season'].astype(int)
    return df


def _combine_team_data(record, df):
    abbrs = df.loc[
        (df['team_id'] == record.team_id) & (df['season'] == record.season),
        'abbr',
    ].unique().tolist()
    assert len(abbrs) == 1
    abbr = abbrs[0]
    return collections.OrderedDict({
        'season': record.season,
        'team_id': record.team_id,
        'abbr': abbr,
        'city': record.city,
        'name': record.name,
        'full_name': f'{record.city} {record.name}',
        'wins': record.wins,
        'losses': record.losses,
        'conf_rank': record.conf_rank,
        'conf_count': record.conf_count,
        'div_rank': record.div_rank,
        'div_count': record.div_count,
        'playoff_wins': record.playoff_wins,
        'playoff_losses': record.playoff_losses,
        'finals': record.finals,
    })


def _scrape_teams(scraper):
    team_abbrs = pd.concat({
        season.text: _unique_teams_for_season(
            team.BoxScores(scraper=scraper, season=season).data
        ) for season in tqdm(params.Season.stats_seasons())
    }).reset_index(drop=True)
    team_history = {
        team_id: _get_team_history(team_id, scraper.session)
        for team_id in tqdm(team_abbrs['team_id'].unique().tolist())
    }
    records = [
        _combine_team_data(record, team_abbrs)
        for team_id, team_data in team_history.items()
        for record in team_data.itertuples(index=False)
    ]
    return pd.DataFrame(records)


def _format_finals(s):
    if s == 'N/A':
        return 'N'
    elif 'CHAMPION' in s:
        return 'W'
    elif 'APPEARANCE' in s:
        return 'L'
    else:
        msg = f'unknown finals value {s}'
        raise exceptions.NBAStatsException(msg)


def _get_team_history(team_id, session):
    api_params = params.Arguments(
        SeasonType=params.SeasonType.default(),
        PerMOde=params.PerMode.Totals,
        TeamID=team_id,
    )
    df = pd.DataFrame(session.records(
        api_endpoint='teamyearbyyearstats',
        api_params=api_params,
    ))
    df.columns = df.columns.str.lower()
    cols = (
        ['team_id', ] +
        [col.replace('team_', '') for col in df.columns if col != 'team_id']
    )
    df.columns = cols
    df = df[[
        'year',
        'team_id',
        'city',
        'name',
        'wins',
        'losses',
        'conf_rank',
        'conf_count',
        'div_rank',
        'div_count',
        'po_wins',
        'po_losses',
        'nba_finals_appearance',
    ]]
    df = df.rename(columns={
        'po_wins': 'playoff_wins',
        'po_losses': 'playoff_losses',
    })
    df['season'] = df['year'].apply(params.Season.text2year)
    df = df[df['season'] >= params.MIN_YEAR]
    int_cols = [
        'team_id',
        'wins',
        'losses',
        'conf_rank',
        'conf_count',
        'div_rank',
        'div_count',
        'playoff_wins',
        'playoff_losses',
    ]
    df['finals'] = df['nba_finals_appearance'].apply(_format_finals)
    df = df.drop(columns=['nba_finals_appearance', 'year'])
    for col in int_cols:
        df[col] = df[col].astype(int)
    return df
