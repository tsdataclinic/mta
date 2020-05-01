import bisect
import io
import logging
import numpy as np
import os
import pandas as pd
import re
import requests

from ast import literal_eval
from datetime import datetime, timedelta
from html.parser import HTMLParser
from typing import Dict

# This module provides methods that handles MTA turnstile data


def _process_raw_data(raw_data: pd.DataFrame) -> pd.DataFrame:
    logging.getLogger().info("Cleaning turnstile data")

    # create datetime from DATE and TIME columns
    processed = raw_data.assign(
        datetime=pd.to_datetime(
            raw_data['DATE'] + " " + raw_data['TIME'],
            format="%m/%d/%Y %H:%M:%S"))

    # remove mysterious duplicate index along STATION + UNIT
    processed = processed.groupby(
        ['STATION','LINENAME', 'UNIT', 'SCP', 'datetime']).sum().reset_index()

    processed = processed.set_index(pd.DatetimeIndex(processed.datetime))
    processed.drop(columns=['datetime'], inplace=True)

    # clean up whitespace in the columns
    processed.rename(columns={c: c.strip()
                              for c in processed.columns}, inplace=True)
    
    return processed


def _process_grouped_data(grouped: pd.DataFrame,
                          frequency: str) -> pd.DataFrame:
    # calculate the diff and take the absolute value
    entry_diffs = grouped.ENTRIES.diff()
    exit_diffs = grouped.EXITS.diff()

    # clean up data
    grouped.loc[entry_diffs < 0, 'entry_diffs'] = 0
    grouped.loc[exit_diffs < 0, 'exit_diffs'] = 0
    grouped.loc[entry_diffs > 10000, 'entry_diffs'] = 0
    grouped.loc[entry_diffs > 10000, 'entry_diffs'] = 0

    # restore cumulative data
    cleaned_entries = entry_diffs.cumsum()
    cleaned_exits = entry_diffs.cumsum()

    # assign new columns
    grouped = grouped.assign(
        entry_diffs=entry_diffs,
        exit_diffs=exit_diffs,
        cleaned_entries=cleaned_entries,
        cleaned_exits=cleaned_exits,
    )

    resampled = grouped.resample(frequency).asfreq()
    interpolated_group = pd.concat([resampled, grouped])
    interpolated_group = interpolated_group.loc[~interpolated_group.index.duplicated(
        keep='first')]
    interpolated_group = interpolated_group.sort_index(ascending=True)
    interpolated_group.cleaned_entries.interpolate(
        method='linear', inplace=True)
    interpolated_group.cleaned_exits.interpolate(method='linear', inplace=True)
    interpolated_group = interpolated_group.assign(
        estimated_entries=interpolated_group.cleaned_entries.diff().round(),
        estimated_exits=interpolated_group.cleaned_exits.diff().round())
    interpolated_group.fillna(method='ffill', inplace=True)
    interpolated_group = interpolated_group.loc[resampled.index]
    interpolated_group.drop(
        columns=[
            "ENTRIES",
            "EXITS",
            "cleaned_entries",
            "cleaned_exits"],
        inplace=True)
    return interpolated_group


def _interpolate(intervalized_data: pd.DataFrame,
                 frequency: str) -> pd.DataFrame:
    logging.getLogger().info("Start interpolating turnstile data")

    interpolated = []
    intervalized_data.groupby(['UNIT', 'SCP']).apply(
        lambda g: interpolated.append(_process_grouped_data(g, frequency)))
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
            lower = max(
                0, lower - 1) if keys[lower] == self.start_date else lower
        else:
            lower = 0

        upper = len(keys) - 1
        if self.end_date:
            upper = bisect.bisect_right(keys, self.end_date)
            if upper != len(keys):
                upper = min(len(keys) - 1, upper +
                            1) if keys[upper] == self.end_date else upper
            else:
                upper = len(keys) - 1
        return [r[1] for r in self.links[lower:upper + 1]]


def download_turnstile_data(start_date: datetime,
                            end_date: datetime = None) -> pd.DataFrame:
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
    dfs = [
        pd.read_csv(
            io.StringIO(
                requests.get(
                    mta_link_rook +
                    l).content.decode('utf-8'))) for l in parser.get_all_links()]
    return pd.concat(dfs)


def create_interpolated_turnstile_data(
        start_date: datetime,
        end_date: datetime = None,
        frequency: str = '1H') -> pd.DataFrame:
    """
    Create interpolated turnstile data

    Raw turnstile data is downloaded from http://web.mta.info/developers/turnstile.html
    For each turnstile unit, the differences of ENTRIES/EXITS are taken between two snapshots
    and large difference (>= 10000) and negative values are set to zero.
    The cleaned data is linearly interpolated using the frequency provided

    Parameters
    start_date : datetime
    end_date : datetime, optional
    frequency: str, optional

    Returns
    dataframe
    [STATION: str,
     UNIT: str
     SCP: str
     estimated_entries: int
     estimated_exits: int]

    """
    raw = download_turnstile_data(start_date, end_date)
    raw['date'] = pd.to_datetime(raw.DATE)
    raw = raw[(raw.date <= (end_date + timedelta(1))) & (raw.date >= (start_date - timedelta(1)))]
    raw.drop('date',axis=1,inplace=True)
    
    interpolated = _interpolate(_process_raw_data(raw), frequency)
    end_date = end_date or interpolated.index.max()
    return interpolated[interpolated.index.to_series().between(
        start_date, end_date)] .drop(columns=["entry_diffs", "exit_diffs"])


def aggregate_turnstile_data_by_station(turnstile_data: pd.DataFrame,
                                        output_directory: str = None) -> Dict[str,
                                                                              pd.DataFrame]:
    """
    aggregate turnstile data by station and save to output directory if passed.

    Parameters
    turnstile_data: pandas.DataFram
    output_directory: str, optional - If specified, the data by station will be saved under the specified directory.


    Return
    dict[station_name:str, station_turnstile_data: pd.DataFrame] will be returned.

    """

    aggregated_by_station = turnstile_data.groupby(
        ['datetime', 'STATION','LINENAME']).sum().reset_index()
    turnstile_by_station = {
        re.sub(
            r"\s+",
            '_',
            re.sub(
                r"[/|-]",
                " ",
                '_'.join(station))) + 
        ".csv": df for (
            station,
            df) in aggregated_by_station.groupby(
            ['STATION','LINENAME'])}
    if output_directory:
        if not os.path.exists(output_directory):
            os.mkdir(output_directory)
        for key in turnstile_by_station:
            d = turnstile_by_station[key]
            d.to_csv(
                os.path.join(
                    output_directory.strip('/'),
                    '/') + key,
                index=False)
    return turnstile_by_station
