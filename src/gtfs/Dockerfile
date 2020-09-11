FROM python:3.7
COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt
COPY DataCollector.py .env stops.txt DailyFileCreator.py schedule_tasks.py ts-dataclinic-dev-029b433d790c.json  ./

ENTRYPOINT ["python", "schedule_tasks.py"]
