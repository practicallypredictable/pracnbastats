"""NBA playoff series information and analysis"""

import collections
import re
from enum import Enum
from itertools import permutations
import pandas as pd
from . import params
from . import utils
from . import team
from . import exceptions

# See https://en.wikipedia.org/wiki/NBA_playoffs#Timeline
MIN_PLAYOFFS_YEAR = 1983  # Start of modern 16-team NBA playoffs format


def _enum_name(class_name):
    """Extract simple class name from Enum repr string"""
    pattern = "\'.*\'"
    return re.search(pattern, str(class_name)).group().replace('\'', '')


class TeamType(Enum):
    """Team with or without playoff series home court advantage"""
    SHCA = '1'
    OTHER = '2'

    @staticmethod
    def convert_string(s):
        """Convert various possible input strings to standard format"""
        s = s.upper()
        # Permit various aliases
        s = s.replace('Y', TeamType.SHCA.value)
        s = s.replace('N', TeamType.OTHER.value)
        s = s.replace('H', TeamType.SHCA.value)
        s = s.replace('R', TeamType.OTHER.value)
        return s

    def __repr__(self):
        return f'{_enum_name(self.__class__)}.{self.name}'


class GameOutcome(collections.namedtuple('GameOutcomeTuple', [
        'home_team',
        'winner',
])):
    """Representation of NBA playoff game"""
    __slots__ = ()


class PlayoffSeries(collections.namedtuple('PlayoffSeriesTuple', [
        'season',
        'playoff_round',
        'best_of',
        'games_played',
        'series_hca',
        'series_non_hca',
        'series_winner',
        'game_home_teams',
        'game_winners',
        'game_ids',
])):
    """Historical NBA playoff series"""
    __slots__ = ()

    @property
    def outcome(self):
        """Series outcome representation for historical playoff series"""
        game_winners = self.game_winners.split(',')
        series_hca = self.series_hca
        s = ''.join(
            TeamType.SHCA.value
            if winner == series_hca
            else TeamType.OTHER.value
            for winner in game_winners
        )
        return SeriesOutcome(s)

    @property
    def all_game_ids(self):
        """Game IDs from stats.nba.com for historical NBA playoff series"""
        return [int(s) for s in self.game_id.split(',')]

    @property
    def all_home_teams(self):
        """Representation of game home teams for historical playoff series"""
        return [
            TeamType.SHCA
            if team == self.series_hca
            else TeamType.OTHER
            for team in self.home_teams.split(',')
        ]

    @property
    def all_game_winners(self):
        """Representation of game winners for historical playoff series"""
        return [
            TeamType.SHCA
            if team == self.series_hca
            else TeamType.OTHER
            for team in self.game_winners.split(',')
        ]

    @property
    def game_outcomes(self):
        """Sequence of game outcomes for historical playoff series"""
        return [GameOutcome(
            home_team=game[0],
            winner=game[1],
        ) for game in zip(
            self.all_home_teams,
            self.all_game_winners,
        )]


class SeriesFormat(Enum):
    """NBA playoff schedule from perspective of SHCA team"""
    BEST_OF_7 = ''.join(str(c) for c in (
        # Current 7-game 2-2-1-1-1 format
        TeamType.SHCA.value,
        TeamType.SHCA.value,
        TeamType.OTHER.value,
        TeamType.OTHER.value,
        TeamType.SHCA.value,
        TeamType.OTHER.value,
        TeamType.SHCA.value,
    ))
    BEST_OF_5 = ''.join(str(c) for c in (
        # First rounds prior to 2002-3 season playoffs were 2-2-1
        TeamType.SHCA.value,
        TeamType.SHCA.value,
        TeamType.OTHER.value,
        TeamType.OTHER.value,
        TeamType.SHCA.value,
    ))
    FINALS_PRE_2013 = ''.join(str(c) for c in (
        # Finals prior to 2013 were 2-3-2
        TeamType.SHCA.value,
        TeamType.SHCA.value,
        TeamType.OTHER.value,
        TeamType.OTHER.value,
        TeamType.OTHER.value,
        TeamType.SHCA.value,
        TeamType.SHCA.value,
    ))

    def __repr__(self):
        return f'{_enum_name(self.__class__)}.{self.name}'

    @property
    def home_teams(self):
        return [TeamType(c) for c in self.value]

    @classmethod
    def parse(cls, s):
        """Convert string to a corresponding class member"""
        if len(s) not in (5, 7):
            msg = f'series must be best of 5 or 7 games, {s} has {len(s)}'
            raise exceptions.NBAStatsValueException(msg)
        s = TeamType.convert_string(s)
        return cls(s)

    @classmethod
    def choose(
            cls, *,
            season=params.Season.current_start_year(),
            playoff_round):
        """Playoff format appropriate for given season and playoff round"""
        # Express season as an integer start year
        if isinstance(season, params.Season):
            season = season.start_year
        elif isinstance(season, str):
            season = params.Season(text=season).start_year
        if season < MIN_PLAYOFFS_YEAR:
            msg = f'season {season} prior to modern NBA playoff formats'
            raise exceptions.NBAStatsValueException(msg)
        if (season < 2002 and
                playoff_round == params.PlayoffRound.ConferenceQuarters):
            return cls.BEST_OF_5
        elif playoff_round == params.PlayoffRound.Finals:
            if season < 2013:
                return cls.FINALS_PRE_2013
            else:
                return cls.BEST_OF_7
        else:
            return cls.BEST_OF_7


class SeriesOutcome():
    """Representation of a particular NBA playoff series outcome"""
    def __init__(self, outcome):
        s = ''.join(outcome)
        self._outcome = SeriesOutcome._valid_string(s)

    def __hash__(self):
        return hash(self._outcome)

    def __eq__(self, other):
        return self.outcome == other.outcome

    @staticmethod
    def _valid_string(s):
        s = TeamType.convert_string(s)
        if len(s) < 3 or len(s) > 7:
            msg = f'outcome {s} has invalid number ({len(s)}) of games'
            raise exceptions.NBAStatsValueException(msg)
        shca_wins = s.count(TeamType.SHCA.value)
        other_wins = s.count(TeamType.OTHER.value)
        if len(s) != (shca_wins + other_wins):
            msg = f'outcome {s} has invalid characters'
            raise exceptions.NBAStatsValueException(msg)
        if shca_wins > other_wins:
            winner_wins = shca_wins
            win_symbol = TeamType.SHCA.value
        elif other_wins > shca_wins:
            winner_wins = other_wins
            win_symbol = TeamType.OTHER.value
        else:
            msg = f'outcome {s} has no winner'
            raise exceptions.NBAStatsValueException(msg)
        if winner_wins not in (3, 4):
            msg = f'outcome {s} is not valid best of 5 or 7'
            raise exceptions.NBAStatsValueException(msg)
        last_index = len(s) - s[::-1].index(win_symbol)
        return s[:last_index]

    def __len__(self):
        return len(self.outcome)

    def __repr__(self):
        return f'{self.__class__.__name__}(\'{self.outcome}\')'

    def __str__(self):
        return f'{self.outcome}'

    def __lt__(self, other):
        if self.games_played < other.games_played:
            return True
        elif self.games_played > other.games_played:
            return False
        else:
            for i, c in enumerate(self.outcome):
                if c < other.outcome[i]:
                    return True
                elif c > other.outcome[i]:
                    return False

    @property
    def outcome(self):
        return self._outcome

    @property
    def games_played(self):
        return len(self.outcome)

    @property
    def best_of(self):
        return 5 if self.outcome.count(self.winner.value) == 3 else 7

    @property
    def winner(self):
        return TeamType(self.outcome[-1])

    @property
    def game_winners(self):
        return [TeamType(team) for team in self.outcome]

    @property
    def key(self):
        return f'{self.winner.name} in {self.games_played}'

    @staticmethod
    def key_from(*, winner=None, games_played=None):
        if games_played and games_played not in (3, 4, 5, 6, 7):
            msg = f'invalid number of games played {games_played}'
            raise exceptions.NBAStatsValueException(msg)
        if winner and games_played:
            key = f'{winner.name} in {games_played}'
        elif winner:
            key = f'{winner.name}'
        elif games_played:
            key = f'in {games_played}'
        else:
            msg = f'must pass either winner or games played'
            raise exceptions.NBAStatsValueException(msg)
        return key

    @staticmethod
    def keys_match(key, winner=None, games_played=None):
        return SeriesOutcome.key_from(
            winner=winner,
            games_played=games_played,
        ) in key


class SeriesOutcomes():
    """Representation of potential NBA playoff series outcomes"""
    def __init__(self, series_format=SeriesFormat.BEST_OF_7):
        if isinstance(series_format, str):
            series_format = SeriesFormat.parse(series_format)
        elif not isinstance(series_format, SeriesFormat):
            msg = f'invalid playoffs series format {series_format}'
            raise exceptions.NBAStatsTypeException(msg)
        self._format = series_format
        self._best_of = len(series_format.value)
        self._outcomes = {}

    @property
    def series_format(self):
        return self._format

    @property
    def home_teams(self):
        return self.series_format.home_teams

    @property
    def best_of(self):
        """Maximum number of games in series"""
        return self._best_of

    @property
    def need_to_win(self):
        """Minimum number of games to win series"""
        return 4 if self.best_of == 7 else 3

    def outcomes(self, *, winner=None, games_played=None):
        """Possible playoff series outcomes"""
        if winner and winner in self._outcomes:
            outcomes = self._outcomes[winner]
        elif winner:
            outcomes = self._outcomes_for_winner(winner)
            self._outcomes[winner] = outcomes
        else:
            if TeamType.SHCA in self._outcomes:
                shca_outcomes = self._outcomes[TeamType.SHCA]
            else:
                shca_outcomes = self._outcomes_for_winner(TeamType.SHCA)
                self._outcomes[TeamType.SHCA] = shca_outcomes
            if TeamType.OTHER in self._outcomes:
                nonshca_outcomes = self._outcomes[TeamType.OTHER]
            else:
                nonshca_outcomes = self._outcomes_for_winner(TeamType.OTHER)
                self._outcomes[TeamType.OTHER] = nonshca_outcomes
            outcomes = shca_outcomes + nonshca_outcomes
        if games_played:
            if games_played < self.need_to_win or games_played > self.best_of:
                msg = f'invalid number of games {games_played}'
                raise exceptions.NBAStatsValueException(msg)
            else:
                outcomes = [
                    outcome for outcome in outcomes
                    if outcome.games_played == games_played
                ]
        return outcomes

    def _outcomes_for_winner(self, winner):
        symbols = self._symbols(winner)
        unique_outcomes = set(permutations(symbols))
        return sorted(SeriesOutcome(outcome) for outcome in unique_outcomes)

    def _symbols(self, winner):
        win_symbol = winner.value
        if winner == TeamType.SHCA:
            lose_symbol = TeamType.OTHER.value
        else:
            lose_symbol = TeamType.SHCA.value
        symbols = (
            win_symbol*self.need_to_win +
            lose_symbol*(self.best_of - self.need_to_win)
        )
        return symbols

    def _valid(self, outcome, symbol):
        assert outcome.count(symbol) == self.need_to_win  # Sanity-check input
        last_index = len(outcome) - outcome[::-1].index(symbol)
        return outcome[:last_index]


class SeriesBoxScores():
    """NBA playoff series box scores for a given season"""
    def __init__(self, *, scraper, season=params.Season.default()):
        self._scraper = scraper
        self._season = season
        self._boxscores = team.BoxScores(
            scraper=self._scraper,
            season=self._season,
            season_type=params.SeasonType.Playoffs,
        )
        matchups = SeriesBoxScores._format_matchups(self._boxscores.matchups)
        self._df = SeriesBoxScores._playoff_series(season, matchups)

    @property
    def season(self):
        return self._season

    @property
    def box_scores(self):
        return self._boxscores

    @property
    def data(self):
        return self._df

    @staticmethod
    def _matchup_id(season_year, abbrs):
        abbrs = sorted(list(abbrs))
        abbr1 = abbrs.pop(0)
        abbr2 = abbrs.pop(0)
        return f'{abbr1}_{abbr2}_{season_year}'

    @staticmethod
    def _create_matchup_id(row):
        return SeriesBoxScores._matchup_id(
            row['season'],
            set([row['team_abbr_h'], row['team_abbr_r']])
        )

    @staticmethod
    def _format_matchups(df):
        df['matchup_id'] = df.apply(SeriesBoxScores._create_matchup_id, axis=1)
        first_cols = ['matchup_id', ]
        cols = first_cols + [
            col for col in df.columns if col not in first_cols
        ]
        return df[cols].sort_values(by=['date']).reset_index(drop=True)

    @staticmethod
    def _get_series_info(g):
        results = {}
        results['first_game_date'] = g['date'].min()
        results['games_played'] = g['game_id'].count()
        results['game_home_teams'] = g['team_abbr_h'].str.cat(sep=',')
        results['series_hca'] = results['game_home_teams'].split(',')[0]
        results['series_non_hca'] = (
            g['team_abbr_r'].str.cat(sep=',').split(',')[0]
        )
        results['game_winners'] = g['winner'].str.cat(sep=',')
        results['series_winner'] = results['game_winners'].split(',')[-1]
        winner_won = results['game_winners'].count(results['series_winner'])
        results['best_of'] = 5 if winner_won == 3 else 7
        results['game_ids'] = g['game_id'].apply(str).str.cat(sep=',')
        return pd.Series(results, index=[
            'best_of',
            'games_played',
            'series_hca',
            'series_non_hca',
            'series_winner',
            'game_home_teams',
            'game_winners',
            'first_game_date',
            'game_ids',
        ])

    @staticmethod
    def _playoff_rounds(df):
        df.loc[(
            df.index < 8),
            'playoff_round',
        ] = params.PlayoffRound.ConferenceQuarters.value
        df.loc[
            (df.index >= 8) & (df.index < 12),
            'playoff_round',
        ] = params.PlayoffRound.ConferenceSemis.value
        df.loc[
            (df.index >= 12) & (df.index < 14),
            'playoff_round',
        ] = params.PlayoffRound.ConferenceFinals.value
        df.loc[
            (df.index == 14),
            'playoff_round',
        ] = params.PlayoffRound.Finals.value
        df['playoff_round'] = df['playoff_round'].astype(int)
        return df

    def _playoff_series(season, matchups):
        df = (
            matchups.groupby(['matchup_id'])
            .apply(SeriesBoxScores._get_series_info)
            .sort_values(by=['first_game_date'])
            .reset_index()
        )
        df = SeriesBoxScores._playoff_rounds(df)
        df['season'] = season.start_year
        first_cols = ['season', 'playoff_round', ]
        drop_cols = ['matchup_id', 'first_game_date', ]
        cols = first_cols + [
            col for col in df.columns
            if col not in first_cols and
            col not in drop_cols
        ]
        return df[cols]

    def as_tuples(self, *, index=False):
        return utils.as_tuples(
            df=self._df,
            to_tuple=PlayoffSeries,
            index=index,
        )

    def playoff_round(self, playoff_round, *, index=False):
        rows = self._df[self._df['playoff_round'] == playoff_round]
        return utils.as_tuples(df=rows, to_tuple=PlayoffSeries, index=index)

    def conf_qtrs(self, *, index=False):
        return self.playoff_round(
            playoff_round=params.PlayoffRound.ConferenceQuarters.value
        )

    def conf_semis(self, *, index=False):
        return self.playoff_round(
            playoff_round=params.PlayoffRound.ConferenceSemis.value
        )

    def conf_finals(self, *, index=False):
        return self.playoff_round(
            playoff_round=params.PlayoffRound.ConferenceFinals.value
        )

    def finals(self, *, index=False):
        return self.playoff_round(
            playoff_round=params.PlayoffRound.Finals.value
        )
