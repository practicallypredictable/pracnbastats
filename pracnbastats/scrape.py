import requests
from time import sleep
from collections import OrderedDict
import pandas as pd

USER_AGENT = (
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) ' +
    'AppleWebKit/537.36 (KHTML, like Gecko) ' +
    'Chrome/61.0.3163.100 Safari/537.36'
)

REQUEST_HEADERS = {
    'user-agent': USER_AGENT,
    'Dnt': '1',
    'Accept-Encoding': 'gzip, deflate, sdch',
    'Accept-Language': 'en',
    'origin': 'http://stats.nba.com',
    'Cache-Control': 'max-age=0',
    'Connection': 'keep-alive',
}

DEFAULT_REFERER = 'scores'
DEFAULT_TIMEOUT = 10

NBA_STATS_BASE_URL = 'http://stats.nba.com/stats'

class NBAStatsRequests():
    def __init__(self,
            base_url=NBA_STATS_BASE_URL,
            headers=REQUEST_HEADERS,
            referer=DEFAULT_REFERER,
            allow_redirects=False,
            timeout=DEFAULT_TIMEOUT):
        self._base_url = base_url
        self._headers = headers
        self._headers['referer'] = referer
        self._allow_redirects = allow_redirects
        self._timeout = timeout

    def get(self, api_endpoint, params):
        url = f'{self._base_url}/{api_endpoint}'
        response = requests.get(
            url,
            headers=self._headers,
            params=params,
            allow_redirects=self._allow_redirects,
            timeout=self._timeout,
        )
        response.raise_for_status()
        return response

DEFAULT_NBA_STATS_REQUESTS = NBAStatsRequests()

class NBAStats():
    def __init__(self, *,
            api_endpoint,
            params=None,
            index=0,
            nba_stats_requests=None,
            filehandler=None,
            tablename=None):
        self._api_endpoint = api_endpoint
        self._params = params
        self._index = index
        if nba_stats_requests:
            self._requests = nba_stats_requests
        else:
            self._requests = DEFAULT_NBA_STATS_REQUESTS
        self._response = None
        if filehandler:
            if not tablename:
                tablename = api_endpoint
            self._scraped = filehandler.load(
                scraper=self._scrape_data,
                tablename=tablename,
                params=self._params,
            )
        else:
            self._scraped = self._scrape_data()

    @property
    def api_endpoint(self):
        return self._api_endpoint

    @property
    def params(self):
        return self._params

    @property
    def request_params(self):
        return self._params.sorted_by_key()

    @property
    def response(self):
        return self._response

    @property
    def url(self):
        return self._response.request.url

    @property
    def scraped(self):
        return self._scraped

    def _scrape_data(self):
        params_for_request = self._params.for_request
        self._response = NBAStats.get_response(
                                self._api_endpoint,
                                params_for_request,
                                self._requests)
        json = self._response.json()
        df = pd.DataFrame(NBAStats.process_json(json, self._index))
        return df

    @staticmethod
    def get(api_endpoint, params_for_request, index=0,
                nba_stats_requests=DEFAULT_NBA_STATS_REQUESTS):
        response = NBAStats.get_response(
                                api_endpoint,
                                params_for_request,
                                nba_stats_requests)
        json = response.json()
        return NBAStats.process_json(json, index)

    @staticmethod
    def get_response(api_endpoint, params_for_request,
                nba_stats_requests=DEFAULT_NBA_STATS_REQUESTS):
        return nba_stats_requests.get(api_endpoint, params_for_request)

    @staticmethod
    def process_json(json, index):
        """Process JSON from stats.nba.com and return list of dicts."""
        if 'resultSets' in json.keys():
            results = 'resultSets'
        elif 'resultSet' in json.keys():
            results = 'resultSet'
        else:
            raise KeyError('cannot find results in:', json.keys())
        try:
            headers = NBAStats._headers(json[results][index]['headers'])
            rows = json[results][index]['rowSet']
        except KeyError:
            headers = NBAStats._headers(json[results]['headers'])
            rows = json[results]['rowSet']
        assert len(headers) == len(rows[0])
        if len(rows) > 1:
            return [OrderedDict(zip(headers, row)) for row in rows]
        elif len(rows) == 1:
            return OrderedDict(zip(headers, rows[0]))
        else:
            return None

    @staticmethod
    def _headers(rows, sep='~'):
        assert isinstance(rows, list)
        if all(isinstance(col, str) for col in rows):
            return rows
        elif len(rows) == 2:
            top_cols = rows[0]['columnNames']
            col_span = rows[0]['columnSpan']
            col_skip = rows[0]['columnsToSkip']
            bottom_cols = rows[1]['columnNames']
            cols = bottom_cols[:col_skip]
            for i, top in enumerate(top_cols):
                for j in range(col_span):
                    k = col_skip + i*col_span + j
                    cols.append(f'{bottom_cols[k]}{sep}{top_cols[i]}')
            return cols
        else:
            raise ValueError('more than two header rows?', rows)
