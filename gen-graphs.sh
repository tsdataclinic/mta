#!/bin/bash
# get equipment list
python3 src/stationgraph/get_equipment_list.py \
 > data/raw/EE_master_list.csv 

# Build elevator network edgelist
python3 src/stationgraph/station_to_elevator.py \
  --master-list data/raw/EE_master_list.csv \
 > data/processed/stationgraph/elevator_to_line_dir_station.csv
python3 src/stationgraph/buildgraphs.py \
  --no-inaccessible \
  --no-escalators \
  --master-list data/raw/EE_master_list.csv \
  --platform-list data/processed/stationgraph/elevator_to_line_dir_station.csv \
  --override-list data/raw/elevator-override.csv \
 > data/processed/stationgraph/mta-elevators-graph.csv

# Make graphml file from edgelist
python3 src/stationgraph/csv2graphml.py --pretty \
 < data/processed/stationgraph/mta-elevators-graph.csv \
 > data/processed/stationgraph/mta-elevators.graphml
 
# visualize individual station graphs
Rscript src/visualization/visualize_graphs.R \
    --g data/processed/stationgraph/mta-elevators.graphml \
    --routes data/raw/google_transit/routes.txt \
    --elevators data/raw/EE_master_list.csv \
    --out figures/elevator_maps/
