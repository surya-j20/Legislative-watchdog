from airflow.providers.http.hooks.http import HttpHook
from airflow.providers.postgres.hooks.postgres import PostgresHook
import json


def fetch_publications():

    pg_hook = PostgresHook(
        postgres_conn_id="supabase_legislative_db"
    )

    conn = pg_hook.get_conn()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT doc_id
        FROM documents
        WHERE source = 'UK Parliament'
        LIMIT 1
    """)

    bill = cursor.fetchone()
    cursor.close()

    if not bill:
        print("No bills found")
        return []

    bill_id = bill[0]

    print(f"\n🔎 Inspecting Bill {bill_id}")

    http_hook = HttpHook(
        method="GET",
        http_conn_id="uk_parliament_api"
    )

    endpoint = f"/api/v1/Bills/{bill_id}"

    response = http_hook.run(endpoint)
    data = response.json()

    print("\n===== FULL BILL RESPONSE =====")
    print(json.dumps(data, indent=2))
    print("================================")

    return []
