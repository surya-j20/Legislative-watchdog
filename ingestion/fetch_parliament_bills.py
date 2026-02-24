from airflow.providers.http.hooks.http import HttpHook


def fetch_parliament_bills():

    hook = HttpHook(
        method="GET",
        http_conn_id="uk_parliament_api"
    )

    # 🔥 Fetch most recently updated bills
    endpoint = "/api/v1/Bills?SortOrder=DateUpdatedDescending&Take=50"

    response = hook.run(endpoint)
    data = response.json()

    bills = []

    for item in data.get("items", []):

        bills.append({
            "doc_id": str(item.get("billId")),
            "title": item.get("shortTitle"),
            "publication_date": item.get("lastUpdate"),
            "source": "UK Parliament"
        })

    print(f"Fetched {len(bills)} Recently Updated Parliament bills")

    return bills
