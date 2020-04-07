mta_data_repo
==============================

short desc

Getting Started
------------

setup & requirements

Project Description
------------

Accessibility Graph for stations:


Turnstile Data:


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

