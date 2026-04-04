---
name: gke-troubleshooting
description: "Step-by-step GKE troubleshooting for pod crashes, node issues, OOM kills, scaling failures, image pull errors, and networking problems on Google Kubernetes Engine."
---

## GKE Troubleshooting Workflow

Use this skill to diagnose and resolve Google Kubernetes Engine issues.

### General Diagnostics (Start Here)

1. **Check Cluster Status**: Use `get_gke_cluster_health` with the cluster name and location to verify the cluster is RUNNING with healthy node pools.
2. **Check Node Conditions**: Use `analyze_node_conditions` to detect CPU, memory, disk, or PID pressure on nodes.
3. **Check Pod Restarts**: Use `get_pod_restart_events` with `minutes_ago=60` to find pods with high restart counts.
4. **Check OOM Events**: Use `get_container_oom_events` with `minutes_ago=60` to find OOMKilled containers.

### Issue: ImagePullBackOff / ErrImagePull

**Symptoms**: Pod stuck in ImagePullBackOff, ErrImagePull errors, container creation pending.

**Diagnostic Steps**:
1. Verify image name and tag exist in the registry
2. Check image pull secrets: `kubectl get secrets -n <namespace>`
3. Verify node service account has `storage.objects.get` permission

**Remediation**:
- Fix image reference to point to an existing image
- Create/update image pull secret with valid credentials
- Grant the node service account `roles/storage.objectViewer`

**Prevention**: Use immutable image tags, configure pull secrets at namespace level, use Artifact Registry with Workload Identity.

### Issue: CrashLoopBackOff

**Symptoms**: Pod in CrashLoopBackOff, high restart count, container exits immediately.

**Diagnostic Steps**:
1. Use `list_log_entries` with filter `resource.type="k8s_container" AND resource.labels.pod_name="<pod>"` to check container logs
2. Check previous container logs: `kubectl logs <pod> --previous`
3. Use `get_container_oom_events` to check if OOMKilled

**Remediation**:
- Fix the application error causing the crash
- Increase memory limits if OOMKilled
- Adjust liveness probe: increase `initialDelaySeconds` or failure threshold

**Prevention**: Implement error handling, set appropriate resource limits, use startup probes.

### Issue: Pod Unschedulable (Pending)

**Symptoms**: Pod stuck in Pending, FailedScheduling events, insufficient resource warnings.

**Diagnostic Steps**:
1. Describe the pod to see scheduling failure: `kubectl describe pod <pod> -n <namespace>`
2. Use `analyze_node_conditions` to check available node resources
3. Check resource quotas: `kubectl describe resourcequota -n <namespace>`

**Remediation**:
- Scale up cluster or enable cluster autoscaler
- Lower resource requests if over-specified
- Update node selector to match available nodes

### Issue: Node NotReady

**Symptoms**: Node in NotReady state, pods being evicted, kubelet not responding.

**Diagnostic Steps**:
1. Use `analyze_node_conditions` for detailed node conditions
2. Use `list_log_entries` with filter `resource.type="gce_instance"` for node logs
3. Check serial console output

**Remediation**:
- Cordon and drain the unhealthy node
- Let GKE auto-repair or manually delete the node for replacement

**Prevention**: Enable node auto-repair, use regional clusters, monitor node health metrics.

### Issue: OOMKilled

**Symptoms**: Container exit code 137, OOMKilled reason, sudden restarts.

**Diagnostic Steps**:
1. Use `get_container_oom_events` to identify affected containers
2. Use `list_time_series` with metric `kubernetes.io/container/memory/used_bytes` to check memory usage trend

**Remediation**:
- Increase container memory limits (add 20% headroom)
- Profile and fix memory leaks
- Enable Vertical Pod Autoscaler (VPA)

### Issue: HPA Not Scaling

**Symptoms**: Pods not scaling despite high load, HPA shows unknown metrics.

**Diagnostic Steps**:
1. `kubectl describe hpa <name> -n <namespace>` to check HPA status
2. `kubectl top pods -n <namespace>` to verify metrics availability
3. Use `analyze_hpa_events` to review scaling decisions

**Remediation**:
- Ensure containers have CPU/memory requests set
- Lower target utilization to trigger scaling earlier
- Increase maxReplicas if capacity limit reached

### Key Metrics to Monitor

- `kubernetes.io/container/restart_count`
- `kubernetes.io/container/cpu/limit_utilization`
- `kubernetes.io/container/memory/limit_utilization`
- `kubernetes.io/node/cpu/allocatable_utilization`
- `kubernetes.io/node/memory/allocatable_utilization`

### Key Log Filters

- `resource.type=k8s_container`
- `resource.type=k8s_pod`
- `resource.type=k8s_node`

### Best Practices

- Use namespace resource quotas to prevent resource starvation
- Configure pod disruption budgets for HA workloads
- Enable cluster autoscaling for dynamic workloads
- Implement proper health checks (liveness, readiness, startup probes)
- Use Workload Identity for secure GCP API access
