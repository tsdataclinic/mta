from dotenv import load_dotenv
import os
import schedule
import time 
from DataCollector import DataCollector
from DailyFileCreator import DailyFileCreator

load_dotenv()

api_key = os.getenv('TRANSIT_API_KEY')
poll_freq = int(os.getenv('POLL_FREQ')) # in seconds
data_dir = os.getenv('DATA_DIR') +'/'
data_clinic_bucket = os.getenv('BUCKET')
run_in_cloud = os.getenv('CLOUD')

def job():
    print('boo')

if __name__ == '__main__':
    data_collector = DataCollector(api_key,data_dir,data_clinic_bucket,run_in_cloud)
    daily_creator  = DailyFileCreator(data_clinic_bucket,run_in_cloud)
    schedule.every(poll_freq).seconds.do(data_collector.collect_data)
    schedule.every().day.at("00:30").do(daily_creator.process_yesterday_cloud)
    while True:
        schedule.run_pending()
        time.sleep(1)