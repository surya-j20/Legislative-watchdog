from ingestion.fetch_parliament_bills import fetch_parliament_bills


def run_all_ingestion():

    print("🚀 Running Parliament-only ingestion pipeline...")

    data = []

    parliament = fetch_parliament_bills()

    if parliament:
        data += parliament

    print(f"Total records collected: {len(data)}")

    return data
