mta_accessibility
==============================

Analyzing MTA elevator outages

### Git stuff 

We encourage people to follow the git feature branch workflow which you can read more about here: [https://towardsdatascience.com/why-git-and-how-to-use-git-as-a-data-scientist-4fa2d3bdc197](How to use git as a Data Scientist)

For each feature you are adding to the code 

1. Switch to the master branch and pull the most recent changes 
```
git checkout master 
git pull
```

2. Make a new branch for your addition 
```
git checkout -b cleaning_script
``` 
3. Write your awesome code.
4. Once it's done add it to git 
```
git status
git add {files that have changed}
git commit -m {some descriptive commit message}
```
5. Push the branch to gitlab 
```
git push -u origin cleaning_script
``` 
6. Go to git lab and create a merge request.
7. Either merge the branch yourself if your confident it's good or request that someone else reviews the changes and merges it in.
8. Repeat
9. ...
10. Profit.

Project Organization
------------

Data Clinic projects are a little different form internal Two Sigma projects. We work with external partners 
who will either be the ones who we hope will take our work and use it in their day to day missions to 
empower the communities they serve. We also try to open source as much of our analysis as possible 
to enable others to build on what we have done. 

Because these wider audiences will have to deal with the code / analysis we write potentially long after 
all our volunteers have moved on, we try to adhere to some best practises while working on a project.

To that end we have adopted the Data Science Cookie cutter approach to project structure. The full 
structure is described in detail in the next section but some major guidelines are:

1. Data should be immutable. Datafiles should not be modified in place ever especially the data in RAW. Instead 
scripts should be written that reads in data from a previous step and outputs the results to a new file. 

2. Treat analysis as code in a DAG: Each script should build on those that go before it, reading in data from 
the raw data files and from interim data files and generating new datasets. It shouldn't be required for you 
to run a processing stage again once it has been run. The make file is a good way to ensure this.

3. Notebooks should be for exploration and communication. Try to keep processing code out of notebooks especially 
code that can be used in multiple parts of the analysis. Instead add that code to the robinhood module. In general
someone coming to the project fresh should be able to recreate the analysis using nothing but the code in the robinhood 
directory and data in the data directory. An example notebook for how to access the module can be found in notebooks/Examples.ipynb


Directory Structure:

    ├── LICENSE
    ├── Makefile           <- Makefile with commands like `make data` or `make train`
    ├── README.md          <- The top-level README for developers using this project.
    ├── data
    │   ├── external       <- Data from third party sources.
    │   ├── interim        <- Intermediate data that has been transformed.
    │   ├── processed      <- The final, canonical data sets for modeling.
    │   └── raw            <- The original, immutable data dump.
    │
    ├── docs               <- A default Sphinx project; see sphinx-doc.org for details
    │
    ├── models             <- Trained and serialized models, model predictions, or model summaries
    │
    ├── notebooks          <- Jupyter notebooks. Naming convention is a number (for ordering),
    │                         the creator's initials, and a short `-` delimited description, e.g.
    │                         `1.0-jqp-initial-data-exploration`.
    │
    ├── references         <- Data dictionaries, manuals, and all other explanatory materials.
    │
    ├── reports            <- Generated analysis as HTML, PDF, LaTeX, etc.
    │   └── figures        <- Generated graphics and figures to be used in reporting
    │
    ├── requirements.txt   <- The requirements file for reproducing the analysis environment, e.g.
    │                         generated with `pip freeze > requirements.txt`
    │
    ├── setup.py           <- makes project pip installable (pip install -e .) so src can be imported
    ├── src                <- Source code for use in this project.
    │   ├── __init__.py    <- Makes src a Python module
    │   │
    │   ├── data           <- Scripts to download or generate data
    │   │   └── make_dataset.py
    │   │
    │   ├── features       <- Scripts to turn raw data into features for modeling
    │   │   └── build_features.py
    │   │
    │   ├── models         <- Scripts to train models and then use trained models to make
    │   │   │                 predictions
    │   │   ├── predict_model.py
    │   │   └── train_model.py
    │   │
    │   └── visualization  <- Scripts to create exploratory and results oriented visualizations
    │       └── visualize.py
    │
    └── tox.ini            <- tox file with settings for running tox; see tox.testrun.org


--------

<p><small>Project based on the <a target="_blank" href="https://drivendata.github.io/cookiecutter-data-science/">cookiecutter data science project template</a>. #cookiecutterdatascience</small></p>

