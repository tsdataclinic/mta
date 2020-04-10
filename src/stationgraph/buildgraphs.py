#
# Build a graph describing the layout of each station based on data
# from the MTA's elevator and escalator equipment file. We also
# incorporate an override file, since some of the MTA descriptions
# too difficult for this simple program to understand. Writes to
# stdout.
#
import argparse
import pandas as pd
import re
import sys


def load_equipment(master_file, with_inactive=False, with_inaccessible=False, with_escalators=False, with_elevators=True):
    equipment = pd.read_csv(master_file)

    # filter by equipment
    equipment_type = []
    if with_escalators:
        equipment_type.append('ES')
    if with_elevators:
        equipment_type.append('EL')
    equipment = equipment[ equipment.equipment_type.isin(equipment_type) ]

    # filter by active
    if not with_inactive:
        equipment = equipment[ equipment.is_active == 'Y' ]

    # filter by accessibility
    if not with_inaccessible:
        equipment = equipment[ equipment.ada_compliant == 'Y' ]

    # discard columns we don't need
    equipment = equipment[["station_name", "equipment_id", "description", "connection_to_street"]]

    return equipment


def load_platforms(platform_file):
    platforms = pd.read_csv(platform_file)

    # ensure the expected columns are present
    platforms = platforms[["equipment_id", "line", "direction"]]

    return platforms


def load_overrides(override_file):
    columns = ["station_name", "equipment_id", "from", "to", "platform_id"]
    if override_file is None:
        return pd.DataFrame(columns=columns)

    overrides = pd.read_csv(override_file)

    # ensure the expected columns are present
    overrides = overrides[columns]

    return overrides


def merge_platforms(equipment, platforms):
    # the MTA direction information is incomplete!
    platform_ids = platforms[['equipment_id', 'line', 'direction']].set_index('equipment_id')
    platform_ids = platform_ids.apply(lambda t : '-'.join(t), axis=1).groupby(level=0).unique()
    platform_ids = platform_ids.apply(lambda t : '/'.join(sorted(t)))
    equipment = equipment.set_index('equipment_id')
    equipment['platform_id'] = platform_ids
    equipment.reset_index(inplace=True)
    return equipment


def merge_overrides(equipment, overrides):
    # discard any old data for elevators described in the override file
    equipment = equipment[~equipment.equipment_id.isin(overrides.equipment_id.unique())]
    # now append the overrides
    equipment = equipment.append(overrides, sort=True)

    return equipment


def identify_edges(equipment):
    def elevator_route(desc):
        def simplify(name):
            if re.match(r'.*[Pp]latform.*', name):
                return 'Platform'
            if re.match(r'.*(St|Av|Plaza|Blvd|Park|Sidewalk|Pl|Rd|Square).*', name):
                return 'Street'
            if re.match(r'.*Upper Mezzanine.*', name):
                return 'Upper Mezzanine'
            if re.match(r'.*Lower Mezzanine.*', name):
                return 'Lower Mezzanine'
            if re.match(r'.*([Mm]ezzanine|[Bb]alcony).*', name):
                return 'Mezzanine'
            if re.match(r'.*[Bb]alcony.*', name):
                return 'Balcony'
            if name in ['PA Bus Terminal', 'Oculus Main Level']:
                return 'Street'
            return 'Unknown'

        # try "to" and "for" first
        m = re.search(r'^(.*?) (to|for) (.*)$', desc)
        if m:
            return simplify(m.group(1)), simplify(m.group(3))
        # then try for "and"
        m = re.search(r'^(.*?) (and) (.*)$', desc)
        if m:
            return simplify(m.group(1)), simplify(m.group(3))

        if re.match('^Mezzanine .*bound Platform$', desc):
            return ('Mezzanine', 'Platform')

        return ('Unknown', 'Unknown')

    # some sanity tests
    assert elevator_route('125 St & Lexington Ave to Mezzanine for service in both directions') == ('Street', 'Mezzanine')
    assert elevator_route('Mezzanine to Platform for downtown A/C service') == ('Mezzanine', 'Platform')
    assert elevator_route('Mezzanine to Platforms for service in both directions') == ('Mezzanine', 'Platform')
    assert elevator_route('Mezzanine to uptown Platform') == ('Mezzanine', 'Platform')
    assert elevator_route('161 St & River Ave (NE Corner) to Mezzanine to reach service in both directions') == ('Street', 'Mezzanine')
    assert elevator_route('Street to # 6 Northbound platform') == ('Street', 'Platform')
    assert elevator_route('Sidewalk entrance (east of the pedestrian skybridge) to Manhattan bound Platform') == ('Street', 'Platform')
    assert elevator_route('G and 7 Mezzanines to Flushing-bound 7 Platform') == ('Mezzanine', 'Platform')

    from_col = equipment.description.apply(lambda d : elevator_route(d)[0])
    # some elevators record the street part explicitly
    from_col.loc[equipment['connection_to_street'] == 'Y'] = 'Street'

    to_col = equipment.description.apply(lambda d : elevator_route(d)[1])

    return pd.DataFrame({'from': from_col, 'to': to_col})

def canonical_names(equipment):        
    def make_canon(t):
        label, station, platform_id = t
        if label == 'Unknown':
            return 'Unknown-' + station
        if label == 'Platform':
            return '-'.join([str(x) for x in [label, station, platform_id]])
        return '-'.join([str(x) for x in [label, station]])

    return pd.DataFrame({
        'fqn_from'  : equipment[['from', 'station_name', 'platform_id']].apply(make_canon, axis=1),
        'fqn_to'    : equipment[['to', 'station_name', 'platform_id']].apply(make_canon, axis=1),
        'label_from': equipment[['from', 'station_name']].apply(lambda t : t[1] if t[0] == 'Street' else t[0], axis=1),
        'label_to'  : equipment['to']})


def main():
    parser = argparse.ArgumentParser("Station graph builder")
    parser.add_argument("--master-list", required=True)
    parser.add_argument("--override-list",  required=False)
    parser.add_argument("--platform-list",  required=True)
    parser.add_argument("--output", required=False)
    parser.add_argument("--inactive", dest="inactive", action="store_true", required=False, default=False)
    parser.add_argument("--no-inactive", dest="inactive", action="store_false", required=False)
    parser.add_argument("--inaccessible", dest="inaccessible", action="store_true", required=False, default=False)
    parser.add_argument("--no-inaccessible", dest="inaccessible", action="store_false", required=False)
    parser.add_argument("--escalators", dest="escalators", action="store_true", required=False, default=False)
    parser.add_argument("--no-escalators", dest="escalators", action="store_false", required=False)
    parser.add_argument("--elevators", dest="elevators", action="store_true", required=False, default=True)
    parser.add_argument("--no-elevators", dest="elevators", action="store_false", required=False)
    parser.add_argument("--verbose", dest="verbose", action="store_true", required=False, default=False)

    opts = parser.parse_args()

    log = (lambda hdr,df: print("==={}===\n{}".format(hdr, df.head()), file=sys.stderr)
          ) if opts.verbose else (lambda hdr,df: None)

    equipment = load_equipment(opts.master_list,
                               with_inactive=opts.inactive, with_inaccessible=opts.inaccessible,
                               with_escalators=opts.escalators, with_elevators=opts.elevators)
    log("Equipment", equipment)

    platforms = load_platforms(opts.platform_list)
    log("Platforms", platforms)

    overrides = load_overrides(opts.override_list)
    log("Overrides", overrides)

    equipment = merge_platforms(equipment, platforms)
    log("Merged 1", equipment)

    from_to = identify_edges(equipment)
    equipment = pd.concat([equipment, from_to], axis=1, sort=False)
    log("Merged 2", equipment)

    column_names = ['station_name','equipment_id','from','to','platform_id']
    equipment = equipment[column_names]
    equipment = merge_overrides(equipment, overrides)
    log("Merged 3", equipment)

    equipment.to_csv(sys.stdout if opts.output is None else opts.output,
                     index=False, columns=column_names)

    #canonical_cols = canonical_names(equipment)
    #equipment = pd.concat([equipment, canonical_cols], axis=1, sort=False)
    #print("===Merged===")
    #print(equipment.head())


if __name__ == "__main__":
    main()

