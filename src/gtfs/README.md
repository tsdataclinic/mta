## GTFS Data Pipeline Project

The goal of this project is to create a pipeline to process real-time GTFS data, the (messy!) data feed that powers trip planners 
and the boards that indicate arrival times of trains in a station. We'd like to create python module to process raw GTFS data and 
generate the list of trips on a given day. This would be useful to make working with this data a lot easier for everyone but also 
feed into a couple of analyses we are currently working on.

The challenge here can be broken down into below three parts.

### Getting Started
You can set-up the environment needed to run this project using conda as below:
- Add conda-forge to the config and
- Install the conda environment named {env_name} from the requirements file

```
conda config --append channels conda-forge
conda env create -f mta.yml

## to have the environment showup as a kernel on jupyter
python -m ipykernel install --user --name {env_name} --display-name "Python ({env_name})"
```

### Data & other resources
All the data for this project can be found in `data/raw/gtfs`

[Jan 9th release of static GTFS data](https://github.com/tsdataclinic/mta-accessibility/tree/q2-gtfs-hackday/data/raw/gtfs/gtfs_9Jan)  
[Apr 30th release of static GTFS data](https://github.com/tsdataclinic/mta-accessibility/tree/q2-gtfs-hackday/data/raw/gtfs/gtfs_9Jan)  
[De-duplicated data for a week in April (weekdays)](https://github.com/tsdataclinic/mta-accessibility/blob/q2-gtfs-hackday/data/raw/gtfs/weekday_gtfs_0420_0424.csv)  
[De-duplicated data for couple of weekends in April](https://github.com/tsdataclinic/mta-accessibility/blob/q2-gtfs-hackday/data/raw/gtfs/weekend_gtfs_0418-0419_0425-0426.csv)  
Raw data for a couple of days in June:  
[GTFS specifications](https://developers.google.com/transit)  
[MTA Data Download](http://web.mta.info/developers/download.html)
[MTA Realtime Feed Docs](http://datamine.mta.info/feed-documentation)

### Data Collection
A process that continuously polls MTA gtfs api for live data.
Data comes back in live GTFS format which needs to processed into usable dataframes.

- How much raw data to keep around?
- What frequency to poll api with?
- Need robust error handling, mta api isn’t always reliable
- Notifications if the pipeline stops working? Transient issues with api seem to occur often.
- L train gtfs format appears to be different than rest of system

### Collating Data
Process the raw dataframes into cleaned daily/hourly files.
We want to store consolidated files with complete trip details for each train (tripifying). 
Given the messiness of the data, with segments of time/trips sometimes missing, we need to impute these with the "expected" schedule that we have from quarterly static feed the MTA puts out.

- De-duplicate data
- Logic to come up with expected stops for a trip
- Logic to fill in missing stops given expected stops

### Summary Statistics / Sanity Checks
Get an idea of the relative health/quality of the collected data, both raw and tripified
- Are there significant gaps in time between rows?
- Are all trains/stops accounted for
- Using the static schedule, compare accuracy of live data to static schedule
- Present summary statistics to aid in selecting good datasets to work with


### Deploying to GCP

We run this code in production on GCP as a docker image on a GCP instance. 

First you need to setup google cloud as a container repository 

```bash
gcloud auth configure-docker
```

Then to build and deploy the container run 

```bash
./publish_docker_image.sh
```

This will upload the image to Google cloud container repository. Then simply start an instance with that image and the processing should start running.
