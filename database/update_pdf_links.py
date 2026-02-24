from airflow.providers.postgres.hooks.postgres import PostgresHook
from ingestion.fetch_publications import fetch_publications


def update_pdf_links():

    publications = fetch_publications()

    if not publications:
        print("⚠️ No PDFs to update")
        return

    hook = PostgresHook(
        postgres_conn_id="supabase_legislative_db"
    )

    conn = hook.get_conn()
    cursor = conn.cursor()

    updated = 0

    for pub in publications:

        cursor.execute("""
            UPDATE documents
            SET pdf_url = %s
            WHERE doc_id = %s
        """, (pub["pdf_url"], pub["doc_id"]))

        updated += 1

    conn.commit()
    cursor.close()

    print(f"\nTotal PDFs updated: {updated}")
