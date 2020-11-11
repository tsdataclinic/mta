from dotenv import load_dotenv
import os
import schedule
import time
from OutageDownloader import OutageDownloader
from merge_snapshots import MergedFileCreator

load_dotenv()

poll_freq = int(os.getenv('POLL_FREQ')) # in seconds
data_dir = os.getenv('DATA_DIR') #+'/'
data_clinic_bucket = os.getenv('BUCKET')

if __name__ == '__main__':
    data_collector = OutageDownloader(output_path="gcs:{}".format(data_dir), bucket_name=data_clinic_bucket)
    daily_file_creator = MergedFileCreator(bucket_name=data_clinic_bucket,run_in_cloud=True)
    schedule.every(poll_freq).seconds.do(data_collector.run)
    schedule.every().day.at("05:30").do(daily_file_creator.process_pending)
    while True:
        schedule.run_pending()
        time.sleep(1)
