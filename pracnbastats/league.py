import numpy as np
import pandas as pd
from . import params
from . import scrape
from .table import Table
import logging

log = logging.getLogger(__name__)


class BoxScores(scrape.NBAStats):
    """Player or team box scores for season across league."""
    def __init__(
            self, *, scraper,
            player_team_flag=params.PlayerTeamFlag.default(),
            season=params.Season.default(),
            season_type=params.SeasonType.default(),
            date_from=params.DateFrom.default(),
            date_to=params.DateTo.default(),
            sorter=params.Sorter.default(),
            sort_direction=params.SortDirection.default(),
            counter=params.NBACounter.default()):
        api_params = params.Arguments(
            PlayerOrTeam=player_team_flag,
            Season=season,
            SeasonType=season_type,
            DateFrom=date_from,
            DateTo=date_to,
            Sorter=sorter,
            Direction=sort_direction,
            Counter=counter,
        )
        table = Table(
            api_endpoint='leaguegamelog',
            api_params=api_params,
        )
        super().__init__(
            scraper=scraper,
            table=table,
        )
        self._data = self._format()

    def select(self, home_road=None, win_loss=None):
        rows = self.data.copy()
        if home_road:
            if isinstance(home_road, params.GameLocation):
                home_road = 'H' if home_road.value == 'Home' else 'R'
            rows = rows[rows['home_road'] == home_road]
        if win_loss:
            if isinstance(win_loss, params.GameOutcome):
                win_loss = 'W' if win_loss.value == 'Win' else 'L'
            rows = rows[rows['win_loss'] == win_loss]
        return rows

    @property
    def home_games(self):
        return self.select(home_road='H')

    @property
    def road_games(self):
        return self.select(home_road='R')

    @property
    def wins(self):
        return self.select(win_loss='W')

    @property
    def losses(self):
        return self.select(win_loss='L')

    @property
    def game_ids(self):
        return self.data['game_id'].unique()

    @property
    def dates(self):
        return self.data['date'].unique()

    @property
    def matchups(self):
        home_columns = [
            'season',
            'season_type',
            'game_id',
            'date',
            'video',
            'team_id',
            'team_abbr',
            'pts',
            'win_loss',
        ]
        home = (
            self.data.loc[self.data['home_road'] == 'H', home_columns]
            .drop_duplicates(subset=['game_id'])
            .set_index(['game_id'])
        )
        road_columns = [
            'game_id',
            'team_id',
            'team_abbr',
            'pts',
            'win_loss',
        ]
        road = (
            self.data.loc[self.data['home_road'] == 'R', road_columns]
            .drop_duplicates(subset=['game_id'])
            .set_index(['game_id'])
        )
        df = home.join(road, lsuffix='_h', rsuffix='_r')
        df = df.reset_index()
        df['hr_winner'] = np.where(df['win_loss_h'] == 'W', 'H', 'R')

        def winner(row):
            if row['hr_winner'] == 'H':
                return row['team_abbr_h']
            else:
                return row['team_abbr_r']
        df['winner'] = df.apply(winner, axis=1)

        def loser(row):
            if row['hr_winner'] == 'H':
                return row['team_abbr_r']
            else:
                return row['team_abbr_h']
        df['loser'] = df.apply(loser, axis=1)

        def mov(row):
            if row['hr_winner'] == 'H':
                return row['pts_h'] - row['pts_r']
            else:
                return row['pts_r'] - row['pts_h']
        df['mov'] = df.apply(mov, axis=1)
        return df

    def _format(self):
        df = self.data.copy()
        df = BoxScores._season_id(df)
        df = BoxScores._matchup(df)
        df['video'] = np.where(df['VIDEO_AVAILABLE'], 'Y', 'N')
        df = df.drop(columns=['TEAM_NAME', 'VIDEO_AVAILABLE'])
        df = df.rename(columns={
            'TEAM_ABBREVIATION': 'team_abbr',
            'GAME_DATE': 'date',
            'WL': 'win_loss',
        })
        df.columns = df.columns.str.lower()
        df['date'] = pd.to_datetime(df['date'])
        df['season_type'] = df['season_type'].astype('category')
        df['team_abbr'] = df['team_abbr'].astype('category')
        df['opp_team_abbr'] = df['opp_team_abbr'].astype('category')
        df['win_loss'] = df['win_loss'].astype('category')
        df['home_road'] = df['home_road'].astype('category')
        df['video'] = df['video'].astype('category')
        return df

    @staticmethod
    def _season_id(df):
        """Extract season and season type from a box score season ID."""
        df['season'] = df['SEASON_ID'].apply(
            lambda s: params.Season.season_from_id(s).start_year
        )
        df['season_type'] = df['SEASON_ID'].apply(
            lambda s: params.SeasonType.season_type_abbr(s)
        )
        df = df.drop(columns=['SEASON_ID'])
        return df

    @staticmethod
    def _matchup(df):
        """Add more useful columns based upon matchup information."""
        df['home_road'] = np.where(df['MATCHUP'].str.contains('@'), 'R', 'H')
        df['opp_team_abbr'] = df['MATCHUP'].str.split(' ').str.get(-1)
        df = df.drop(columns=['MATCHUP'])
        return df


class Leaders(scrape.NBAStats):
    """League-wide ranking of players for season by statistic category."""
    def __init__(
            self, *, scraper,
            per_mode=params.PerMode.default(),
            stat_category=params.StatCategory.default(),
            season=params.Season.default(),
            season_type=params.SeasonType.default(),
            scope=params.PlayerScopeLeagueLeaders.default()):
        api_params = params.Arguments(
            PerMode=per_mode,
            StatCategory=stat_category,
            Season=season,
            SeasonType=season_type,
            Scope=scope,
        )
        table = Table(
            api_endpoint='leagueleaders',
            api_params=api_params,
        )
        super().__init__(
            scraper=scraper,
            table=table,
        )

    @classmethod
    def Rookies(cls, **kwargs):
        kwargs['scope'] = params.PlayerScopeLeagueLeaders.Rookies
        return cls(**kwargs)


class PlayerTracking(scrape.NBAStats):
    """Aggregate tracking statistics by player or team for season."""
    def __init__(
            self, *, scraper,
            team=None,
            player_team_flag=params.PlayerTeamTracking.default(),
            pt_measure_type=params.PTMeasureType.default(),
            season=params.Season.default(),
            season_type=params.SeasonType.default(),
            per_mode=params.PerMode.default(),
            plus_minus=params.PlusMinus.default(),
            pace_adjust=params.PaceAdjust.default(),
            rank=params.Rank.default(),
            last_n_games=params.PriorGames.default(),
            month=params.SeasonMonth.default(),
            season_segment=params.SeasonSegment.default(),
            opposing_team=params.OpponentTeamID.default(),
            conference=params.Conference.default(),
            vs_conference=params.Conference.default(),
            division=params.Division.default(),
            vs_division=params.Division.default(),
            date_from=params.DateFrom.default(),
            date_to=params.DateTo.default(),
            playoff_round=params.PlayoffRound.default(),
            game_outcome=params.GameOutcome.default(),
            game_location=params.GameLocation.default(),
            shot_clock_range=params.ShotClockRange.default(),
            period=params.Period.default(),
            game_segment=params.GameSegment.default(),
            player_position=params.PlayerPosition.default(),
            player_experience=params.PlayerExperience.default(),
            starter_bench=params.StarterBench.default(),
            draft_year=params.DraftYear.default(),
            draft_pick=params.DraftPick.default(),
            college=params.College.default(),
            country=params.Country.default(),
            weight=params.PlayerWeight.default(),
            height=params.PlayerHeight.default(),
            game_scope=params.GameScopeBlankDefault.default(),
            counter=params.NBACounter.default(),
            sorter=params.Sorter.default(),
            sort_direction=params.SortDirection.default()):
        api_params = params.Arguments(
            team=team,
            PlayerOrTeam=player_team_flag,
            PtMeasureType=pt_measure_type,
            Season=season,
            SeasonType=season_type,
            PerMode=per_mode,
            PlusMinus=plus_minus,
            PaceAdjust=pace_adjust,
            Rank=rank,
            LastNGames=last_n_games,
            Month=month,
            SeasonSegment=season_segment,
            OpponentTeamID=opposing_team,
            Conference=conference,
            VsConference=vs_conference,
            Division=division,
            VsDivision=vs_division,
            DateFrom=date_from,
            DateTo=date_to,
            PORound=playoff_round,
            Outcome=game_outcome,
            Location=game_location,
            ShotClockRange=shot_clock_range,
            Period=period,
            GameSegment=game_segment,
            PlayerPosition=player_position,
            PlayerExperience=player_experience,
            StarterBench=starter_bench,
            DraftYear=draft_year,
            DraftPick=draft_pick,
            College=college,
            Country=country,
            Weight=weight,
            Height=height,
            GameScope=game_scope,
            Counter=counter,
            Sorter=sorter,
            Direction=sort_direction,
        )
        table = Table(
            api_endpoint='leaguedashptstats',
            api_params=api_params,
        )
        super().__init__(
            scraper=scraper,
            table=table,
        )


class PlayersDashboard(scrape.NBAStats):
    """Player box score and related statistics for season across league."""
    def __init__(
            self, *, scraper,
            team=None,
            measure_type=params.MeasureType.default(),
            season=params.Season.default(),
            season_type=params.SeasonType.default(),
            per_mode=params.PerMode.default(),
            plus_minus=params.PlusMinus.default(),
            pace_adjust=params.PaceAdjust.default(),
            rank=params.Rank.default(),
            last_n_games=params.PriorGames.default(),
            month=params.SeasonMonth.default(),
            season_segment=params.SeasonSegment.default(),
            opposing_team=params.OpponentTeamID.default(),
            conference=params.Conference.default(),
            vs_conference=params.Conference.default(),
            division=params.Division.default(),
            vs_division=params.Division.default(),
            date_from=params.DateFrom.default(),
            date_to=params.DateTo.default(),
            playoff_round=params.PlayoffRound.default(),
            game_outcome=params.GameOutcome.default(),
            game_location=params.GameLocation.default(),
            shot_clock_range=params.ShotClockRange.default(),
            period=params.Period.default(),
            game_segment=params.GameSegment.default(),
            player_position=params.PlayerPosition.default(),
            player_experience=params.PlayerExperience.default(),
            starter_bench=params.StarterBench.default(),
            draft_year=params.DraftYear.default(),
            draft_pick=params.DraftPick.default(),
            college=params.College.default(),
            country=params.Country.default(),
            weight=params.PlayerWeight.default(),
            height=params.PlayerHeight.default(),
            game_scope=params.GameScopeBlankDefault.default(),
            counter=params.NBACounter.default(),
            sorter=params.Sorter.default(),
            sort_direction=params.SortDirection.default()):
        api_params = params.Arguments(
            team=team,
            MeasureType=measure_type,
            Season=season,
            SeasonType=season_type,
            PerMode=per_mode,
            PlusMinus=plus_minus,
            PaceAdjust=pace_adjust,
            Rank=rank,
            LastNGames=last_n_games,
            Month=month,
            SeasonSegment=season_segment,
            OpponentTeamID=opposing_team,
            Conference=conference,
            VsConference=vs_conference,
            Division=division,
            VsDivision=vs_division,
            DateFrom=date_from,
            DateTo=date_to,
            PORound=playoff_round,
            Outcome=game_outcome,
            Location=game_location,
            ShotClockRange=shot_clock_range,
            Period=period,
            GameSegment=game_segment,
            PlayerPosition=player_position,
            PlayerExperience=player_experience,
            StarterBench=starter_bench,
            DraftYear=draft_year,
            DraftPick=draft_pick,
            College=college,
            Country=country,
            Weight=weight,
            Height=height,
            GameScope=game_scope,
            Counter=counter,
            Sorter=sorter,
            Direction=sort_direction,
        )
        table = Table(
            api_endpoint='leaguedashplayerstats',
            api_params=api_params,
        )
        super().__init__(
            scraper=scraper,
            table=table,
        )


class TeamsDashboard(scrape.NBAStats):
    """Team box score and related statistics for season across league."""
    def __init__(
            self, *, scraper,
            team=None,
            measure_type=params.MeasureType.default(),
            season=params.Season.default(),
            season_type=params.SeasonType.default(),
            per_mode=params.PerMode.default(),
            plus_minus=params.PlusMinus.default(),
            pace_adjust=params.PaceAdjust.default(),
            rank=params.Rank.default(),
            last_n_games=params.PriorGames.default(),
            month=params.SeasonMonth.default(),
            season_segment=params.SeasonSegment.default(),
            opposing_team=params.OpponentTeamID.default(),
            conference=params.Conference.default(),
            vs_conference=params.Conference.default(),
            division=params.Division.default(),
            vs_division=params.Division.default(),
            date_from=params.DateFrom.default(),
            date_to=params.DateTo.default(),
            playoff_round=params.PlayoffRound.default(),
            game_outcome=params.GameOutcome.default(),
            game_location=params.GameLocation.default(),
            shot_clock_range=params.ShotClockRange.default(),
            period=params.Period.default(),
            game_segment=params.GameSegment.default(),
            player_position=params.PlayerPosition.default(),
            player_experience=params.PlayerExperience.default(),
            starter_bench=params.StarterBench.default(),
            game_scope=params.GameScopeBlankDefault.default(),
            counter=params.NBACounter.default(),
            sorter=params.Sorter.default(),
            sort_direction=params.SortDirection.default()):
        api_params = params.Arguments(
            team=team,
            MeasureType=measure_type,
            Season=season,
            SeasonType=season_type,
            PerMode=per_mode,
            PlusMinus=plus_minus,
            PaceAdjust=pace_adjust,
            Rank=rank,
            LastNGames=last_n_games,
            Month=month,
            SeasonSegment=season_segment,
            OpponentTeamID=opposing_team,
            Conference=conference,
            VsConference=vs_conference,
            Division=division,
            VsDivision=vs_division,
            DateFrom=date_from,
            DateTo=date_to,
            PORound=playoff_round,
            Outcome=game_outcome,
            Location=game_location,
            ShotClockRange=shot_clock_range,
            Period=period,
            GameSegment=game_segment,
            PlayerPosition=player_position,
            PlayerExperience=player_experience,
            StarterBench=starter_bench,
            GameScope=game_scope,
            Counter=counter,
            Sorter=sorter,
            Direction=sort_direction,
        )
        table = Table(
            api_endpoint='leaguedashteamstats',
            api_params=api_params,
        )
        super().__init__(
            scraper=scraper,
            table=table,
        )


class TeamsClutchDashboard(scrape.NBAStats):
    """Team clutch-time statistics for season across league."""
    def __init__(
            self, *, scraper,
            team=None,
            clutch_time=params.ClutchTime.default(),
            ahead_behind=params.AheadBehind.default(),
            point_diff=params.PointDiff.default(),
            measure_type=params.MeasureType.default(),
            season=params.Season.default(),
            season_type=params.SeasonType.default(),
            per_mode=params.PerMode.default(),
            plus_minus=params.PlusMinus.default(),
            pace_adjust=params.PaceAdjust.default(),
            rank=params.Rank.default(),
            last_n_games=params.PriorGames.default(),
            month=params.SeasonMonth.default(),
            season_segment=params.SeasonSegment.default(),
            opposing_team=params.OpponentTeamID.default(),
            conference=params.Conference.default(),
            vs_conference=params.Conference.default(),
            division=params.Division.default(),
            vs_division=params.Division.default(),
            date_from=params.DateFrom.default(),
            date_to=params.DateTo.default(),
            playoff_round=params.PlayoffRound.default(),
            game_outcome=params.GameOutcome.default(),
            game_location=params.GameLocation.default(),
            shot_clock_range=params.ShotClockRange.default(),
            period=params.Period.default(),
            game_segment=params.GameSegment.default(),
            player_position=params.PlayerPosition.default(),
            player_experience=params.PlayerExperience.default(),
            starter_bench=params.StarterBench.default(),
            game_scope=params.GameScopeBlankDefault.default(),
            counter=params.NBACounter.default(),
            sorter=params.Sorter.default(),
            sort_direction=params.SortDirection.default(),
            nba_stats_requests=None,
            filehandler=None):
        api_params = params.Arguments(
            team=team,
            ClutchTime=clutch_time,
            AheadBehind=ahead_behind,
            PointDiff=point_diff,
            MeasureType=measure_type,
            Season=season,
            SeasonType=season_type,
            PerMode=per_mode,
            PlusMinus=plus_minus,
            PaceAdjust=pace_adjust,
            Rank=rank,
            LastNGames=last_n_games,
            Month=month,
            SeasonSegment=season_segment,
            OpponentTeamID=opposing_team,
            Conference=conference,
            VsConference=vs_conference,
            Division=division,
            VsDivision=vs_division,
            DateFrom=date_from,
            DateTo=date_to,
            PORound=playoff_round,
            Outcome=game_outcome,
            Location=game_location,
            ShotClockRange=shot_clock_range,
            Period=period,
            GameSegment=game_segment,
            PlayerPosition=player_position,
            PlayerExperience=player_experience,
            StarterBench=starter_bench,
            GameScope=game_scope,
            Counter=counter,
            Sorter=sorter,
            Direction=sort_direction,
        )
        table = Table(
            api_endpoint='leaguedashteamclutch',
            api_params=api_params,
        )
        super().__init__(
            scraper=scraper,
            table=table,
        )


class TeamsDefenseDashboard(scrape.NBAStats):
    """Team defensive statistics for season across league."""
    def __init__(
            self, *, scraper,
            team=None,
            defense_category=params.DefenseCategory.default(),
            season=params.Season.default(),
            season_type=params.SeasonType.default(),
            per_mode=params.PerMode.default(),
            last_n_games=params.PriorGames.default(),
            month=params.SeasonMonth.default(),
            season_segment=params.SeasonSegment.default(),
            opposing_team=params.OpponentTeamID.default(),
            conference=params.Conference.default(),
            vs_conference=params.Conference.default(),
            division=params.Division.default(),
            vs_division=params.Division.default(),
            date_from=params.DateFrom.default(),
            date_to=params.DateTo.default(),
            playoff_round=params.PlayoffRound.default(),
            game_outcome=params.GameOutcome.default(),
            game_location=params.GameLocation.default(),
            shot_clock_range=params.ShotClockRange.default(),
            period=params.Period.default(),
            game_segment=params.GameSegment.default()):
        api_params = params.Arguments(
            team=team,
            DefenseCategory=defense_category,
            Season=season,
            SeasonType=season_type,
            PerMode=per_mode,
            LastNGames=last_n_games,
            Month=month,
            SeasonSegment=season_segment,
            OpponentTeamID=opposing_team,
            Conference=conference,
            VsConference=vs_conference,
            Division=division,
            VsDivision=vs_division,
            DateFrom=date_from,
            DateTo=date_to,
            PORound=playoff_round,
            Outcome=game_outcome,
            Location=game_location,
            ShotClockRange=shot_clock_range,
            Period=period,
        )
        table = Table(
            api_endpoint='leaguedashptteamdefend',
            api_params=api_params,
        )
        super().__init__(
            scraper=scraper,
            table=table,
        )


class TeamsShotLocations(scrape.NBAStats):
    """Team shooting locations for season across league."""
    def __init__(
            self, *, scraper,
            team=None,
            measure_type=params.MeasureType.default(),
            distance_range=params.DistanceRange.default(),
            season=params.Season.default(),
            season_type=params.SeasonType.default(),
            per_mode=params.PerMode.default(),
            plus_minus=params.PlusMinus.default(),
            pace_adjust=params.PaceAdjust.default(),
            rank=params.Rank.default(),
            last_n_games=params.PriorGames.default(),
            month=params.SeasonMonth.default(),
            season_segment=params.SeasonSegment.default(),
            opposing_team=params.OpponentTeamID.default(),
            conference=params.Conference.default(),
            vs_conference=params.Conference.default(),
            division=params.Division.default(),
            vs_division=params.Division.default(),
            date_from=params.DateFrom.default(),
            date_to=params.DateTo.default(),
            playoff_round=params.PlayoffRound.default(),
            game_outcome=params.GameOutcome.default(),
            game_location=params.GameLocation.default(),
            period=params.Period.default(),
            game_segment=params.GameSegment.default(),
            player_position=params.PlayerPosition.default(),
            player_experience=params.PlayerExperience.default(),
            starter_bench=params.StarterBench.default(),
            game_scope=params.GameScopeBlankDefault.default()):
        api_params = params.Arguments(
            team=team,
            MeasureType=measure_type,
            DistanceRange=distance_range,
            Season=season,
            SeasonType=season_type,
            PerMode=per_mode,
            PlusMinus=plus_minus,
            PaceAdjust=pace_adjust,
            Rank=rank,
            LastNGames=last_n_games,
            Month=month,
            SeasonSegment=season_segment,
            OpponentTeamID=opposing_team,
            Conference=conference,
            VsConference=vs_conference,
            Division=division,
            VsDivision=vs_division,
            DateFrom=date_from,
            DateTo=date_to,
            PORound=playoff_round,
            Outcome=game_outcome,
            Location=game_location,
            Period=period,
            GameSegment=game_segment,
            PlayerPosition=player_position,
            PlayerExperience=player_experience,
            StarterBench=starter_bench,
            GameScope=game_scope,
        )
        table = Table(
            api_endpoint='leaguedashteamshotlocations',
            api_params=api_params,
        )
        super().__init__(
            scraper=scraper,
            table=table,
        )

    @classmethod
    def OpponentOverall(cls, **kwargs):
        kwargs['measure_type'] = params.MeasureType.Opponent
        return cls(**kwargs)


class TeamsShotDashboard(scrape.NBAStats):
    """Team shooting statistics for season across league."""
    def __init__(
            self, *, scraper,
            team=None,
            general_range=params.GeneralRange.default(),
            shot_clock_range=params.ShotClockRange.default(),
            dribble_range=params.DribbleRange.default(),
            touch_time_range=params.TouchTimeRange.default(),
            closest_defender=params.CloseDefDistRange.default(),
            shot_distance=params.ShotDistRange.default(),
            season=params.Season.default(),
            season_type=params.SeasonType.default(),
            per_mode=params.PerMode.default(),
            last_n_games=params.PriorGames.default(),
            month=params.SeasonMonth.default(),
            season_segment=params.SeasonSegment.default(),
            opposing_team=params.OpponentTeamID.default(),
            conference=params.Conference.default(),
            vs_conference=params.Conference.default(),
            division=params.Division.default(),
            vs_division=params.Division.default(),
            date_from=params.DateFrom.default(),
            date_to=params.DateTo.default(),
            playoff_round=params.PlayoffRound.default(),
            game_outcome=params.GameOutcome.default(),
            game_location=params.GameLocation.default(),
            period=params.Period.default(),
            game_segment=params.GameSegment.default(),
            player_position=params.PlayerPosition.default(),
            player_experience=params.PlayerExperience.default(),
            starter_bench=params.StarterBench.default()):
        api_params = params.Arguments(
            team=team,
            GeneralRange=general_range,
            ShotClockRange=shot_clock_range,
            DribbleRange=dribble_range,
            TouchTimeRange=touch_time_range,
            CloseDefDistRange=closest_defender,
            ShotDistRange=shot_distance,
            Season=season,
            SeasonType=season_type,
            PerMode=per_mode,
            LastNGames=last_n_games,
            Month=month,
            SeasonSegment=season_segment,
            OpponentTeamID=opposing_team,
            Conference=conference,
            VsConference=vs_conference,
            Division=division,
            VsDivision=vs_division,
            DateFrom=date_from,
            DateTo=date_to,
            PORound=playoff_round,
            Outcome=game_outcome,
            Location=game_location,
            Period=period,
            GameSegment=game_segment,
            PlayerPosition=player_position,
            PlayerExperience=player_experience,
            StarterBench=starter_bench,
        )
        table = Table(
            api_endpoint='leaguedashteamptshot',
            api_params=api_params,
        )
        super().__init__(
            scraper=scraper,
            table=table,
        )


class TeamsOpponentShotDashboard(scrape.NBAStats):
    """Team opponents' shooting statistics for season across league."""
    def __init__(
            self, *, scraper,
            team=None,
            general_range=params.GeneralRange.default(),
            shot_clock_range=params.ShotClockRange.default(),
            dribble_range=params.DribbleRange.default(),
            touch_time_range=params.TouchTimeRange.default(),
            closest_defender=params.CloseDefDistRange.default(),
            shot_distance=params.ShotDistRange.default(),
            season=params.Season.default(),
            season_type=params.SeasonType.default(),
            per_mode=params.PerMode.default(),
            last_n_games=params.PriorGames.default(),
            month=params.SeasonMonth.default(),
            season_segment=params.SeasonSegment.default(),
            opposing_team=params.OpponentTeamID.default(),
            conference=params.Conference.default(),
            vs_conference=params.Conference.default(),
            division=params.Division.default(),
            vs_division=params.Division.default(),
            date_from=params.DateFrom.default(),
            date_to=params.DateTo.default(),
            playoff_round=params.PlayoffRound.default(),
            game_outcome=params.GameOutcome.default(),
            game_location=params.GameLocation.default(),
            period=params.Period.default(),
            game_segment=params.GameSegment.default(),
            player_position=params.PlayerPosition.default(),
            player_experience=params.PlayerExperience.default(),
            starter_bench=params.StarterBench.default()):
        api_params = params.Arguments(
            team=team,
            GeneralRange=general_range,
            ShotClockRange=shot_clock_range,
            DribbleRange=dribble_range,
            TouchTimeRange=touch_time_range,
            CloseDefDistRange=closest_defender,
            ShotDistRange=shot_distance,
            Season=season,
            SeasonType=season_type,
            PerMode=per_mode,
            LastNGames=last_n_games,
            Month=month,
            SeasonSegment=season_segment,
            OpponentTeamID=opposing_team,
            Conference=conference,
            VsConference=vs_conference,
            Division=division,
            VsDivision=vs_division,
            DateFrom=date_from,
            DateTo=date_to,
            PORound=playoff_round,
            Outcome=game_outcome,
            Location=game_location,
            Period=period,
            GameSegment=game_segment,
            PlayerPosition=player_position,
            PlayerExperience=player_experience,
            StarterBench=starter_bench,
        )
        table = Table(
            api_endpoint='leaguedashoppptshot',
            api_params=api_params,
        )
        super().__init__(
            scraper=scraper,
            table=table,
        )


class TeamsHustleDashboard(scrape.NBAStats):
    """Team hustle statistics for season across league."""
    def __init__(
            self, *, scraper, force_reload=False, archive=True,
            team=None,
            season=params.Season.default(),
            season_type=params.SeasonType.default(),
            per_mode=params.PerMode.default(),
            month=params.SeasonMonth.default(),
            season_segment=params.SeasonSegment.default(),
            opposing_team=params.OpponentTeamID.default(),
            conference=params.Conference.default(),
            vs_conference=params.Conference.default(),
            division=params.Division.default(),
            vs_division=params.Division.default(),
            date_from=params.DateFrom.default(),
            date_to=params.DateTo.default(),
            playoff_round=params.PlayoffRound.default(),
            game_outcome=params.GameOutcome.default(),
            game_location=params.GameLocation.default(),
            player_position=params.PlayerPosition.default(),
            player_experience=params.PlayerExperience.default()):
        api_params = params.Arguments(
            team=team,
            Season=season,
            SeasonType=season_type,
            PerMode=per_mode,
            Month=month,
            SeasonSegment=season_segment,
            OpponentTeamID=opposing_team,
            Conference=conference,
            VsConference=vs_conference,
            Division=division,
            VsDivision=vs_division,
            DateFrom=date_from,
            DateTo=date_to,
            PORound=playoff_round,
            Outcome=game_outcome,
            Location=game_location,
            PlayerPosition=player_position,
            PlayerExperience=player_experience,
        )
        table = Table(
            api_endpoint='leaguehustlestatsteam',
            api_params=api_params,
        )
        super().__init__(
            scraper=scraper,
            table=table,
        )
