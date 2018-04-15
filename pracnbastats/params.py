from enum import Enum
from datetime import date, datetime
from collections import OrderedDict

# Miscellaneous constants used in parameters

LeagueID = '00' # NBA identifier
MIN_YEAR = 1996 # Earliest season for which site has advanced stats
MIN_PT_YEAR = 2013 # Earliest season for which site has player tracking data
MIN_DATE = date(1996, 11, 1) # First day of 1996 season
NBA_COUNTER = 1000 # Not sure what this does

# Helper base classes for simple parameters
# Credit to https://github.com/seemethere/nba_py/ for this idea,
# although these default classes are implemented differently here
# Notice that these base classes doesn't define any Enum members, so derived
# classes can define members.

class _DefaultEnum(Enum):
    @classmethod
    def api_name(cls):
        return cls.__name__


class _DefaultBlank(_DefaultEnum):
    @staticmethod
    def default():
        return ''


class _DefaultZero(_DefaultEnum):
    @staticmethod
    def default():
        return 0


class _DefaultNo(_DefaultEnum):
    @staticmethod
    def default():
        return 'N'


# Helper base class for "important" parameters where we want to store data
# keyed by these parameters. Examples include:
#    - Season
#    - MeasureType
#    - PerMode
# This base class defines concept of an "attribute abbreviation" which
# we can use later as a key to get back the correct data.
# Notice that this base class doesn't define any Enum members, so derived
# classes can define members.

class _EnumParam(Enum):
    def __init__(self, param, attr_abbr):
        self.param = param
        self.attr_abbr = attr_abbr
    @classmethod
    def api_name(cls):
        return cls.__name__


# Main class for grouping and passing around parameters

class Arguments():
    def __init__(self,
            team=None,
            opposing_team=None,
            player=None,
            game=None,
            **kwargs):
        self._dict = {'LeagueID': LeagueID}
        self._for_request = {'LeagueID': LeagueID}
        if team:
            self._dict.update({'TeamID': team})
            self._for_request.update({'TeamID': team.id})
        if player:
            self._dict.update({'PlayerID': player})
            self._for_request.update({'PlayerID': player.id})
        if game:
            self._dict.update({'GameID': game})
            self._for_request.update({'GameID': game.id})
        self._add_params(**kwargs)
        # Put checks here for parameter combinations that don't make sense
        # If Playoff round specified, then season type should be playoffs
        if self._dict.get('PORound', 0) > 0:
            if self._dict.get('SeasonType', None) != SeasonType.Playoffs:
                raise ValueError('SeasonType and PORound not compatible')

    def _add_params(self, **kwargs):
        for request_param, value in kwargs.items():
            self._dict.update({request_param: value})
            if isinstance(value, _EnumParam):
                self._for_request.update({request_param: value.param})
            elif isinstance(value, _DefaultEnum):
                self._for_request.update({request_param: value.value})
            elif isinstance(value, Enum):
                self._for_request.update({request_param: value.value})
            elif isinstance(value, Season):
                self._for_request.update({request_param: value.text})
            else:
                self._for_request.update({request_param: value})

    def __repr__(self):
        return f'{self.__class__.__name__}({self._dict})'

    def __str__(self):
        return f'{self.__class__.__name__}({self._for_request})'

    def sorted_by_key(self):
        return OrderedDict(sorted(self._for_request.items()))

    @property
    def for_request(self):
        return self._for_request.copy()

    def get(self, param):
        return self._dict.get(param, None)

    def update(self, param, value):
        self._dict.update({param: value})
        self._for_request.update({param: value.param})


# Parameters relating to statistics types

class MeasureType(_EnumParam):
    """Box score and related categories."""
    Traditional = ('Base', 'trad')
    Advanced = ('Advanced', 'adv')
    Misc = ('Misc', 'misc')
    FourFactors = ('Four Factors', 'fourfact')
    Scoring = ('Scoring', 'score')
    Opponent = ('Opponent', 'opp')
    Usage = ('Usage', 'usage')
    Defense = ('Defense', 'def')
    def __init__(self, param, attr_abbr):
        super().__init__(param, attr_abbr)
    @classmethod
    def default(cls):
        return cls.Traditional


class PTMeasureType(_EnumParam):
    """Player Tracking categories."""
    Drives = ('Drives', 'drives')
    DefensiveImpact = ('Defense', 'defense')
    CatchShoot = ('CatchShoot', 'catch')
    Passing = ('Passing', 'passing')
    Touches = ('Possessions', 'touches')
    PullUpShooting = ('PullUpShot', 'pullup')
    Rebounding = ('Rebounding', 'rebound')
    ShootingEfficiency = ('Efficiency', 'eff')
    SpeedDistance = ('SpeedDistance', 'speeddist')
    ElbowTouches = ('ElbowTouch', 'elbow')
    PostUps = ('PostTouch', 'post')
    PaintTouches = ('PaintTouch', 'paint')
    def __init__(self, param, attr_abbr):
        super().__init__(param, attr_abbr)
    @classmethod
    def default(cls):
        return cls.Drives


class PerMode(_EnumParam):
    """Units for statistics."""
    Totals = ('Totals', 'totals')
    PerGame = ('PerGame', 'pergame')
    MinutesPer = ('MinutesPer', 'minper')
    Per48 = ('Per48', 'per48')
    Per40 = ('Per40', 'per40')
    Per36 = ('Per36', 'per36')
    PerMinute = ('PerMinute', 'permin')
    PerPossession = ('PerPossession', 'perposs')
    PerPlay = ('PerPlay', 'perplay')
    Per100Possessions = ('Per100Possessions', 'per100poss')
    Per100Plays = ('Per100Plays', 'per100play')
    def __init__(self, param, attr_abbr):
        super().__init__(param, attr_abbr)
    @classmethod
    def default(cls):
        return cls.PerGame


class DefenseCategory(_EnumParam):
    """Team defensive statistics categories."""
    Overall = ('Overall', 'overall')
    Twos = ('2 Pointers', 'fg2')
    Threes = ('3 Pointers', 'fg3')
    LessThan6Ft = ('Less Than 6Ft', 'lt6')
    LessThan10Ft = ('Less Than 10Ft', 'lt10')
    MoreThan15Ft = ('Greater Than 15Ft', 'gt15')
    def __init__(self, param, attr_abbr):
        super().__init__(param, attr_abbr)
    @classmethod
    def default(cls):
        return cls.Overall


class GeneralRange(_EnumParam):
    Blank = ('', 'NA')
    Overall = ('Overall', 'overall')
    CatchShoot = ('Catch and Shoot', 'catch')
    Pullups = ('Pullups', 'pullup')
    LessThan10Ft = ('Less Than 10 Ft', 'lt10')
    def __init__(self, param, attr_abbr):
        super().__init__(param, attr_abbr)
    @classmethod
    def default(cls):
        return cls.Blank


class DribbleRange(_EnumParam):
    Blank = ('', 'NA')
    NoDribbles = ('0 Dribbles', 'drib0')
    OneDribble = ('1 Dribble', 'drib1')
    TwoDribbles = ('2 Dribbles', 'drib2')
    SeveralDribbles = ('3-6 Dribbles', 'sevdrib')
    ManyDribbles = ('7+ Dribbles', 'manydrib')
    def __init__(self, param, attr_abbr):
        super().__init__(param, attr_abbr)
    @classmethod
    def default(cls):
        return cls.Blank


class TouchTimeRange(_EnumParam):
    Blank = ('', 'NA')
    LessThan2Sec = ('Touch < 2 Seconds', 'touchlt2')
    TwoTo6Sec = ('Touch 2-6 Seconds', 'touch2to6')
    MoreThan6Sec = ('Touch 6+ Seconds', 'touchgt6')
    def __init__(self, param, attr_abbr):
        super().__init__(param, attr_abbr)
    @classmethod
    def default(cls):
        return cls.Blank


class CloseDefDistRange(_EnumParam):
    """Closest defender for shooting statistics."""
    Blank = ('', 'NA')
    VeryTight = ('0-2 Feet - Very Tight', 'verytight')
    Tight = ('2-4 Feet - Tight', 'tight')
    Open = ('4-6 Feet - Open', 'open')
    WideOpen = ('6+ Feet - Wide Open', 'wideopen')
    def __init__(self, param, attr_abbr):
        super().__init__(param, attr_abbr)
    @classmethod
    def default(cls):
        return cls.Blank


class DistanceRange(_EnumParam):
    """Opponent shooting distance."""
    Blank = ('', 'NA')
    FiveFeet = ('5ft Range', 'ft5')
    EightFeet = ('8ft Range', 'ft8')
    ByZone = ('By Zone', 'zone')
    def __init__(self, param, attr_abbr):
        super().__init__(param, attr_abbr)
    @classmethod
    def default(cls):
        return cls.Blank


class ShotDistRange(_DefaultBlank):
    MoreThan10Ft = '>=10.0'


class PlusMinus(_DefaultNo):
    pass


class PaceAdjust(_DefaultNo):
    pass


class Rank(_DefaultNo):
    pass


class StatCategory(_EnumParam):
    """Categories for league leaders statistics."""
    PTS = ('PTS', 'pts')
    FGM = ('FGM', 'fgm')
    FGA = ('FGA', 'fga')
    FG_PCT = ('FG%', 'fg_pct')
    FG3M = ('3PM', 'fg3m')
    FG3A = ('3PA', 'fg3a')
    FG3_PCT = ('3P%', 'fg3_pct')
    FTM = ('FTM', 'ftm')
    FTA = ('FTA', 'fta')
    FT_PCT = ('FT%', 'ft_pct')
    OREB = ('OREB', 'oreb')
    DREB = ('DREB', 'dreb')
    REB = ('REB', 'reb')
    AST = ('AST', 'ast')
    STL = ('STL', 'stl')
    BLK = ('BLK', 'blk')
    TOV = ('TOV', 'tov')
    AST_TOV = ('AST/TO', 'ast_to')
    STL_TOV = ('STL/TOV', 'stl_to')
    PF = ('PF', 'pf')
    EFF = ('EFF', 'eff')
    MIN = ('MIN', 'min')
    def __init__(self, param, attr_abbr):
        super().__init__(param, attr_abbr)
    @classmethod
    def default(cls):
        return cls.PTS


# Parameters relating to season and game date selection

class Season():
    """An NBA season."""
    def __init__(self, *, start_year=None, text=None):
        if not start_year and not text:
            self._start_year = Season.current_start_year()
            self._text = Season.current_text()
        elif start_year:
            if start_year >= MIN_YEAR:
                self._start_year = int(start_year)
            else:
                raise ValueError('invalid season start year', start_year)
            self._text = Season.year2text(start_year)
            if text and text != self._text:
                raise ValueError(f'incompatiable {start_year} and {text}')
        elif text:
            self._text = text
            self._start_year = Season.text2year(text)
            if self._start_year < MIN_YEAR:
                 raise ValueError('invalid season start year', self._start_year)

    def __repr__(self):
        return f'{self.__class__.__name__}(start_year={self.start_year})'

    def __str__(self):
        return self.text

    @property
    def attr_abbr(self):
        return self.text.replace('-', '_')

    @classmethod
    def api_name(cls):
        return cls.__name__

    @property
    def start_year(self):
        return self._start_year

    @property
    def text(self):
        return self._text

    @classmethod
    def current(cls):
        return cls(start_year=Season.current_start_year())

    @classmethod
    def default(cls):
        return cls.current()

    @classmethod
    def stats_seasons(cls):
        start_year = NBA_STATS_MIN_YEAR
        end_year = Season.current_start_year()
        return [cls(start_year=year)
                    for year in range(start_year, end_year+1)]

    @staticmethod
    def current_start_year():
        year = datetime.now().year
        return year if datetime.now().month > 6 else year-1

    @staticmethod
    def current_text():
        return Season.year2text(Season.current_start_year())

    @staticmethod
    def year2text(year):
        return str(year) + '-' + str(year+1)[2:]

    @staticmethod
    def text2year(season):
        return int(season[:4])

    @staticmethod
    def season_from_id(season_id):
        last4_digits = str(season_id)[-4:]
        return Season(start_year=int(last4_digits))


class SeasonType(_EnumParam):
    """Regular season or post-season."""
    # Pre-season and All-Star games not currently implemented
    Regular = ('Regular Season', 'reg')
    Playoffs = ('Playoffs', 'post')
    def __init__(self, param, attr_abbr):
        super().__init__(param, attr_abbr)
    @classmethod
    def default(cls):
        return cls.Regular
    @staticmethod
    def season_type_from_id(season_id):
        first_digit = int(str(season_id)[:1])
        if first_digit == 2:
            return SeasonType.Regular
        elif first_digit == 4:
            return SeasonType.Playoffs
        else:
            raise ValueError('unrecognized season ID', season_id)


class PriorGames():
    """Select games relative to most recent game."""
    @staticmethod
    def default():
        return 0
    @staticmethod
    def most_recent(n):
        if n < 0 or n > 15:
            raise ValueError('invalid prior game', n)
        else:
            return int(n)
    @staticmethod
    def api_name():
        return 'LastNGames'


class SeasonSegment(_DefaultBlank):
    """Select games relative to All-Star break."""
    BeforeBreak = 'Pre All-Star'
    AfterBreak = 'Post All-Star'


class SeasonMonth(_DefaultZero):
    """Select games by month."""
    October = 1
    November = 2
    December = 3
    January = 4
    February = 5
    March = 6
    April = 7
    May = 8
    June = 9
    July = 10
    August = 11
    September = 12
    @classmethod
    def api_name(cls):
        return 'Month'


class PlayoffRound(_DefaultZero):
    """Select post-season games by playoff round."""
    ConferenceQuarters = 1
    ConferenceSemis = 2
    ConferenceFinals = 3
    Finals = 4
    @classmethod
    def api_name(cls):
        return 'PORound'


# TO DO: Fix these classes to handle date logic

class DateFrom(_DefaultBlank):
    pass


class DateTo(_DefaultBlank):
    pass


# Parameters relating to league dashboard mode (team or player)
# Sloppy that NBA has two separate parameter categories for this

class PlayerTeamFlag(_EnumParam):
    """Select league data by either player or team."""
    Player = ('P', 'player')
    Team = ('T', 'team')
    @classmethod
    def default(cls):
        return cls.Player
    @staticmethod
    def api_name():
        return 'PlayerOrTeam'


class PlayerTeamTracking(_EnumParam):
    """Select league player tracking data by either player or team."""
    Player = ('Player', 'player')
    Team = ('Team', 'team')
    @classmethod
    def default(cls):
        return cls.Player
    @staticmethod
    def api_name():
        return 'PlayerOrTeam'


# Some miscellaneous (ugly) parameters

class PlayerScopeLeagueLeaders(Enum):
    """Select league leader data for all players or just rookies."""
    AllPlayers= 'S'
    Rookies = 'Rookies'
    @classmethod
    def default(cls):
        return cls.AllPlayers


class PlayerScope(Enum):
    AllPlayers = 'All Players'
    Rookies = 'Rookie'
    @classmethod
    def default(cls):
        return cls.AllPlayers


class GameScope(Enum):
    Season = 'Season'
    Last10 = 'Last 10'
    Yesterday = 'Yesterday'
    Finals = 'Finals'
    @classmethod
    def default(cls):
        return cls.Season


class GameScopeBlankDefault(_DefaultBlank):
    Last10 = 'Last 10'
    Yesterday = 'Yesterday'
    @staticmethod
    def api_name():
        return 'GameScope'


# Parameters relating to game situation

class GameOutcome(_DefaultBlank):
    """Select games by wins or losses."""
    Wins = 'W'
    Losses = 'L'
    @staticmethod
    def api_name():
        return 'Outcome'


class GameLocation(_DefaultBlank):
    """Select games by home or away."""
    Home = 'Home'
    Road = 'Road'
    @staticmethod
    def api_name():
        return 'Location'


class ShotClockRange(_DefaultBlank):
    Off = 'ShotClock Off'
    VeryVeryEarly = '24-22'
    VeryEarly = '22-18 Very Early'
    Early = '18-15 Early'
    Average = '15-7 Average'
    Late = '7-4 Late'
    VeryLate = '4-0 Very Late'
    @classmethod
    def SecondsLeft(sec):
        if 22 <= sec <= 24:
            return VeryVeryEarly.value
        elif 18 <= sec < 22:
            return VeryEarly.value
        elif 15 <= sec < 18:
            return Early.value
        elif 7 <= sec < 15:
            return Average.value
        elif 4 <= sec < 7:
            return Late.value
        elif 0 <= sec < 4:
            return VeryLate.value
        else:
            raise ValueError('invalid shot clock value', sec)


class Period(_EnumParam):
    AllQuarters = (0, 'all')
    FirstQuarter = (1, 'qtr1')
    SecondQuarter = (2, 'qtr2')
    ThirdQuarter = (3, 'qtr3')
    FourthQuarter = (4, 'qtr4')
    OT1 = (5, 'ot1')
    OT2 = (6, 'ot2')
    OT3 = (7, 'ot3')
    OT4 = (8, 'ot4')
    OT5 = (9, 'ot5')
    OT6 = (10, 'ot6')
    OT7 = (11, 'ot7')
    OT8 = (12, 'ot8')
    OT9 = (13, 'ot9')
    OT10 = (14, 'ot10')
    def __init__(self, param, attr_abbr):
        super().__init__(param, attr_abbr)
    @classmethod
    def default(cls):
        return cls.AllQuarters
    @classmethod
    def Overtime(cls, n=1):
        return cls(n+4)


class GameSegment(_DefaultBlank):
    FirstHalf = 'First Half'
    SecondHalf = 'Second Half'
    Overtime = 'Overtime'


# Parameters relating to team selection
# TO DO: figure out how to do VsDivision and VsConference
#    Problem is can't extend Enum

class OpponentTeamID(_DefaultZero):
    pass


class Division(_DefaultBlank):
    Atlantic = 'Atlantic'
    Central = 'Central'
    Northwest = 'Northwest'
    Pacific = 'Pacific'
    Southeast = 'Southeast'
    Southwest = 'Southwest'


class Conference(_DefaultBlank):
    East = 'East'
    West = 'West'


class GroupQuantity(_EnumParam):
    FiveMen = (5, '5men')
    FourMen = (4, '4men')
    ThreeMen = (3, '3men')
    TwoMen = (2, '2men')
    def __init__(self, param, attr_abbr):
        super().__init__(param, attr_abbr)
    @classmethod
    def default(cls):
        return cls.FiveMen


# Clutch parameters

class ClutchTime(_EnumParam):
    Last5Min = ('Last 5 Minutes', 'last5')
    Last4Min = ('Last 4 Minutes', 'last4')
    Last3Min = ('Last 3 Minutes', 'last3')
    Last2Min = ('Last 2 Minutes', 'last2')
    Last1Min = ('Last 1 Minutes', 'last1')
    Last30Sec = ('Last 30 Seconds', 'last30sec')
    Last10Sec = ('Last 10 Seconds', 'last10sec')
    def __init__(self, param, attr_abbr):
        super().__init__(param, attr_abbr)
    @classmethod
    def default(cls):
        return cls.Last5Min


class AheadBehind(_EnumParam):
    Unspecified = ('Ahead or Behind', 'unspecified')
    AheadTied = ('Ahead or Tied', 'ahead')
    BehindTied = ('Behind or Tied', 'behind')
    def __init__(self, param, attr_abbr):
        super().__init__(param, attr_abbr)
    @classmethod
    def default(cls):
        return cls.Unspecified


class PointDiff(_EnumParam):
    LessThan5Points = (5, 'lt5')
    LessThan4Points = (4, 'lt4')
    LessThan3Points = (3, 'lt3')
    LessThan2Points = (2, 'lt2')
    OnePoint = (1, '1pt')
    def __init__(self, param, attr_abbr):
        super().__init__(param, attr_abbr)
    @classmethod
    def default(cls):
        return cls.LessThan5Points


# Selecting players

class PlayerPosition(_DefaultBlank):
    Forward = 'F'
    Center = 'C'
    Guard = 'G'


class StarterBench(_DefaultBlank):
    Starters = 'Starters'
    Bench = 'Bench'


class PlayerExperience(_DefaultBlank):
    Rookie = 'Rookie'
    Sophomore = 'Sophomore'
    Veteran = 'Veteran'


class PlayerHeight(_DefaultBlank):
    @staticmethod
    def less_than(feet, inches):
        return f'LT+{feet}-{inches}'
    @staticmethod
    def greater_than(feet, inches):
        return f'GT+{feet}-{inches}'


class PlayerWeight(_DefaultBlank):
    @staticmethod
    def less_than(pounds):
        return f'LT+{pounds}lbs'
    @staticmethod
    def greater_than(pounds):
        return f'GT+{pounds}lbs'


class Country(_DefaultBlank):
    International = 'International'


class College(_DefaultBlank):
    HighSchool = 'High School'
    NoCollege = 'None'


class DraftYear(_DefaultBlank):
    pass


class DraftPick(_DefaultBlank):
    FirstRound = '1st+Round'
    SecondRound = '2nd+Round'
    FirstPick = '1st+Pick'
    Lottery = 'Lottery+Pick'
    Top5 = 'Top+5+Pick'
    Top10 = 'Top+10+Pick'
    Top15 = 'Top+15+Pick'
    Top20 = 'Top+20+Pick'
    Top25 = 'Top+25+Pick'
    Picks11Thru20 = 'Picks+11+Thru+20'
    Picks21Thru30 = 'Picks+21+Thru+30'
    Undrafted = 'Undrafted'


# Parameters relating to sorting

class Sorter(Enum):
    DATE = 'DATE'
    PTS = 'PTS'
    FGM = 'FGM'
    FGA = 'FGA'
    FG_PCT = 'FG_PCT'
    FG3M = 'FG3M'
    FG3A = 'FG3A'
    FG3_PCT = 'FG3_PCT'
    FTM = 'FTM'
    FTA = 'FTA'
    FT_PCT = 'FT_PCT'
    OREB = 'OREB'
    DREB = 'DREB'
    AST = 'AST'
    STL = 'STL'
    BLK = 'BLK'
    TOV = 'TOV'
    REB = 'REB'
    @classmethod
    def default(cls):
        return cls.DATE
    @staticmethod
    def api_name():
        return 'Sorter'


class SortDirection(Enum):
    DESC = 'DESC'
    ASC = 'ASC'
    @classmethod
    def default(cls):
        return cls.DESC
    @staticmethod
    def api_name():
        return 'Direction'
