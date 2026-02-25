from airflow import DAG
from airflow.decorators import task
from datetime import datetime
import requests
import os
import uuid
from supabase import create_client


DEFAULT_ARGS = {
    "owner": "airflow",
    "retries": 1,
}

BASE_URL = "https://bills-api.parliament.uk/api/v1"
MAX_BILLS = 50
MAX_PDFS = 100   # safety limit for downloads


with DAG(
    dag_id="uk_bills_full_ingestion",
    default_args=DEFAULT_ARGS,
    start_date=datetime(2026, 1, 1),
    schedule_interval=None,
    catchup=False,
    tags=["uk_parliament", "bills"],
) as dag:


    # ---------------------------------------------------
    # 1️⃣ Get Latest Bill IDs
    # ---------------------------------------------------
    @task
    def get_latest_bill_ids():

        url = f"{BASE_URL}/Bills"
        params = {
            "SortOrder": "DateUpdatedDescending",
            "Take": MAX_BILLS
        }

        response = requests.get(url, params=params, timeout=20)
        response.raise_for_status()

        data = response.json()
        items = data.get("items", [])

        bill_ids = [bill["billId"] for bill in items[:MAX_BILLS]]

        print(f"Processing {len(bill_ids)} bills:", bill_ids)

        return bill_ids


    # ---------------------------------------------------
    # 2️⃣ Fetch PDF URLs
    # ---------------------------------------------------
    @task
    def fetch_pdf_urls(bill_ids):

        all_pdf_urls = []

        for bill_id in bill_ids:
            try:
                pub_url = f"{BASE_URL}/Bills/{bill_id}/Publications"
                print(f"\nChecking bill {bill_id}")

                response = requests.get(pub_url, timeout=20)
                response.raise_for_status()

                data = response.json()
                publications = data.get("publications", [])

                for pub in publications:

                    # Extract from links
                    for link in pub.get("links", []):
                        if link.get("contentType") == "application/pdf":
                            pdf_url = link.get("url")
                            if pdf_url:
                                all_pdf_urls.append(pdf_url)

                    # Extract from files
                    for file in pub.get("files", []):
                        if file.get("contentType") == "application/pdf":
                            publication_id = pub.get("id")
                            document_id = file.get("id")

                            if publication_id and document_id:
                                file_url = (
                                    f"{BASE_URL}/Publications/"
                                    f"{publication_id}/Documents/"
                                    f"{document_id}/Download"
                                )
                                all_pdf_urls.append(file_url)

            except Exception as e:
                print(f"Error processing bill {bill_id}: {e}")

        print(f"\nTotal PDFs found: {len(all_pdf_urls)}")

        return all_pdf_urls


    # ---------------------------------------------------
    # 3️⃣ Download & Upload to Supabase
    # ---------------------------------------------------
    @task
    def download_and_store_pdfs(pdf_urls):
        from airflow.models import Variable
        supabase_url = Variable.get("SUPABASE_URL")
        supabase_key = Variable.get("SUPABASE_SERVICE_ROLE_KEY")

        if not supabase_url or not supabase_key:
            raise Exception("Supabase credentials missing")

        supabase = create_client(supabase_url, supabase_key)
        bucket_name = "legislative-pdfs"

        stored_files = []

        for url in pdf_urls[:MAX_PDFS]:   # safety limit
            try:
                print(f"\nDownloading: {url}")

                response = requests.get(url, timeout=40)
                response.raise_for_status()

                file_name = f"{uuid.uuid4()}.pdf"
                file_path = f"uk_bills/{file_name}"

                supabase.storage.from_(bucket_name).upload(
                    file_path,
                    response.content,
                    {"content-type": "application/pdf"}
                )

                public_url = supabase.storage.from_(bucket_name).get_public_url(file_path)

                stored_files.append({
                    "original_url": url,
                    "storage_path": file_path,
                    "public_url": public_url
                })

                print(f"Uploaded → {file_path}")

            except Exception as e:
                print(f"Failed for {url}: {e}")

        print(f"\nTotal uploaded: {len(stored_files)}")

        return stored_files


    # DAG FLOW
    bill_ids = get_latest_bill_ids()
    pdf_urls = fetch_pdf_urls(bill_ids)
    download_and_store_pdfs(pdf_urls)
