from typing import List, Dict
import requests
import os 
import sys
import time
import datetime
import logging
import warnings
import numpy as np
import pandas as pd
from pandas import json_normalize

from google.transit import gtfs_realtime_pb2 as gtfs_rt
from protobuf_to_dict import protobuf_to_dict
from google.cloud import storage


# Train lines to feed_id
feed_id_dict = {
    "123456": None,
    "7": "7",
    # "l": "l",
    "nqrw": "nqrw",
    "jz": "jz",
    "g": "g",
    "ace": "ace"
}

main_thread_retires = 50


class DataCollector:
    """Collects live gtfs data from mta api"""
    def __init__(self,api_key=None, data_dir=None, bucket_name=None, run_in_cloud=False):
        log = logging.getLogger("gtfs_collector")
        log.setLevel(logging.DEBUG)

        filename = "gtfs_collector-{}.log".format(
            datetime.datetime.now().strftime("%Y%m%d-%I%M%S")
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

        os.makedirs(data_dir, exist_ok=True)
        self.data_dir = data_dir
        self.bucket_name = bucket_name
        self.run_in_cloud = run_in_cloud

        self.stop_df = pd.read_csv("stops.txt")
        self.log = log
        self.gcs_client = storage.Client()
        self.gcs_bucket = self.gcs_client.bucket(bucket_name)
        self.api_key = api_key
        
    def write_dataframe_to_gcs(self, df: pd.DataFrame, blob_path: str):
        temp_path = "temp_df.pkl"
        try:
            df.to_pickle(temp_path)
            blob = self.gcs_bucket.blob(blob_path)
            blob.upload_from_filename(temp_path)
        finally:
            os.remove(temp_path)

    def parse_vehicle_updates(self, realtime_data: List[Dict]) -> pd.DataFrame:
        stop_df = self.stop_df[["stop_id", "stop_name"]]
        df = json_normalize(realtime_data)
        df = df[df["vehicle.trip.trip_id"].notnull()]
        df = df.drop(list(df.filter(regex="trip_update")), axis=1)
        df.columns = df.columns.str.replace("vehicle\.", "")
        df.columns = df.columns.str.replace("trip\.", "")
        df = df.merge(stop_df, on="stop_id")
        df["timestamp"] = pd.to_datetime(df.timestamp, unit="s")
        return df.drop_duplicates()

    def parse_trip_updates(self, realtime_data: List[Dict]) -> pd.DataFrame:
        stop_df = self.stop_df[["stop_id", "stop_name"]]
        df = json_normalize(realtime_data)

        # Parse trip updates
        df = df[~df["trip_update.stop_time_update"].isnull()]
        idx = df.index.repeat(df["trip_update.stop_time_update"].str.len())
        df1 = pd.DataFrame(
            {
                "trip_update.stop_time_update": np.concatenate(
                    df["trip_update.stop_time_update"].values
                )
            }
        )
        df1.index = idx
        df = df1.join(df.drop("trip_update.stop_time_update", axis=1), how="left")
        df = df.reset_index(drop=True)
        d2 = json_normalize(df["trip_update.stop_time_update"])
        df = pd.concat([d2, df.drop("trip_update.stop_time_update", axis=1)], axis=1)
        df = df.drop(list(df.filter(regex="vehicle")), axis=1)
        df = df.merge(stop_df, on="stop_id")

        df.columns = df.columns.str.replace("trip_update\.trip\.", "")
        df.columns = df.columns.str.replace("\.", "_")
        df["arrival_time"] = pd.to_datetime(df.arrival_time, unit="s")
        df["departure_time"] = pd.to_datetime(df.departure_time, unit="s")

        return df.drop_duplicates()

    def get_dir_for_timestamp(self):
        now = datetime.datetime.now()        
        date = now.strftime("%Y%m%d")
        hour = now.strftime("%H")        
        vehicle_dir = f"raw_data/{date}/{hour}"        
        return vehicle_dir

    def write_vehicle_update_dataframe(self, df: pd.DataFrame, base_dir: str):
        now = datetime.datetime.now()        
        time_str = now.strftime("%Y%m%d-%H%M%S")
        vehicle_path = f"{base_dir}/vehicle_updates_{time_str}.pkl"
        df.to_pickle(vehicle_path)        
        self.log.info(f"Wrote {len(df.index)} rows to {vehicle_path}")
        
    def write_trip_update_dataframe(self, df: pd.DataFrame):
        now = datetime.datetime.now()        
        time_str = now.strftime("%Y%m%d-%H%M%S")
        trip_path = f"{base_dir}/trip_updates_{time_str}.pkl"
        df.to_pickle(trip_path)
        self.log.info(f"Wrote {len(df.index)} rows to {trip_path}\n")

    def write_vehicle_update_dataframe_cloud(self, df: pd.DataFrame, base_dir:str):
        now = datetime.datetime.now()        
        time_str = now.strftime("%Y%m%d-%H%M%S")
        vehicle_path = f"{base_dir}/vehicle_updates_{time_str}.pkl"
        self.write_dataframe_to_gcs(df,vehicle_path)
        self.log.info(f"Wrote {len(df.index)} rows to {vehicle_path}")

    def write_trip_update_dataframe_cloud(self,df: pd.DataFrame, base_dir:str):
        now = datetime.datetime.now()        
        time_str = now.strftime("%Y%m%d-%H%M%S")
        trip_path = f"{base_dir}/trip_updates_{time_str}.pkl"
        self.write_dataframe_to_gcs(df,trip_path)
        self.log.info(f"Wrote {len(df.index)} rows to {trip_path} on the cloud\n")
        
    def gtfs_str_to_dict(self, raw_str: str) -> Dict:
        try:
            # The MTA data feed uses the General Transit Feed Specification (GTFS) which
            # is based upon Google's "protocol buffer" data format. While possible to
            # manipulate this data natively in python, it is far easier to use the
            # "pip install --upgrade gtfs-realtime-bindings" library which can be found on pypi
            feed = gtfs_rt.FeedMessage()        
            with warnings.catch_warnings():
                warnings.filterwarnings('error')
                try:
                    feed.ParseFromString(raw_str)
                except Warning as w:  
                    raise Exception(f"{w}")

                subway_feed = protobuf_to_dict(feed)
                realtime_data = subway_feed['entity']
                return realtime_data
        except Exception as ex:
            raise Exception(f"Error parsing raw string {ex}")
    
    def collect_data(self):
        realtime_data_list = []
        for train_names, feed_id in feed_id_dict.items():
            if feed_id is None:
                url = "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs"
            else:        
                url = "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-{}".format(feed_id)

            try:
                # ParseErrors occur often because of bad data from mta api.
                raw_str = requests.get(url, headers={'x-api-key': self.api_key}, allow_redirects=True).content                                    
                realtime_data = self.gtfs_str_to_dict(raw_str)                    
                realtime_data_list.append(realtime_data)
            except Exception as ex:
                self.log.error(f"Train {train_names}")
                self.log.error(ex)
        
        vdf = pd.concat(
            [self.parse_vehicle_updates(data) for data in realtime_data_list], sort=True
        )
        tdf = pd.concat(
            [self.parse_trip_updates(data) for data in realtime_data_list], sort=True
        )
        
        base_dir = self.get_dir_for_timestamp()
        os.makedirs(base_dir, exist_ok=True)
        if self.run_in_cloud:
            self.write_vehicle_update_dataframe_cloud(vdf,base_dir)
            self.write_trip_update_dataframe_cloud(tdf,base_dir)
        else:
            self.write_vehicle_update_dataframe(vdf,base_dir)
            self.write_trip_update_dataframe(tdf,base_dir)

    def start_collecting(self):
        while True:
            collect_data
            time.sleep(poll_freq)

def main():
    collector = DataCollector()    
    while True:
        try:            
            collector.start_collecting()
        except Exception as ex:
            collector.log.error(ex)
            raise(ex)

    print("Something went wrong")


if __name__ == "__main__":
    main()
