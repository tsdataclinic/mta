#!/usr/bin/env python
# coding: utf-8
import argparse
import numpy as np
import pandas as pd
import sys

from datetime import datetime, time


# route_ids 2 characters or longer are special service trains, with the
# exception of the Staten Island route
def remove_special_case_lines(r):
    return len(r) == 1 or r == "SI"


# Transit timestamps can have an hour greater than 23 to represent that day's
# service extending into the next day. So a train at 3am might be 27h.
def fix_24h(timestamp):
    hour = int(timestamp[:2])
    if hour >= 24:
        return f"{hour % 24}{timestamp[2:]}"
    return timestamp


# This converts the string timestamp into a datetime value
def convert_to_datetime(timestamp):
    return datetime.strptime(fix_24h(timestamp), '%H:%M:%S').time()


# Takes an ordered list and returns a list of adjacent pairs
def get_adjacent_conns(l):
    return [f"{l[i]},{l[i+1]}" for i in range(len(l) - 1)]


# This generates station to station connections for weekday, day-time service
def main():
    parser = argparse.ArgumentParser("Station graph builder")
    parser.add_argument("--routes", required=True)
    parser.add_argument("--stop-times", required=True)
    parser.add_argument("--output", required=False)

    opts = parser.parse_args()
    routes = pd.read_csv(opts.routes)
    routes = routes[
            (routes.route_type == 1) & # subway routes
            (routes.route_id.apply(remove_special_case_lines))]

    stop_times = pd.read_csv(opts.stop_times)
    stop_times.arrival_time = stop_times.arrival_time.apply(convert_to_datetime)
    stop_times = stop_times[
            (stop_times.trip_id.str.contains('Weekday')) & # filter to weekday
            (stop_times.arrival_time >= time(hour=7)) & # filter to day-time service
            (stop_times.arrival_time <= time(hour=19))]

    # get list of stops in order for a train's route
    station_conns = stop_times.sort_values(['stop_sequence']) \
        .groupby(['trip_id'], sort=False)['stop_id'] \
        .apply(list).reset_index(name='stations')
    station_conns['stations'] = station_conns['stations'].apply(get_adjacent_conns)
    # explode column into separate rows
    station_conns = station_conns.set_index('trip_id').stations \
        .apply(pd.Series).stack() \
        .reset_index(level=0) \
        .rename(columns={0:'stations'})

    # extract line from trip id
    station_conns['line'] = station_conns.trip_id.str.extract(r'.*_(\w*)\..*')
    # filter special case lines
    station_conns = station_conns[station_conns.line.apply(remove_special_case_lines)]

    # get trips between stations by line
    station_conns = station_conns.groupby(['line', 'stations']).size().to_frame('num_trips').reset_index()
    station_conns[['from','to']] = station_conns.stations.str.split(",", expand=True)

    # filter out a few routes that are not part of normal advertised service
    filter_conns = station_conns[station_conns.num_trips >= 10]
    filter_conns[['from', 'to', 'line']].to_csv(sys.stdout if opts.output is None else opts.output, index=False)


if __name__ == "__main__":
    main()
