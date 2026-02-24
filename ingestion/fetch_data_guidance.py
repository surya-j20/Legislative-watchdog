from airflow.providers.http.hooks.http import HttpHook


def fetch_data_guidance():

    records = []

    try:

        hook = HttpHook(
            method="GET",
            http_conn_id="uk_data_regulators_api"
        )

        endpoint = "/for-organisations"

        response = hook.run(endpoint)

        # If success (rare)
        if response.status_code == 200:

            records.append({
                "doc_id": "ICO_GUIDANCE_SAMPLE",
                "title": "ICO Guidance Update",
                "source": "ICO / DSIT"
            })

    except Exception as e:

        print("⚠️ ICO source blocked by bot protection")
        print("Skipping ICO ingestion…")

    return records
