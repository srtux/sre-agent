"""Common Google Cloud Platform (GCP) metrics definitions.

This file contains a consolidated list of key metrics for various GCP services
to assist the Metrics Maestro in selecting the correct metrics for analysis.

For the "Top Services" in Google Cloud Platform (GCP), the metrics are organized by service prefix. Because there are over 6,500 total metrics, the "full list" below focuses on the comprehensive set of standard metrics for the most widely used services: **Compute Engine**, **GKE**, **Cloud Storage**, **BigQuery**, **Cloud SQL**, and **Pub/Sub**.

### **Metric Structure**

All GCP metrics follow the format: `[Service Prefix]/[Metric Name]`

* **Example:** `compute.googleapis.com/instance/cpu/utilization`

---

### **1. Compute Engine**

**Prefix:** `compute.googleapis.com/`
These metrics measure the performance of VM instances.

* **CPU**
* `instance/cpu/utilization`: Fractional utilization of allocated CPU (0.0 to 1.0+).
* `instance/cpu/reserved_cores`: Number of vCPUs reserved on the host.
* `instance/cpu/usage_time`: Delta vCPU usage in seconds.
* `instance/cpu/scheduler_wait_time`: Time a vCPU is ready but not scheduled.


* **Network**
* `instance/network/received_bytes_count`: Bytes received from the network.
* `instance/network/sent_bytes_count`: Bytes sent over the network.
* `instance/network/received_packets_count`: Packets received.
* `instance/network/sent_packets_count`: Packets sent.
* `mirroring/mirrored_bytes_count`: Count of mirrored bytes (Packet Mirroring).


* **Disk (Guest)**
* `guest/disk/bytes_used`: Bytes used on disk (requires Ops Agent).
* `guest/memory/bytes_used`: Memory used (requires Ops Agent).


* **Disk (Infrastructure)**
* `instance/disk/read_bytes_count`: Bytes read from persistent disk.
* `instance/disk/write_bytes_count`: Bytes written to persistent disk.
* `instance/disk/read_ops_count`: Count of read operations.
* `instance/disk/write_ops_count`: Count of write operations.


* **Integrity**
* `instance/integrity/late_boot_validation_status`: Status of Shielded VM late boot validation.



---

### **2. Google Kubernetes Engine (GKE)**

**Prefixes:** `kubernetes.io/` (System) and `container.googleapis.com/` (Legacy/Container)
GKE metrics are split between the Kubernetes system metrics and container metrics.

* **Node Metrics (`kubernetes.io/node/...`)**
* `cpu/allocatable_cores`: CPU cores available for allocation.
* `cpu/total_cores`: Total CPU cores on the node.
* `memory/allocatable_bytes`: Memory available for allocation.
* `memory/total_bytes`: Total memory on the node.
* `network/received_bytes_count`: Bytes received by the node.


* **Pod Metrics (`kubernetes.io/pod/...`)**
* `network/received_bytes_count`: Bytes received by the pod.
* `network/sent_bytes_count`: Bytes sent by the pod.
* `volume/total_bytes`: Total storage capacity of the pod's volume.
* `volume/used_bytes`: Used storage in the pod's volume.


* **Container Metrics (`kubernetes.io/container/...`)**
* `cpu/core_usage_time`: Cumulative CPU usage in seconds.
* `cpu/limit_cores`: CPU core limit for the container.
* `cpu/request_cores`: CPU core request for the container.
* `memory/limit_bytes`: Memory limit for the container.
* `memory/used_bytes`: Memory currently used by the container.
* `restart_count`: Number of times the container has restarted.



---

### **3. Cloud Storage**

**Prefix:** `storage.googleapis.com/`
Monitors bucket size, object counts, and access traffic.

* **Storage & Capacity**
* `storage/total_bytes`: Total size of all objects in the bucket.
* `storage/total_object_count`: Total number of objects in the bucket.
* `storage/v2/total_bytes`: (Newer) Total bytes grouped by storage class.
* `storage/v2/total_count`: (Newer) Total object count grouped by storage class.


* **Network & Access**
* `network/received_bytes_count`: Total bytes received by the bucket (Uploads).
* `network/sent_bytes_count`: Total bytes sent by the bucket (Downloads).
* `api/request_count`: Number of API requests (Get, Put, List, etc.).
* `authz/object_specific_acl_mutation_count`: Changes to object ACLs.



---

### **4. BigQuery**

**Prefix:** `bigquery.googleapis.com/`
Focuses on query performance, slot usage, and storage.

* **Jobs & Queries**
* `job/num_in_flight`: Number of jobs currently running.
* `query/count`: Number of queries in flight.
* `query/execution_times`: Distribution of query execution times.
* `query/scanned_bytes`: Bytes scanned by queries (driver of cost).
* `query/scanned_bytes_billed`: Bytes billed for queries.


* **Slots (Compute)**
* `slots/allocated`: Number of slots currently allocated.
* `slots/total_available`: Total slots available to the project.


* **Storage**
* `storage/stored_bytes`: Total bytes stored.
* `storage/uploaded_bytes`: Bytes uploaded to tables.
* `storage/table_count`: Number of tables.



---

### **5. Cloud SQL**

**Prefix:** `cloudsql.googleapis.com/`
Essential for monitoring database health (MySQL, PostgreSQL, SQL Server).

* **CPU & Memory**
* `database/cpu/utilization`: Fraction of reserved CPU in use.
* `database/cpu/reserved_cores`: Number of cores reserved.
* `database/memory/usage`: RAM usage in bytes.
* `database/memory/utilization`: Fraction of memory in use.
* `database/memory/quota`: Maximum RAM available.


* **Disk & I/O**
* `database/disk/bytes_used`: Data stored on disk.
* `database/disk/utilization`: Fraction of disk quota used.
* `database/disk/read_ops_count`: Disk read IOPS.
* `database/disk/write_ops_count`: Disk write IOPS.


* **Network & Connections**
* `database/network/received_bytes_count`: Bytes received by the DB instance.
* `database/network/sent_bytes_count`: Bytes sent by the DB instance.
* `database/mysql/threads_connected`: (MySQL only) Current open connections.
* `database/postgresql/num_backends`: (Postgres only) Current connections.


* **Status**
* `database/up`: Boolean (1 if up, 0 if down).
* `database/state`: Current state (Running, Suspended, etc.).



---

### **6. Pub/Sub**

**Prefix:** `pubsub.googleapis.com/`
Metrics for messaging throughput and backlogs.

* **Subscription Metrics**
* `subscription/num_undelivered_messages`: Number of messages waiting to be delivered.
* `subscription/oldest_unacked_message_age`: Age of the oldest unacknowledged message (backlog age).
* `subscription/sent_message_count`: Number of messages sent to subscribers.
* `subscription/ack_message_count`: Number of messages acknowledged.
* `subscription/pull_request_count`: Number of pull requests made.


* **Topic Metrics**
* `topic/send_request_count`: Number of publish requests (messages published).
* `topic/send_message_operation_count`: Count of publish operations.
* `topic/byte_cost`: Storage cost of retained messages.


* **Snapshots**
* `snapshot/num_messages`: Number of messages retained in a snapshot.
* `snapshot/oldest_message_age`: Age of the oldest message in a snapshot.
"""

COMMON_GCP_METRICS = {
    # -------------------------------------------------------------------------
    # Compute & Containers
    # -------------------------------------------------------------------------
    "GKE (Kubernetes Engine)": [
        # Pod/Container
        "kubernetes.io/container/cpu/core_usage_time",
        "kubernetes.io/container/cpu/limit_cores",
        "kubernetes.io/container/cpu/request_cores",
        "kubernetes.io/container/memory/used_bytes",
        "kubernetes.io/container/memory/limit_bytes",
        "kubernetes.io/container/memory/request_bytes",
        "kubernetes.io/pod/network/sent_bytes_count",
        "kubernetes.io/pod/network/received_bytes_count",
        "kubernetes.io/container/restart_count",
        # Node
        "kubernetes.io/node/cpu/allocatable_cores",
        "kubernetes.io/node/cpu/core_usage_time",
        "kubernetes.io/node/memory/allocatable_bytes",
        "kubernetes.io/node/memory/used_bytes",
        # Storage
        "kubernetes.io/pod/volume/utilized_bytes",
    ],
    "Cloud Run": [
        "run.googleapis.com/request_count",
        "run.googleapis.com/request_latencies",
        "run.googleapis.com/container/cpu/utilizations",
        "run.googleapis.com/container/memory/utilizations",
        "run.googleapis.com/container/instance_count",
        "run.googleapis.com/container/billable_instance_time",
        "run.googleapis.com/container/startup_latencies",
    ],
    "Compute Engine (GCE)": [
        "compute.googleapis.com/instance/cpu/utilization",
        "compute.googleapis.com/instance/disk/read_bytes_count",
        "compute.googleapis.com/instance/disk/write_bytes_count",
        "compute.googleapis.com/instance/network/sent_bytes_count",
        "compute.googleapis.com/instance/network/received_bytes_count",
        "compute.googleapis.com/instance/uptime",
        "compute.googleapis.com/instance/memory/balloon/ram_used",  # If agent installed
    ],
    "Cloud Functions": [
        "cloudfunctions.googleapis.com/function/execution_count",
        "cloudfunctions.googleapis.com/function/execution_times",
        "cloudfunctions.googleapis.com/function/active_instances",
        "cloudfunctions.googleapis.com/function/user_memory_bytes",
    ],
    # -------------------------------------------------------------------------
    # Networking & Load Balancing
    # -------------------------------------------------------------------------
    "Load Balancing (HTTP/S)": [
        "loadbalancing.googleapis.com/https/request_count",
        "loadbalancing.googleapis.com/https/total_latencies",
        "loadbalancing.googleapis.com/https/backend_latencies",
        "loadbalancing.googleapis.com/https/frontend_tcp_rtt",
        "loadbalancing.googleapis.com/https/backend_request_count",
        "loadbalancing.googleapis.com/https/backend_response_bytes_count",
    ],
    "Load Balancing (L3/L4)": [
        "loadbalancing.googleapis.com/l3/external/ingress_bytes_count",
        "loadbalancing.googleapis.com/l3/external/egress_bytes_count",
    ],
    # -------------------------------------------------------------------------
    # Databases & Storage
    # -------------------------------------------------------------------------
    "Cloud SQL": [
        "cloudsql.googleapis.com/database/cpu/utilization",
        "cloudsql.googleapis.com/database/memory/utilization",
        "cloudsql.googleapis.com/database/memory/used_bytes",
        "cloudsql.googleapis.com/database/disk/read_ops_count",
        "cloudsql.googleapis.com/database/disk/write_ops_count",
        "cloudsql.googleapis.com/database/postgresql/transaction_count",  # Example for PG
        "cloudsql.googleapis.com/database/mysql/queries",  # Example for MySQL
        "cloudsql.googleapis.com/database/network/received_bytes_count",
        "cloudsql.googleapis.com/database/network/sent_bytes_count",
        "cloudsql.googleapis.com/database/up",
    ],
    "Cloud Spanner": [
        "spanner.googleapis.com/instance/cpu/utilization_by_priority",
        "spanner.googleapis.com/instance/storage/used_bytes",
        "spanner.googleapis.com/api/request_count",
        "spanner.googleapis.com/api/latencies",
    ],
    "Cloud Redis (Memorystore)": [
        "redis.googleapis.com/stats/cpu_utilization",
        "redis.googleapis.com/stats/memory/usage_ratio",
        "redis.googleapis.com/stats/memory/used_bytes",
        "redis.googleapis.com/stats/connections/current_connections",
        "redis.googleapis.com/commands/calls",
        "redis.googleapis.com/keyspace/hits",
        "redis.googleapis.com/keyspace/misses",
    ],
    "BigQuery": [
        "bigquery.googleapis.com/job/query/execution_time",
        "bigquery.googleapis.com/slots/utilization",
        "bigquery.googleapis.com/storage/stored_bytes",
        "bigquery.googleapis.com/job/scanned_bytes",
        "bigquery.googleapis.com/job/query/count",
        "bigquery.googleapis.com/job/error_count",
    ],
    "Cloud Storage (GCS)": [
        "storage.googleapis.com/network/sent_bytes_count",
        "storage.googleapis.com/network/received_bytes_count",
        "storage.googleapis.com/api/request_count",
        "storage.googleapis.com/authn/requests_count",  # For access errors
    ],
    # -------------------------------------------------------------------------
    # Messaging & Eventing
    # -------------------------------------------------------------------------
    "Pub/Sub": [
        "pubsub.googleapis.com/subscription/num_undelivered_messages",
        "pubsub.googleapis.com/subscription/oldest_unacked_message_age",
        "pubsub.googleapis.com/topic/send_request_count",
        "pubsub.googleapis.com/topic/byte_cost",
        "pubsub.googleapis.com/subscription/ack_message_count",
        "pubsub.googleapis.com/subscription/push_request_count",  # For push subs
    ],
    # -------------------------------------------------------------------------
    # AI & Machine Learning
    # -------------------------------------------------------------------------
    "Vertex AI": [
        # AI Agents (Reasoning Engine)
        "aiplatform.googleapis.com/ReasoningEngine/request_count",
        "aiplatform.googleapis.com/ReasoningEngine/request_latencies",
        "aiplatform.googleapis.com/ReasoningEngine/container/cpu/allocation_time",
        "aiplatform.googleapis.com/ReasoningEngine/container/memory/allocation_time",
        # Online Prediction
        "aiplatform.googleapis.com/prediction/online/request_count",
        "aiplatform.googleapis.com/prediction/online/prediction_count",
        "aiplatform.googleapis.com/prediction/online/cpu/utilization",
        "aiplatform.googleapis.com/prediction/online/gpu/utilization",
        "aiplatform.googleapis.com/prediction/online/replica_count",
    ],
    # -------------------------------------------------------------------------
    # Operations
    # -------------------------------------------------------------------------
    "Cloud Logging": [
        "logging.googleapis.com/log_entry_count",
        "logging.googleapis.com/byte_count",
        "logging.googleapis.com/dropped_log_entry_count",
        "logging.googleapis.com/write_count",
    ],
    "Cloud Tasks": [
        "cloudtasks.googleapis.com/queue/depth",
        "cloudtasks.googleapis.com/queue/task_attempt_count",
    ],
}
