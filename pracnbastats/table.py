from . import exceptions


class Table():
    def __init__(
            self, *,
            store_name=None, api_endpoint=None, api_params=None, index=0):
        self._api_endpoint = api_endpoint
        self._api_params = api_params
        self._index = index
        if store_name:
            self._store_name = store_name
        elif not self.api_endpoint:
            msg = 'need to specify either store_name or api_endpoint'
            raise exceptions.NBAStatsValueException(msg)
        else:
            self._store_name = None

    def __repr__(self):
        return (
            f'{self.__class__.__name__}(store_name={self.store_name}, '
            f'api_endpoint={self.api_endpoint}, api_params={self.api_params}, '
            f'index={self.index})'
        )

    @property
    def store_name(self):
        return self._store_name

    @property
    def api_endpoint(self):
        return self._api_endpoint

    @property
    def api_params(self):
        return self._api_params

    @property
    def store_keys(self):
        if self.api_params:
            return self.api_params.store_keys
        else:
            return None

    @property
    def index(self):
        return self._index

    def exists(self, store):
        return store.exists(locator=store.locator(table=self))

    def load(self, store):
        return store.load(locator=store.locator(table=self))

    def save(self, *, store, data, archive=True):
        store.save(
            locator=store.locator(table=self),
            data=data,
            archive=archive
        )
