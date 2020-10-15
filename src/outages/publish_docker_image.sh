#!/bin/bash

docker build . -t mta_outage_collector
docker tag mta_outage_collector gcr.io/ts-dataclinic-dev/mta_outage_collector:tag2
docker push gcr.io/ts-dataclinic-dev/mta_outage_collector:tag2
