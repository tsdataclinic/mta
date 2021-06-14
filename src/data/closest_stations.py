import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, LineString
import networkx as nx
import osmnx as ox
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt

DATA_PATH = Path('../../data')
PROCESSED_DATA_PATH = DATA_PATH / 'processed/nearest'
def load_graph():
    ox.config(use_cache=True, log_console=True)
    graph = ox.graph_from_place("New York City, USA")
    return graph

def plot_graph(graph):
    ox.plot.plot_graph(graph, save=True, filepath=PROCESSED_DATA_PATH / 'nyc_streets.png', dpi=600, edge_linewidth=0.08, node_size=0, show=False)

def load_stations_with_elevators():
    stations = pd.read_csv(DATA_PATH / "crosswalk/Master_crosswalk.csv", dtype={'lat':np.float64, 'lon':np.float64})
    return stations.drop_duplicates(subset=['station_name'] )

def get_nearest_nodes(stations, graph):
    nodes = {}
    for index, station in stations.iterrows():
        nodes[station.station_name]=ox.get_nearest_node(graph,[station.lat,station.lon])
    return nodes

def calculate_euclid_distances(nodes,graph):
    distances = {}
    euclidian_distances ={} 
    done = 0
    for origin_station, origin_node in nodes.items():
        for dest_station, dest_node in nodes.items():
            o = graph.nodes[origin_node]
            d = graph.nodes[dest_node]
            if (dest_station, origin_station) not in euclidian_distances.keys() and origin_station!=dest_station:
                e_dist = (o['x'] - d['x'])**2 + (o['y']-d['y'])**2
                euclidian_distances[(origin_station,dest_station)] = e_dist
            done+=1
            if(done%100==0):
                print("done ",done, ' of ', len(nodes)**2, done*100/(len(nodes)**2)/2, '%')
    euclidian_distances = [ [od[0],od[1],dist] for od,dist in euclidian_distances.items() ]
    return pd.DataFrame(euclidian_distances, columns=['origin','destination','dist'])

def calculate_walking_distances(nodes,graph, eculid_distances, no_candidates=30):
    distances={}
    done=0
    for origin_station, origin_node in nodes.items():
        nearest_candidates = eculid_distances[eculid_distances.origin == origin_station].sort_values(by='dist').head(20).destination
        for dest_station in list(nearest_candidates):
            if (dest_station, origin_station) not in distances.keys():
                dest_node = nodes[dest_station]
                distance  = nx.shortest_path_length(graph, origin_node, dest_node, weight='length')
                distances[(origin_station,dest_station)] = distance
            done+=1
            if(done%100==0):
                print("done ",done, ' of ', len(nodes)*no_candidates, done*100/(len(nodes)*no_candidates), '%')
    distances= [ [od[0],od[1],dist] for od,dist in distances.items() ]
    return pd.DataFrame(distances, columns=['origin','destination','walking_dist'])

def get_closest(walking_distances):
    normed_od = pd.concat([walking_distances, walking_distances.rename(columns={"origin":"destination", "destination":"origin"})])
    return normed_od.groupby('origin').apply(lambda x: x.sort_values(by='walking_dist').iloc[0]).drop('origin',axis=1)

def plot_route(graph, origin, destination):
    o = graph.nodes[origin] 
    d = graph.nodes[destination]
    print(o)
    north = max(o['y'], d['y'])
    south = min(o['y'], d['y'])
    east = max(o['x'], d['x'])
    west = min(o['x'],d['x'])
    padding = 0.01
    local_graph = ox.truncate.truncate_graph_bbox(graph, north+padding,south -padding, east+padding,west-padding)
    return ox.plot.plot_graph_route(local_graph, nx.shortest_path(graph,origin,destination, weight='length'),show=False)

def plot_all_routes(graph,nodes,routes):
    path = PROCESSED_DATA_PATH / "plots"
    path.mkdir(exist_ok=True)
    for index, route in routes.iterrows():
        fig,ax = plot_route(graph,nodes[index], nodes[route.destination])
        ax.set_title(f"{index} - {route.destination}: {route.walking_dist} meters")
        fig.savefig(path / f"{index}-{route.destination}.png")

def process():
    PROCESSED_DATA_PATH.mkdir(exist_ok=True)
    graph = load_graph()
    plot_graph(graph)
    stations = load_stations_with_elevators()
    nodes = get_nearest_nodes(stations,graph)
    euclidian_distances = calculate_euclid_distances(nodes,graph) 
    walking_distances = calculate_walking_distances(nodes,graph, euclidian_distances)
    nearest = get_closest(walking_distances)
    nearest.to_csv(PROCESSED_DATA_PATH / 'nearest_stations.csv',index=False)
    walking_distances.to_csv(PROCESSED_DATA_PATH / "all_walking_distances.csv",index=False)
    plot_all_routes(graph,nodes,nearest) 


if __name__ =='__main__':
    process() 