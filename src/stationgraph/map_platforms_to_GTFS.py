import pandas as pd
import re
import textdistance
import numpy as np
import argparse

north_bound = ['north','norwood 205 st', 'woodlawn','jamaica', 'flushing main st','jamaica center','flushing', 'wakefield 241 st','jamaica, forest hills']
south_bound = ['south','bay ridge', 'coney island','flatbush av brooklyn college','brighton beach, coney island, bay ridge','brighton beach','coney island, brighton beach','far rockaway']

def get_dir(df):
    if df.possible_stops == '': return "NULL"
    if len(df.possible_stops.split(', ')) == 1: return df.possible_stops
    # hack for Kings Highway Q line
    if len(df.possible_stops.split(', ')) == 3: return 'N08N'
    
    if df.direction in north_bound:
        match = [x for x in df.possible_stops.split(', ') if re.match('.*N$',x)]
        return match[0]
    elif (df.direction in south_bound) | ((df.direction == 'manhattan') & (df.line in ['4','6','7','Z'])):
        match = [x for x in df.possible_stops.split(', ') if re.match('.*S$',x)]
        return match[0]
    elif (df.direction == 'manhattan') & (df.line in ['3','G']):
        match = [x for x in df.possible_stops.split(', ') if re.match('.*N$',x)]
        return match[0]
    else:
        return "NULL"
    
def match_jaccard(ee, platforms):
    for index, row in ee.iterrows():
        if row.possible_stops == '':
            subset = platforms[platforms.routes_wkd.str.contains(row.line)]
            if subset.shape[0] > 0:
                subset_stop_names = pd.DataFrame(subset.stop_name.unique(),columns=['stop_name'])
                name_dist = [textdistance.jaccard(row.station_name,y) for y in subset_stop_names.stop_name]

                matched_station_name = subset_stop_names.iloc[np.argmax(name_dist),0]
                matched_stop_ids = subset[subset.stop_name == matched_station_name][['stop_id']]
                score = max(name_dist)
                if score >=0.8:
                    ee.loc[index,'possible_stops'] = ', '.join(matched_stop_ids.stop_id)
    return ee

def match_jaro_winkler(ee, platforms):
    for index, row in ee.iterrows():
        if row.possible_stops == '':
            subset = platforms[platforms.routes_wkd.str.contains(row.line)]
            if subset.shape[0] > 0:
                subset_stop_names = pd.DataFrame(subset.stop_name.unique(),columns=['stop_name'])
                name_dist = [textdistance.jaro_winkler(row.station_name,y) for y in subset_stop_names.stop_name]

                matched_station_name = subset_stop_names.iloc[np.argmax(name_dist),0]
                matched_stop_ids = subset[subset.stop_name == matched_station_name][['stop_id']]
                score = max(name_dist)
                if score > 0.79:
                    ee.loc[index,'possible_stops'] = ', '.join(matched_stop_ids.stop_id)
    return ee

# This generates a mapping between platforms and GTFS Stop IDs
def main():
    parser = argparse.ArgumentParser("Station graph builder")
    parser.add_argument("--edgelist", required=True)
    parser.add_argument("--gtfs", required=True)
    parser.add_argument("--output", required=False)
    
    opts = parser.parse_args()
    
    ee = pd.read_csv(opts.edgelist)
    
    ee = ee[ee.to_type == 'Train']
    ee['line'] = [x.split('-')[0] for x in ee.to]
    ee['direction'] = [x.split('-')[1] for x in ee.to]
    
    routes = pd.read_csv(opts.gtfs+'routes.txt')
    trips = pd.read_csv(opts.gtfs+'trips.txt')
    stops = pd.read_csv(opts.gtfs+'stops.txt')
    stop_times = pd.read_csv(opts.gtfs+'stop_times.txt')
    
    platforms = stops[stops.location_type == 0]
    stop_times['line'] = [x[x.find('..')-1:x.find('..')] for x in stop_times.trip_id]
    weekday = stop_times[stop_times.trip_id.str.contains('Weekday')]
    routes_subset = routes[(routes.route_id.str.len() == 1) & (routes.route_id != 'H')]
    weekday = weekday.merge(trips[trips.route_id.isin(routes_subset.route_id)][['trip_id','route_id']],on="trip_id")
    
    unique_stop_ids = pd.DataFrame(weekday.stop_id.unique(),columns=['stop_id'])
    unique_stop_ids['routes_wkd'] = [''.join(weekday[weekday.stop_id == x]['route_id'].unique()) for x in unique_stop_ids.stop_id]
    platforms = platforms.merge(unique_stop_ids,on='stop_id')
    
    ee['possible_stops'] = ''
    
    ee = match_jaccard(ee,platforms)
    ee = match_jaro_winkler(ee,platforms)

    ## Manual overrides
    ee.loc[ee[(ee.possible_stops == '') & (ee.station_name == 'Broadway-Lafayette/Bleecker St')].index,'possible_stops'] = '637N, 637S'
    ee.loc[ee[(ee.possible_stops == '') & (ee.station_name == 'Kings Highway')].index,'possible_stops'] = 'D35N, D35S'
    ee.loc[ee[(ee.possible_stops == '') & (ee.station_name.str.contains('New Utrecht'))].index,'possible_stops'] = 'N04N, N04S'
    
    ee['stop_id'] = ee.apply(get_dir,axis=1)
    
    ## Manual overrides
    ee.loc[(ee.stop_id == 'NULL') & ~(ee.possible_stops == '') & (ee.station_name.str.contains('Flushing')) & (ee.direction == 'manhattan'),'stop_id'] = 'M12S' 
    ee.loc[(ee.stop_id == 'NULL') & ~(ee.possible_stops == '') & (ee.station_name.str.contains('Times')) & (ee.direction == 'east'),'stop_id'] = '725N' 
    ee.loc[(ee.stop_id == 'NULL') & ~(ee.possible_stops == '') & (ee.station_name.str.contains('Times')) & (ee.direction == 'west'),'stop_id'] = '725S'
    ee.loc[(ee.stop_id == 'NULL') & ~(ee.possible_stops == '') & (ee.station_name.str.contains('Dekalb')) & (ee.direction == 'manhattan'),'stop_id'] = 'R30N'
    ee.loc[(ee.stop_id == 'NULL') & ~(ee.possible_stops == '') & (ee.station_name.str.contains('Kings')) & (ee.direction == 'brighton'),'stop_id'] = 'D35S'
    
    plt_stop_id = ee[['station_name','from','line','direction','stop_id']]
    plt_stop_id = plt_stop_id[plt_stop_id.stop_id != 'NULL']
    plt_stop_id['platform_id'] = plt_stop_id['from']
    plt_stop_id = plt_stop_id[['station_name','platform_id','line','direction','stop_id']]

    plt_stop_id.to_csv(opts.output,index=False)
    
if __name__ == "__main__":
    main()