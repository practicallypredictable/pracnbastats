from collections import OrderedDict
import logging
import requests
import pandas as pd
from . import params
from . import exceptions

log = logging.getLogger(__name__)


class NBASession():
    DEFAULT_BASE_URL = 'http://stats.nba.com/stats'
    DEFAULT_REFERER = 'scores'
    DEFAULT_TIMEOUT = 10
    REQUEST_HEADERS = {
        'dnt': '1',
        'accept-encoding': 'gzip, deflate, sdch',
        'accept-language': 'en',
        'origin': 'http://stats.nba.com',
        'cache-control': 'max-age=0',
        'connection': 'keep-alive',
    }

    def __init__(self, *, user_agent, referer=DEFAULT_REFERER):
        self._headers = NBASession.REQUEST_HEADERS
        self._headers['user-agent'] = user_agent
        self._headers['referer'] = referer

    def get(self, *,
            base_url=None, api_endpoint, headers=None, api_params=None,
            allow_redirects=False, timeout=DEFAULT_TIMEOUT):
        if not base_url:
            base_url = NBASession.DEFAULT_BASE_URL
        url = f'{base_url}/{api_endpoint}'
        if not headers:
            headers = self._headers
        if isinstance(api_params, params.Arguments):
            api_params = api_params.for_request
        try:
            response = requests.get(
                url,
                headers=headers,
                params=api_params,
                allow_redirects=allow_redirects,
                timeout=timeout,
            )
        except requests.exceptions.RequestException as e:
            raise exceptions.ExternalException(
                msg='call to requests failed',
                original_exception=e,
            )
        return response

    def records(self, *, api_endpoint, api_params=None, index=0):
        response = self.get(
            api_endpoint=api_endpoint,
            api_params=api_params.for_request,
        )
        json = response.json()
        return NBASession.process_json(json, index)

    @staticmethod
    def process_json(json, index=0):
        """Process JSON from stats.nba.com and return list of dicts."""
        if 'resultSets' in json.keys():
            results = 'resultSets'
        elif 'resultSet' in json.keys():
            results = 'resultSet'
        else:
            msg = f'cannot find results in {json.keys()}'
            raise exceptions.ScrapeJSONException(msg)
        try:
            headers = NBASession._headers(json[results][index]['headers'])
            rows = json[results][index]['rowSet']
        except KeyError:
            headers = NBASession._headers(json[results]['headers'])
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
                    cols.append(f'{bottom_cols[k]}{sep}{top}')
            return cols
        else:
            raise ValueError('more than two header rows?', rows)


class NBAScraper():
    def __init__(self, *, session, store, force_reload=False, archive=True):
        self._session = session
        self._store = store
        self._force_reload = force_reload
        self._archive = archive

    @property
    def session(self):
        return self._session

    @property
    def store(self):
        return self._store

    @property
    def force_reload(self):
        return self._force_reload

    @force_reload.setter
    def force_reload(self, value):
        self._force_reload = value

    @property
    def archive(self):
        return self._archive

    @archive.setter
    def archive(self, value):
        self._archive = value

    def get(self, *, api_endpoint, api_params=None, index=0):
        records = self.session.records(
            api_endpoint=api_endpoint,
            api_params=api_params,
            index=index,
        )
        if isinstance(records, list):
            df = pd.DataFrame(records)
        else:
            df = pd.DataFrame(list(records))
        return df

    def load(self, *, table):
        if not self.force_reload and self.store and table.exists(self.store):
            df = table.load(self.store)
        else:
            df = self.get(
                api_endpoint=table.api_endpoint,
                api_params=table.api_params,
                index=table.index,
            )
        if self.store and (self.force_reload or not table.exists(self.store)):
            table.save(store=self.store, data=df, archive=self.archive)
        return df

    def load_pipeline(self, *, table, pipeline):
        if not self.force_reload and self.store and table.exists(self.store):
            df = table.load(self.store)
        else:
            funcs = iter(pipeline)
            func = next(funcs)
            df = func(self.session)
            for func in funcs:
                df = func(df, self.session)
            if self.store:
                table.save(store=self.store, data=df, archive=self.archive)
        return df


class NBAStats():
    def __init__(self, *, scraper, table):
        self._scraper = scraper
        self._table = table
        self._data = self.scraper.load(
            table=table,
        )

    @property
    def scraper(self):
        return self._scraper

    @property
    def table(self):
        return self._table

    @property
    def api_endpoint(self):
        return self.table.api_endpoint

    @property
    def api_params(self):
        return self.table.api_params

    @property
    def request_params(self):
        return self.table.api_params.sorted_by_key()

    @property
    def index(self):
        return self.table.index

    @property
    def data(self):
        return self._data
