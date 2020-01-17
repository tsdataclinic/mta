import requests
from bs4 import BeautifulSoup
import pandas as pd

page = requests.get('http://advisory.mtanyct.info/eedevwebsvc/allequipments.aspx')
soup = BeautifulSoup(page.content, 'lxml')

station = [t.text for t in soup.findAll('station')]
el_id = [t.text for t in soup.findAll('equipmentno')]
desc = [t.text for t in soup.findAll('serving')]
borough = [t.text for t in soup.findAll('borough')]
lines = [t.text for t in soup.findAll('trainno')]
equipment_type = [t.text for t in soup.findAll('equipmenttype')]
ada = [t.text for t in soup.findAll('ada')]
is_active = [t.text for t in soup.findAll('isactive')]

elevators_master_list = pd.DataFrame(list(zip(station,el_id,desc,borough,lines,equipment_type, ada, is_active)),
                                     columns=["station_name","equipment_id","description","borough","subway_lines",
                                             "equipment_type","ada_compliant","is_active"])

## TODO: split lines to make data more long-form
## TODO: parse descriptions to create columns 
## 			- subset of connecting lines
## 			- if connection to street level
## 			- direction of travel

elevators_master_list.to_csv('data/EE_master_list.csv')