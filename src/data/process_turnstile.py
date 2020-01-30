import pandas as pd
import numpy as np
import os

TURNSTILE_DATA_DIR = '../../data/processed/'

def clean_turnstile_data(turnstile,recache=False,output_path=False):
    '''
    Pulls in raw 2019 turnstile data files and cleans them to get rid of negatives and large outliers. 
    
    TODO: check if already available and don't run is recache is False
    '''
#     t_jan_nov = pd.read_pickle(os.path.join(TURNSTILE_DATA_DIR,'turnstile_2019.pkl.gz'))
#     t_nov_dec = pd.read_pickle(os.path.join(TURNSTILE_DATA_DIR,'turnstile_data_2019_nov_dec.pkl.gz'))
#     turnstile = pd.concat([t_jan_nov,t_nov_dec])

    turnstile = turnstile.set_index('datetime').sort_index()
    entry_diffs = turnstile.groupby(['UNIT','SCP'],as_index=False)['ENTRIES'].transform(pd.Series.diff)['ENTRIES']
    exit_diffs = turnstile.groupby(['UNIT','SCP'],as_index=False)['EXITS'].transform(pd.Series.diff)['EXITS']
    turnstile = turnstile.assign(entry_diff = entry_diffs,exit_diff =exit_diffs)

    turnstile['entry_diff_abs'] = turnstile.entry_diff.abs()
    turnstile['exit_diff_abs'] = turnstile.exit_diff.abs()

    time_diff = turnstile.reset_index().groupby(['UNIT','SCP'],as_index=False)['datetime'].transform(pd.Series.diff)['datetime']

    turnstile['time_diffs'] = time_diff.values/np.timedelta64(1,'h')
    turnstile.entry_diff_abs = [x if y < 4.2 else np.NaN for x,y in zip(turnstile.entry_diff_abs,turnstile.time_diffs)]
    turnstile.exit_diff_abs = [x if y < 4.2 else np.NaN for x,y in zip(turnstile.exit_diff_abs,turnstile.time_diffs)]

    turnstile.entry_diff_abs = [x if x <= 10000 else np.NaN for x in turnstile.entry_diff_abs]
    turnstile.exit_diff_abs = [x if x <= 10000 else np.NaN for x in turnstile.exit_diff_abs]
    
    turnstile.reset_index(inplace=True)
    turnstile = turnstile[(turnstile.datetime >= '2019-01-01') & (turnstile.datetime < '2020-01-01')]
    
    if output_path:
        turnstile.to_pickle(os.path.join(TURNSTILE_DATA_DIR,'cleaned_turnstile_data_2019.pkl.gz'),compression='gzip')
    else:
        return turnstile
    