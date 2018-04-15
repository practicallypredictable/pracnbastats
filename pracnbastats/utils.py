from collections import namedtuple, OrderedDict
import numpy as np
import pandas as pd

def convert_tuple(to_tuple, from_tuple):
    """Converts one namedtuple type to another."""
    from_dict = from_tuple._asdict()
    fields = OrderedDict((key, from_dict[key]) for key in to_tuple._fields)
    return to_tuple(**fields)

def as_tuples(df, to_tuple, index=False):
    """DataFrame rows as iterable of namedtuples of a given type."""
    for row in df.itertuples(index=index):
        yield convert_tuple(to_tuple, row)

def select_row(df, **kwargs):
    """Get a row from a DataFrame based upon a field value."""
    if len(kwargs) > 1:
        raise ValueError('only one keyword argument permitted')
    key = list(kwargs)[0]
    value = kwargs[key]
    row = df.copy()[df[key] == value]
    if len(row) > 1:
        raise ValueError(f'key {key} does not return a unique row')
    return row

def select_row_as_tuple(df, to_tuple, index=False, **kwargs):
    """Get a row from a DataFrame based upon a field value, return as namedtuple."""
    row = select_row(df, **kwargs)
    return list(as_tuples(row, to_tuple, index))[0]

def chunkify(df, chunk_size):
    """Split a DataFrame by rows into chunks of a given size."""
    rows = df.shape[0]
    df = df.copy()
    print(rows)
    split_points = range(
        chunk_size,
        (rows // chunk_size + 1) * chunk_size,
        chunk_size
    )
    print(split_points)
    return np.split(df, split_points)
