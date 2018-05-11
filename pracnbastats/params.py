from enum import Enum
from datetime import date, datetime
from collections import OrderedDict
from . import exceptions
import logging

log = logging.getLogger(__name__)

# Miscellaneous constants used in parameters

LeagueID = '00'  # NBA identifier
MIN_YEAR = 1996  # Earliest season for which site has advanced stats
MIN_PT_YEAR = 2013  # Earliest season for which site has player tracking data
MIN_DATE = date(1996, 11, 1)  # First day of 1996 season


# Helper base classes
# Use Python object inheritance to impose some struture on the parameters
# Many of the parameters have default values, and we want to reuse  code
#   as much as possible

class _Parameters:
    """Base class for NBA API parameters."""
    registry = {}
    _api_name_registry = None

    def __init_subclass__(cls, *args, **kwargs):
        super().__init_subclass__(*args, **kwargs)
        # Do not register internal base classes starting with "_"
        if not cls.__name__.startswith('_'):
            cls.registry[cls.__name__] = cls

    @classmethod
    def api_name(cls):
        return cls.__name__


class _EnumBase(_Parameters, Enum):
    """Base class for NBA API parameters that are defined via Enum."""
    pass


def _create(
        to_cls, name, from_enum, getter,
        default_value=None, default_member=None, api_name=None):
    """Create a new class based on a given Enum."""
    members = [
        (member.name, getter(member))
        for _, member in from_enum.__members__.items()
    ]
    if default_value is not None:
        if default_member is not None:
            msg = 'specify either default value and member, not both'
            raise exceptions.ParamValueException(msg)
        default_member = '_DEFAULT'
        members.append((default_member, default_value))
    elif not default_member:
        msg = 'need to specify one of default value or member'
        raise exceptions.ParamValueException(msg)

    new_cls = to_cls(value=name, names=members)
    new_cls.__doc__ = from_enum.__doc__

    methods = [
        getattr(from_enum, obj)
        for obj in from_enum.__dict__
        if not obj.startswith('_') and callable(getattr(from_enum, obj))
    ]
    for method in methods:
        setattr(new_cls, method.__name__, method)

    # Create default() and api_name() methods that are expected
    #   by other parts of this parameter ecosystem
    @classmethod
    def _default_member_func(cls):
        return cls[default_member]
    new_cls.default = _default_member_func
    if api_name:
        @classmethod
        def api_func(cls):
            return api_name
        new_cls.api_name = api_func
    return new_cls


class _DefaultEnumCreator(_EnumBase):
    """Class factory for NBA API parameters with default Enum member."""
    def __new__(cls, value):
        member = object.__new__(cls)
        member._value_ = value
        return member

    @classmethod
    def create(
            cls, *,
            name, from_enum, default_value=None,
            default_member=None, api_name=None):
        """Class factory function for default Enums."""
        def getter(member):
            return member.value
        return _create(
            to_cls=cls,
            name=name,
            from_enum=from_enum,
            getter=getter,
            default_value=default_value,
            default_member=default_member,
            api_name=api_name
        )


class DefaultEnum():
    """Class decorator to implement DefaultEnum class creation."""
    def __init__(self, default_value=None, default_member=None, api_name=None):
        self._default_value = default_value
        self._default_member = default_member
        self._api_name = api_name

    def __call__(self, decorated):
        return _DefaultEnumCreator.create(
            name=decorated.__name__,
            from_enum=decorated,
            default_value=self._default_value,
            default_member=self._default_member,
            api_name=self._api_name,
        )


class _EnumStoreKeyBase(_EnumBase):
    """Base class for NBA API parameter Enum with key for storage."""
    def __init__(self, value, store_key):
        self._value = value
        self._store_key = store_key

    @property
    def value(self):
        return self._value

    @property
    def store_key(self):
        return self._store_key


class _EnumStoreKeyCreator(_EnumBase):
    """Class factory for NBA API parameters with store keys."""
    def __new__(cls, value, store_key):
        member = object.__new__(cls)
        member._value_ = value
        member._store_key = store_key
        return member

    @property
    def store_key(self):
        return self._store_key

    @classmethod
    def create(cls, *, name, from_enum, default_member, api_name=None):
        """Class factory function for Enums with store keys."""
        def getter(member):
            return (member.value, member.store_key)
        return _create(
            to_cls=cls,
            name=name,
            from_enum=from_enum,
            getter=getter,
            default_value=None,
            default_member=default_member,
            api_name=api_name
        )


class EnumStoreKey():
    """Class decorator to implement EnumStoreKey class creation."""
    def __init__(self, default_member, api_name=None):
        self._default_member = default_member
        self._api_name = api_name

    def __call__(self, decorated):
        return _EnumStoreKeyCreator.create(
            name=decorated.__name__,
            from_enum=decorated,
            default_member=self._default_member,
            api_name=self._api_name,
        )


# Module-level interface functions for use outside this module

def api_names():
    """All registered NBA API parameters."""
    cls = _Parameters
    # Check if we need to build the registry keyed by NBA API name
    if (cls._api_name_registry is None
            or len(cls.registry) != len(cls._api_name_registry)):
        cls._api_name_registry = {
            v.api_name(): v for k, v in cls.registry.items()
        }
    return cls._api_name_registry


def get(api_name):
    """Get NBA API parameter by name."""
    return api_names()[api_name]


class Season(_Parameters):
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

    # Implement expected interface methods for all NBA parameters
    # Season in a special case that needs to implement all of these
    #   since it doesn't inherit from one of the intermediate base classes
    # We want Season to have the methods of an _EnumStoreKey object

    @classmethod
    def default(cls):
        return cls.current()

    @classmethod
    def api_name(cls):
        return cls.__name__

    @property
    def value(self):
        return self.text

    @property
    def store_key(self):
        return self.text.replace('-', '_')

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
    def stats_seasons(cls):
        start_year = MIN_YEAR
        end_year = Season.current_start_year()
        return [cls(start_year=year) for year in range(start_year, end_year+1)]

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


# Main class for grouping and passing around parameters

class Arguments():
    def __init__(
            self, *,
            team=None, opposing_team=None, player=None, game=None,
            **kwargs):
        self._dict = {'LeagueID': LeagueID}
        self._for_request = {'LeagueID': LeagueID}
        self._store_keys = {}
        if team:
            self._dict.update({'TeamID': team})
            self._for_request.update({'TeamID': team.id})
        # TODO: figure out the various opposing team parameters
        if opposing_team:
            raise NotImplementedError('not working yet!')
        if player:
            self._dict.update({'PlayerID': player})
            self._for_request.update({'PlayerID': player.id})
        if game:
            self._dict.update({'GameID': game})
            self._for_request.update({'GameID': game.id})
        if team or opposing_team or player or game:
            self._has_store_key = False  # can only store manually
        else:
            self._has_store_key = None  # will check this as we add params
        self._add_params(**kwargs)

    def _add_params(self, **kwargs):
        for request_param, value in kwargs.items():
            self._dict.update({request_param: value})
            if isinstance(value, _EnumBase):
                self._for_request.update({request_param: value.value})
            else:
                self._for_request.update({request_param: value})
            if hasattr(value, 'store_key'):
                self._store_keys[request_param] = value.store_key

    @property
    def store_keys(self):
        return self._store_keys

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

@EnumStoreKey(default_member='Traditional')
class MeasureType(_EnumStoreKeyBase):
    """Box score and related categories."""
    Traditional = ('Base', 'trad')
    Advanced = ('Advanced', 'adv')
    Misc = ('Misc', 'misc')
    FourFactors = ('Four Factors', 'fourfact')
    Scoring = ('Scoring', 'score')
    Opponent = ('Opponent', 'opp')
    Usage = ('Usage', 'usage')
    Defense = ('Defense', 'def')


@EnumStoreKey(default_member='Drives')
class PTMeasureType(_EnumStoreKeyBase):
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


@EnumStoreKey(default_member='PerGame')
class PerMode(_EnumStoreKeyBase):
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


@EnumStoreKey(default_member='Overall')
class DefenseCategory(_EnumStoreKeyBase):
    """Team defensive statistics categories."""
    Overall = ('Overall', 'overall')
    Twos = ('2 Pointers', 'fg2')
    Threes = ('3 Pointers', 'fg3')
    LessThan6Ft = ('Less Than 6Ft', 'lt6')
    LessThan10Ft = ('Less Than 10Ft', 'lt10')
    MoreThan15Ft = ('Greater Than 15Ft', 'gt15')


@EnumStoreKey(default_member='All')
class GeneralRange(_EnumStoreKeyBase):
    All = ('', 'all')
    Overall = ('Overall', 'overall')
    CatchShoot = ('Catch and Shoot', 'catch')
    Pullups = ('Pullups', 'pullup')
    LessThan10Ft = ('Less Than 10 Ft', 'lt10')


@EnumStoreKey(default_member='All')
class DribbleRange(_EnumStoreKeyBase):
    All = ('', 'all')
    NoDribbles = ('0 Dribbles', 'drib0')
    OneDribble = ('1 Dribble', 'drib1')
    TwoDribbles = ('2 Dribbles', 'drib2')
    SeveralDribbles = ('3-6 Dribbles', 'sevdrib')
    ManyDribbles = ('7+ Dribbles', 'manydrib')


@EnumStoreKey(default_member='All')
class TouchTimeRange(_EnumStoreKeyBase):
    All = ('', 'all')
    LessThan2Sec = ('Touch < 2 Seconds', 'touchlt2')
    TwoTo6Sec = ('Touch 2-6 Seconds', 'touch2to6')
    MoreThan6Sec = ('Touch 6+ Seconds', 'touchgt6')


@EnumStoreKey(default_member='All')
class CloseDefDistRange(_EnumStoreKeyBase):
    """Closest defender for shooting statistics."""
    All = ('', 'all')
    VeryTight = ('0-2 Feet - Very Tight', 'verytight')
    Tight = ('2-4 Feet - Tight', 'tight')
    Open = ('4-6 Feet - Open', 'open')
    WideOpen = ('6+ Feet - Wide Open', 'wideopen')


@EnumStoreKey(default_member='All')
class DistanceRange(_EnumStoreKeyBase):
    """Opponent shooting distance."""
    All = ('', 'all')
    FiveFeet = ('5ft Range', 'ft5')
    EightFeet = ('8ft Range', 'ft8')
    ByZone = ('By Zone', 'zone')


@DefaultEnum(default_value='')
class ShotDistRange(_EnumBase):
    MoreThan10Ft = '>=10.0'


@DefaultEnum(default_value='N')
class PlusMinus(_EnumBase):
    pass


@DefaultEnum(default_value='N')
class PaceAdjust(_EnumBase):
    pass


@DefaultEnum(default_value='N')
class Rank(_EnumBase):
    pass


@EnumStoreKey(default_member='PTS')
class StatCategory(_EnumStoreKeyBase):
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


# Parameters relating to season and game date selection

@EnumStoreKey(default_member='Regular')
class SeasonType(_EnumStoreKeyBase):
    """Regular season or post-season."""
    # Pre-season and All-Star games not currently implemented
    Regular = ('Regular Season', 'reg')
    Playoffs = ('Playoffs', 'post')

    @staticmethod
    def season_type_from_id(season_id):
        first_digit = int(str(season_id)[:1])
        if first_digit == 2:
            return SeasonType.Regular
        elif first_digit == 4:
            return SeasonType.Playoffs
        else:
            raise ValueError('unrecognized season ID', season_id)

    @staticmethod
    def season_type_abbr(season_id):
        season_type = SeasonType.season_type_from_id(season_id)
        return season_type.store_key


@DefaultEnum(default_value=0, api_name='LastNGames')
class PriorGames(_EnumBase):
    """Select games relative to most recent game."""
    @staticmethod
    def most_recent(n):
        if n < 0 or n > 15:
            raise ValueError('invalid prior game', n)
        else:
            return int(n)


@DefaultEnum(default_value='')
class SeasonSegment(_EnumBase):
    BeforeBreak = 'Pre All-Star'
    AfterBreak = 'Post All-Star'


@DefaultEnum(default_value=0, api_name='Month')
class SeasonMonth(_EnumBase):
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


@DefaultEnum(default_value=0, api_name='PORound')
class PlayoffRound(_EnumBase):
    ConferenceQuarters = 1
    ConferenceSemis = 2
    ConferenceFinals = 3
    Finals = 4


# TODO: Fix these classes to handle date logic

@DefaultEnum(default_value='')
class DateFrom(_EnumBase):
    pass


@DefaultEnum(default_value='')
class DateTo(_EnumBase):
    pass


# Parameters relating to league dashboard mode (team or player)
# Sloppy that NBA has two separate parameter categories for this

@EnumStoreKey(default_member='Player', api_name='PlayerOrTeam')
class PlayerTeamFlag(_EnumStoreKeyBase):
    """Select league data by either player or team."""
    Player = ('P', 'player')
    Team = ('T', 'team')


@EnumStoreKey(default_member='Player', api_name='PlayerOrTeam')
class PlayerTeamTracking(_EnumStoreKeyBase):
    """Select league player tracking data by either player or team."""
    Player = ('Player', 'player')
    Team = ('Team', 'team')


# Some miscellaneous (ugly) parameters

@DefaultEnum(default_member='AllPlayers')
class PlayerScopeLeagueLeaders(_EnumBase):
    """Select league leader data for all players or just rookies."""
    AllPlayers = 'S'
    Rookies = 'Rookies'


@DefaultEnum(default_member='AllPlayers')
class PlayerScope(_EnumBase):
    AllPlayers = 'All Players'
    Rookies = 'Rookie'


@DefaultEnum(default_member='Season')
class GameScope(_EnumBase):
    Season = 'Season'
    Last10 = 'Last 10'
    Yesterday = 'Yesterday'
    Finals = 'Finals'


@DefaultEnum(default_value='', api_name='GameScope')
class GameScopeBlankDefault(_EnumBase):
    Last10 = 'Last 10'
    Yesterday = 'Yesterday'


# Parameters relating to game situation

@DefaultEnum(default_value='', api_name='Outcome')
class GameOutcome(_EnumBase):
    Wins = 'W'
    Losses = 'L'


@DefaultEnum(default_value='', api_name='Location')
class GameLocation(_EnumBase):
    Home = 'Home'
    Road = 'Road'


@DefaultEnum(default_value='')
class ShotClockRange(_EnumBase):
    Off = 'ShotClock Off'
    VeryVeryEarly = '24-22'
    VeryEarly = '22-18 Very Early'
    Early = '18-15 Early'
    Average = '15-7 Average'
    Late = '7-4 Late'
    VeryLate = '4-0 Very Late'

    @classmethod
    def SecondsLeft(cls, sec):
        if 22 <= sec <= 24:
            return cls.VeryVeryEarly
        elif 18 <= sec < 22:
            return cls.VeryEarly
        elif 15 <= sec < 18:
            return cls.Early
        elif 7 <= sec < 15:
            return cls.Average
        elif 4 <= sec < 7:
            return cls.Late
        elif 0 <= sec < 4:
            return cls.VeryLate
        else:
            raise ValueError('invalid shot clock value', sec)


@EnumStoreKey(default_member='All')
class Period(_EnumStoreKeyBase):
    All = (0, 'all')
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

    @classmethod
    def Overtime(cls, n=1):
        if 1 <= n <= 10:
            return cls[f'OT{n}']
        else:
            raise ValueError('invalid overtime', n)


@DefaultEnum(default_value='')
class GameSegment(_EnumBase):
    FirstHalf = 'First Half'
    SecondHalf = 'Second Half'
    Overtime = 'Overtime'


# Parameters relating to team selection
# TODO: figure out how to do VsDivision and VsConference
#    Problem is can't extend Enum

@DefaultEnum(default_value=0)
class OpponentTeamID(_EnumBase):
    pass


@DefaultEnum(default_value='')
class Division(_EnumBase):
    Atlantic = 'Atlantic'
    Central = 'Central'
    Northwest = 'Northwest'
    Pacific = 'Pacific'
    Southeast = 'Southeast'
    Southwest = 'Southwest'


@DefaultEnum(default_value='')
class Conference(_EnumBase):
    East = 'East'
    West = 'West'


@EnumStoreKey(default_member='FiveMen')
class GroupQuantity(_EnumStoreKeyBase):
    FiveMen = (5, '5men')
    FourMen = (4, '4men')
    ThreeMen = (3, '3men')
    TwoMen = (2, '2men')


# Clutch parameters

@EnumStoreKey(default_member='Last5Min')
class ClutchTime(_EnumStoreKeyBase):
    Last5Min = ('Last 5 Minutes', 'last5')
    Last4Min = ('Last 4 Minutes', 'last4')
    Last3Min = ('Last 3 Minutes', 'last3')
    Last2Min = ('Last 2 Minutes', 'last2')
    Last1Min = ('Last 1 Minutes', 'last1')
    Last30Sec = ('Last 30 Seconds', 'last30sec')
    Last10Sec = ('Last 10 Seconds', 'last10sec')


@EnumStoreKey(default_member='Any')
class AheadBehind(_EnumStoreKeyBase):
    Any = ('Ahead or Behind', 'any')
    AheadTied = ('Ahead or Tied', 'ahead')
    BehindTied = ('Behind or Tied', 'behind')


@EnumStoreKey(default_member='LessThan5Points')
class PointDiff(_EnumStoreKeyBase):
    LessThan5Points = (5, 'lt5')
    LessThan4Points = (4, 'lt4')
    LessThan3Points = (3, 'lt3')
    LessThan2Points = (2, 'lt2')
    OnePoint = (1, '1pt')


# Selecting players

@DefaultEnum(default_value='')
class PlayerPosition(_EnumBase):
    Forward = 'F'
    Center = 'C'
    Guard = 'G'


@DefaultEnum(default_value='')
class StarterBench(_EnumBase):
    Starters = 'Starters'
    Bench = 'Bench'


@DefaultEnum(default_value='')
class PlayerExperience(_EnumBase):
    Rookie = 'Rookie'
    Sophomore = 'Sophomore'
    Veteran = 'Veteran'


@DefaultEnum(default_value='')
class PlayerHeight(_EnumBase):
    @staticmethod
    def less_than(feet, inches):
        return f'LT+{feet}-{inches}'

    @staticmethod
    def greater_than(feet, inches):
        return f'GT+{feet}-{inches}'


@DefaultEnum(default_value='')
class PlayerWeight(_EnumBase):
    @staticmethod
    def less_than(pounds):
        return f'LT+{pounds}lbs'

    @staticmethod
    def greater_than(pounds):
        return f'GT+{pounds}lbs'


@DefaultEnum(default_value='')
class Country(_EnumBase):
    International = 'International'


@DefaultEnum(default_value='')
class College(_EnumBase):
    HighSchool = 'High School'
    NoCollege = 'None'


@DefaultEnum(default_value='')
class DraftYear(_EnumBase):
    pass


@DefaultEnum(default_value='')
class DraftPick(_EnumBase):
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

@DefaultEnum(default_member='DATE', api_name='Sorter')
class Sorter(_EnumBase):
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


@DefaultEnum(default_member='DESC', api_name='Direction')
class SortDirection(_EnumBase):
    DESC = 'DESC'
    ASC = 'ASC'


@DefaultEnum(default_value=1000, api_name='Counter')
class NBACounter(_EnumBase):
    pass
