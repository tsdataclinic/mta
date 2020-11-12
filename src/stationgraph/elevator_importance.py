#!/usr/bin/env python

import argparse
import copy
import igraph
import matplotlib.pyplot as plt
import pandas as pd
import sys

def calc_betweeness(graph):
    elevators = graph.vs.select(lambda vertex: vertex["node_type"] == "Elevator")
    betweenness = graph.betweenness(vertices=elevators)

    rez = []
    for e, b in zip(elevators, betweenness):
        rez.append([e["station"], e["name"], b])

    return rez    

def elevator_redudancy_analysis(stations):
    # mode is ignored in this case, because it's undirected
    graph = stations.clusters(mode="WEAK")

    rez = []
    for station in graph:
        rez.extend(analyze_station(stations.subgraph(station)))
    return rez

def analyze_station(station):
    """ Analyze elevator importance at a station"""
    rez = []
    # test what changes to accessbility when you remove a single elevator from it
    for v in station.vs:
        if v["node_type"] != "Elevator":
            # only test elevator importance
            continue
        
        t = copy.deepcopy(station)
        t.delete_vertices([v["id"]])

        # determine number of trains that lose access to the street as a result
        # of the removal
        station_split = t.clusters(mode="WEAK")
        severity = 0
        for split in station_split:
            severity += calc_elevator_importance(t, split)
        rez.append([v["station"], v["id"], severity])
    return rez

def calc_elevator_importance(graph, vs):
    """ Calculate the commuter importance of a graph
    
    Commuter importance is defined as the number of trains that don't
    have access to the street.
    """
    severity = 0
    for v in vs:
        if graph.vs[v]["node_type"] == "Street":
            return 0
        if graph.vs[v]["node_type"] == "Train":
            severity += 1
    return severity


def main():
    parser = argparse.ArgumentParser("Elevator Importance Calculator")
    parser.add_argument("--individual-station-graph", required=True)
    parser.add_argument("--complete-station-graph", required=True)
    parser.add_argument("--output", required=False)

    opts = parser.parse_args()

    independent_stations_graph = igraph.Graph.Read_GraphML(opts.individual_station_graph)
    importance = elevator_redudancy_analysis(independent_stations_graph)
    output = pd.DataFrame(importance, columns = ['Station', 'Elevator', 'Importance'])  
    
    full_graph = igraph.Graph.Read_GraphML(opts.complete_station_graph)
    betweenness = calc_betweeness(full_graph)
    output['Betweenness'] = output["Elevator"].map({e[1]: e[2] for e in betweenness}) 

    output.to_csv(sys.stdout if opts.output is None else opts.output, index=False)

if __name__ == "__main__":
    main()