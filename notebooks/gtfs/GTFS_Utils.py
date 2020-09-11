import re
from os import listdir
from os.path import isfile, join
from typing import Dict, List

from google.transit import gtfs_realtime_pb2 as gtfs_rt
from protobuf_to_dict import protobuf_to_dict
import warnings

"""
Utilities to navigate GTFS archived directories.
"""

def gtfs_file_count(data_dir: str) -> Dict[str, int]:
    '''
    Prints information on a single day GTFS directory. Archived GTFS files come in the format
    gtfs_<train_line>_<date>_<seconds>.gtfs
    A directory will have many files for each train/date pair.
    '''
    file_name_pat = re.compile('gtfs_([a-zA-Z0-9]+)_([0-9]+)_([0-9]+)\.gtfs')

    # All files in given data_dir
    all_files = [f for f in listdir(data_dir) if isfile(join(data_dir, f))]
    unmatched_files = [f for f in all_files if not file_name_pat.match(f)]
    regex_groups = [file_name_pat.match(f) for f in all_files]

    # Sets of train_lines and dates.
    train_lines = set([m.group(1) for m in regex_groups if m])
    dates = set([m.group(2) for m in regex_groups if m])

    # Check to see how many files are in each date-train bucket.
    file_count = {"unmatched": len(unmatched_files)}
    for trains in train_lines:
        for date in dates:
            file_regex = re.compile('gtfs_{}_{}_[0-9]+\.gtfs'.format(trains, date))
            num_match = len([f for f in all_files if file_regex.match(f)])
            train_date = '{}-{}'.format(date,trains)
            file_count[train_date] = num_match

    return file_count

# Get all files in directory with given train_line and date
def get_file_names(data_dir: str, train_line:str, date:str) -> List[str]:
    file_name_pat = re.compile('gtfs_{}_{}_([0-9]+)\.gtfs'.format(train_line, date))
    all_files = [f for f in listdir(data_dir) if isfile(join(data_dir, f))]
    return ["{}/{}".format(data_dir, f) for f in all_files if file_name_pat.match(f)]


def gtfs_str_to_dict(raw_str: str) -> Dict:
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
        raise Exception("Error parsing raw string")
            

def gtfs_file_to_dict(file) -> Dict:        
    try:
        # The MTA data feed uses the General Transit Feed Specification (GTFS) which
        # is based upon Google's "protocol buffer" data format. While possible to
        # manipulate this data natively in python, it is far easier to use the
        # "pip install --upgrade gtfs-realtime-bindings" library which can be found on pypi
        feed = gtfs_rt.FeedMessage()
        raw_str = file.read()        
        return gtfs_str_to_dict(raw_str)            
    
    except Exception as ex:
        raise Exception("Error with file {} {}".format(file, str(ex)))


def load_gtfs(file_paths: List[str]) -> List[Dict]:
    '''
    Returns a list of dictionaries.
    Each row in the list is either a trip_update or a vehicle_update.
    '''
    feed_lst: List[Dict] = []
    for file_path in file_paths:
        with open(file_path, 'rb') as file:
            realtime_data = gtfs_file_to_dict(file)
            feed_lst += realtime_data            
    return feed_lst    
