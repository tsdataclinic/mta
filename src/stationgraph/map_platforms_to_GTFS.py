import pandas as pd
import re
import textdistance
import numpy as np
import argparse

north_bound = ['north','norwood 205 st', 'woodlawn','jamaica', 'flushing main st','jamaica center','flushing', 'wakefield 241 st','jamaica, forest hills']
south_bound = ['south','bay ridge', 'coney island','flatbush av brooklyn college','brighton beach, coney island, bay ridge','brighton beach','coney island, brighton beach','far rockaway']

def get_code_for_direction(direction, line):
    if direction in north_bound:
        return 'N'
    elif (direction in south_bound) | ((direction == 'manhattan') & (line in ['4','6','7','Z'])):
        return 'S'
    elif (direction == 'manhattan') & (line in ['3','G']):
        return 'N'
    else:
        return ''
    
def match_jaccard(ee, platforms):
    for index, row in ee.iterrows():
        if row.possible_stops == '':
            subset = platforms[platforms.line == row.line]
            if subset.shape[0] > 0:
                subset_stop_names = pd.DataFrame(subset.stop_name.unique(),columns=['stop_name'])
                name_dist = [textdistance.jaccard(row.station_name,y) for y in subset_stop_names.stop_name]

                matched_station_name = subset_stop_names.iloc[np.argmax(name_dist),0]
                matched_stop_ids = subset[subset.stop_name == matched_station_name].stop_id
                score = max(name_dist)
                if score >=0.8:
                    ee.loc[index,'possible_stops'] = list(matched_stop_ids)[0][:3]
    return ee

def match_jaro_winkler(ee, platforms):
    for index, row in ee.iterrows():
        if row.possible_stops == '':
            subset = platforms[platforms.line == row.line]
            if subset.shape[0] > 0:
                subset_stop_names = pd.DataFrame(subset.stop_name.unique(),columns=['stop_name'])
                name_dist = [textdistance.jaro_winkler(row.station_name,y) for y in subset_stop_names.stop_name]

                matched_station_name = subset_stop_names.iloc[np.argmax(name_dist),0]
                matched_stop_ids = subset[subset.stop_name == matched_station_name].stop_id
                score = max(name_dist)
                if score > 0.79:
                    ee.loc[index,'possible_stops'] = list(matched_stop_ids)[0][:3]
    return ee

def explode(df, lst_cols, fill_value='', preserve_index=False):
    # make sure `lst_cols` is list-alike
    if (lst_cols is not None
        and len(lst_cols) > 0
        and not isinstance(lst_cols, (list, tuple, np.ndarray, pd.Series))):
        lst_cols = [lst_cols]
    # all columns except `lst_cols`
    idx_cols = df.columns.difference(lst_cols)
    # calculate lengths of lists
    lens = df[lst_cols[0]].str.len()
    # preserve original index values    
    idx = np.repeat(df.index.values, lens)
    # create "exploded" DF
    res = (pd.DataFrame({
                col:np.repeat(df[col].values, lens)
                for col in idx_cols},
                index=idx)
             .assign(**{col:np.concatenate(df.loc[lens>0, col].values)
                            for col in lst_cols}))
    # append those rows that have empty lists
    if (lens == 0).any():
        # at least one list in cells is empty
        res = (res.append(df.loc[lens==0, idx_cols], sort=False)
                  .fillna(fill_value))
    # revert the original index order
    res = res.sort_index()
    # reset index if requested
    if not preserve_index:        
        res = res.reset_index(drop=True)
    return res

# This generates a mapping between platforms and GTFS Stop IDs
def main():
    parser = argparse.ArgumentParser("Platform to GTFS mapping")
    parser.add_argument("--edgelist", required=True)
    parser.add_argument("--gtfs", required=True)
    parser.add_argument("--output", required=False)
    
    opts = parser.parse_args()
    
    ee = pd.read_csv(opts.edgelist)
#     ee.loc[ee.to == '5 service via manhattan','to'] = '5-manhattan'
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
    platforms['line'] = [list(r) for r in platforms.routes_wkd]
    
    platforms = explode(platforms, ['line'], fill_value='')
    
    ee = ee.merge(platforms[['parent_station','stop_name','line']],how='left',left_on=["station_name",'line'],right_on=["stop_name",'line'])
    ee.parent_station = ee.parent_station.fillna('')
    ee = ee.rename(columns={'parent_station':'possible_stops'})
    
    ee = match_jaccard(ee,platforms)
    ee = match_jaro_winkler(ee,platforms)

    ## Manual overrides
    ee.loc[ee[(ee.possible_stops == '') & (ee.station_name == 'Broadway-Lafayette/Bleecker St')].index,'possible_stops'] = '637'
    ee.loc[ee[(ee.possible_stops == '') & (ee.station_name == 'Kings Highway')].index,'possible_stops'] = 'D35'
    ee.loc[ee[(ee.possible_stops == '') & (ee.station_name.str.contains('New Utrecht'))].index,'possible_stops'] = 'N04'
    ee.loc[ee[(ee.possible_stops == '') & (ee.station_name.str.contains('Broadway / Roosevelt Av'))].index,'possible_stops'] = 'G14'
    ee.loc[ee[(ee.possible_stops == '') & (ee.station_name.str.contains('Lexington Av / 53 St and 51 St'))].index,'possible_stops'] = '630'

    
    ee['stop_id'] = [s+get_code_for_direction(d,l) for s,d,l in zip(ee.possible_stops, ee.direction, ee.line)]
    
#     ## Manual overrides
#     ee.loc[(ee.stop_id == 'NULL') & ~(ee.possible_stops == '') & (ee.station_name.str.contains('Flushing')) & (ee.direction == 'manhattan'),'stop_id'] = 'M12S' 
#     ee.loc[(ee.stop_id == 'NULL') & ~(ee.possible_stops == '') & (ee.station_name.str.contains('Times')) & (ee.direction == 'east'),'stop_id'] = '725N' 
#     ee.loc[(ee.stop_id == 'NULL') & ~(ee.possible_stops == '') & (ee.station_name.str.contains('Times')) & (ee.direction == 'west'),'stop_id'] = '725S'
#     ee.loc[(ee.stop_id == 'NULL') & ~(ee.possible_stops == '') & (ee.station_name.str.contains('Dekalb')) & (ee.direction == 'manhattan'),'stop_id'] = 'R30N'
#     ee.loc[(ee.stop_id == 'NULL') & ~(ee.possible_stops == '') & (ee.station_name.str.contains('Kings')) & (ee.direction == 'brighton'),'stop_id'] = 'D35S'
    
    plt_stop_id = ee[['station_name','from','line','direction','stop_id']]
    plt_stop_id = plt_stop_id[plt_stop_id.stop_id != '']
    plt_stop_id['platform_id'] = plt_stop_id['from']
    plt_stop_id = plt_stop_id[['station_name','platform_id','line','direction','stop_id']]

    plt_stop_id.to_csv(opts.output,index=False)
    
if __name__ == "__main__":
    main()