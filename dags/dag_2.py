from airflow import DAG
from airflow.decorators import task
from airflow.models import Variable
from datetime import datetime
import requests
import uuid
import time
from supabase import create_client

DEFAULT_ARGS = {
    "owner": "airflow",
    "retries": 1,
}

BASE_URL = "https://bills-api.parliament.uk/api/v1"
MAX_BILLS = 50


with DAG(
    dag_id="uk_bills_single_pdf_ingestion",
    default_args=DEFAULT_ARGS,
    start_date=datetime(2026, 1, 1),
    schedule_interval=None,
    catchup=False,
    tags=["uk_parliament", "bills"],
) as dag:


    # ---------------------------------------------------
    # 1️⃣ Fetch Latest Bills (Pagination)
    # ---------------------------------------------------
    @task
    def get_latest_bills():

        all_bills = []
        page = 1
        page_size = 25

        while len(all_bills) < MAX_BILLS:

            url = f"{BASE_URL}/Bills"
            params = {
                "SortOrder": "DateUpdatedDescending",
                "Page": page,
                "Take": page_size
            }

            print(f"Fetching page {page}")

            response = requests.get(url, params=params, timeout=20)
            response.raise_for_status()

            items = response.json().get("items", [])

            if not items:
                break

            all_bills.extend(items)
            page += 1
            time.sleep(0.2)

        selected = all_bills[:MAX_BILLS]
        print(f"Collected {len(selected)} bills")
        return selected


    # ---------------------------------------------------
    # 2️⃣ Extract ONE Main PDF per Bill
    # ---------------------------------------------------
    # ---------------------------------------------------
    # 2️⃣ Extract ONE Main PDF per Bill
    # ---------------------------------------------------
    @task
    def extract_main_pdf(bills):

        supabase_url = Variable.get("SUPABASE_URL")
        supabase_key = Variable.get("SUPABASE_SERVICE_ROLE_KEY")
        supabase = create_client(supabase_url, supabase_key)

        bill_pdf_list = []

        for bill in bills:

            bill_id = bill["billId"]

            # 🔹 Skip already processed bills
            existing = supabase.table("uk_bills_main") \
                .select("bill_id") \
                .eq("bill_id", bill_id) \
                .execute()

            if existing.data:
                print(f"Skipping bill {bill_id} (already exists)")
                continue

            try:
                pub_url = f"{BASE_URL}/Bills/{bill_id}/Publications"
                response = requests.get(pub_url, timeout=20)
                response.raise_for_status()

                publications = response.json().get("publications", [])

                main_pdf_url = None

                # 🔹 Take ONLY FIRST PDF found
                for pub in publications:
                    for file in pub.get("files", []):
                        if file.get("contentType") == "application/pdf":

                            publication_id = pub.get("id")
                            document_id = file.get("id")

                            if publication_id and document_id:
                                main_pdf_url = (
                                    f"{BASE_URL}/Publications/"
                                    f"{publication_id}/Documents/"
                                    f"{document_id}/Download"
                                )
                                break
                    if main_pdf_url:
                        break

                if main_pdf_url:
                    bill_pdf_list.append({
                        "bill": bill,
                        "pdf_url": main_pdf_url
                    })

                time.sleep(0.2)

            except Exception as e:
                print(f"Error for bill {bill_id}: {e}")

        print(f"New bills with PDFs: {len(bill_pdf_list)}")
        return bill_pdf_list



    # ---------------------------------------------------
    # 3️⃣ Upload PDF + Store Metadata
    # ---------------------------------------------------
    @task
    def upload_and_store(bill_pdf_list):

        supabase_url = Variable.get("SUPABASE_URL")
        supabase_key = Variable.get("SUPABASE_SERVICE_ROLE_KEY")
        supabase = create_client(supabase_url, supabase_key)

        bucket_name = "legislative-pdfs"
        processed = 0

        for item in bill_pdf_list:

            bill = item["bill"]
            pdf_url = item["pdf_url"]
            bill_id = bill["billId"]

            try:
                print(f"Downloading bill {bill_id}")

                pdf_response = requests.get(pdf_url, timeout=40)
                pdf_response.raise_for_status()

                # 🔥 CLEAN BILL TITLE FOR FILENAME
                raw_title = bill.get("shortTitle", f"bill_{bill_id}")
                safe_title = "".join(
                    c for c in raw_title if c.isalnum() or c in (" ", "_")
                ).strip().replace(" ", "_")

                file_name = f"{safe_title}.pdf"
                file_path = f"uk_bills/{file_name}"

                supabase.storage.from_(bucket_name).upload(
                    file_path,
                    pdf_response.content,
                    {"content-type": "application/pdf"}
                )

                public_url = supabase.storage.from_(bucket_name).get_public_url(file_path)

                supabase.table("uk_bills_main").upsert(
                    {
                        "bill_id": bill_id,
                        "title": bill.get("shortTitle"),
                        "long_title": bill.get("longTitle"),
                        "introduced_date": bill.get("introducedDate"),
                        "current_stage": bill.get("currentStage", {}).get("stage"),
                        "sponsor": bill.get("sponsors", [{}])[0].get("name"),
                        "pdf_storage_path": file_path,
                        "pdf_public_url": public_url
                    },
                    on_conflict="bill_id"
                ).execute()

                processed += 1
                print(f"Stored: {file_name}")

                time.sleep(0.2)

            except Exception as e:
                print(f"Error processing bill {bill_id}: {e}")

        print(f"Total processed: {processed}")


    # DAG FLOW
    bills = get_latest_bills()
    bill_pdf_list = extract_main_pdf(bills)
    upload_and_store(bill_pdf_list)