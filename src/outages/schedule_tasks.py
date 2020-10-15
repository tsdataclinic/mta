from dotenv import load_dotenv
import os
import schedule
import time 
from OutageDownloader import OutageDownloader

load_dotenv()

poll_freq = int(os.getenv('POLL_FREQ')) # in seconds
data_dir = os.getenv('DATA_DIR') +'/'
data_clinic_bucket = os.getenv('BUCKET')

if __name__ == '__main__':
    data_collector = OutageDownloader(data_dir=data_dir, bucket_name=data_clinic_bucket, frequency= poll_freq)
    schedule.every(poll_freq).seconds.do(data_collector.run)
    while True:
        schedule.run_pending()
        time.sleep(1)