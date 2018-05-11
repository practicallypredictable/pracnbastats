from . import params
from . import utils
from . import league


class BoxScores(league.BoxScores):
    def __init__(
            self, *, scraper,
            season=params.Season.default(),
            season_type=params.SeasonType.default(),
            date_from=params.DateFrom.default(),
            date_to=params.DateTo.default(),
            counter=params.NBACounter.default(),
            sorter=params.Sorter.default(),
            sort_direction=params.SortDirection.default()):
        super().__init__(
            scraper=scraper,
            player_team_flag=params.PlayerTeamFlag.Player,
            season=season,
            season_type=season_type,
            date_from=date_from,
            date_to=date_to,
            counter=counter,
            sorter=sorter,
            sort_direction=sort_direction,
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
        self._data = utils.order_columns(
            self._data,
            first_cols=start,
            last_cols=end,
        )

    @property
    def matchups(self):
        df = super().matchups.copy()
        # These columns don't make sense for players
        # For simplicity, the league base class returns the data for teams,
        #    and we just drop the extra columns here
        df = df.drop(columns=['pts_h', 'pts_r', 'mov'])
        return df
