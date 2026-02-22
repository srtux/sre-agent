# Google Cloud Spanner Troubleshooting Playbook

**Based on Official Google Cloud Documentation**

> **Implementation Status**: This document serves as a reference guide for Cloud Spanner troubleshooting. A corresponding code playbook (`sre_agent/tools/playbooks/spanner.py`) has **not yet been implemented**. The playbook framework (`sre_agent/tools/playbooks/`) supports Spanner as a planned category under `PlaybookCategory.DATA` (see `tools/playbooks/__init__.py`). The existing code playbooks cover GKE, Cloud Run, Cloud SQL, GCE, BigQuery, Pub/Sub, and Self-Healing.
>
> **Available SRE Agent tools for Spanner diagnostics**: While no dedicated Spanner playbook tool exists, the agent can investigate Spanner issues using:
> - `list_time_series` -- Query Spanner metrics (CPU utilization, latency, request count, storage)
> - `get_logs_for_trace` -- Correlate Spanner operations with trace data
> - `fetch_trace` -- Analyze distributed traces involving Spanner calls
> - Spanner metrics are cataloged in `sre_agent/resources/gcp_metrics.py` under "Cloud Spanner"

---

## Table of Contents
1. [Query Performance Optimization](#1-query-performance-optimization)
2. [Lock Contention and Deadlocks](#2-lock-contention-and-deadlocks)
3. [Hot Spotting and Data Distribution](#3-hot-spotting-and-data-distribution)
4. [Replication and Consistency](#4-replication-and-consistency)
5. [Connection and Timeout Problems](#5-connection-and-timeout-problems)
6. [Schema Design Best Practices](#6-schema-design-best-practices)
7. [Monitoring and Diagnostic Tools](#7-monitoring-and-diagnostic-tools)
8. [Quick Reference Decision Tree](#8-quick-reference-decision-tree)
9. [SRE Agent Integration Notes](#9-sre-agent-integration-notes)

---

## 1. Query Performance Optimization

### Problem Identification
- Slow query execution times
- High latency on specific operations
- Performance degradation after data changes

### Troubleshooting Steps

**Step 1: Detect Performance Changes**
- Monitor query execution speed using Query Insights
- Compare metrics to baseline performance
- Identify queries that recently degraded

**Step 2: Review Statistics**
- Spanner automatically generates statistics packages every 3 days
- For newly-created databases, manually construct optimizer statistics packages to avoid 3-day delay
- Statistics provide cardinality estimates for query optimization

**Step 3: Analyze Query Execution Plans**
- Use Google Cloud Console's Spanner Studio
- Review execution plan operators:
  - **Table scan**: Full table scan (no secondary index)
  - **Index scan**: Secondary index utilized
  - **Cross apply/Distributed cross apply**: Index joined with base table
  - **Distributed union**: Results combined from multiple servers

**Step 4: Test Alternative Approaches**
- Use `FORCE_INDEX` directive to test different indexes
- Compare base table scans vs. index scans
- Bind query parameters to frequently-used values
- Test with realistic data distributions

### Optimization Best Practices

| Scenario | Recommendation |
|----------|-----------------|
| Match primary key prefixes | Consider base table scans |
| Many rows satisfy predicates | Use base table scan |
| Small tables | Avoid unnecessary indexes |
| Selective predicates (REGEXP_CONTAINS, STARTS_WITH) | Use secondary indexes |
| Hash joins or apply joins | Place smallest result set first |
| Queries use parameters | Cache execution plans |
| Full table scans | Consider missing indexes |

### Query Parameter Optimization
- Queries using parameters execute faster on each invocation
- Parameterization enables execution plan caching
- Bind to frequently-used values during testing

### Batch Processing
- Consider batch-oriented processing for large scans
- Lower CPU utilization than row-oriented processing
- Reduces overall latency

### Recovery Actions
- **Recently dropped index**: Consider restoring it
- **Over-indexing**: Remove redundant indexes that slow writes
- **Stale statistics**: Force statistics package regeneration

---

## 2. Lock Contention and Deadlocks

### Problem Identification
- High write latencies at 99th percentile
- "ABORTED" errors with `RESOURCE_EXHAUSTED` code
- Increased lock wait times
- Transaction retries and failures

### Lock Types in Spanner

| Lock Type | Acquired When | Purpose |
|-----------|---------------|---------|
| ReaderShared | Read-write transaction reads data | Share row access |
| WriterShared | Read-write transaction writes without reading first | Exclusive write access |
| Exclusive | Read-write transaction reads then writes | Serialization |

### Deadlock Prevention: Wound-Wait Algorithm
- Spanner tracks age of each transaction requesting conflicting locks
- Older transactions can abort younger transactions
- "Older" = transaction's earliest read/query/commit happened sooner
- Reduces circular wait conditions automatically

### Diagnosing Lock Contention

**Step 1: Check Latency Spikes**
- Monitor Spanner latency at 99th percentile in Cloud Console
- Focus on write latencies as primary indicator
- Compare against baseline patterns

**Step 2: Use Lock Insights**
- Access Lock Insights in Spanner Console
- View total lock wait time across instance/database
- Identify specific row ranges experiencing conflicts
- Review sample lock requests showing affected columns
- Data retained for up to 30 days

**Step 3: Use Transaction Insights**
- Identify transactions causing delays
- View average latency per transaction
- See which tables and columns each transaction reads/writes
- Review commit latency and abort patterns
- Analyze average number of participants in commits

**Step 4: Correlate with Query Insights**
- Compare lock contention with query execution
- Internal Spanner system tables may contribute to lock wait times without topN query entries
- Distinguish application-level from system-level contention

### Resolution Strategies

**For High Lock Contention:**
1. Reduce concurrent writes to same row/key
2. Implement write distribution across multiple keys
3. Use SELECT FOR UPDATE carefully (can increase contention)
4. Shorten transaction duration
5. Review transaction isolation levels
6. Consider read-only replicas for read-heavy workloads

**For Frequent Aborts:**
1. Reduce transaction interdependencies
2. Implement optimistic locking with version columns
3. Break large transactions into smaller ones
4. Use appropriate transaction timeout settings

---

## 3. Hot Spotting and Data Distribution

### Problem Identification
- Latency concentrated on specific database splits
- High CPU utilization on subset of servers
- Uneven load distribution
- Performance ceiling despite headroom on other nodes

### What Causes Hotspots

**Primary Cause: Monotonically Increasing Primary Keys**
- New rows appended to same split
- Only one server handles all writes
- Single node bottleneck

**Example Problem:**
```
PRIMARY KEY (id)  -- where id is auto-incrementing
// All new rows go to last split
// Only 1 of N nodes handles writes
// Result: 1 node at 100% CPU, others idle
```

### Identifying Hotspots

**Step 1: Access Hotspot Insights Dashboard**
- Navigate to Spanner instance in Cloud Console
- Select "Hotspot insights" tab
- No additional cost for monitoring

**Step 2: Review Peak Split CPU Usage**
- Dashboard displays "peak split CPU usage score" (0-100)
- Near 100 score indicates hot splits
- TopN splits table sorted by CPU usage shows:
  - Split key ranges
  - CPU usage score
  - Affected tables

**Step 3: Assess Impact**
- Look for persistent 100% CPU lasting 10+ minutes
- Check for elevated latency coinciding with hotspots
- Verify if affecting user experience

### Resolution Strategies

**Solution 1: Change Primary Key Design**

**Option A: Use UUID (Random)**
```
PRIMARY KEY (request_id)  -- UUID v4 (random)
// Distributes writes across all splits
// Prevents single-node bottleneck
```

**Option B: Reverse Key Order**
```
PRIMARY KEY (user_id, timestamp)  -- timestamp not first
// Spreads writes by user
// Historical data clustered by user
```

**Option C: Bit-Reversed Sequences**
```
PRIMARY KEY (bit_reversed_seq)  -- Spanner built-in
// Sequential but distributed
// Maintains ordering for reads
```

**Option D: Hash-Based Sharding**
```
PRIMARY KEY (shard_id, base_key)
// shard_id = HASH(base_key) % N
// Distributes writes across N shards
// Enables efficient retrieval by base_key
```

**Solution 2: Pre-Split Strategy**
- Manually specify split points
- Distribute data evenly across existing splits
- Reduce likelihood of future hotspots

**Solution 3: Index Optimization**
- Use Index Advisor to optimize query patterns on hot data
- Consider interleaved indexes
- Keep frequently-accessed data together

### Best Practice Summary
- Never use timestamp as first key for high-write tables
- Use UUID v4 or bit-reversed sequences
- Consider sharding for extreme write volumes
- Monitor hotspots continuously

---

## 4. Replication and Consistency

### Spanner's Consistency Guarantees

**External Consistency (Strongest)**
- Spanner provides external consistency by default
- Stronger than strong consistency
- Transactions appear to execute in order they commit

**TrueTime Technology**
- GPS + atomic clocks in data centers
- Precise time synchronization across regions
- Enables external consistency across geographic distribution

### Default Read Behavior

**Strong Reads (Default)**
- Observe effects of all transactions that committed before read start
- Independent of which replica receives the read
- May incur slight latency waiting for replication

### Replication Architecture

**Paxos-Based Synchronous Replication**
- Every write replicated to multiple geo-distributed locations
- Write committed when majority (quorum) of replicas agree
- Ensures durability even if replicas fail

**Multi-Region Deployment**
- Data replicated across multiple regions
- Monitor Cross region replicated bytes metric
- Track replication rate and data volume

### Consistency Problem Scenarios and Solutions

| Problem | Cause | Solution |
|---------|-------|----------|
| Stale reads | Using stale-read version | Use strong reads by default |
| Replication lag observed | Normal eventual consistency window | Expected; use strong reads to avoid |
| Read inconsistency across regions | Eventual consistency in specific configurations | Verify configuration; use strong reads |
| Data loss after write | Insufficient replication | Verify replication topology; check quorum settings |

### Monitoring Replication Health

1. **Check replication status** in Cloud Console
2. **Monitor Cross region replicated bytes** metric
3. **Verify replica count** matches configuration
4. **Review transaction abort rates** (high aborts indicate replication issues)

### Best Practices

- Use strong reads for consistency-critical operations (default)
- Stale reads acceptable for non-critical, historical data
- Monitor replication lag via metrics
- Verify multi-region configuration matches requirements
- Test failover scenarios in staging environment

---

## 5. Connection and Timeout Problems

### Error: DEADLINE_EXCEEDED

#### What It Means
Response not received within configured timeout period

#### Root Causes

| Cause | Indicator | Fix |
|-------|-----------|-----|
| Instance overload | High CPU utilization | Scale up instance or optimize queries |
| Expensive queries | Full table scans, cross-joins | Optimize query, add indexes |
| Lock contention | High lock wait times | Reduce concurrent writes, redesign keys |
| Suboptimal schemas | Slow base table scans | Follow schema design best practices |
| Hotspots | 100% CPU on specific splits | Implement key sharding |
| Network latency | Latency breakdown shows network delays | Check network configuration, GFE status |
| Misconfigured timeouts | Deadline shorter than needed | Increase timeout to realistic value |

### Debugging DEADLINE_EXCEEDED

**Step 1: Check CPU Utilization**
- Monitor CPU% in Cloud Console
- Compare against healthy thresholds (typically <60% CPU is safe)
- High CPU across instance indicates overload

**Step 2: Analyze Query Performance**
- Use Query Statistics tables
- Review expensive queries
- Check execution plans for full table scans

**Step 3: Review Lock Statistics**
- Find row keys with high lock wait times
- Reduce contention on popular rows
- Implement write distribution

**Step 4: Optimize Schema**
- Follow schema design best practices
- Redesign primary keys to avoid hotspots
- Review index strategy

**Step 5: Examine Latency Breakdown**
- Identify where delays occur across:
  - Client to Google Front End (GFE)
  - GFE to Spanner servers
  - Within Spanner processing
- Address specific bottleneck

### Timeout Configuration

#### Default Timeouts
- Short operations (CreateSession): 30 seconds
- Long operations (queries, reads): 3600 seconds

#### Setting Custom Timeouts

**Key Principle**: Never set timeout shorter than actual time needed

**Configuration Pattern:**
```
Initial retry delay: 500 ms
Maximum delay: 16 seconds
Backoff multiplier: 1.5x
Retryable error: UNAVAILABLE
```

**Language Support:**
- C++, C#, Go, Java, Node.js, Python, Ruby
- Each uses client library API (CallSettings, RetrySettings, etc.)

#### Retry Behavior
- UNAVAILABLE errors trigger automatic retry on transient network problems
- Exponential backoff increases wait time until reaching maximum
- Excessive retries can overload backend (avoid aggressive policies)

### Connection Management

**Session Lifecycle**
- Sessions deleted if idle > 1 hour
- Implement connection pooling to reuse sessions
- Monitor session creation rate

**Best Practices:**
1. Set timeouts to reflect "maximum time response is useful"
2. Avoid overly aggressive deadlines
3. Match timeout to expected operation duration
4. Test timeouts with realistic data loads
5. Use exponential backoff for retries
6. Implement connection pooling
7. Monitor session lifecycle

---

## 6. Schema Design Best Practices

### PRIMARY KEY Design

#### Anti-Pattern: Monotonically Increasing Keys
```sql
-- BAD: All writes go to last split
CREATE TABLE orders (
  order_id INT64,
  customer_id INT64,
  PRIMARY KEY (order_id)
);
```

#### Pattern 1: UUID-Based Keys
```sql
-- GOOD: Distributes writes across splits
CREATE TABLE orders (
  order_id STRING(36),  -- UUID v4
  customer_id INT64,
  PRIMARY KEY (order_id)
);
```

#### Pattern 2: Reversed Key Order
```sql
-- GOOD: Spread by customer, historical by timestamp
CREATE TABLE customer_events (
  customer_id INT64,
  event_timestamp INT64 DESC,  -- Most recent first
  event_id STRING(36),
  PRIMARY KEY (customer_id, event_timestamp DESC, event_id)
);
```

#### Pattern 3: Bit-Reversed Sequences
```sql
-- GOOD: Sequential ordering with distribution
CREATE TABLE audit_logs (
  log_id INT64,
  timestamp INT64,
  PRIMARY KEY (log_id)  -- Use SPANNER_SYS.GENERATE_UUID()
);
```

#### Pattern 4: Hash-Based Sharding
```sql
-- GOOD: Distribute high-volume writes
CREATE TABLE user_metrics (
  shard_id INT64,  -- HASH(user_id) % N
  user_id INT64,
  metric_timestamp INT64,
  value FLOAT64,
  PRIMARY KEY (shard_id, user_id, metric_timestamp)
);
```

### INDEX Design

#### Anti-Pattern: Non-Interleaved Index on High-Write Column
```sql
-- BAD: Creates hotspot
CREATE INDEX idx_timestamp ON events (event_timestamp);
```

#### Better: Interleaved Index
```sql
-- GOOD: Keeps related data together
CREATE INDEX idx_user_time ON events (user_id, event_timestamp)
INTERLEAVE IN PARENT users;
```

#### Index Best Practices
- Don't create regular indexes on monotonically increasing columns
- Use interleaved indexes to keep related data together
- Use STORING clause to tradeoff read vs. write performance
- Use NULL_FILTERED to control sparse index storage costs

### Data Organization Principles

**Principle: Cluster Frequently-Accessed Data**
```sql
-- GOOD: Parent-child interleaving for related reads/writes
CREATE TABLE users (
  user_id INT64,
  name STRING(100),
  PRIMARY KEY (user_id)
);

CREATE TABLE user_preferences (
  user_id INT64,
  preference_key STRING(50),
  preference_value STRING(200),
  PRIMARY KEY (user_id, preference_key),
  INTERLEAVE IN PARENT users ON DELETE CASCADE
);
```

**Benefits:**
- Fixed cost to communicate to any server/disk block
- Get as much data as possible while there
- Improves both latency and throughput

### Key Ordering

```sql
-- Descending for "most recent first" queries
CREATE TABLE posts (
  user_id INT64,
  post_timestamp INT64 DESC,  -- Newest first
  post_id STRING(36),
  PRIMARY KEY (user_id, post_timestamp DESC, post_id)
);

-- Ascending for "oldest first" queries
CREATE TABLE archives (
  archive_id INT64,
  created_date INT64 ASC,  -- Oldest first
  record_id STRING(36),
  PRIMARY KEY (archive_id, created_date ASC, record_id)
);
```

### Column Storage Optimization

**STORING Clause:**
```sql
CREATE INDEX idx_user_events ON events (user_id)
STORING (event_type, event_data)
-- Tradeoff: Faster reads, slower writes, larger storage
```

**NULL_FILTERED:**
```sql
CREATE INDEX idx_deleted_users ON users (deletion_date)
WHERE deletion_date IS NOT NULL
-- Reduces storage costs for sparse data
```

---

## 7. Monitoring and Diagnostic Tools

### Built-in Spanner Statistics Tables

Located in `SPANNER_SYS` schema:

| Table | Purpose | Use Case |
|-------|---------|----------|
| `SPANNER_SYS.QUERY_STATS_TOP_MINUTE` | Top queries by elapsed time | Identify slow queries |
| `SPANNER_SYS.LOCK_STATISTICS` | Lock wait times | Find lock contention |
| `SPANNER_SYS.HOT_SPLIT_STATISTICS` | CPU usage by split | Identify hotspots |
| `SPANNER_SYS.TRANSACTION_STATS_TOP_MINUTE` | Transaction performance | Analyze transaction latency |

### Google Cloud Console Tools

**Query Insights**
- Detect query performance problems
- Supports sorting and filtering
- Provides execution plan analysis
- 30-day data retention

**Lock Insights**
- View lock wait times
- Identify row ranges with contention
- See transaction participants
- Track patterns over time

**Hotspot Insights**
- Monitor split CPU usage
- Identify persistent hotspots
- Show affected tables and ranges
- Available in single/multi/dual-region

**Key Visualizer**
- Visual heatmap of data access patterns
- Shows CPU, storage, throughput by key range
- Identify hotspots and usage patterns
- Historical trending

### Request/Transaction Tags

Use tags for better troubleshooting attribution:

```
USING (tags = {"tag_key": "tag_value"})
```

Benefits:
- Attribute requests to specific clients/features
- Filter queries and transactions by tag
- Improved troubleshooting isolation
- Cost allocation per tag

### Latency Analysis

**Components of Spanner Latency:**
1. **Client to Google Front End (GFE)**
2. **GFE to Spanner servers**
3. **Spanner processing** (query execution, locking, replication)
4. **Return path** (GFE to client)

Use latency breakdown in monitoring to identify bottleneck.

### SRE Agent Metrics for Spanner

The SRE Agent includes the following Spanner metrics in its GCP metrics catalog (`sre_agent/resources/gcp_metrics.py`):

| Metric | Description |
|--------|-------------|
| `spanner.googleapis.com/instance/cpu/utilization_by_priority` | CPU utilization broken down by priority |
| `spanner.googleapis.com/instance/storage/used_bytes` | Storage usage in bytes |
| `spanner.googleapis.com/api/request_count` | API request count |
| `spanner.googleapis.com/api/latencies` | API latency distribution |

These metrics can be queried via the `list_time_series` tool with appropriate filters.

---

## 8. Quick Reference Decision Tree

```
START: Spanner Performance Issue
|
+-- Is response not received in time? (DEADLINE_EXCEEDED)
|  +-- Check CPU > 60%? YES -> Scale instance or optimize queries
|  +-- Full table scan? YES -> Add index or use primary key
|  +-- High lock waits? YES -> Reduce concurrent writes, redesign keys
|  +-- Timeout too short? YES -> Increase timeout to realistic value
|
+-- Is query execution slow?
|  +-- Full table scan? YES -> Add appropriate index
|  +-- Wrong join order? YES -> Reorder tables or use FORCE_INDEX
|  +-- Stale statistics? YES -> Force statistics package regeneration
|  +-- Missing index? YES -> Create selective secondary index
|
+-- Is latency concentrated on certain splits? (Hotspots)
|  +-- Monotonically increasing key? YES -> Redesign primary key
|  +-- High-volume writes to same row? YES -> Implement sharding
|  +-- CPU 100% on subset of nodes? YES -> Pre-split distribution
|
+-- High lock contention?
|  +-- Multiple transactions on same row? YES -> Distribute writes
|  +-- Long transactions? YES -> Split into smaller transactions
|  +-- SELECT FOR UPDATE overhead? YES -> Review necessity
|
+-- Schema issues?
   +-- Using timestamp as first key? YES -> Switch to UUID or reorder
   +-- Non-interleaved index on high-write column? YES -> Use interleaved
   +-- Related data scattered? YES -> Use interleave or reorder keys
```

---

## 9. SRE Agent Integration Notes

### Current State
This playbook is a **documentation-only reference**. The SRE Agent's playbook framework (`sre_agent/tools/playbooks/`) does not yet include a code-level Spanner playbook.

### Existing Playbooks in Code
The following playbooks are implemented as structured `Playbook` objects with `DiagnosticStep` sequences:

| Playbook | File | Category |
|----------|------|----------|
| GKE | `sre_agent/tools/playbooks/gke.py` | Compute |
| Cloud Run | `sre_agent/tools/playbooks/cloud_run.py` | Compute |
| Cloud SQL | `sre_agent/tools/playbooks/cloud_sql.py` | Data |
| GCE | `sre_agent/tools/playbooks/gce.py` | Compute |
| BigQuery | `sre_agent/tools/playbooks/bigquery.py` | Data |
| Pub/Sub | `sre_agent/tools/playbooks/pubsub.py` | Messaging |
| Self-Healing | `sre_agent/tools/playbooks/self_healing.py` | Management |

### Implementation Path for Spanner Playbook
To convert this documentation into an agent-usable playbook:

1. Create `sre_agent/tools/playbooks/spanner.py` following the pattern in `cloud_sql.py`
2. Use `PlaybookCategory.DATA` (same as BigQuery and Cloud SQL)
3. Define `TroubleshootingIssue` entries for:
   - Query performance regression
   - Lock contention / deadlocks
   - Hot spotting
   - DEADLINE_EXCEEDED errors
   - Replication issues
4. Map diagnostic steps to existing SRE Agent tools:
   - `list_time_series` for Spanner metrics
   - `get_logs_for_trace` for log correlation
   - `fetch_trace` for latency analysis
5. Register in `registry.py` by adding to `load_all_playbooks()`
6. Note: The playbook registry is currently data-only (no agent tool exposes it). A `search_playbooks` or `get_playbook_details` tool would need to be created to make playbooks accessible to the agent.

---

## Reference Links

**Official Google Cloud Spanner Documentation:**
- [Troubleshoot Performance Regressions](https://docs.cloud.google.com/spanner/docs/troubleshooting-performance-regressions)
- [Deadline Exceeded Errors](https://docs.cloud.google.com/spanner/docs/deadline-exceeded)
- [Find Hotspots in Database](https://docs.cloud.google.com/spanner/docs/find-hotspots-in-database)
- [Lock and Transaction Insights](https://docs.cloud.google.com/spanner/docs/use-lock-and-transaction-insights)
- [Schema Design Best Practices](https://docs.cloud.google.com/spanner/docs/schema-design)
- [Custom Timeouts and Retries](https://docs.cloud.google.com/spanner/docs/custom-timeout-and-retry)
- [Error Codes Reference](https://docs.cloud.google.com/spanner/docs/error-codes)
- [Query Insights](https://docs.cloud.google.com/spanner/docs/using-query-insights)
- [Lock Statistics](https://docs.cloud.google.com/spanner/docs/introspection/lock-statistics)

---

*Last verified: 2026-02-21
*Source: Official Google Cloud Spanner Documentation*
