# input folders and files
RAW_DATA          := data/raw
GTFS_DATA         := $(RAW_DATA)/google_transit
MASTER_LIST       := $(RAW_DATA)/EE_master_list.csv
EQUIP_OVERRIDES   := $(RAW_DATA)/elevator-override.csv
GTFS_ROUTES       := $(GTFS_DATA)/routes.txt
GTFS_STOP_TIMES   := $(GTFS_DATA)/stop_times.txt
GTFS_STOPS        := $(GTFS_DATA)/stops.txt

# outputs folders and files
GRAPH_DATA        := data/processed/stationgraph
CROSSWALK_DATA    := data/crosswalk
MAPS_FIGURES      := figures/elevator_maps
EDGELIST_W_PID    := $(GRAPH_DATA)/edgelist_w_pid.csv
EDGELIST_W_STNS_1 := $(GRAPH_DATA)/mta-elevators-w-station-connections-tmp1.graphml
EDGELIST_W_STNS   := $(GRAPH_DATA)/mta-elevators-w-station-connections.graphml
ELEV_IMPORTANCE   := $(GRAPH_DATA)/elevator-importance.csv
EQUIP_GRAPH_CSV   := $(GRAPH_DATA)/mta-elevators-graph.csv
EQUIP_GRAPHML     := $(GRAPH_DATA)/mta-elevators.graphml
EQUIP_TO_LINE_DIR := $(GRAPH_DATA)/elevator_to_line_dir_station.csv
STN2STN_CSV       := $(GRAPH_DATA)/station_to_station.csv
MAPS_TIMESTAMP    := $(MAPS_FIGURES)/timestamp
PLAT2GTFS_CSV     := $(CROSSWALK_DATA)/platform_id_to_GTFS_mapping.csv

# TODO: some of these are just intermediate products that needn't
# be in the 'all' target
all: $(EQUIP_TO_LINE_DIR) $(EQUIP_GRAPH_CSV) $(EQUIP_GRAPHML) $(MAPS_TIMESTAMP) \
     $(EDGELIST_W_PID) $(EDGELIST_W_STNS) $(PLAT2GTFS_CSV) $(STN2STN_CSV) \
     $(ELEV_IMPORTANCE)

#
# Delete all derived data
#
clean:
	-rm $(GRAPH_DATA)/*
	#-rm $(CROSSWALK_DATA)/*
	-rm $(PLAT2GTFS_CSV)
	-rm $(MAPS_FIGURES)/*

#
# Delete all derived data and any raw data we can refetch
#
realclean: clean
	-rm $(MASTER_LIST)

#
# get equipment list (usually not necessary!)
#
$(MASTER_LIST): src/stationgraph/get_equipment_list.py
	> $@ python3 $< 

#
# extract platform information from MTA data
#
$(EQUIP_TO_LINE_DIR): src/stationgraph/station_to_elevator.py $(MASTER_LIST)
	> $@ python3 $< --master-list $(MASTER_LIST)

#
# build network of elevators, mezzanines and platforms for each station
#
$(EQUIP_GRAPH_CSV): src/stationgraph/buildgraphs.py $(MASTER_LIST) $(EQUIP_TO_LINE_DIR) $(EQUIP_OVERRIDES)
	> $@ python3 $< \
	  --no-inaccessible \
	  --no-escalators \
	  --master-list $(MASTER_LIST) \
	  --platform-list $(EQUIP_TO_LINE_DIR) \
	  --override-list $(EQUIP_OVERRIDES)

#
# build graphml file from edgelist
#
$(EQUIP_GRAPHML): src/stationgraph/csv2graphml.py $(EQUIP_GRAPH_CSV)
	> $@ python3 $< --pretty < $(EQUIP_GRAPH_CSV)

#
# visualize individual station graphs
#
$(MAPS_TIMESTAMP): src/visualization/visualize_graphs.R $(EQUIP_GRAPHML) $(GTFS_ROUTES) $(MASTER_LIST)
	-rm $@
	-rm $(dir $@)/*.png
	Rscript $< \
	  --g $(EQUIP_GRAPHML) \
	  --routes $(GTFS_ROUTES) \
	  --elevators $(MASTER_LIST) \
	  --out $(dir $@)
	> $@ date

#
# assign platforms IDs in Graph
#
$(EDGELIST_W_PID) $(EDGELIST_W_STNS_1) &: src/stationgraph/assign_platform_ids.R $(EQUIP_GRAPHML)
	Rscript $< \
	  --graph $(EQUIP_GRAPHML) \
	  --outel $(EDGELIST_W_PID) \
	  --outgraph $(EDGELIST_W_STNS_1)

#
# map platform IDs to GTFS Stop IDs
#
# NB: This script implicitly depends on several files in the GTFS directory!
GTFS_INPUTS := $(addprefix $(GTFS_DATA)/,routes.txt trips.txt stops.txt stop_times.txt)
$(PLAT2GTFS_CSV): src/stationgraph/map_platforms_to_GTFS.py $(EDGELIST_W_PID) $(GTFS_INPUTS)
	python3 $< \
	  --edgelist $(EDGELIST_W_PID) \
	  --gtfs $(GTFS_DATA)/ \
	  --output $@

#
# build station-to-station connections
#
$(STN2STN_CSV): src/stationgraph/station_to_station.py $(GTFS_ROUTES) $(GTFS_STOP_TIMES)
	> $@ python3 $< \
	  --routes $(GTFS_ROUTES) \
	  --stop-times $(GTFS_STOP_TIMES) \

#
# add station-to-station edges to graph
#
# TODO: this R script modifies the file in place, so we need to copy the source
# file then rename it when we're done. Instead, the script should have in & out graphs
$(EDGELIST_W_STNS): src/stationgraph/update_graph_w_station_connections.R \
                    $(EDGELIST_W_STNS_1) $(STN2STN_CSV) $(PLAT2GTFS_CSV) $(GTFS_STOPS)
	cp $(EDGELIST_W_STNS_1) $(@:.graphml=.tmp.graphml)
	Rscript $< \
	  --graph $(@:.graphml=.tmp.graphml) \
	  --stations $(STN2STN_CSV) \
	  --gtfsmapping $(PLAT2GTFS_CSV) \
	  --stops $(GTFS_STOPS)
	mv $(@:.graphml=.tmp.graphml) $@
    
#
# elevator redundancy analysis
#
$(ELEV_IMPORTANCE): src/stationgraph/elevator_importance.py $(EDGELIST_W_STNS_1) $(EDGELIST_W_STNS)
	> $@ python3 $< \
	  --individual-station-graph $(EDGELIST_W_STNS_1) \
	  --complete-station-graph $(EDGELIST_W_STNS) \