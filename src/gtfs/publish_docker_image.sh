#!/bin/bash

docker build . -t mta_collector
docker tag mta_collector gcr.io/ts-dataclinic-dev/mta_collector:tag2
docker push gcr.io/ts-dataclinic-dev/mta_collector:tag2
