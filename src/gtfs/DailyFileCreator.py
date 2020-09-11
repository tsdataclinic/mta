from typing import List, Dict
import requests
import os 
import shutil
import time
from datetime import date, datetime, timedelta
import logging
import warnings
import numpy as np
import pandas as pd

from google.cloud import storage


class DailyFileCreator:
    """Creates daily files from the files written by DataCollector"""
    def __init__(self, bucket_name,run_in_cloud):
        log = logging.getLogger("gtfs_daily_creator")
        log.setLevel(logging.DEBUG)

        filename = "gtfs_daily_creator-{}.log".format(
            datetime.now().strftime("%Y%m%d-%I%M%S")
        )
        # create file handler which logs even debug messages
        fh = logging.FileHandler(filename)
        fh.setLevel(logging.DEBUG)

        # create console handler with a higher log level
        ch = logging.StreamHandler()
        ch.setLevel(logging.ERROR)

        # create formatter and add it to the handlers
        formatter = logging.Formatter("%(asctime)s-%(levelname)s: %(message)s")
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)

        if log.hasHandlers():
            log.handlers.clear()

        # add the handlers to the logger
        log.addHandler(fh)
        log.addHandler(ch)
        self.log = log

        self.bucket_name = bucket_name
        self.run_in_cloud = run_in_cloud

        self.gcs_client = storage.Client()
        self.gcs_bucket = self.gcs_client.bucket(bucket_name)

    def write_dataframe_to_gcs(self, df: pd.DataFrame, blob_path: str):
        temp_path = "temp_df.pkl"
        try:
            df.to_pickle(temp_path)
            blob = self.gcs_bucket.blob(blob_path)
            blob.upload_from_filename(temp_path)
        finally:
            os.remove(temp_path)

    def get_data_fragemnts(self):
        """
        Returns a list of the real time fragments from the google cloud bucket
        """
        return list(self.gcs_bucket.list_blobs(prefix='raw_data/'))

    def get_data_fragments_for_day(self,date:str):
        """
        Returns a list of google bucket file objects that contain vehicle and trip data for
        the specified date
        Keyword arguments:
        date: the date to pull data for
        """
        return list(self.gcs_bucket.list_blobs(prefix=f'raw_data/{date}/'))
    
    def get_unique_days(self, fragments):
        """
        Given a set of file fragments, will return a set of unique days for which we have data
        Keyword arguments:
        fragments: the result of get_data_fragments, a list of google cloud bucket files
        """
        return set([fragment.name.split('/')[1] for fragment in fragments])
    
    def get_processed_day_files(self):
        """ 
        Returns the list of daily summary files from the google cloud bucket
        """
        return self.gcs_bucket.list_blobs(prefix='realtime/daily/trip_updates')

    def get_days_to_do(self):
        """
        Looks at the google clound bucket and determines which of the days we have 
        fragmented data for that we have not combined in to daily summary data yet
        """
        data_fragments = self.get_data_fragemnts()
        unique_to_do = self.get_unique_days(data_fragments)
        already_done  = set([ file.name.split('_')[-1] for file in self.get_processed_day_files()])
        days_to_do = unique_to_do - already_done
        return list(days_to_do)
    
    def create_daily_file_cloud(self,date:str):
        """
        Will download and concatinate all of the fragments for a given day and write 
        the resulting data back to google cloud
        Keyword arguments:
        date -- Date for which to create daily files for
        """
        fragments = self.get_data_fragments_for_day(date)
        
        vehicle_files = [file for file in fragments if "vehicle_updates" in file.name]
        trip_files = [file for file in fragments if 'trip_updates' in file.name]
        
        print('processing ',len(vehicle_files),' vfs')
        print('processing ',len(trip_files), 'tfs')

        vdfs = [pd.read_pickle(f"gs://{self.bucket_name}/{file.name}") for file in vehicle_files ]
        tdfs = [pd.read_pickle(f"gs://{self.bucket_name}/{file.name}") for file in trip_files ]

        tdf = pd.concat(tdfs, sort=True).drop_duplicates()
        vdf = pd.concat(vdfs, sort=True).drop_duplicates()

        self.write_dataframe_to_gcs(tdf, f"realtime/daily/trip_updates_{date}")
        self.write_dataframe_to_gcs(vdf, f"realtime/daily/vehicle_updates_{date}")

    def create_daily_file(self, data_dir: str, date: str):
        """
            Writes two daily files(trip updates and vehicle updates) to google cloud storage.
            Keyword arguments:
            data_dir -- Directory where files are for the matching date
            date -- Date for which to create daily files for
        """
        all_files = []
        for root, dirs, files in os.walk(data_dir):
            for name in files:
                all_files.append(os.path.join(root, name))

        start = datetime.now()
        vehicle_files = [file for file in all_files if f"vehicle_updates_{date}" in file]
        trip_files = [file for file in all_files if f"trip_updates_{date}" in file]

        vdfs = [pd.read_pickle(file) for file in vehicle_files]
        tdfs = [pd.read_pickle(file) for file in trip_files]

        tdf = pd.concat(tdfs, sort=True).drop_duplicates()
        vdf = pd.concat(vdfs, sort=True).drop_duplicates()

        self.write_dataframe_to_gcs(tdf, f"realtime/daily/trip_updates_{date}")
        self.write_dataframe_to_gcs(vdf, f"realtime/daily/vehicle_updates_{date}")

        end = datetime.now()
        self.log.info(f"GTFS for date {date} took {end - start}")

    def process_yesterday_cloud(self):
        day = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
        self.create_daily_file_cloud(day)
        
    def process_all_pending_cloud(self):
        for day in self.get_days_to_do():
            try:
                self.create_daily_file_cloud(day)
            except Exception as ex:
                self.log.error(ex)

def main():
    daily_creator = DailyFileCreator()

    if cloud:
        daily_creator.process_all_pending_cloud()
    else:
        while True:
            try:
                sub_dirs = next(os.walk(data_dir))[1]
                today = date.today()

                for sub_dir in sub_dirs:
                    # Interpret sub directory name as date.
                    sub_dir_date = datetime.strptime(sub_dir, "%Y%m%d").date()

                    # Only create daily files for previous dates.
                    if sub_dir_date < today:
                        sub_dir_path = f"{data_dir}/{sub_dir}"
                        # Create daily file for sub_dir_date.
                        daily_creator.create_daily_file(
                            sub_dir_path,
                            sub_dir_date.strftime('%Y%m%d')
                        )
                        # Delete raw files for sub_dir_date
                        # shutil.rmtree(sub_dir_path)
            except Exception as ex:
                daily_creator.log.error(ex)



if __name__ == "__main__":
    main()
