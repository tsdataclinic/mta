#!/bin/bash

# Assigning platforms IDs in Graph
Rscript src/stationgraph/assign_platform_ids.R \
    --graph data/processed/stationgraph/mta-elevators.graphml \
    --outel data/processed/stationgraph/edgelist_w_pid.csv \
    --outgraph data/processed/stationgraph/mta-elevators-w-station-connections.graphml

# Map platform IDs to GTFS Stop IDs
python src/stationgraph/map_platforms_to_GTFS.py \
    --edgelist data/processed/stationgraph/edgelist_w_pid.csv \
    --gtfs data/raw/google_transit/ \
    --output data/crosswalk/platform_id_to_GTFS_mapping.csv

# build station-to-station connections
python3 src/stationgraph/station_to_station.py \
  --routes data/raw/google_transit/routes.txt \
  --stop-times data/raw/google_transit/stop_times.txt \
 > data/processed/stationgraph/station_to_station.csv
 
# add station-to-station edges to graph
Rscript src/stationgraph/update_graph_w_station_connections.R \
    --graph data/processed/stationgraph/mta-elevators-w-station-connections.graphml \
    --stations data/processed/stationgraph/station_to_station.csv \
    --gtfsmapping data/crosswalk/platform_id_to_GTFS_mapping.csv \
    --stops data/raw/google_transit/stops.txt
    
