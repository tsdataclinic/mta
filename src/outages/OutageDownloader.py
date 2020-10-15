import dateutil
import pandas as pd
import requests
import time
import xml.etree.ElementTree as ET
import os

from datetime import datetime, timezone
from google.cloud import storage

class OutageDownloader:
    def __init__(self, data_dir=None, bucket_name=None, frequency: int):
        self._frequency = frequency
        
        self._tz = dateutil.tz.gettz('America/New_York')
        os.makedirs(data_dir, exist_ok=True)
        self.data_dir = data_dir
        self.bucket_name = bucket_name
    
    def get_dir_for_timestamp(self):
        now = datetime.now().astimezone(self._tz)
        date = now.strftime("%Y%m%d")
        hour = now.strftime("%H")        
        base_dir = f"raw_data/{date}/{hour}"        
        return base_dir
    
    def write_dataframe_to_gcs(self, df: pd.DataFrame, blob_path: str):
        temp_path = "tmp.csv"
        try:
            df.to_csv(temp_path)
            blob = self.gcs_bucket.blob(blob_path)
            blob.upload_from_filename(temp_path)
        finally:
            os.remove(temp_path)
   
    def run(self):
        response = requests.get(
            'http://web.mta.info/developers/data/nyct/nyct_ene.xml')
        alerts = [n for n in ET.fromstring(response.text) if n.tag == 'outage']
        current_snapshot = pd.DataFrame(
            [{field.tag: field.text for field in alert} for alert in alerts])
        
        time_str = datetime.now().astimezone(self._tz).strftime("%Y%m%d-%I%M%S")
        base_dir = self.get_dir_for_timestamp()
        os.makedirs(base_dir, exist_ok=True)
        file_path = f"{base_dir}/outage_alerts_{time_str}.csv"
        self.write_dataframe_to_gcs(current_snapshot, file_path)


def main():
    downloader = OutageDownloader(opts.output, opts.frequency, opts.end_time)
    downloader.run()


if __name__ == "__main__":
    main()
