from datetime import datetime
from enum import Enum
from pathlib import Path
import shutil
import pandas as pd

class FileFormat(Enum):
    CSV = '.csv'
    PKL = '.pkl'
    HDF5 = '.hdf5'

    @classmethod
    def default(cls):
        return cls.CSV

class FileHandler():

    _FILE_PREFIX = 'pracnbastats-'

    def __init__(self, data_dir, file_type=FileFormat.default(), overwrite=False):
        self._dir = data_dir
        self._file_type = file_type
        self._overwrite = overwrite

    @property
    def dir(self):
        return self._dir

    @property
    def file_type(self):
        return self._file_type

    @property
    def overwrite(self):
        return self._overwrite

    @overwrite.setter
    def overwrite(self, on):
        self._overwrite = on

    def load(self, scraper, tablename, params=None):
        suffix = self.file_type.value
        filename = self._FILE_PREFIX + tablename
        if params:
            for attr_abbr in FileHandler._get_attr_abbrs(params):
                filename += f'-{attr_abbr}'
        filename += suffix
        f = self._dir.joinpath(filename)
        if f.exists() and not self._overwrite:
            data = self._load_data(f)
        else:
            data = scraper()
            if f.exists() and self._overwrite:
                self._backup(f)
            self._write_data(f, data)
        return data

    def _load_data(self, f):
        if self.file_type == FileFormat.HDF5:
            raise ValueError('unimplemented file type', self.file_type)
        elif self.file_type == FileFormat.CSV:
            data = pd.read_csv(f)
        elif self.file_type == FileFormat.PKL:
            data = pd.read_pickle(f)
        else:
            raise ValueError('unimplemented file type', self.file_type)
        return data

    def _write_data(self, f, data):
        if self.file_type == FileFormat.HDF5:
            raise ValueError('unimplemented file type', self.file_type)
        elif self.file_type == FileFormat.CSV:
            data.to_csv(f, index=False, na_rep='NaN', float_format='%.4f')
        elif self.file_type == FileFormat.PKL:
            raise ValueError('unimplemented file type')
        else:
            raise ValueError('unimplemented file type', self.file_type)

    def save_as(self, data, tablename, new_file_type, params=None):
        suffix = self.new_file_type.value
        filename = self._FILE_PREFIX + tablename
        if params:
            for attr_abbr in FileHandler._get_attr_abbrs(params):
                filename += f'-{attr_abbr}'
        filename += suffix
        f = self._dir.joinpath(filename)
        if f.exists():
            self._backup(f)
        self._write_data(f, data)

    @staticmethod
    def _get_attr_abbrs(params):
        attr_abbrs = []
        params_needing_mods = [
            'Season',
            'SeasonType',
            'MeasureType',
            'Period',
        ]
        for param in params_needing_mods:
            value = params.get(param)
            if value:
                attr_abbrs.append(value.attr_abbr)
        return attr_abbrs

    def _backup(self, file):
        filename = str(file)
        timestamp = datetime.now().isoformat().replace(':', '-')
        backup_filename = filename + f'.{timestamp}.bak'
        try:
            shutil.copy(filename, backup_filename)
        except Exception as e:
            print('cannot create backup for', filename)
            raise
