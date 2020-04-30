#
# Get a lit of all equipments (elevators and escalators)
# and their descriptions from MTA Data portal and save it 
# to data/raw/EE_master_list.csv
#

import argparse
import sys
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re


def get_direction(x):
    r = re.findall('uptown|downtown|both directions', x)
    if len(r):
        return r[0]
    else:
        return ""

def main():
    parser = argparse.ArgumentParser("MTA Equipment fetcher")
    parser.add_argument("--output", required=False)

    opts = parser.parse_args()
    
    url = 'http://advisory.mtanyct.info/eedevwebsvc/allequipments.aspx'
    try:
        response = requests.get(url)

        # If the response was successful, no Exception will be raised
        response.raise_for_status()
    except Exception as err:
        print(f'Error in getting elevator list from {url}: {err}')  # Python 3.6

    soup = BeautifulSoup(response.content, 'lxml')
    station = [t.text for t in soup.findAll('station')]
    el_id = [t.text for t in soup.findAll('equipmentno')]
    desc = [t.text for t in soup.findAll('serving')]
    borough = [t.text for t in soup.findAll('borough')]
    lines = [t.text for t in soup.findAll('trainno')]
    equipment_type = [t.text for t in soup.findAll('equipmenttype')]
    ada = [t.text for t in soup.findAll('ada')]
    is_active = [t.text for t in soup.findAll('isactive')]

    elevators_master_list = pd.DataFrame(
        list(zip(station,el_id,desc,borough,lines,equipment_type, ada, is_active)),
        columns=["station_name","equipment_id","description","borough","subway_lines",
                 "equipment_type","ada_compliant","is_active"])
                                             
    elevators_master_list['direction'] = [get_direction(x) for x in elevators_master_list.description]
    tmp = [re.findall(y,x) if y != ' ' else None for x,y in zip(elevators_master_list.description,
                                          elevators_master_list.subway_lines)]
    elevators_master_list['subset_lines'] = [x if x else y for x,y in zip(tmp,
                                            elevators_master_list.subway_lines)]

    tmp = [re.match('Street|St|Ave|{}'.format(y),x) for x,y in zip(elevators_master_list.description,
                                                                   elevators_master_list.station_name)]
    elevators_master_list['connection_to_street'] =["Y" if x else "N" for x in tmp]

    elevators_master_list.to_csv(sys.stdout if opts.output is None else opts.output,index=False)
    
if __name__ == "__main__":
    main()