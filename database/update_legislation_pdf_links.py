from airflow.providers.postgres.hooks.postgres import PostgresHook


def update_legislation_pdf_links():

    pg_hook = PostgresHook(
        postgres_conn_id="supabase_legislative_db"
    )

    conn = pg_hook.get_conn()
    cursor = conn.cursor()

    # -----------------------------
    # GET LEGISLATION DOCS
    # -----------------------------
    cursor.execute("""
        SELECT doc_id
        FROM documents
        WHERE source = 'UK Legislation'
        AND pdf_url IS NULL
    """)

    records = cursor.fetchall()

    updated = 0

    for record in records:

        doc_id = record[0]

        print(f"\nChecking: {doc_id}")

        try:

            parts = doc_id.split("/")

            doc_type = parts[0]   # uksi
            year = parts[1]
            number = parts[2]

            pdf_url = (
                f"https://www.legislation.gov.uk/"
                f"{doc_type}/{year}/{number}/pdfs/"
                f"{doc_type}_{year}{number}_en.pdf"
            )

            # -----------------------------
            # UPDATE DB
            # -----------------------------
            cursor.execute("""
                UPDATE documents
                SET pdf_url = %s
                WHERE doc_id = %s
            """, (pdf_url, doc_id))

            updated += 1

        except Exception:

            print("⚠️ Pattern build failed")

    conn.commit()

    print(f"\nTotal PDFs updated: {updated}")
