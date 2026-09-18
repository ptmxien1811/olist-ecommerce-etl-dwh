FROM apache/airflow:3.3.1-python3.12

COPY airflow/requirements-airflow.txt /requirements-airflow.txt

RUN pip install --no-cache-dir \
    "apache-airflow==3.3.1" \
    -r /requirements-airflow.txt