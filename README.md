# mta_data_repo
During a Data Clinic Hack Day back in December 2019, we set out to use open data to better understand the impact of elevator outages within the NYC subway system. Our goal was to use the insights we derived to a) offer a data-driven method to prioritize and schedule elevator maintenance to minimize rider impact, b) enhance alternative routing capabilities during outages, and c) inspire members of the public to build solutions, tools, apps, etc. to support elevator riders navigate the subway system more effectively.

We made a lot of headway that day, but given the complexity of the data on subway systems, elevators, and ridership, we turned the Hack Day investigation into a full-fledged project. While we continue to work on additional analyses and dataset, in the short term, we are releasing three initial data products in this repo:

1. **Accessible station elevator maps:** Using open data on elevator descriptions and some crowdsourcing efforts, we have built a graph/network for each of the 125 accessible stations in the subway system. The graph maps possible street to platform connections using only elevators. The accessibility graphs are available to download as graphml files and as figures for each station at the below links.  
    - [Data in graphml format](data/processed/stationgraph)
    - [Figures for each station](figures/elevator_maps)

2. **Turnstile Data Processing:** A script to pull, process, and standardize turnstile usage data for ease of use in analysis. The processing involves data cleaning to correct for integer overflows and interpolation to standardize time of measurement across all turnstiles. You can find a list of CSVs for each station containing data from the start of 2020 to date [here](turnstile_station_data.md).

3. **Crosswalks:** Mapping variations in station names across elevator listing data, turnstile usage data, station location data, and GTFS data. This will provide a consolidated crosswalk that enables all datasets to be easily merged with each other at the station level. The crosswalk linking these different MTA data sets is pre-generated and made available [here](data/crosswalk/Master_crosswalk.csv)

## Getting Started
You can set-up the environment needed to run this project using conda as below:
- Add conda-forge to the config and
- Install the conda environment named {env_name} from the requirements file

```
conda config --append channels conda-forge
conda create -n {env_name} --file requirements.txt

## to have the environment showup as a kernel on jupyter
python -m ipykernel install --user --name {env_name} --display-name "Python ({env_name})"
```
A Dockerfile is also available to run the project within a container.

## Project Description

### Accessibility Graph for stations

To run the below defined pipeline to generate the accessibility graphs for stations, you simply need to run `make` from the project directory.

```bash
# This looks for any changes in file dependencies and runs only the parts of the pipeline downstream from the it
make  

# This removes all the file dependencies and runs the full pipeline afresh
make clean
```

#### Pipeline Dependencies
```
get_equipment_list.py +---->station_to_elevator.py
                      |               +
                      |               |
                      |               v
                      +-------->buildgraphs.py
                      |               +
                      |               |
                      v               v
         visualize_graphs.R<---+csv2graphml.py
                                      +
                                      |
                                      v
                             assign_platform_ids.R
                                      +
   station_to_station.py              |
            +                         v
            |               map_platforms_to_GTFS.py
            |                         +
            |                         |
            |                         v
            +------->update_graph_w_station_connections.R
```
#### Pipeline descriptions
1. ``get_equipment_list.py`` - Gets the list of all equipment (elevators and escalators) and their descriptions from MTA Data portal.
1. ``station_to_elevator.py`` - Determines which elevators serve which platforms. It then extracts the line and direction of trains that will stop at each platform.
1. ``buildgraphs.py`` - Builds a map of floor to floor connections for each station. For our solution, we only consider ADA compliant elevators accessible via ADA compliant routes, but the script can include more via configuration.
1. ``csv2graphml.py`` - Turns the edgelist output of ``buildgraphs.py`` into a graphml file.
1. ``assign_platform_ids.R`` - Adds platform ids to the graph produced by ``csv2graphml.py``.
1. ``map_platforms_to_GTFS.py`` - Maps platform IDs to GTFS Stop IDs onto the output of ``assign_platform_ids.R``.
1. ``station_to_station.py`` - Uses ``GTFS_ROUTES`` and ``GTFS_STOP_TIMES`` to determine which platforms are connected by which trains. It is designed to determine the weekday schedule, which is what the standard NYC subway map shows.
1. ``update_graph_w_station_connections.R`` - Connects all the individual station maps together by the train lines that service them. It adds intermediary nodes for stations without any elevators, creating a complete  view of all stations in the subway system, mapped from street to train back to street via ADA compliant routes.
1. ``visualize_graphs.R`` - Produces individual station graphs.

### Turnstile Data

The script `process_turnstiles.py` provides a CLI for processing the turnstile data.

```bash
python process_turnstiles.py --help

usage: process_turnstiles.py [-h] [-s START] [-e END] [-i INTERVAL] [-o OUTPUT] [-m MANIFEST] [-p PREFIX]

Downloads turnstile data for a given time period, interpolates and aggregates to station level

optional arguments:
  -h, --help            show this help message and exit
  -s START, --start START
                        Date to start pulling data from
  -e END, --end END     Date to stop pulling data from
  -i INTERVAL, --interval INTERVAL
                        The interpolation interval, 1H, 15M etc
  -o OUTPUT, --output OUTPUT
                        Directory to output to.
  -m MANIFEST, --manifest MANIFEST
                        Create a manifest markdown file?
  -p PREFIX, --prefix PREFIX
                        Prefix to add on the the url's in the manifest
```

`src/turnstile.py` provides 3 methods to process turnstile data:

*download_turnstile_data* - Download MTA turnstile data from http://web.mta.info/developers/turnstile.html for a given data range

*get_hourly_turnstile_data* - Clean the raw data and generate linearly interpolated hourly turnstile entries/exits data. The clean up methodology is mainly based on https://www.kaggle.com/nieyuqi/mta-turnstile-data-analysis

*aggregate_turnstile_data_by_station* - Aggregate turnstile data created by get_hourly_turnstile_data by station using the station-to-turnstile mapping file (`data/crosswalk/ee_turnstile.csv`)

Jupyter notebook illustrating the usage can be found at `notebooks/Turnstile_sample.ipynb`


### Crosswalk
`make_crosswalk.py` contains the script used to generate a crosswalk of station names and lines between 
- Subway Stations GeoJSON (https://data.cityofnewyork.us/Transportation/Subway-Stations/arq3-7z49)
- Equipment list (Elevators and Escalators) ('http://advisory.mtanyct.info/eedevwebsvc/allequipments.aspx')
- Tunrstile Remote Unit/Control Area/Station Name Key (http://web.mta.info/developers/turnstile.html)
- New York City Transit Subway Static GTFS data (http://web.mta.info/developers/developer-data-terms.html#data)

### Directory Structure
    mta-accessibility/
    ├── LICENSE
    ├── README.md               <- The top-level README for developers using this project.
    ├── Makefile                <- Makefile with commands like `make` and `make clean`
    ├── process_turnstiles.py   <- Python script that provides a CLI for generating processed turnstile data
    │
    ├── data
    │   ├── crosswalk       <- Crosswalks between different MTA data sets.
    │   ├── processed       <- The final, canonical data sets.
    │   │   ├── stationgraph
    │   │   └── turnstile
    │   └── raw             <- The original, immutable data dump.
    │
    ├── figures             <- Generated graphics and figures to be used in reporting
    │
    ├── notebooks           <- Jupyter notebooks illustrating some of the code.
    │   ├── Crosswalk.ipynb
    │   └── Turnstile_sample.ipynb
    │
    ├── requirements.txt
    ├── setup.py
    │
    ├── src
    │   ├── crosswalks      <- Scripts used to generate crosswalks
    │   ├── stationgraph    <- Scripts to build accessibility graph for stations
    │   ├── turnstile       <- Scripts to download and process turnstile data
    │   └── visualization   <- Scripts to visualize graph data

--------

<p><small>Project based on the <a target="_blank" href="https://drivendata.github.io/cookiecutter-data-science/">cookiecutter data science project template</a>. #cookiecutterdatascience</small></p>
