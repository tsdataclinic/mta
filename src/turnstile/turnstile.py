import bisect
import io
import logging
import numpy as np
import os
import pandas as pd
import re
import requests

from ast import literal_eval
from datetime import datetime
from html.parser import HTMLParser
from typing import Dict

# This module provides methods that handles MTA turnstile data

def _process_raw_data(raw_data: pd.DataFrame) -> pd.DataFrame:
    logging.getLogger().info("Cleaning turnstile data")

    # create datetime from DATE and TIME columns
    processed = raw_data.assign(datetime=pd.to_datetime(raw_data['DATE'] + " " + raw_data['TIME']))

    # remove mysterious duplicate index along STATION + UNIT
    processed = processed.groupby(['STATION', 'UNIT', 'SCP', 'datetime']).sum().reset_index()

    processed = processed.set_index(pd.DatetimeIndex(processed.datetime))
    processed.drop(columns=['datetime'], inplace=True)

    # clean up whitespace in the columns
    processed.rename(columns={c : c.strip() for c in processed.columns}, inplace=True)

    return processed


def _process_grouped_data(grouped: pd.DataFrame):
    # calculate the diff and take the absolute value
    entry_diffs =grouped.ENTRIES.diff()
    exit_diffs = grouped.EXITS.diff()
    entry_diffs_abs = entry_diffs.abs()
    exit_diffs_abs = exit_diffs.abs()

    # more clean up

    # restore cumulative data
    cleaned_entries = entry_diffs_abs.cumsum()
    cleaned_exits = exit_diffs_abs.cumsum()

    # assign new columns
    grouped = grouped.assign(
        entry_diffs=entry_diffs,
        exit_diffs=exit_diffs,
        entry_diffs_abs=entry_diffs_abs,
        exit_diffs_abs=exit_diffs_abs,
        cleaned_entries=cleaned_entries,
        cleaned_exits=cleaned_exits,
    )

    # cleaned.reset_index(inplace=True)
    hourly_sampled = grouped.resample('1H').asfreq()
    interpolated_group = pd.concat([hourly_sampled, grouped])
    interpolated_group = interpolated_group.loc[~interpolated_group.index.duplicated(keep='first')]
    interpolated_group = interpolated_group.sort_index(ascending=True)
    interpolated_group.cleaned_entries.interpolate(method='linear', inplace=True)
    interpolated_group.cleaned_exits.interpolate(method='linear', inplace=True)
    interpolated_group = interpolated_group.assign(
        cleaned_entries_diff=interpolated_group.cleaned_entries.diff().round(), \
        cleaned_exists_diff=interpolated_group.cleaned_exits.diff().round())
    interpolated_group.fillna   (method='ffill', inplace=True)
    interpolated_group = interpolated_group.loc[hourly_sampled.index]
    return interpolated_group


def _interpolate(intervalized_data: pd.DataFrame) -> pd.DataFrame:
    logging.getLogger().info("Start creating hourly turnstile data")

    interpolated = []
    intervalized_data.groupby(['UNIT', 'SCP']).apply(lambda g: interpolated.append(_process_grouped_data(g)))
    logging.getLogger().info("Finish interpolating")
    result = pd.concat(interpolated)
    logging.getLogger().info("Finish concatenating the result")

    return result


class TurnstilePageParser(HTMLParser):
    def __init__(self, start_date, end_date=None):
        super().__init__()
        self.start_date = start_date
        self.end_date = end_date
        self.href = False
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
           for name, value in attrs:
               if name == "href":
                   self.href = True
                   self.link = value

    def handle_endtag(self, tag):
        if tag == "a":
            self.href = False

    def handle_data(self, data):
        if self.href:
            try:
                d = datetime.strptime(data.strip(), '%A, %B %d, %Y')
            except ValueError:
                pass
            else:
                self.links.append((d, self.link))

    def get_all_links(self):
        self.links.sort(key=lambda r: r[0])
        keys = [r[0] for r in self.links]
        lower = bisect.bisect_left(keys, self.start_date)
        if lower != len(keys):
            lower = max(0, lower - 1) if keys[lower] == self.start_date else lower
        else:
            lower = 0

        upper = len(keys) - 1
        if self.end_date:
            upper = bisect.bisect_right(keys, self.end_date)
            if upper != len(keys):
                upper = min(len(keys) - 1, upper + 1) if keys[upper] == self.end_date else upper
            else:
                upper = len(keys) - 1
        return [r[1] for r in self.links[lower:upper+1]]


def download_turnstile_data(start_date: datetime, end_date: datetime=None) -> pd.DataFrame:
    """
    Download raw turnstile data from http://web.mta.info/developers/turnstile.html

    Parameters
    start_date: datatime
    end_date: datetime, optional

    Return
    pandas.DataFrame

    """
    logging.getLogger().info("Downloading turnstile data")
    mta_link_rook = 'http://web.mta.info/developers/'
    start_page = requests.get(mta_link_rook + 'turnstile.html')
    parser = TurnstilePageParser(start_date, end_date)
    parser.feed(start_page.content.decode('utf-8'))
    print(parser.get_all_links())
    dfs = [pd.read_csv(io.StringIO(requests.get(mta_link_rook + l).content.decode('utf-8'))) for l in parser.get_all_links()]
    return pd.concat(dfs)


def get_hourly_turnstile_data(start_date: datetime, end_date=None) -> pd.DataFrame:
    """
    Get hourly turnstile data

    Raw turnstile data is downloaded from http://web.mta.info/developers/turnstile.html
    For each turnstile unit, the differences of ENTRIES/EXITS are taken between two snapshots
    and negative values are excluded.
    The cleaned data is linearly interpolated to generate hourly turnstile usage

    Parameters
    start_date : datetime
    end_date : datetime, optional

    Returns
    dataframe
    [STATION: str,
     UNIT: str
     SCP: str
     ENTRIES: int
     EXITS: int
     cleaned_entries: int
     cleaned_exits: int
     cleaned_entries_diff: int
     cleaned_exists_diff: int]

    """
    raw = download_turnstile_data(start_date, end_date)
    interpolated = _interpolate(_process_raw_data(raw))
    end_date = end_date or interpolated.index.max()
    return interpolated[interpolated.index.to_series().between(start_date, end_date)] \
        .drop(columns=["entry_diffs", "exit_diffs", "entry_diffs_abs", "exit_diffs_abs"])


def split_turnstile_data_by_station(turnstile_data: pd.DataFrame, station_turnstile_file_path: str, output=False) \
    -> Dict[str, pd.DataFrame]:

    """
    Split turnstile data by station and save to output directory if passed.

    Parameters
    turnstile_data: pandas.DataFram
    station_turnstile_file_path: str
    output: str

    Return
    dict[station_name:str, station_turnstile_data: pd.DataFrame]

    """

    equipment = pd.read_csv(station_turnstile_file_path)
    equipment.remote = equipment.remote.apply(lambda x: literal_eval(str(x)))
    lst_col = 'remote'
    mapping = pd.DataFrame({col:np.repeat(equipment[col].values, equipment[lst_col].str.len())
                    for col in equipment.columns.difference([lst_col])}).assign(
                        **{lst_col:np.concatenate(equipment[lst_col].values)})[equipment.columns.tolist()]
    mapping.drop(columns = ['Unnamed: 0'], inplace=True)
    aggregated = turnstile_data.groupby(['datetime', 'STATION', 'UNIT']).sum().reset_index()
    merged = aggregated.merge(mapping, how='left', left_on=['UNIT'], right_on=[lst_col])
    turnstile_by_station = {re.sub(r"\s+", '_', re.sub(r"[/|-]", " ", station)) + ".csv": df \
                             for (station, df) in merged.groupby(['station_name'])}
    if not output:
        return turnstile_by_station
    else:
        if not os.path.exists(output):
                os.mkdir(output)
        for key in turnstile_by_station:
            d = turnstile_by_station[key]
            d.to_csv(output.strip('/')+'/'+key,index=False)
