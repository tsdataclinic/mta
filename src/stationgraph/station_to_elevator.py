#!/usr/bin/env python

import argparse
import pandas as pd
import re
import sys
import geopandas as gp
import json
import itertools

from utils import split_elevator_description_rec


def get_all_lines(desc, fallback):
    # some sanity tests
    assert get_lines_on_floor("platform for downtown a/c service", "") == (["A", "C"], ["south"])
    assert get_lines_on_floor("platform for a line", "") == (["A"], ["north", "south"])
    assert get_lines_on_floor("platform", "A/B") == (["A", "B"], ["north", "south"])
    assert get_lines_on_floor("southbound platform", "A/B") == (["A", "B"], ["south"])
    assert get_lines_on_floor("7 platform for service in both directions", "") == (["7"], ["north", "south"])
    assert get_lines_on_floor("7/A/W platform for service in both directions", "") == (["7", "W", "A"], ["north", "south"])

    desc = desc.lower()
    floors = split_elevator_description_rec(desc)
    rez = []
    for floor in floors:
        lines = get_lines_on_floor(floor, fallback)
        if lines:
            rez.append(lines)
    return rez

platform = {"line", "service", "train", "platform", "terminal"}
line_regex = f'(?:^| )(\w(?:/\w)*) ({"|".join(platform)})'

def is_platform_floor(floor):
    for synonym in platform:
        if synonym in floor:
            return True
    return False

def get_lines_on_floor(floor, fallback):
    # exclude floors that don't serve trains
    if "mezzanine" in floor or not is_platform_floor(floor):
        return None

    if "mezzanine below 7 line (one level up), platform of flushing main st" in floor:
        return None

    if floor is "downtown A/B/C/D & 1 platforms":
        return (["A", "B", "C", "D", "1"], "south")

    directions = get_canon_direction(floor)

    # get list of lines served by the floor
    lines = []
    for match in re.findall(line_regex, floor):
        lines.extend(match[0].split("/"))

    if lines:
        return ([x.upper() for x in set(lines)], directions)
    else:
        return (fallback.split("/"), directions)

dir_map = {
    "uptown": ["north"],
    "both directions": ["north", "south"],
    "downtown": ["south"],
}

def get_canon_direction(x):
    output = set()

    x = x.lower()

    # look for usage of north/south
    north_r = re.findall('uptown|north|both directions', x)
    south_r = re.findall('downtown|south|both directions', x)
    if north_r:
        output.update(north_r)
    if south_r:
        output.update(south_r)

    # grab the direction a train is bound for
    bound_to_r = re.search('(?:to|for) (.*)-bound', x)
    if not bound_to_r:
        to = bound_to_r = re.search('(.*)-bound', x)
    if bound_to_r:
        to = bound_to_r.group(1).split(" and ")
        to = [v.replace("the", "").strip() for v in to]
        output.update(to)

    # combine similar directions
    rez = set()
    for o in output:
        rez.update(dir_map.get(o, [o]))
    return list(rez) if len(rez) > 0 else ['north', 'south']


def expand_all(data):
    rez = []
    for lines in data.subway_lines:
        for r in itertools.product(lines[0], lines[1]):
            rez.append((r[0], r[1], data.station_name))

    return rez

def format_for_output(inp):
    lines = inp.all_combos.apply(pd.Series) \
        .merge(inp[['equipment_id']], right_index = True, left_index = True) \
        .melt(id_vars = ['equipment_id'], value_name = "all_combos") \
        .drop("variable", axis = 1) \
        .dropna() \
        .sort_values(by=['equipment_id'])
    lines["line"] = lines.all_combos.apply(lambda x : x[0])
    lines["direction"] = lines.all_combos.apply(lambda x : x[1])
    lines["station"] = lines.all_combos.apply(lambda x : x[2])
    lines = lines.drop("all_combos", axis=1)
    return lines

def main():
    parser = argparse.ArgumentParser("Station graph builder")
    parser.add_argument("--master-list", required=True)
    parser.add_argument("--output", required=False)

    opts = parser.parse_args()

    elevators = pd.read_csv(opts.master_list)
    # filter to ada compliant elevators that serve a train platform

    elevators = elevators[
            (elevators.equipment_type == 'EL') &
            (elevators.ada_compliant == 'Y') &
            (elevators.description.str.contains('platform', case = False, regex = False))]

    # add subway lines to each description row
    elevators["subway_lines"] = elevators.apply(lambda x: get_all_lines(x.description, x.subway_lines), axis=1)

    # explode to create a row per line, direction, station
    elevators["all_combos"] = elevators.apply(lambda x: expand_all(x), axis=1)

    output = format_for_output(elevators)
    output.to_csv(sys.stdout if opts.output is None else opts.output, index=False)

if __name__ == "__main__":
    main()
