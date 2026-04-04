---
name: cloud-run-troubleshooting
description: "Step-by-step Cloud Run troubleshooting for container startup failures, cold start latency, memory limits, connection resets, and permission errors."
---

## Cloud Run Troubleshooting Workflow

Use this skill to diagnose and resolve Google Cloud Run issues.

### General Diagnostics (Start Here)

1. **Check Service Status**: `gcloud run services describe <service> --region=<region>`
2. **Check Recent Logs**: Use `list_log_entries` with filter `resource.type="cloud_run_revision" AND resource.labels.service_name="<service>"` and `minutes_ago=30`
3. **Check Request Errors**: Use `list_log_entries` with filter `resource.type="cloud_run_revision" AND httpRequest.status>=400` and `minutes_ago=30`

### Issue: Container Failed to Start

**Symptoms**: Deployment fails with "Container failed to start", 0 healthy instances, revision stuck deploying.

**Diagnostic Steps**:
1. Use `list_log_entries` with `resource.type="cloud_run_revision" AND severity>=ERROR` to check startup logs
2. Verify container listens on `0.0.0.0:$PORT` (not localhost)
3. Test locally: `docker run -p 8080:8080 -e PORT=8080 <image>`

**Remediation**:
- Fix port binding to `0.0.0.0:$PORT`
- Configure longer startup probe timeout
- Enable CPU boost: `gcloud run services update <service> --cpu-boost`

### Issue: Cold Start Latency

**Symptoms**: First requests have high latency, intermittent spikes, latency after idle periods.

**Diagnostic Steps**:
1. Use `list_time_series` with metric `run.googleapis.com/container/startup_latencies` to measure startup time
2. Check minimum instance configuration

**Remediation**:
- Set minimum instances: `gcloud run services update <service> --min-instances=1`
- Enable CPU boost: `gcloud run services update <service> --cpu-boost`
- Defer expensive initialization until after startup

### Issue: Memory Limit Exceeded

**Symptoms**: Unexpected container restarts, 503 errors, memory at 100%, OOM in logs.

**Diagnostic Steps**:
1. Use `list_time_series` with metric `run.googleapis.com/container/memory/utilizations` to check memory usage
2. Use `list_log_entries` with filter containing `"memory"` to find OOM errors

**Remediation**:
- Increase memory: `gcloud run services update <service> --memory=2Gi`
- Reduce concurrency: `gcloud run services update <service> --concurrency=50`
- Delete temporary files promptly (Cloud Run uses in-memory filesystem)

### Issue: Connection Reset by Peer

**Symptoms**: ECONNRESET errors, connection refused, timeouts on outbound requests.

**Diagnostic Steps**:
1. Use `list_log_entries` with filter containing `"ECONNRESET"` to find connection errors
2. Check VPC connector configuration

**Remediation**:
- Switch to instance-based billing for background work
- Implement connection pooling with retry logic
- Configure socket keepalive options

### Issue: Permission Denied (401/403)

**Symptoms**: 401 Unauthorized or 403 Forbidden responses, unable to invoke service.

**Diagnostic Steps**:
1. Check IAM bindings: `gcloud run services get-iam-policy <service> --region=<region>`
2. Verify authentication configuration

**Remediation**:
- Grant invoker role: `gcloud run services add-iam-policy-binding <service> --member='user:<email>' --role='roles/run.invoker'`
- For public access: add `allUsers` with `roles/run.invoker`

### Key Metrics to Monitor

- `run.googleapis.com/request_count` - Request volume
- `run.googleapis.com/request_latencies` - Request latency
- `run.googleapis.com/container/memory/utilizations` - Memory usage
- `run.googleapis.com/container/cpu/utilizations` - CPU usage
- `run.googleapis.com/container/startup_latencies` - Cold start time

### Best Practices

- Configure appropriate memory and CPU limits
- Use minimum instances for latency-sensitive services
- Enable startup CPU boost for faster cold starts
- Implement health checks for reliability
- Configure request timeout appropriately
