from google.cloud import logging

client = logging.Client(project="summitt-gcp", _http=None)
filter_str = 'resource.type="aiplatform.googleapis.com/ReasoningEngine" AND textPayload=~"google.genai.errors.ClientError: 401 UNAUTHENTICATED"'
for entry in client.list_entries(
    filter_=filter_str, max_results=1, order_by=logging.DESCENDING
):
    payload = entry.payload or entry.text_payload
    print(payload)
