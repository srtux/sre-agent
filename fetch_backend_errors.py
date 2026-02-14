from datetime import datetime, timedelta, timezone

from google.cloud import logging

client = logging.Client(project="summitt-gcp")
query = 'resource.type="aiplatform.googleapis.com/ReasoningEngine" AND resource.labels.reasoning_engine="4168506966131343360" AND severity>=ERROR'
# last 10 minutes
now = datetime.now(timezone.utc)
ten_mins_ago = now - timedelta(minutes=10)
# iso format
query += f' AND timestamp>="{ten_mins_ago.isoformat()}"'

print(f"Querying: {query}")
count = 0
for entry in client.list_entries(
    filter_=query, order_by=logging.DESCENDING, max_results=10
):
    print(f"[{entry.timestamp}] {entry.severity}: {entry.payload}")
    count += 1
if count == 0:
    print("Found no errors in the last 10 minutes!")
