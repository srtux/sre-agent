"""Common Google Cloud Platform (GCP) metrics definitions.

This file contains a consolidated list of key metrics for various GCP services
to assist the Metrics Maestro in selecting the correct metrics for analysis.
"""

COMMON_GCP_METRICS = {
    "GKE": [
        "kubernetes.io/container/cpu/core_usage_time",
        "kubernetes.io/container/cpu/limit_cores",
        "kubernetes.io/container/cpu/request_cores",
        "kubernetes.io/container/memory/used_bytes",
        "kubernetes.io/container/memory/limit_bytes",
        "kubernetes.io/container/memory/request_bytes",
        "kubernetes.io/pod/network/sent_bytes_count",
        "kubernetes.io/pod/network/received_bytes_count",
        "kubernetes.io/container/restart_count",
    ],
    "Cloud Run": [
        "run.googleapis.com/request_count",
        "run.googleapis.com/request_latencies",
        "run.googleapis.com/container/cpu/utilizations",
        "run.googleapis.com/container/memory/utilizations",
        "run.googleapis.com/container/instance_count",
        "run.googleapis.com/container/billable_instance_time",
    ],
    "Compute Engine": [
        "compute.googleapis.com/instance/cpu/utilization",
        "compute.googleapis.com/instance/disk/read_bytes_count",
        "compute.googleapis.com/instance/disk/write_bytes_count",
        "compute.googleapis.com/instance/network/sent_bytes_count",
        "compute.googleapis.com/instance/network/received_bytes_count",
        "compute.googleapis.com/instance/uptime",
    ],
    "Vertex AI": [
        "aiplatform.googleapis.com/ReasoningEngine/request_count",
        "aiplatform.googleapis.com/ReasoningEngine/request_latencies",
        "aiplatform.googleapis.com/PublisherModel/prediction/online/prediction_count",
        "aiplatform.googleapis.com/PublisherModel/prediction/online/prediction_latencies",
    ],
    "BigQuery": [
        "bigquery.googleapis.com/job/query/execution_time",
        "bigquery.googleapis.com/slots/utilization",
        "bigquery.googleapis.com/storage/stored_bytes",
        "bigquery.googleapis.com/job/scanned_bytes",
        "bigquery.googleapis.com/job/query/count",
    ],
    "Cloud Logging": [
        "logging.googleapis.com/log_entry_count",
        "logging.googleapis.com/byte_count",
        "logging.googleapis.com/dropped_log_entry_count",
        "logging.googleapis.com/write_count",
    ],
}
