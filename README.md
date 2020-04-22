mta_data_repo
==============================

During a Data Clinic Hack Day back in December 2019, we set out to use open data to better understand how elevator outages impact riders in the hopes that any insights could empower the MTA to make data-informed decisions on prioritizing/scheduling elevator maintenance and to enhance the information they might choose to provide re: alternate routes, etc. Similarly, we hoped these insights would inspire and empower civic tech members of the public to build solutions, tools, apps, etc. to help elevator users navigate the subway system.

We made a lot of headway that day, but given the complexity of data on the subway system, its elevators, and its ridership, we turned the Hack Day investigation into a full-fledged project.
 
While we have many more exciting analyses and data products in the works, in the short term, we are releasing three initial resources in this repo:

1. **Accessible station elevator maps:** Using open data on elevator descriptions and some crowdsourcing efforts, we have built a graph/network for each of the 125 accessible stations in the subway system. The graph maps possible street to platform connections using only elevators. 

2. **Turnstile Data Processing:** A script to pull, process, and standardize turnstile usage data for ease of use in analysis. The processing involves data cleaning to correct for integer overflows and interpolation to standardize time of measurement across all turnstiles. 

3. **Crosswalks:** Mapping variations in station names across elevator listing data, turnstile usage data, station location data, and GTFS data. This will provide a consolidated crosswalk that enables all datasets to be easily merged with each other at the station level.

Getting Started
------------

You can set-up the environment needed to run this project using conda as below: 
- Add conda-forge to the config and 
- Install the conda environment named {env_name} from the requirements file 

```
conda config --append channels conda-forge
conda create -n {env_name} --file requirements.txt
```


Project Description
------------

Accessibility Graph for stations:


Turnstile Data:
`turnstile.py` provides 3 methods to process turnstile data:

*download_turnstile_data* - Download MTA turnstile data from http://web.mta.info/developers/turnstile.html for a given data range

*get_hourly_turnstile_data* - Clean the raw data and generate linearly interpolated hourly turnstile entries/exits data. The clean up methodology is mainly based on https://www.kaggle.com/nieyuqi/mta-turnstile-data-analysis

*aggregate_turnstile_data_by_station* - Aggregate turnstile data created by get_hourly_turnstile_data by station using the station-to-turnstile mapping file (`data/crosswalk/ee_turnstile.csv`)

Jupyter notebook illustrating the usage can be found at `notebooks/Turnstile_sample.ipynb`

Crosswalks:



### Directory Structure:

    mta-accessibility/
    ├── LICENSE
    ├── README.md           <- The top-level README for developers using this project.
    ├── Makefile            <- Makefile with commands like `make data` or `make train`
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
    ├── add_station_connections.sh
    ├── gen-graphs.sh
    │
    ├── notebooks           <- Jupyter notebooks illustrating some of the code.
    │   ├── Station_Graph.ipynb
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

