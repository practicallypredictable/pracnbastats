from collections import namedtuple
import numpy as np
import pandas as pd
from tqdm import tqdm
from . import params
from . import scrape
from . import utils
from . import format
from . import league


class BoxScores(league.BoxScores):
    def __init__(self, *,
            season=params.Season.default(),
            season_type=params.SeasonType.default(),
            date_from=params.DateFrom.default(),
            date_to=params.DateTo.default(),
            counter=params.NBA_COUNTER,
            sorter=params.Sorter.default(),
            sort_direction=params.SortDirection.default(),
            nba_stats_requests=None,
            filehandler=None):
        super().__init__(
            season=season,
            season_type=season_type,
            date_from=date_from,
            date_to=date_to,
            player_team_flag=params.PlayerTeamFlag.Player,
            counter=counter,
            sorter=sorter,
            sort_direction=sort_direction,
            nba_stats_requests=nba_stats_requests,
            filehandler=filehandler
        )
        self._additional_formatting()

    def _additional_formatting(self):
        start = [
            'season',
            'season_type',
            'player_id',
            'player_name',
            'team_id',
            'team_abbr',
            'game_id',
            'date',
            'opp_team_abbr',
            'home_road',
            'win_loss',
        ]
        end = [
            'video',
        ]
        self._df = format.order_columns(self._df, first_cols=start, last_cols=end)

    @property
    def matchups(self):
        df = super().matchups.copy()
        # These columns don't make sense for players
        # For simplicity, the league base class returns the data for teams,
        #    and we just drop the extra columns here
        df = df.drop(columns=['pts_h', 'pts_r', 'mov'])
        return df
