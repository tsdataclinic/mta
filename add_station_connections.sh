#!/bin/bash

# Assigning platforms IDs in Graph
Rscript src/stationgraph/assign_platform_ids.R \
    --g data/processed/stationgraph/mta-elevators.graphml \
    --out data/processed/stationgraph/edgelist_w_pid.csv

# Map platform IDs to GTFS Stop IDs


# build station-to-station connections
python3 src/stationgraph/station_to_station.py \
  --routes data/raw/google_transit/routes.txt \
  --stop-times data/raw/google_transit/stop_times.txt \
 > data/processed/stationgraph/station_to_station.csv
 
# add station-to-station edges to graph
