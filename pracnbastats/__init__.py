"""Scrape and process NBA basketball information from stats.nba.com

"""

from . import params
from .scrape import NBAStatsRequests, NBAStats
from .store import FileFormat, FileHandler
from . import utils
from . import allplayers
from . import currentteams
from . import player
from . import team
from . import league
from . import playtype
