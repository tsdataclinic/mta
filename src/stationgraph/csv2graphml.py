#
# Convert the output from buildgraphs.py from comma separated values
# into the standard graphml format. Reads from stdin and writes to
# stdout.
#
import argparse
import networkx as nx
import pandas as pd 
import sys

def add_to_graph(g, df):
    for _, row in df.iterrows():
        station = row['station_name']
        g.add_node(row['fqn_from'], node_type=row['from'], label=row['label_from'], station=station)
        g.add_node(row['fqn_to'], node_type=row['to'], label=row['label_to'], station=station)
        if isinstance(row['equipment_id'], str):
            g.add_node(row['equipment_id'], node_type='Elevator', label=row['equipment_id'], station=station)
            g.add_edge(row['fqn_from'], row['equipment_id'])
            g.add_edge(row['equipment_id'], row['fqn_to'])
        else:
            g.add_edge(row['fqn_from'], row['fqn_to'])
        if row['to'] == 'Platform' and isinstance(row['platform_id'], str):
            for train in row['platform_id'].split('/'):
                train_fqn = row['station_name'] + '-' + train
                g.add_node(train_fqn, node_type='Train', label=train, station=station)
                g.add_edge(row['fqn_to'], train_fqn)

    return g


def add_canonical_names(df):
    def make_canon(t):
        label, station, platform_id = t
        if label == 'Unknown':
            return 'Unknown-' + station
        if label == 'Platform':
            return '-'.join([str(x) for x in [label, station, platform_id]])
        return '-'.join([str(x) for x in [label, station]])

    df['fqn_from'] = df[['from', 'station_name', 'platform_id']].apply(make_canon, axis=1)
    df['fqn_to'] = df[['to', 'station_name', 'platform_id']].apply(make_canon, axis=1)

    return df


def add_labels(df):
    df['label_from'] = df[['from', 'station_name']].apply(lambda t : t[1] if t[0] == 'Street' else t[0], axis=1)
    df['label_to'] = df['to']
    return df


def main():
    parser = argparse.ArgumentParser("csv2graphml")
    parser.add_argument("--verbose", action="store_true", required=False, default=False)
    parser.add_argument("--pretty", action="store_true", required=False, default=False)
    parser.add_argument('stations', nargs="*")

    opts = parser.parse_args()

    log = (lambda txt: print(txt, file=sys.stderr)) if opts.verbose else (lambda txt: None)

    graph_in = pd.read_csv(sys.stdin)
    log("Read {} lines.".format(len(graph_in)))
    if opts.stations:
        log("Filtering by station: {}.".format(str(opts.stations)))
        graph_in = graph_in[graph_in.station_name.isin(opts.stations)]
        log("Filtered to {} lines.".format(len(graph_in)))

    graph_in = add_canonical_names(graph_in)
    graph_in = add_labels(graph_in)
    log("Added canonical names and labels.")
    graph_out = add_to_graph(nx.Graph(), graph_in)
    log("Constructed graph.")
    nx.write_graphml(graph_out, sys.stdout.buffer, prettyprint=opts.pretty)
    log("Done.")


if __name__ == "__main__":
    main()
