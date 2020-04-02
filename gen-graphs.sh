#!/bin/bash
python3 src/stationgraph/get_equipment_list.py \
 > data/raw/EE_master_list.csv 
python3 src/stationgraph/station_to_elevator.py \
  --master-list data/raw/EE_master_list.csv \
 > data/processed/stationgraph/elevator_to_line_dir_station.csv
python3 src/stationgraph/station_to_station.py \
  --routes data/raw/google_transit/routes.txt \
  --stop-times data/raw/google_transit/stop_times.txt \
 > data/processed/stationgraph/station_to_station.csv
python3 src/stationgraph/buildgraphs.py \
  --no-inaccessible \
  --no-escalators \
  --master-list data/raw/EE_master_list.csv \
  --platform-list data/processed/stationgraph/elevator_to_line_dir_station.csv \
  --override-list data/raw/elevator-override.csv \
 > data/processed/stationgraph/mta-elevators-graph.csv
python3 src/stationgraph/csv2graphml.py --pretty \
 < data/processed/stationgraph/mta-elevators-graph.csv \
 > data/processed/stationgraph/mta-elevators.graphml
