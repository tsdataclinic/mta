import pandas as pd
import geopandas as gpd
import re
import textdistance
import numpy as np
import math

def make_ordinal(s):
    ordinal = lambda n: "%d%s" % (n,"tsnrhtdd"[(math.floor(n/10)%10!=1)*(n%10<4)*n%10::4])
    
    name_ord = []
    for x in s:
        x = x.title()
        m = re.findall(r'\d+', x)
        if(len(m) > 0):
            num = m[0]
            t = re.sub('{}'.format(num), ordinal(int(num)), x)
            name_ord.append(t)
        else:
            t = x
            name_ord.append(t)
    return name_ord


def main():
    elevator_list = pd.read_csv('../../data/raw/EE_master_list.csv')
    stations = gpd.read_file('../../data/raw/subway_stations.geojson')
    turnstile_remotes = pd.read_excel('../../data/raw/Remote-Booth-Station.xls')
    gtfs = pd.read_csv('../../data/raw/google_transit/stops.txt')
    
    turnstile_remotes['Line Name'] = turnstile_remotes['Line Name'].astype(str)
    gtfs = gtfs[gtfs.location_type == 1]
    
    gtfs_routes = pd.read_csv('../../data/raw/google_transit/routes.txt')
    gtfs_trips = pd.read_csv('../../data/raw/google_transit/trips.txt')
    gtfs_stop_times = pd.read_csv('../../data/raw/google_transit/stop_times.txt')
    
    ## Getting lines for each GTFS Stop ID
    gtfs_stop_times = gtfs_stop_times[gtfs_stop_times.trip_id.str.contains('Weekday')]
    gtfs_lines = gtfs_stop_times.merge(gtfs_trips,on="trip_id")
    gtfs_lines = gtfs_lines.merge(gtfs_routes,on='route_id')
    
    gtfs_lines['stop_id'] = [re.sub('N$|S$','',x) for x in gtfs_lines.stop_id]
    gtfs_lines['lines'] = gtfs_lines[['stop_id','route_short_name']].groupby(['stop_id'])['route_short_name'].transform(lambda x:
                                                                                                                        ','.join(x.unique()))
    gtfs_lines = gtfs_lines[['stop_id','lines']]
    gtfs_lines = gtfs_lines.drop_duplicates()
    gtfs = gtfs.merge(gtfs_lines[['stop_id','lines']],how='left',on='stop_id')
    gtfs = gtfs[~gtfs.lines.isnull()]
    
    ## Standardization
    stations = pd.DataFrame(stations.drop('geometry',axis=1))
    
    # Standardizing names
    stations['name_ord'] = stations.name
    turnstile_remotes['name_ord'] = make_ordinal(turnstile_remotes.Station)
    elevator_list['name_ord'] = make_ordinal(elevator_list.station_name)
    gtfs['name_ord'] = make_ordinal(gtfs.stop_name)
    
    # Standardizing lines
    stations["clean_lines"] = [re.sub('-','',re.sub('-\d+ Express','',x)) for x in stations.line]
    turnstile_remotes['clean_lines'] = [re.sub('-','',re.sub(r'(\w)(?!$)',r'\1-',str(x))) for x in turnstile_remotes['Line Name']]
    elevator_list['clean_lines'] = [re.sub('-','',re.sub('/', '-',re.sub('(/METRO-NORTH)|(/LIRR)','', x))) for x in
                                    elevator_list.subway_lines]
    gtfs['clean_lines'] = [re.sub('-','',re.sub(',','-',re.sub(',((\d)|(\w))X','',x))) for x in gtfs.lines]
    
    # Dropping unnecessary columns
    stations = stations[['name','name_ord','clean_lines','line']]
    elevator_list = elevator_list[['equipment_id','station_name','name_ord','clean_lines','subway_lines']]
    turnstile_remotes = turnstile_remotes[['Remote','Station','name_ord','clean_lines','Line Name']]
    gtfs = gtfs[['stop_id','stop_name','stop_lat','stop_lon','name_ord','clean_lines','lines']]
    
    ###### Text Matching
    elevator_list.reset_index(drop=True,inplace=True)
    elevator_list['station_match'] = ''
    elevator_list['station_lines'] = ''
    for i,row in elevator_list.iterrows():
        ## station matching lines
        st_line_matches = [y if len(textdistance.lcsstr(row.clean_lines,y)) > 0 else None for y in stations.clean_lines]
        st_line_matches = [x for x in st_line_matches if x is not None]
        st_subset = stations[stations.clean_lines.isin(st_line_matches)] 

        ## Fails to find the right match for just 59th St
        if row.station_name == '59 St':
            continue

        ## elevator
        if st_subset.shape[0] > 0:
            st_dist = [textdistance.jaccard(row.name_ord,y) for y in st_subset.name_ord]
            st_match = st_subset.iloc[np.argmax(st_dist),]
            st_score = max(st_dist)
            if st_score > 0.75:
                elevator_list.iloc[i,][['station_match','station_lines']] = st_match[['name_ord','line']]
            else:
                st_dist = [textdistance.jaro_winkler(row.name_ord,y) for y in st_subset.name_ord]
                st_match = st_subset.iloc[np.argmax(st_dist),]
                st_score = max(st_dist)
                elevator_list.iloc[i,][['station_match','station_lines']] = st_match[['name_ord','line']]
                
    ## Manual overrides
    elevator_list.loc[(elevator_list.station_name == '57 St - 7 Av')&(elevator_list.station_match == ''),
                      ['clean_lines','station_match','station_lines']] = ['NQRW','57th St','N-Q-R-W']
    elevator_list.loc[(elevator_list.station_name == '59 St')&(elevator_list.station_match == ''),
                      ['clean_lines','station_match','station_lines']] = ['456','Lexington Ave - 59th St','4-5-6-6 Express']
    elevator_list.loc[(elevator_list.station_name == '68 St / Hunter College')&(elevator_list.station_match == ''),
                      ['clean_lines','station_match','station_lines']] = ['46','68th St - Hunter College','4-6-6 Express']
    elevator_list.loc[(elevator_list.station_name == '86 St')&(elevator_list.station_match == ''),
                      ['clean_lines','station_match','station_lines']] = ['456','86th St','4-5-6-6 Express']
    elevator_list.loc[(elevator_list.station_name == 'Bedford Park Blvd/Grand Concourse Line')&(elevator_list.station_match == ''),
                      ['clean_lines','station_match','station_lines']] = ['BD','Bedford Park Blvd','B-D']
    elevator_list.loc[(elevator_list.station_name == 'Chambers St')&(elevator_list.station_match == ''),
                      ['clean_lines','station_match','station_lines']] = ['JZ','Chambers St','J-Z']
    
    el_station_merge = elevator_list.copy()
    el_station_merge['equipments'] = el_station_merge.groupby(['station_match','station_lines'])['equipment_id'].transform(lambda x :
                                                                                                                        ','.join(x.unique()))
    
    el_station_merge.drop(['equipment_id','name_ord'],axis=1,inplace=True)
    el_station_merge = el_station_merge.drop_duplicates()
    
    crosswalk = stations.merge(el_station_merge,how='left',left_on=['name','line'],right_on=['station_match','station_lines'])
    crosswalk.rename(columns={'clean_lines_x':'clean_lines','station_name':'el_station_name','subway_lines':'el_lines'},inplace=True)
    crosswalk.drop(['station_match','station_lines','clean_lines_y'],axis=1,inplace=True)
    crosswalk.fillna('',inplace=True)
    
    ## Matching GTFS
    crosswalk.reset_index(drop=True,inplace=True)
    crosswalk['gtfs_station_name'] = ''
    crosswalk['gtfs_lines'] = ''

    for i,row in crosswalk.iterrows():
        ## gtfs matching lines
        gtfs_line_matches = [y if len(textdistance.lcsstr(row.clean_lines,y)) > 0 else None for y in gtfs.clean_lines]
        gtfs_line_matches = [x for x in gtfs_line_matches if x is not None]
        gtfs_subset = gtfs[gtfs.clean_lines.isin(gtfs_line_matches)]

        ###### distances
        ## exceptions where it fails
        if((row.name_ord == '46th St') | (row.name_ord == '57th St')):
            continue

        if gtfs_subset.shape[0] > 0:
            gtfs_dist = [textdistance.jaccard(row.name_ord,y) for y in gtfs_subset.name_ord]
            gtfs_match = gtfs_subset.iloc[np.argmax(gtfs_dist),]
            gtfs_score = max(gtfs_dist)
            if gtfs_score > 0.88:
                crosswalk.iloc[i,][['gtfs_station_name','gtfs_lines']] = gtfs_match[['stop_name','lines']]
            else:
                gtfs_dist = [textdistance.jaro_winkler(row.name_ord,y) for y in gtfs_subset.name_ord]
                gtfs_match = gtfs_subset.iloc[np.argmax(gtfs_dist),]
                gtfs_score = max(gtfs_dist)
                if gtfs_score > 0.74:
                    crosswalk.iloc[i,][['gtfs_station_name','gtfs_lines']] = gtfs_match[['stop_name','lines']]
                    
    
    ## Manual overrides
    crosswalk.loc[(crosswalk.name_ord == 'Lexington Ave - 59th St')&(crosswalk.gtfs_station_name == ''),
                  ['gtfs_station_name','gtfs_lines']] = ['59 St','4,5,5X,6,6X']
    crosswalk.loc[(crosswalk.name_ord == 'Long Island City - Court Sq')&(crosswalk.gtfs_station_name == ''),
                  ['gtfs_station_name','gtfs_lines']] = ['Court Sq - 23 St','G']
    crosswalk.loc[(crosswalk.name_ord == '46th St')&(crosswalk.clean_lines=='EMR')&(crosswalk.gtfs_station_name == ''),
                  ['gtfs_station_name','gtfs_lines']] = ['46 St','E,M,R']
    crosswalk.loc[(crosswalk.name_ord == '46th St')&(crosswalk.clean_lines=='7')&(crosswalk.gtfs_station_name == ''),
                  ['gtfs_station_name','gtfs_lines']] = ['46 St - Bliss St','7']
    crosswalk.loc[(crosswalk.name_ord == 'Gravesend - 86th St')&(crosswalk.gtfs_station_name == ''),
                  ['gtfs_station_name','gtfs_lines']] = ['86 St','N,W,Q']
    crosswalk.loc[(crosswalk.name_ord == 'Lower East Side - 2nd Ave')&(crosswalk.gtfs_station_name == ''),
                  ['gtfs_station_name','gtfs_lines']] = ['2 Av','F,FX']
    crosswalk.loc[(crosswalk.name_ord == '57th St')&(crosswalk.clean_lines=='F')&(crosswalk.gtfs_station_name == ''),
                  ['gtfs_station_name','gtfs_lines']] = ['57 St','F,FX,M']
    crosswalk.loc[(crosswalk.name_ord == '57th St')&(crosswalk.clean_lines=='NQRW')&(crosswalk.gtfs_station_name == ''),
                  ['gtfs_station_name','gtfs_lines']] = ['57 St - 7 Av','N,W,Q,R']
    
    
    
    ##### Turnstile
    stations_w_issues = ['36th Ave','111th St','168th St','104th St','7th Ave','28th St','39th Ave','81st St','30th Ave', 
                         'Broadway Junction','49th St', '57th St', '80th St','96th St','176th St']
    
    crosswalk.reset_index(drop=True,inplace=True)
    crosswalk['turnstile_station_name'] = ''
    crosswalk['turnstile_lines'] = ''

    for i,row in crosswalk.iterrows():
        ## turnstile matching lines
        ts_line_matches = [y if len(textdistance.lcsstr(row.clean_lines,y)) > 0 else None for y in turnstile_remotes.clean_lines]
        ts_line_matches = [x for x in ts_line_matches if x is not None]
        ts_subset = turnstile_remotes[turnstile_remotes.clean_lines.isin(ts_line_matches)]

        ##### distances
        if (row.name_ord in stations_w_issues):
            continue

        # turnstile
        if ts_subset.shape[0] > 0:
            ts_dist = [textdistance.jaccard(row.name_ord,y) for y in ts_subset.name_ord]
            ts_match = ts_subset.iloc[np.argmax(ts_dist),]
            ts_score = max(ts_dist)
            if ts_score > 0.88:
                crosswalk.iloc[i,][['turnstile_station_name','turnstile_lines']] = ts_match[['Station','Line Name']]
            else:
                ts_dist = [textdistance.jaro_winkler(row.name_ord,y) for y in ts_subset.name_ord]
                ts_match = ts_subset.iloc[np.argmax(ts_dist),]
                ts_score = max(ts_dist)
                if ts_score > 0.81:
                    crosswalk.iloc[i,][['turnstile_station_name','turnstile_lines']] = ts_match[['Station','Line Name']]
    
    missing_vals = crosswalk[crosswalk.turnstile_station_name == ''][['name','clean_lines']]
    missing_vals.reset_index(drop=True,inplace=True)
    
    ## manual overrides
    ts_override = [['MAIN ST','7'],['138 ST-3 AVE','6'],['42 ST-GRD CNTRL','4567S'],['96 ST','6'],['61 ST/WOODSIDE','7'],['96 ST','BC'],
    ['168 ST-BROADWAY','1AC'],['UNION TPK-KEW G','EF'],['WASHINGTON-36 A','NQ'],['42 ST-GRD CNTRL','4567S'],['GREENWOOD-111','A'],
    ['OXFORD-104 ST','A'],['7 AV-PARK SLOPE','FG'],['7 AVE','BQ'],['FLATBUSH AVE','25'],['28 ST-BROADWAY','NR'],['COURT SQ','EMG'],
    ['VAN ALSTON-21ST','G'],['BEEBE-39 AVE','NQ'],['96 ST','123'],['110 ST-CPN','23'],['81 ST-MUSEUM','BC'],['110 ST-CATHEDRL','1'],['176 ST','4'],
    ['168 ST-BROADWAY','1AC'],['111 ST','7'],['LEFFERTS BLVD','A'],['28 ST','1'],['28 ST','6'],['42 ST-GRD CNTRL','4567S'],['FOREST PARKWAY','J'],
    ['111 ST','J'],['MYRTLE AVE','LM'],['ROCKAWAY PKY','L'],['EAST 105 ST','L'],['BROADWAY-ENY','ACJLZ'],['ELDERTS LANE','JZ'],['MYRTLE AVE','LM'],
    ['VAN WYCK BLVD','EF'],['HOYT ST-ASTORIA','NQ'],['DITMARS BL-31 S','NQ'],['148 ST-LENOX','3'],['242 ST','1'],['E TREMONT AVE','25'],['DYRE AVE','5'],
    ['BROADWAY-ENY','ACJLZ'],['149 ST-3 AVE','25'],['GRAND-30 AVE','NQ'],['NEW UTRECHT AVE','ND'],['86 ST','N'],['22 AVE-BAY PKY','F'],
    ['7 AVE-53 ST','BDE'],['57 ST','F'],['49 ST-7 AVE','NQR'],['57 ST-7 AVE','NQR'],['57 ST-7 AVE','NQR'],['2 AVE','F'],['BOROUGH HALL/CT','2345R'],['BROADWAY-ENY','ACJLZ'],
    ['BROOKLYN BRIDGE','456JZ'],['METROPOLITAN AV','M'],['ROOSEVELT AVE','EFMR7'],['E 177 ST-PARKCH','6'],['HUDSON-80 ST','A'],['STILLWELL AVE','DFNQ'],['34 ST-HUDSON YD','7'],
    ['72 ST-2 AVE','Q'],['86 ST-2 AVE','Q'],['96 ST-2 AVE','Q']]

    
    turnstile_override = pd.DataFrame(ts_override)
    turnstile_override.rename(columns={0:'turnstile_station_name',1:'turnstile_lines'},inplace=True)

    turnstile_override = pd.concat([missing_vals,turnstile_override],axis=1)
    
    for i,row in crosswalk.iterrows():
        if (row.turnstile_station_name == ''):
            ts_match = turnstile_override[(turnstile_override.name == row.name_ord)&
                                          (turnstile_override.clean_lines == row.clean_lines)][['turnstile_station_name','turnstile_lines']]
            crosswalk.iloc[i,][['turnstile_station_name','turnstile_lines']] = ts_match.values[0]
            
    crosswalk.drop('name_ord',axis=1,inplace=True)
    crosswalk.rename(columns={'name':'station_name','line':'station_lines'},inplace=True)
    
    crosswalk = crosswalk.merge(gtfs.drop('name_ord',axis=1),how='left',left_on=['gtfs_station_name','gtfs_lines'],right_on=['stop_name','lines'])
    
    crosswalk.drop(['stop_name','clean_lines_y','lines'],axis=1,inplace=True)
    crosswalk.rename(columns={'stop_id':'gtfs_stop_id','stop_lat':'lat','stop_lon':'lon','clean_lines_x':'clean_lines'},inplace=True)
    
    turnstile_remotes['turnstile_units'] = turnstile_remotes.groupby(['Station','Line Name'])['Remote'].transform(lambda x : ','.join(x.unique()))
    
    turnstile_merge = turnstile_remotes.drop(['Remote','name_ord','clean_lines'],axis=1).drop_duplicates()

    crosswalk = crosswalk.merge(turnstile_merge,how='left',left_on=['turnstile_station_name','turnstile_lines'],right_on=['Station','Line Name']).drop(['Station','Line Name'],axis=1)
    
    ## adding missing units
    crosswalk.loc[(crosswalk.station_name == '34th St - Hudson Yards')&(crosswalk.clean_lines == '7'),['turnstile_units']] = ['R072']
    crosswalk.loc[(crosswalk.station_name == '72nd St')&(crosswalk.clean_lines == 'Q'),['turnstile_units']] = ['R570']
    crosswalk.loc[(crosswalk.station_name == '86th St')&(crosswalk.clean_lines == 'Q'),['turnstile_units']] = ['R571']
    crosswalk.loc[(crosswalk.station_name == '96th St')&(crosswalk.clean_lines == 'Q'),['turnstile_units']] = ['R572']
    
    crosswalk.to_csv('../../data/crosswalk/Master_crosswalk.csv',index=False)

if __name__ == "__main__":
    main()