import argparse
import glob
import pandas as pd
import re
import dateutil
import logging
from pathlib import Path
from google.cloud import storage
import google.cloud.logging
import tempfile
from datetime import datetime, timezone


class MergedFileCreator:
    def __init__(self, bucket_name, run_in_cloud):
        if run_in_cloud:
            self._tz = dateutil.tz.gettz('America/New_York')
            self.bucket_name = bucket_name
            self.gcs_client = storage.Client()
            self.gcs_bucket = self.gcs_client.bucket(bucket_name)
            self.run_in_cloud = run_in_cloud
            client = google.cloud.logging.Client()
            client.get_default_handler()
            client.setup_logging()

    def get_days_with_raw_data(self):
        return list(self.gcs_bucket.list_blobs(prefix='raw_data/'))

    def get_days_with_processed_data(self):
        return list(self.gcs_bucket.list_blobs(prefix='daily/'))

    def get_days_to_process(self):
        days_with_raw_data = self.get_days_with_raw_data()
        days_with_processed_data = self.get_days_with_processed_data()
        unique_to_do = set([d.name.split('/')[1] for d in days_with_raw_data])
        already_done = [file.name.split('_')[1] for file in days_with_processed_data]
        already_done = set([f.split('.')[0] for f in already_done])
        now = datetime.now().astimezone(self._tz)
        today = now.strftime("%Y%m%d")
        days_to_do = unique_to_do - already_done
        days_to_do = list(days_to_do - set([today]))
        days_to_do = list(filter(None, days_to_do)) 
        days_to_do.sort()
        logging.info(f"Daily files to be processed for {days_to_do}")
        return list(days_to_do)

    def process_pending(self):
        days_to_process = self.get_days_to_process()
        if len(days_to_process) > 0:
            for day in days_to_process:
                try:
                    self.merge(date=day)
                except Exception as ex:
                    logging.error(ex)
                    continue

    def merge(self, input_directory='', output='', date=''):
        if self.run_in_cloud:
            logging.info(f"Processing daily outages for {date}")
            raw_files_for_day = list(self.gcs_bucket.list_blobs(prefix=f'raw_data/{date}/'))
            files = [f"gs://{self.bucket_name}/{file.name}" for file in raw_files_for_day]
            files.sort()
        else:
            files = sorted({
                f
                for f in glob.iglob(input_directory + '**/**', recursive=True)
                if Path(f).is_file()
            })

        previous_snapshot = None
        results = []
        for f in files:
            current_snapshot = pd.read_csv(f)
            if len(current_snapshot) == 0: ## dealing with empty files
                continue
            if 'Unnamed: 0' in current_snapshot.columns: ## dealing with past data which has index column
                current_snapshot = current_snapshot.drop(columns=['Unnamed: 0'])
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

        if self.run_in_cloud:
            Path('daily').mkdir(parents=True, exist_ok=True)
            destination = f"daily/outages_{date}.csv"
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_file = f"{temp_dir}/tmp.csv"
                pd.concat(results, sort=False).to_csv(temp_file,index=False)
                blob = self.gcs_bucket.blob(destination)
                blob.upload_from_filename(temp_file)
        else:
            pd.concat(results, sort=False).to_csv(output,index=False)


def main():
    file_merger = MergedFileCreator(bucket_name='',run_in_cloud=False)
    parser = argparse.ArgumentParser("Merge snapshots")
    parser.add_argument("--input_directory")
    parser.add_argument("--output")
    opts = parser.parse_args()

    file_merger.merge(opts.input_directory, opts.output)


if __name__ == "__main__":
    main()
