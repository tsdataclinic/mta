import argparse
import datetime
import numpy as np
import os
import pandas as pd

from ast import literal_eval

from process_turnstile import clean_turnstile_data
from load_data_util import cache


@cache("../data/cache/hourly_outage.pkl.gz")
def generate_hourly_outage(outages: pd.DataFrame) -> pd.DataFrame:
    '''
    Create hourly outage percentage data for each outage in the input
    '''
    print("Generate hourly outgage...")
    outages['Outage start'] = pd.to_datetime(outages['Date'], format='%Y-%m-%d %H:%M:%S')
    outages['Outage end'] = pd.to_datetime(outages['next_alert_time'], format='%Y-%m-%d %H:%M:%S')
    results = []
    for i, row in outages.iterrows():
        start = row['Outage start']
        end = row['Outage end']
        t = start
        while t <= end:
            outage_percentage = 0
            if t.hour == start.hour:
                outage_percentage = (t.ceil('H') - t).total_seconds() / 3600
            elif t.hour == end.hour:
                outage_percentage = (t - t.floor('H')).total_seconds() / 3600
            else:
                outage_percentage = 1.0
            results.append([t.floor('H'), outage_percentage, row['equipment_no_from_message'], row['planned_outage'],
                            row['station_name'], row['equipment_type']])
            t += datetime.timedelta(hours=1)
    return pd.DataFrame(results, columns=['Time', 'Percentage', "Equipment Number", 'Planned Outage',
                                         'Station Name', 'Equipment Type'])


def process_subway_turnstile(equipments: pd.DataFrame) -> pd.DataFrame:
    '''
    Split remotes in the raw equipment data
    '''
    print("Processing subway turnstile data...")
    equipments.remote = equipments.remote.apply(lambda x: literal_eval(str(x)))
    lst_col = 'remote'
    subway_turnstile = pd.DataFrame({col:np.repeat(equipments[col].values, equipments[lst_col].str.len())
                  for col in equipments.columns.difference([lst_col])}).assign(
                      **{lst_col:np.concatenate(equipments[lst_col].values)})[equipments.columns.tolist()]
    subway_turnstile.drop(columns = ['Unnamed: 0'], inplace=True)
    return subway_turnstile


def _interpolate(data):
    augmented = data.resample('1H').asfreq()
    augmented.ENTRIES.interpolate(method='linear', inplace=True)
    augmented.EXITS.interpolate(method='linear', inplace=True)
    augmented.fillna(method='ffill', inplace=True)
    return augmented


@cache("../data/cache/interpolated_turnstile.pkl.gz")
def interpolate_turnstile_usage(turnstile_usage: pd.DataFrame, subway_turnstile: pd.DataFrame) -> pd.DataFrame:
    '''
    Interploate turnstile entries/exists into hourly data
    '''
    print("Interpolate turnstile data...")
    filtered_turnstile = turnstile_usage.loc[(turnstile_usage.ENTRIES > 0)
                                    & (turnstile_usage.EXITS > 0)]
                                    #& (turnstile_usage.UNIT.isin(subway_turnstile.remote.unique()))]
    filtered_turnstile.reset_index(inplace=True)
    filtered_turnstile = filtered_turnstile.groupby(['LINENAME', 'STATION', 'UNIT', 'SCP', 'datetime']).sum().reset_index()
    filtered_turnstile.set_index(pd.DatetimeIndex(filtered_turnstile.datetime), inplace=True)
    results = []
    filtered_turnstile.groupby(['LINENAME', 'STATION', 'UNIT', 'SCP']).apply(lambda g: results.append(_interpolate(g)))
    result = pd.concat(results)
    result.drop(columns=['datetime'], inplace=True)
    return result


def join_outage_with_turnstile(outage: pd.DataFrame, subway_turnstile:
    pd.DataFrame, turnstile_usage: pd.DataFrame) -> pd.DataFrame:
    '''
    Join houlry ourtage data with hourly turnstile
    '''
    print("Joining turnstile with outage...")
    interpolated_grps = turnstile_usage.reset_index().groupby(['UNIT','datetime']).sum()[['entry_diff_abs','exit_diff_abs']]
    interpolated_grps.reset_index(inplace=True)
    joined = interpolated_grps.merge(subway_turnstile,how="outer",left_on=['UNIT'],right_on=['remote'])
    joined = joined.merge(outage,how='left',left_on=["equipment_id","datetime"],right_on=["Equipment Number","Time"])
    joined[['Percentage']] = joined[['Percentage']].fillna(value=0)

    return joined[['datetime','UNIT','equipment_id','station_name','Percentage','entry_diff_abs','exit_diff_abs','Planned Outage','subway_lines']]


def get_data_path(data_root, data_path):
    return os.path.join(data_root, data_path)


def load_turnstile_data(data_root, turnstile_data):
    dfs = []
    for t in turnstile_data:
        dfs.append(pd.read_pickle(get_data_path(data_root, t)))

    return pd.concat(dfs)


def main():
    parser = argparse.ArgumentParser("Turnstile data")
    parser.add_argument("--data_root", required=True)
    parser.add_argument("--outage_data",  required=True)
    parser.add_argument("--equipment_data",  required=True)
    parser.add_argument("--turnstile_data", nargs="+",  required=True)
    parser.add_argument("--output",  required=True)

    opts = parser.parse_args()

    outage = generate_hourly_outage(pd.read_csv(get_data_path(opts.data_root, opts.outage_data)))
#     outage.to_pickle(get_data_path(opts.data_root, 'processed/hourly_outages.pkl.gz'),compression='gzip')
    subway_turnstile = process_subway_turnstile(pd.read_csv(get_data_path(opts.data_root, opts.equipment_data)))

    print("Loading turnstile data...")
    turnstile_data = clean_turnstile_data(load_turnstile_data(opts.data_root, opts.turnstile_data))

    interpolated_turnstile_data = interpolate_turnstile_usage(turnstile_data, subway_turnstile)
#     interpolated_turnstile_data.to_pickle(get_data_path(opts.data_root, 'processed/interpolated_data.pkl.gz'),compression='gzip')
    joined_data = join_outage_with_turnstile(outage, subway_turnstile, interpolated_turnstile_data)
    print("Saving results...")
    print(joined_data.shape)
    joined_data.to_pickle(get_data_path(opts.data_root, opts.output),compression='gzip')


if __name__ == "__main__":
    main()

### sample command

# python data/combine_turnstile_outage.py --data_root "/content/jupyter/mta-accessibility/data" --outage_data "processed/2019_outages.csv.gz" --equipment_data "interim/crosswalks/ee_turnstile.csv" --turnstile_data #"processed/turnstile_2019.pkl.gz" "processed/turnstile_data_2019_nov_dec.pkl.gz" --output "processed/turnstile_with_outage.pkl.gz"

####