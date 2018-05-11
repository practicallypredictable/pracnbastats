import numpy as np
from . import params
from . import scrape
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
            season=season,
            season_type=season_type,
            date_from=date_from,
            date_to=date_to,
            player_team_flag=params.PlayerTeamFlag.Team,
            counter=counter,
            sorter=sorter,
            sort_direction=sort_direction,
        )
        self._additional_formatting()

    def _additional_formatting(self):
        self._data = self._data.rename(columns={
            'plus_minus': 'mov',
        })
        start = [
            'season',
            'season_type',
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
            last_cols=end
        )

    @property
    def team_records(self):
        df = super().matchups
        info = (
            df[['season', 'season_type', 'team_id_h', 'team_abbr_h']]
            .drop_duplicates(subset=['team_abbr_h'])
        )
        info = info.rename(columns={
            'team_id_h': 'team_id',
            'team_abbr_h': 'team_abbr'
        }).set_index(['team_abbr'])
        home = (
            df.groupby(['team_abbr_h'])['win_loss_h']
            .value_counts()
            .unstack()
        )
        road = (
            df.groupby(['team_abbr_r'])['win_loss_r']
            .value_counts()
            .unstack()
        )
        df = home.join(road, lsuffix='_h', rsuffix='_r').reset_index()
        df = df.rename(columns={
            'team_abbr_h': 'team_abbr',
            'L_h': 'home_losses',
            'W_h': 'home_wins',
            'L_r': 'road_losses',
            'W_r': 'road_wins',
        })
        df['wins'] = df['home_wins'] + df['road_wins']
        df['losses'] = df['home_losses'] + df['road_losses']
        df['home'] = df['home_wins'] + df['home_losses']
        df['road'] = df['road_wins'] + df['road_losses']
        df['games'] = df['wins'] + df['losses']
        cols = [
            'team_abbr',
            'games',
            'wins',
            'losses',
            'home',
            'road',
            'home_wins',
            'home_losses',
            'road_wins',
            'road_losses'
        ]
        df = df[cols].set_index(['team_abbr'])
        df['win_pct'] = np.where(
            df['games'] > 0,
            df['wins'] / df['games'],
            np.nan
        )
        df['home_win_pct'] = np.where(
            df['home'] > 0,
            df['home_wins'] / df['home'],
            np.nan
        )
        df['road_win_pct'] = np.where(
            df['road'] > 0,
            df['road_wins'] / df['road'],
            np.nan
        )
        df = info.join(df)
        df = df.reset_index()
        return df


class AdvancedBoxScores(scrape.NBAStats):
    # TO DO: Fix opposing team ID
    def __init__(
            self, *,
            scraper,
            team=None,
            opposing_team=None,
            measure_type=params.MeasureType.default(),
            season=params.Season.default(),
            season_type=params.SeasonType.default(),
            season_segment=params.SeasonSegment.default(),
            month=params.SeasonMonth.default(),
            game_outcome=params.GameOutcome.default(),
            game_location=params.GameLocation.default(),
            game_segment=params.GameSegment.default(),
            period=params.Period.default(),
            vs_div=params.Division.default(),
            vs_conf=params.Conference.default(),
            po_round=params.PlayoffRound.default()):
        args = params.Arguments(
            team=team,
            opposing_team=opposing_team,
            MeasureType=measure_type,
            Season=season,
            SeasonType=season_type,
            SeasonSegment=season_segment,
            Month=month,
            Outcome=game_outcome,
            Location=game_location,
            GameSegment=game_segment,
            Period=period,
            VsDivision=vs_div,
            VsConference=vs_conf,
            PORound=po_round,
        )
        super().__init__(
            scraper=scraper,
            api_endpoint="teamgamelogs",
            params=args)
