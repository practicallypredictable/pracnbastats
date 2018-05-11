class NBAStatsException(Exception):
    """Base class for all exceptions raised by this package."""
    pass


class ExternalException(NBAStatsException):
    """Wraps exceptions from external packages called from this package."""
    def __init__(self, msg, original_exception):
        super().__init__(f'{msg}: {original_exception}')
        self.original_exception = original_exception


class ParamValueException(NBAStatsException, ValueError):
    """ValueError in setting up NBA stats API parameters."""
    pass


class TableValueException(NBAStatsException, ValueError):
    """ValueError in setting up a Table."""
    pass


class ScrapeJSONException(NBAStatsException):
    """Error parsing JSON from NBA stats API response."""
    pass
