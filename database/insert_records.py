from airflow.providers.postgres.hooks.postgres import PostgresHook
from ingestion.run_ingestion import run_all_ingestion


def insert_records():

    records = run_all_ingestion()

    if not records:
        print("⚠️ No records to insert")
        return

    hook = PostgresHook(
        postgres_conn_id="supabase_legislative_db"
    )

    conn = hook.get_conn()
    cursor = conn.cursor()

    query = """
        INSERT INTO documents (
            doc_id,
            title,
            source,
            publication_date
        )
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (doc_id) DO NOTHING;
    """

    values = [
        (
            r["doc_id"],
            r["title"],
            r["source"],
            r.get("publication_date")
        )
        for r in records
    ]

    cursor.executemany(query, values)

    conn.commit()
    cursor.close()

    print(f"Inserted {len(values)} records")
