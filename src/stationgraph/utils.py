import re

# Splits elevator description into different levels. If
# there's no levels to split, returns the original value
# in a list.
def split_elevator_description(desc):
    # try "to" first
    m = re.search(r'^(.*?) (to|and) (.*)$', desc)
    if m:
        return [m.group(1), m.group(3)]

    return [desc]


# recursively splits elevator description into different levels
def split_elevator_description_rec(desc):
    floors = split_elevator_description(desc)
    if len(floors) > 1:
        rez = [floors[0]]
        rez.extend(split_elevator_description_rec(floors[1]))
        return rez
    return floors
