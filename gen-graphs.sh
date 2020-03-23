#!/bin/bash
python3 src/stationgraph/buildgraphs.py \
  --no-inaccessible \
  --no-escalators \
  --master-list data/interim/crosswalks/EE_master_list.csv \
  --platform-list data/processed/elevator_to_line_dir_station.csv \
  --override-list data/raw/elevator-override.csv \
 > data/processed/mta-elevators-graph.csv
python3 src/stationgraph/csv2graphml.py --pretty \
 < data/processed/mta-elevators-graph.csv \
 > data/processed/mta-elevators.graphml
