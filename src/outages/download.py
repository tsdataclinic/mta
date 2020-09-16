import argparse
import dateutil
import pandas as pd
import requests
import threading
import time
import xml.etree.ElementTree as ET

from datetime import datetime, timezone
from pathlib import Path


class OutageDownloader:
    def __init__(self, output: str, frequency: int, end_time: str = None):
        self._frequency = frequency
        self._previous_snapshot = None
        self._output = output
        self._tz = dateutil.tz.gettz('America/New_York')
        if end_time:
            self._end_time = datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')
            self._end_time = self._end_time.replace(tzinfo=self._tz)
        else:
            self._end_time = None

    def _record_outages(self, current_snapshot, include_all):
        merged = pd.merge(self._previous_snapshot,
                          current_snapshot[['equipment',
                                            'outagedate',
                                            'estimatedreturntoservice']],
                          on=['equipment',
                              'outagedate'],
                          how='outer')

        # get all outages that have returned to service since last snapshot (rows with null estimatedreturntoservice_y)
        result = merged.loc[merged['estimatedreturntoservice_y'].isnull(), :].copy(deep=True) if not include_all else merged
        result.drop(columns=['estimatedreturntoservice_y'], inplace=True)
        result.rename(
            columns={
                'estimatedreturntoservice_x': 'estimatedreturntoservice'},
            inplace=True)
        current_time = pd.Timestamp.now()

        if not result.empty:
            print(datetime.now(), result)

        # use the current time as the actual return to service time
        result = result.assign(
            actualreturntoservice=current_time,
            duration=current_time-pd.to_datetime(result.outagedate))

        #result['estimatedreturntoservice'] = pd.to_datetime(result['estimatedreturntoservice'])
        #result.loc[result['estimatedreturntoservice'].isnull(), 'estimatedreturntoservice'] = current_time
        #result.loc[result['estimatedreturntoservice'] > current_time, 'estimatedreturntoservice'] = current_time
        existed_result = pd.read_csv(self._output).append(result, sort=False) if Path(self._output).is_file() else result
        existed_result.to_csv(self._output, index=False)

    def run(self):
        response = requests.get(
            'http://web.mta.info/developers/data/nyct/nyct_ene.xml')
        alerts = [n for n in ET.fromstring(response.text) if n.tag == 'outage']
        current_snapshot = pd.DataFrame(
            [{field.tag: field.text for field in alert} for alert in alerts])

        if self._previous_snapshot is not None:
            self._record_outages(current_snapshot, False)

        self._previous_snapshot = current_snapshot

        now = datetime.now().astimezone(self._tz)
        if not self._end_time or self._end_time > now:
            print(f"Taking snapshot at {now}")
            threading.Timer(self._frequency, self.run).start()
        else:
            print(f"Exiting at:{now}, {self._end_time}")
            self._record_outages(current_snapshot, True)


def main():
    parser = argparse.ArgumentParser("Outage downloader")
    parser.add_argument("--frequency", type=int)
    parser.add_argument("--output")
    parser.add_argument("--end_time", default=None)
    opts = parser.parse_args()

    downloader = OutageDownloader(opts.output, opts.frequency, opts.end_time)
    downloader.run()


if __name__ == "__main__":
    main()
