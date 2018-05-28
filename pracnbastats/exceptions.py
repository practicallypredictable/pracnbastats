"""Exception types raised by this package"""


class NBAStatsException(Exception):
    """Base class for all exceptions raised by this package"""
    pass


class NBAStatsValueException(NBAStatsException, ValueError):
    """An erroneous value was encountered"""
    pass


class NBAStatsTypeException(NBAStatsException, TypeError):
    """An erroneous type was encountered"""
    pass


class ExternalException(NBAStatsException):
    """Wraps exceptions from external packages called from this package"""
    def __init__(self, msg, original_exception):
        super().__init__(f'{msg}: {original_exception}')
        self.original_exception = original_exception


class ParamValueException(NBAStatsValueException):
    """Erroneous value for NBA stats API parameters"""
    pass


class TableValueException(NBAStatsValueException):
    """Erroneous value encountered in creating a Table"""
    pass


class ScrapeJSONException(NBAStatsException):
    """Error parsing JSON from NBA stats API response"""
    pass
