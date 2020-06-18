
from src.turnstile import turnstile
from datetime import datetime
from pathlib import Path
import argparse
import logging

if __name__ == "__main__":

    logging.basicConfig(level= logging.INFO)
    parser = argparse.ArgumentParser(description='Downloads turnstile data for a given time period, interpolates and aggregates to station level')
    parser.add_argument('-s','--start', type=lambda s: datetime.fromisoformat(s), help='Date to start pulling data from', default=datetime(2020, 1, 1))
    parser.add_argument('-e','--end', type=lambda s: datetime.fromisoformat(s), help='Date to stop pulling data from', default = datetime.today())
    parser.add_argument('-i','--interval', type=str, help='The interpolation interval, 1H, 15M etc', default = '1H')

    parser.add_argument('-o','--output', type=str, help='Directory to output to. ',default='turnstile_per_station')
    parser.add_argument('-m','--manifest', type=bool, help='Create a manifest markdown file?',default=True)
    parser.add_argument('-p','--prefix', type=str, help="Prefix to add on the the url's in the manifest", default='')

    args = parser.parse_args()
    start = args.start
    end  = args.end
    output = args.output
    make_markdown_manifest= args.manifest
    interpolation_period = args.interval
    url_prefix = args.prefix

    logging.info(f"Downloading data between ${start} and ${end}")
    turnstile_data = turnstile.create_interpolated_turnstile_data(start_date=start, end_date=end,frequency=interpolation_period)

    logging.info("Aggregating data")

    turnstile_by_station = turnstile.aggregate_turnstile_data_by_station(turnstile_data, 'data/crosswalk/ee_turnstile.csv')

    logging.info("Writing out data")
    outputDir = Path(output)
    outputDir.mkdir(exist_ok=True)

    for station in turnstile_by_station.keys():
        outfile = (outputDir / station).with_suffix('.csv')
        turnstile_by_station[station].to_csv(outfile,index=False)

    if (make_markdown_manifest):
        logging.info("Making manifest")

        filelist = outputDir.glob('*.csv')
        linkList = '\n'.join([ f"- [{file.name}]({url_prefix}{file.name})" for file in filelist])
        header = f"## Turnstile data per station per hour for 2020\n {linkList}"
        with open(outputDir /'turnstile_station_data.md', 'w') as f:
            f.write(header)