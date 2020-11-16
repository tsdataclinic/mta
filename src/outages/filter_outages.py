from google.cloud import storage

import pandas as pd
import io
import re


def _is_in_range(path, start_date, end_date, start_time, end_time):
    result = re.search(r'(\d{8})(-(\d{6}))?', path)
    if not result:
        return
    date = result.group(1)
    time = result.group(3)

    return (date > start_date or (date == start_date and (not start_time or time >= start_time))) \
           and (date < end_date or (date == end_date and (not end_time or time <= end_time)))


def get_outages_in_range(start_date, end_date, start_time=None, end_time=None):
    client = storage.Client.create_anonymous_client()
    bucket = client.bucket('mta_outage_data')
    dfs = []
    for blob in bucket.list_blobs(prefix='daily'):
        if _is_in_range(blob.path, start_date, end_date, start_time, end_time):
            dfs.append(pd.read_csv(io.StringIO(blob.download_as_string().decode('utf-8'))))
    merged = pd.concat(dfs)
    merged.sort_values(by=['outagedate'])
    return merged.drop_duplicates(subset=['equipment', 'outagedate', 'ongoing_outage'])
