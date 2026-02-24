import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(PROJECT_ROOT)

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

from ingestion.run_ingestion import run_all_ingestion
from database.insert_records import insert_records
from database.update_pdf_links import update_pdf_links


default_args = {
    "owner": "legislative_watchdog",
    "depends_on_past": False,
    "email_on_failure": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="legislative_watchdog_parliament_only",
    default_args=default_args,
    description="Parliament Bills PDF Pipeline",
    schedule_interval="@daily",
    start_date=datetime(2024, 1, 1),
    catchup=False,
) as dag:

    task_ingestion = PythonOperator(
        task_id="run_all_ingestion",
        python_callable=run_all_ingestion
    )

    task_insert = PythonOperator(
        task_id="insert_records",
        python_callable=insert_records
    )

    task_update_links = PythonOperator(
        task_id="update_pdf_links",
        python_callable=update_pdf_links
    )

    task_ingestion >> task_insert >> task_update_links
