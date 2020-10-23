import argparse
import glob
import pandas as pd
import re

from pathlib import Path


def merge(input_directory, output):
    files = sorted({
        f
        for f in glob.iglob(input_directory + '**/**', recursive=True)
        if Path(f).is_file()
    })
    previous_snapshot = None
    results = []
    for f in files:
        current_snapshot = pd.read_csv(f)
        if previous_snapshot is not None:
            merged = pd.merge(previous_snapshot,
                              current_snapshot[[
                                  'equipment', 'outagedate',
                                  'estimatedreturntoservice'
                              ]],
                              on=['equipment', 'outagedate'],
                              how='outer')

            result = merged.loc[merged['estimatedreturntoservice_y'].isnull(
            ), :].copy(deep=True)
            result.drop(columns=['estimatedreturntoservice_y'], inplace=True)
            result.rename(columns={
                'estimatedreturntoservice_x':
                'estimatedreturntoservice'
            },
                          inplace=True)
            matched_group = re.search(r'(\d{2})/outage_alerts_(\d{8}-\d{6})', f,
                                          re.IGNORECASE).group
            snapshot_time_str = list(matched_group(2))
            snapshot_time_str[9:11] = list(matched_group(1))
            snapshot_time = pd.to_datetime("".join(snapshot_time_str),
                                           format="%Y%m%d-%H%M%S")

            # use the snapshot time as the actual return to service time
            result = result.assign(actualreturntoservice=snapshot_time,
                                   duration=snapshot_time -
                                   pd.to_datetime(result.outagedate),
                                   ongoing_outage=False)
            results.append(result)

        previous_snapshot = current_snapshot
    if previous_snapshot is not None:
        previous_snapshot = previous_snapshot.assign(ongoing_outage=True)
    results.append(previous_snapshot)
    pd.concat(results, sort=False).to_csv(output)


def main():
    parser = argparse.ArgumentParser("Merge snapshots")
    parser.add_argument("--input_directory")
    parser.add_argument("--output")
    opts = parser.parse_args()

    merge(opts.input_directory, opts.output)


if __name__ == "__main__":
    main()
