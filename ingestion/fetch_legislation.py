from airflow.providers.postgres.hooks.postgres import PostgresHook


def fetch_legislation_updates():

    pg_hook = PostgresHook(
        postgres_conn_id="supabase_legislative_db"
    )

    conn = pg_hook.get_conn()
    cursor = conn.cursor()

    # -----------------------------------
    # GET LEGISLATION RECORDS WITHOUT URL
    # -----------------------------------
    cursor.execute("""
        SELECT doc_id
        FROM documents
        WHERE source = 'UK Legislation'
        AND document_url IS NULL
    """)

    records = cursor.fetchall()

    updated = 0

    for record in records:

        doc_id = record[0]

        print(f"\nChecking: {doc_id}")

        try:
            parts = doc_id.split("/")

            doc_type = parts[0]
            year = parts[1]
            number = parts[2]

            document_url = (
                f"https://www.legislation.gov.uk/"
                f"{doc_type}/{year}/{number}/pdfs/"
                f"{doc_type}_{year}{number}_en.pdf"
            )

            cursor.execute("""
                UPDATE documents
                SET document_url = %s
                WHERE doc_id = %s
            """, (document_url, doc_id))

            updated += 1

        except Exception:
            print("⚠️ Pattern build failed")

    conn.commit()
    cursor.close()

    print(f"\nTotal PDFs updated: {updated}")
