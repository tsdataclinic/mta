import argparse
import dateutil
import pandas as pd
import requests
import time
import xml.etree.ElementTree as ET
import os
import tempfile

from datetime import datetime, timezone
from pathlib import Path
from google.cloud import storage

class OutageDownloader:
    def __init__(self, output_path, bucket_name=None):

        self._tz = dateutil.tz.gettz('America/New_York')
        outputs = output_path.split(":")
        if outputs[0] == "gcs":
            self.output_base = outputs[1]
            self.write_to_gcs = True
            self.bucket_name = bucket_name
            self.gcs_client = storage.Client()
            self.gcs_bucket = self.gcs_client.bucket(bucket_name)
        else:
            self.output_base = outputs[0]
            self.write_to_gcs = False

    def get_dir_for_timestamp(self):
        now = datetime.now().astimezone(self._tz)
        date = now.strftime("%Y%m%d")
        hour = now.strftime("%H")
        base_dir = f"{self.output_base}/{date}/{hour}"
        return base_dir

    def write_dataframe(self, df: pd.DataFrame):

        time_str = datetime.now().astimezone(self._tz).strftime("%Y%m%d-%I%M%S")
        base_dir = self.get_dir_for_timestamp()
        Path(base_dir).mkdir(parents=True, exist_ok=True)
        destination = f"{base_dir}/outage_alerts_{time_str}.csv"
        print(destination)
        if self.write_to_gcs:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_file = f"{temp_dir}/tmp.csv"
                df.to_csv(temp_file, index=False)
                blob = self.gcs_bucket.blob(destination)
                blob.upload_from_filename(temp_file)
        else:
            df.to_csv(destination, index=False)


    def run(self):
        response = requests.get(
            'http://web.mta.info/developers/data/nyct/nyct_ene.xml')
        alerts = [n for n in ET.fromstring(response.text) if n.tag == 'outage']
        current_snapshot = pd.DataFrame(
            [{field.tag: field.text for field in alert} for alert in alerts])
        print("fetching data")
        self.write_dataframe(current_snapshot)


def main():
    parser = argparse.ArgumentParser("Outage downloader")
    parser.add_argument("--output_path")
    parser.add_argument("--bucket_name", required=False)
    opts = parser.parse_args()
    downloader = OutageDownloader(opts.output_path, opts.bucket_name)
    downloader.run()


if __name__ == "__main__":
    main()
