# GKE Common Issues Quick Reference

## Error Code Reference

| Error | Meaning | First Check |
|-------|---------|-------------|
| `ImagePullBackOff` | Cannot pull container image | Image name/tag, pull secrets, SA permissions |
| `CrashLoopBackOff` | Container repeatedly crashes | Container logs, previous logs, resource limits |
| `OOMKilled` (exit 137) | Out of memory | Memory limits, usage trends, VPA |
| `FailedScheduling` | Cannot find suitable node | Node resources, selectors, quotas |
| `NodeNotReady` | Node unhealthy | Node conditions, kubelet, disk/memory pressure |
| `FailedGetScale` | HPA cannot read metrics | Metrics server, resource requests |
| `CreateContainerError` | Container runtime error | Runtime logs, image compatibility |

## Key GKE Metrics

### Container Level
- `kubernetes.io/container/restart_count` - Restart frequency
- `kubernetes.io/container/cpu/limit_utilization` - CPU vs limit
- `kubernetes.io/container/memory/limit_utilization` - Memory vs limit
- `kubernetes.io/container/memory/used_bytes` - Absolute memory usage

### Node Level
- `kubernetes.io/node/cpu/allocatable_utilization` - Node CPU pressure
- `kubernetes.io/node/memory/allocatable_utilization` - Node memory pressure
- `kubernetes.io/node/ephemeral_storage/used_bytes` - Disk pressure

### Cluster Level
- `kubernetes.io/deployment/replicas` - Current replica count
- `kubernetes.io/deployment/desired_replicas` - Desired replica count

## Log Filters

```
# All container logs for a specific pod
resource.type="k8s_container" AND resource.labels.pod_name="my-pod"

# Error-level container logs
severity>=ERROR AND resource.type="k8s_container"

# OOM events
textPayload:"OOMKilled"

# Image pull failures
textPayload:"Failed to pull image" OR textPayload:"ErrImagePull"

# Scheduling failures
textPayload:"FailedScheduling" OR textPayload:"Insufficient"

# Node issues
resource.type="k8s_node" AND textPayload:"NodeNotReady"
```

## Documentation Links

- [GKE Troubleshooting](https://cloud.google.com/kubernetes-engine/docs/troubleshooting)
- [GKE Observability](https://cloud.google.com/kubernetes-engine/docs/concepts/observability)
- [Workload Troubleshooting](https://cloud.google.com/kubernetes-engine/docs/troubleshooting/deployed-workloads)
- [HPA Guide](https://cloud.google.com/kubernetes-engine/docs/how-to/horizontal-pod-autoscaling)
