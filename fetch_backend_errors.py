from google.cloud import logging

try:
    client = logging.Client(project="summitt-gcp")
    # Fetch logs for the agent engine
    filter_str = (
        'resource.type="aiplatform.googleapis.com/ReasoningEngine" AND severity>=ERROR'
    )
    entries = client.list_entries(
        filter_=filter_str, max_results=30, order_by=logging.DESCENDING
    )

    count = 0
    for entry in entries:
        count += 1
        print(
            f"[{entry.timestamp}] {entry.severity}: {entry.payload or entry.text_payload}"
        )
    if count == 0:
        print("No errors found in ReasoningEngine logs.")
except Exception as e:
    print("Error:", e)
