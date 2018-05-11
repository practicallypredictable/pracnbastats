"""Scrape and process NBA basketball information from stats.nba.com

"""

# Use tqdm progress bar package (https://pypi.org/project/tqdm/)
# This is a soft dependency; define harmless fallback if cannot import tqdm
try:
    from tqdm import tqdm
except ImportError:
    def tqdm(*args, **kwargs):
        if args:
            return args[0]
        return kwargs.get('iterable', None)

from . import currentteams  # noqa: F401
from . import teamhistory  # noqa: F401
from . import allplayers  # noqa: F401
from . import league  # noqa: F401
from . import team  # noqa: F401
from . import player  # noqa: F401
from . import params  # noqa: F401
from . import scrape  # noqa: F401
from . import store  # noqa: F401
from . import table  # noqa: F401
from . import utils  # noqa: F401
from . import exceptions  # noqa: F401

import logging
log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

__title__ = 'pracnbastats'
__url__ = 'https://github.com/practicallypredictable/pracnbastats'
__status__ = 'Development Status :: 3 - Alpha'
__version__ = '0.1.2'
__author__ = 'Practically Predictable'
__author_email__ = 'practicallypredictable@practicallypredictable.com'
__license__ = 'License :: OSI Approved :: MIT License'
__copyright__ = 'Copyright 2018 Practically Predictable'
