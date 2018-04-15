import numpy as np
import pandas as pd
from . import params

def season_id(df):
    """Extract season and season type from a box score season ID."""
    df['season'] = df['SEASON_ID'].apply(
        lambda id: params.Season.season_from_id(id).start_year
    )
    df['season_type'] = df['SEASON_ID'].apply(
        lambda id: params.SeasonType.season_type_from_id(id).attr_abbr
    )
    df = df.drop(columns=['SEASON_ID'])
    return df

def matchup(df):
    """Add more useful columns based upon matchup information."""
    df['home_road'] = np.where(df['MATCHUP'].str.contains('@'), 'R', 'H')
    df['opp_team_abbr'] = df['MATCHUP'].str.split(' ').str.get(-1)
    df = df.drop(columns=['MATCHUP'])
    return df

def order_columns(df, *, first_cols, last_cols=None):
    """Reorder DataFrame columns by first/middle/last grouping."""
    if last_cols:
        middle_cols = [col for col in df
                            if col not in set().union(first_cols, last_cols)]
    else:
        middle_cols = []
        last_cols = [col for col in df if col not in first_cols]
    return df[(first_cols + middle_cols + last_cols)]
