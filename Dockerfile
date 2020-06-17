from "continuumio/miniconda"
ADD requirements.txt . 

RUN conda config --append channels conda-forge
RUN conda create -n mta --file requirements.txt
RUN apt-get update && apt-get install make

