from airflow.providers.http.hooks.http import HttpHook
from bs4 import BeautifulSoup


def fetch_financial_updates():

    hook = HttpHook(
        method="GET",
        http_conn_id="uk_financial_regulators_api"
    )

    endpoint = "/publications"

    response = hook.run(endpoint)

    soup = BeautifulSoup(response.text, "html.parser")

    records = []

    for link in soup.select("a")[:25]:

        title = link.text.strip()

        if title:

            records.append({
                "doc_id": title,
                "title": title,
                "source": "FCA / HM Treasury"
            })

    print(f"Fetched {len(records)} financial updates")

    return records
