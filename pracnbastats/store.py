from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
import shutil
import pandas as pd


def _build_filename(prefix, table, suffix):
    if table.store_keys:
        keys = '-'.join(
            f'{key}({value})'
            for key, value in table.store_keys.items()
        )
    else:
        keys = None
    if keys:
        filename = f'{prefix}-{table.api_endpoint}-{keys}.{suffix}'
    else:
        filename = f'{prefix}-{table.api_endpoint}.{suffix}'
    return filename


def _archive(file):
    filename = str(file)
    timestamp = datetime.now().isoformat().replace(':', '-')
    archive_filename = f'{filename}.{timestamp}.bak'
    shutil.copy(filename, archive_filename)


class _StorageBase(ABC):
    """Abstract base class for NBA statistics storage format."""
    def __init__(self, *, path):
        self._path = Path(path)

    @property
    def path(self):
        return self._path

    @abstractmethod
    def locator(self, table, **kwargs):
        pass

    @abstractmethod
    def exists(self, locator, **kwargs):
        pass

    @abstractmethod
    def load(self, locator, **kwargs):
        pass

    @abstractmethod
    def save(self, locator, archive=True, **kwargs):
        pass


class FlatFiles(_StorageBase):
    """Store NBA statistics in one or more flat files."""
    def __init__(self, *, path, suffix, loader, saver):
        self._prefix = 'pracnbastats'
        self._suffix = suffix
        self._loader = loader
        self._saver = saver
        super().__init__(path=path)

    def locator(self, table):
        if table.store_name:
            filename = f'{self._prefix}-{table.store_name}.{self._suffix}'
        else:
            filename = _build_filename(
                prefix=self._prefix,
                table=table,
                suffix=self._suffix
            )
        return self._path.joinpath(filename)

    def exists(self, locator):
        return locator.exists()

    def load(self, locator):
        return self._loader(locator)

    def save(self, locator, data, archive=True):
        if self.exists(locator) and archive:
            _archive(locator)
        self._saver(data, locator)

    @staticmethod
    def _csv_loader(file):
        return pd.read_csv(file)

    @staticmethod
    def _csv_saver(data, file):
        data.to_csv(file, index=False, na_rep='NaN', float_format='%.4f')

    @staticmethod
    def _pkl_loader(file):
        return pd.read_pickle(file)

    @staticmethod
    def _pkl_saver(data, file):
        data.to_pickle(file)

    @classmethod
    def CSV(cls, *, path):
        return cls(
            path=path,
            suffix='csv',
            loader=FlatFiles._csv_loader,
            saver=FlatFiles._csv_saver
        )

    @classmethod
    def Pickle(cls, *, path):
        return cls(
            path=path,
            suffix='pkl',
            loader=FlatFiles._pkl_loader,
            saver=FlatFiles._pkl_saver
        )
