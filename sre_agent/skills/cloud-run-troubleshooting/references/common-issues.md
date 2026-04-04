# Cloud Run Common Issues Quick Reference

## Error Code Reference

| Error | Meaning | First Check |
|-------|---------|-------------|
| `CONTAINER_MISSING` | Container image not found | Image path, Artifact Registry permissions |
| `USER_CODE_FAILED` | Application crashed during startup | Container logs, PORT binding |
| `MEMORY_LIMIT_EXCEEDED` | Out of memory | Memory config, concurrency, temp files |
| `ECONNRESET` | Outbound connection reset | VPC connector, connection pooling |
| `ETIMEDOUT` | Outbound connection timeout | Network config, firewall rules |
| `401` | Unauthorized | ID token, audience claim |
| `403` | Forbidden | IAM invoker role |

## Key Cloud Run Metrics

- `run.googleapis.com/request_count` - Total requests (by response code)
- `run.googleapis.com/request_latencies` - Latency distribution
- `run.googleapis.com/container/memory/utilizations` - Memory as % of limit
- `run.googleapis.com/container/cpu/utilizations` - CPU utilization
- `run.googleapis.com/container/startup_latencies` - Container startup time
- `run.googleapis.com/container/instance_count` - Active instances

## Log Filters

```
# All logs for a service
resource.type="cloud_run_revision" AND resource.labels.service_name="my-service"

# Error logs only
resource.type="cloud_run_revision" AND severity>=ERROR

# HTTP errors (4xx/5xx)
resource.type="cloud_run_revision" AND httpRequest.status>=400

# Memory-related issues
resource.type="cloud_run_revision" AND textPayload:"memory"

# Connection errors
resource.type="cloud_run_revision" AND textPayload:"ECONNRESET"
```

## Documentation Links

- [Cloud Run Troubleshooting](https://cloud.google.com/run/docs/troubleshooting)
- [Container Startup](https://cloud.google.com/run/docs/troubleshooting#container-failed-to-start)
- [Memory Limits](https://cloud.google.com/run/docs/configuring/services/memory-limits)
- [Authentication](https://cloud.google.com/run/docs/authenticating/overview)
- [Performance Tips](https://cloud.google.com/run/docs/tips/general#optimizing_performance)
