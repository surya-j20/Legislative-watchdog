from airflow import DAG
from airflow.decorators import task
from datetime import datetime
import requests


DEFAULT_ARGS = {
    "owner": "airflow",
    "retries": 1,
}


with DAG(
    dag_id="uk_bills_fetch_pdf_urls",
    default_args=DEFAULT_ARGS,
    start_date=datetime(2026, 1, 1),
    schedule_interval=None,  # manual trigger
    catchup=False,
    tags=["uk_parliament", "bills"],
) as dag:


    @task
    def get_first_five_bill_ids():
        url = "https://bills-api.parliament.uk/api/v1/Bills"
        params = {
            "SortOrder": "DateUpdatedDescending",
            "Take": 50
        }

        response = requests.get(url, params=params)
        response.raise_for_status()

        data = response.json()
        items = data.get("items", [])

        first_five = items[:5]

        bill_ids = [bill["billId"] for bill in first_five]

        print("First 5 Bill IDs:", bill_ids)

        return bill_ids


    @task
    def fetch_pdf_urls(bill_ids):
        all_pdf_urls = []

        for bill_id in bill_ids:
            try:
                pub_url = f"https://bills-api.parliament.uk/api/v1/Bills/%7Bbill_id%7D/Publications"
                print(f"Calling: {pub_url}")

                response = requests.get(pub_url, timeout=20)

                if response.status_code == 404:
                    print(f"No publications found for bill {bill_id}")
                    continue

                response.raise_for_status()

                publications = response.json().get("publications", [])

                for pub in publications:
                    for file in pub.get("files", []):
                        if file.get("contentType") == "application/pdf":
                            pdf_url = file.get("url")
                            if pdf_url:
                                all_pdf_urls.append(pdf_url)

            except Exception as e:
                print(f"Error processing bill {bill_id}: {e}")

        print("\n====== PDF URLs ======")
        for url in all_pdf_urls:
            print(url)

        return all_pdf_urls

    bill_ids = get_first_five_bill_ids()
    fetch_pdf_urls(bill_ids)