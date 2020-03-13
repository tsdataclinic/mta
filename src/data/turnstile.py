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

def _cleanup_raw_data(raw_data: pd.DataFrame) -> pd.DataFrame:
    logging.getLogger().info("Cleaning turnstile data")

    # create datetime from DATE and TIME columns
    cleaned = raw_data.assign(datetime=pd.to_datetime(raw_data['DATE'] + " " + raw_data['TIME']))
    cleaned = cleaned.set_index('datetime').sort_index()

    # clean up whitespace in the columns
    cleaned.rename(inplace=True, columns={c : c.strip() for c in cleaned.columns})

    # calculate the diff
    entry_diffs = cleaned.groupby(['UNIT','SCP'],as_index=False)['ENTRIES'].transform(pd.Series.diff)['ENTRIES']
    exit_diffs = cleaned.groupby(['UNIT','SCP'],as_index=False)['EXITS'].transform(pd.Series.diff)['EXITS']

    # more clean up

    # Get absolute value
    cleaned = cleaned.assign(cleaned_entries=entry_diffs.abs().cumsum(), cleaned_exits=exit_diffs.abs().cumsum())

    cleaned.reset_index(inplace=True)
    return cleaned

def _interpolate(raw_data: pd.DataFrame) -> pd.DataFrame:
    logging.getLogger().info("Interplating turnstile data")

    grouped = raw_data.groupby(['UNIT', 'SCP', 'datetime']).sum().reset_index()
    grouped.set_index(pd.DatetimeIndex(grouped.datetime), inplace=True)
    interpolated = []
    for _, group in grouped.groupby(['UNIT', 'SCP']):
        hourly_sampled = group.resample('1H').asfreq()
        interpolated_group = pd.concat([hourly_sampled, group])
        interpolated_group = interpolated_group.sort_index(ascending=True)
        interpolated_group.cleaned_entries.interpolate(method='linear', inplace=True)
        interpolated_group.cleaned_exits.interpolate(method='linear', inplace=True)
        interpolated_group = interpolated_group.assign(entries_diff=interpolated_group.cleaned_entries.diff().round(), \
            exists_diff=interpolated_group.cleaned_exits.diff().round())
        interpolated_group.fillna(method='ffill', inplace=True)
        interpolated_group = interpolated_group.loc[hourly_sampled.index]
        interpolated.append(interpolated_group)
    return pd.concat(interpolated)


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
                if self.start_date <= d \
                    and (not self.end_date or self.end_date >= d):
                    self.links.append(self.link)

    def get_all_links(self):
        return self.links


def _download_turnstile_data(start_date, end_date=None):
    mta_link_rook = 'http://web.mta.info/developers/'
    start_page = requests.get(mta_link_rook + 'turnstile.html')
    parser = TurnstilePageParser(start_date, end_date)
    parser.feed(start_page.content.decode('utf-8'))
    dfs = [pd.read_csv(io.StringIO(requests.get(mta_link_rook + l).content.decode('utf-8'))) for l in parser.get_all_links()]
    return pd.concat(dfs)


def process_turnstile_data(start_date: datetime, end_date=None, existed_data: pd.DataFrame=None):
    raw = _download_turnstile_data(start_date, end_date)
    return _interpolate(_cleanup_raw_data(raw))


def create_data_by_station(turnstile_data: pd.DataFrame, output_dir: str):
    equipment = pd.read_csv('../../data/interim/crosswalks/ee_turnstile.csv')
    equipment.remote = equipment.remote.apply(lambda x: literal_eval(str(x)))
    lst_col = 'remote'
    mapping = pd.DataFrame({col:np.repeat(equipment[col].values, equipment[lst_col].str.len())
                    for col in equipment.columns.difference([lst_col])}).assign(
                        **{lst_col:np.concatenate(equipment[lst_col].values)})[equipment.columns.tolist()]
    mapping.drop(columns = ['Unnamed: 0'], inplace=True)
    merged = turnstile_data.merge(mapping, how='left', left_on=['UNIT'], right_on=[lst_col])
    for station, df in merged.groupby(['station_name']):
        file_name = re.sub(r"\s+", '_', re.sub(r"[/|-]", " ", station)) + ".csv"
        df.to_csv(os.path.join(output_dir, file_name))

if __name__ == "__main__":
    pass


