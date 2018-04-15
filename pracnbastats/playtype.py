from enum import Enum
from collections import OrderedDict
import numpy as np
import pandas as pd
from . import params
from .scrape import NBAStatsRequests, NBAStats
from . import utils

MIN_PLAYTYPE_YEAR = 2015 # Earliest season for which site has playtype data
NBA_PLAYTYPE_BASE_URL = 'https://stats-prod.nba.com/wp-json/statscms/v1/synergy/'
DEFAULT_NBA_PLAYTYPE_REQUESTS = NBAStatsRequests(base_url=NBA_PLAYTYPE_BASE_URL)

class Stats(Enum):
    Offensive = 'offensive'
    Defensive = 'defensive'
    @classmethod
    def default(cls):
        return cls.Offensive


class Categories(Enum):
    Transition = 'Transition'
    Isolation = 'Isolation'
    PickRollBallHandler = 'PRBallHandler'
    PickRollRollMan = 'PRRollman'
    PostUp = 'Postup'
    SpotUp = 'Spotup'
    Handoff = 'Handoff'
    Cut = 'Cut'
    OffScreen = 'OffScreen'
    Putbanks = 'OffRebound'
    Misc = 'Misc'
    @classmethod
    def default(cls):
        return cls.Transition


class NBAPlayTypeStats(NBAStats):
    def __init__(self,
            api_endpoint,
            season=params.Season.default(),
            season_type=params.SeasonType.default(),
            stats=Stats.default(),
            category=Categories.default(),
            nba_stats_requests=None,
            filehandler=None,
            tablename=None):
        if api_endpoint not in ['team', 'player']:
            raise ValueError('unsupported play type', api_endpoint)
        if not nba_stats_requests:
            nba_stats_requests = DEFAULT_NBA_PLAYTYPE_REQUESTS
        if season_type == params.SeasonType.Regular:
            season_type = 'Reg'
        elif season_type == params.SeasonType.Playoffs:
            season_type = 'Post'
        else:
            raise ValueError('unsupported season type', season_type)
        args = params.Arguments(
            season=season.start_year,
            seasonType=season_type,
            names=stats,
            category=category,
            limit=500,
        )
        super().__init__(
            api_endpoint=api_endpoint,
            params=args,
            nba_stats_requests=nba_stats_requests,
            filehandler=filehandler,
            tablename=tablename,
        )

    def _scrape_data(self):
        params_for_request = self._params.for_request
        self._response = NBAStats.get_response(
                                self._api_endpoint,
                                params_for_request,
                                self._requests)
        rows = self._response.json()['results']
        df = pd.DataFrame([OrderedDict(row) for row in rows])
        return df


class PlayerPlayTypes(NBAPlayTypeStats):
    def __init__(self, *,
            season=params.Season.default(),
            season_type=params.SeasonType.default(),
            stats=Stats.default(),
            category=Categories.default(),
            nba_stats_requests=None,
            filehandler=None):
        super().__init__(
            api_endpoint="player",
            season=season,
            season_type=season_type,
            stats=stats,
            category=category,
            nba_stats_requests=nba_stats_requests,
            filehandler=filehandler)


class TeamPlayTypes(NBAPlayTypeStats):
    def __init__(self, *,
            season=params.Season.default(),
            season_type=params.SeasonType.default(),
            stats=Stats.default(),
            category=Categories.default(),
            nba_stats_requests=None,
            filehandler=None):
        super().__init__(
            api_endpoint="team",
            season=season,
            season_type=season_type,
            stats=stats,
            category=category,
            nba_stats_requests=nba_stats_requests,
            filehandler=filehandler)
