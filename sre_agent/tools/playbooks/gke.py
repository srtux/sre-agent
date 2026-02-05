"""GKE (Google Kubernetes Engine) Troubleshooting Playbook.

Based on official Google Cloud documentation for GKE troubleshooting.
"""

from .schemas import (
    DiagnosticStep,
    Playbook,
    PlaybookCategory,
    PlaybookSeverity,
    TroubleshootingIssue,
)


def get_playbook() -> Playbook:
    """Get the GKE troubleshooting playbook."""
    return Playbook(
        playbook_id="gke-troubleshooting",
        service_name="GKE",
        display_name="Google Kubernetes Engine",
        category=PlaybookCategory.COMPUTE,
        description=(
            "Troubleshooting playbook for Google Kubernetes Engine covering "
            "cluster issues, workload problems, networking, and scaling."
        ),
        issues=[
            _image_pull_backoff(),
            _crashloop_backoff(),
            _pod_unschedulable(),
            _node_not_ready(),
            _oom_killed(),
            _hpa_not_scaling(),
        ],
        general_diagnostic_steps=[
            DiagnosticStep(
                step_number=1,
                title="Check Cluster Status",
                description="Verify the GKE cluster is in RUNNING state",
                tool_name="get_gke_cluster_health",
                tool_params={
                    "cluster_name": "{cluster_name}",
                    "location": "{location}",
                },
                expected_outcome="Cluster status is RUNNING with healthy node pools",
            ),
            DiagnosticStep(
                step_number=2,
                title="Check Node Conditions",
                description="Look for node pressure conditions (CPU, Memory, Disk, PID)",
                tool_name="analyze_node_conditions",
                tool_params={
                    "cluster_name": "{cluster_name}",
                    "location": "{location}",
                },
                expected_outcome="No pressure conditions detected on nodes",
            ),
            DiagnosticStep(
                step_number=3,
                title="Check Pod Restarts",
                description="Identify pods with high restart counts",
                tool_name="get_pod_restart_events",
                tool_params={"minutes_ago": 60},
                expected_outcome="Low or no pod restarts in the time window",
            ),
            DiagnosticStep(
                step_number=4,
                title="Check for OOM Events",
                description="Find containers that were OOMKilled",
                tool_name="get_container_oom_events",
                tool_params={"minutes_ago": 60},
                expected_outcome="No OOMKilled events detected",
            ),
        ],
        best_practices=[
            "Use namespace resource quotas to prevent resource starvation",
            "Configure pod disruption budgets for high-availability workloads",
            "Enable cluster autoscaling for dynamic workloads",
            "Use node auto-provisioning for diverse workload requirements",
            "Implement proper health checks (liveness, readiness, startup probes)",
            "Use horizontal pod autoscaling based on custom metrics",
            "Enable GKE Dataplane V2 for improved networking",
            "Use Workload Identity for secure GCP API access",
        ],
        key_metrics=[
            "kubernetes.io/container/restart_count",
            "kubernetes.io/container/cpu/limit_utilization",
            "kubernetes.io/container/memory/limit_utilization",
            "kubernetes.io/node/cpu/allocatable_utilization",
            "kubernetes.io/node/memory/allocatable_utilization",
            "kubernetes.io/pod/network/received_bytes_count",
            "kubernetes.io/pod/network/sent_bytes_count",
        ],
        key_logs=[
            "resource.type=k8s_container",
            "resource.type=k8s_pod",
            "resource.type=k8s_node",
            "resource.type=k8s_cluster",
        ],
        related_services=["Cloud Logging", "Cloud Monitoring", "Cloud Trace", "IAM"],
        documentation_urls=[
            "https://cloud.google.com/kubernetes-engine/docs/troubleshooting",
            "https://cloud.google.com/kubernetes-engine/docs/concepts/observability",
        ],
    )


def _image_pull_backoff() -> TroubleshootingIssue:
    """ImagePullBackOff troubleshooting issue."""
    return TroubleshootingIssue(
        issue_id="gke-image-pull-backoff",
        title="ImagePullBackOff / ErrImagePull",
        description="Container image cannot be pulled from the registry",
        symptoms=[
            "Pod stuck in ImagePullBackOff state",
            "ErrImagePull error in pod events",
            "Container creation pending indefinitely",
            "Failed to pull image error in logs",
        ],
        root_causes=[
            "Image name or tag is incorrect",
            "Image does not exist in the registry",
            "Missing or invalid image pull secret",
            "Node service account lacks storage.googleapis.com access",
            "Network connectivity issues to the registry",
            "Private registry authentication failure",
        ],
        severity=PlaybookSeverity.HIGH,
        diagnostic_steps=[
            DiagnosticStep(
                step_number=1,
                title="Check Image Name",
                description="Verify the image name and tag exist in the registry",
                command="gcloud container images list-tags {image_name}",
                expected_outcome="Image and tag are listed in the registry",
            ),
            DiagnosticStep(
                step_number=2,
                title="Check Image Pull Secrets",
                description="Verify image pull secrets are configured correctly",
                command="kubectl get secrets -n {namespace}",
                expected_outcome="Required image pull secrets exist",
            ),
            DiagnosticStep(
                step_number=3,
                title="Check Node Service Account",
                description="Verify node service account has storage.objects.get permission",
                command="gcloud iam service-accounts get-iam-policy {service_account}",
                expected_outcome="Service account has required permissions",
            ),
        ],
        remediation_steps=[
            DiagnosticStep(
                step_number=1,
                title="Fix Image Reference",
                description="Correct the image name and tag in the deployment",
                expected_outcome="Image reference points to existing image",
            ),
            DiagnosticStep(
                step_number=2,
                title="Create Image Pull Secret",
                description="Create or update the image pull secret with valid credentials",
                command="kubectl create secret docker-registry {secret_name} --docker-server={registry} --docker-username={user} --docker-password={password}",
                expected_outcome="Image pull secret created successfully",
            ),
            DiagnosticStep(
                step_number=3,
                title="Grant Storage Access",
                description="Grant the node service account access to Container Registry",
                command="gcloud projects add-iam-policy-binding {project} --member=serviceAccount:{sa} --role=roles/storage.objectViewer",
                expected_outcome="Service account can access container images",
            ),
        ],
        prevention_tips=[
            "Use immutable image tags instead of :latest",
            "Configure image pull secrets at namespace level",
            "Use Artifact Registry with Workload Identity",
            "Enable Binary Authorization for image verification",
        ],
        related_metrics=["kubernetes.io/container/restart_count"],
        related_logs=[
            'textPayload:"Failed to pull image"',
            'textPayload:"ErrImagePull"',
        ],
        error_codes=["ErrImagePull", "ImagePullBackOff"],
        documentation_urls=[
            "https://cloud.google.com/kubernetes-engine/docs/troubleshooting/deployed-workloads#image"
        ],
    )


def _crashloop_backoff() -> TroubleshootingIssue:
    """CrashLoopBackOff troubleshooting issue."""
    return TroubleshootingIssue(
        issue_id="gke-crashloop-backoff",
        title="CrashLoopBackOff",
        description="Container repeatedly crashes after starting",
        symptoms=[
            "Pod stuck in CrashLoopBackOff state",
            "Container restarts incrementally delayed",
            "High restart count on containers",
            "Application fails to start or exits immediately",
        ],
        root_causes=[
            "Application error or uncaught exception",
            "Missing environment variables or configuration",
            "Insufficient memory causing OOMKill",
            "Liveness probe failing too aggressively",
            "Missing dependencies or files",
            "Incorrect command or entrypoint",
        ],
        severity=PlaybookSeverity.HIGH,
        diagnostic_steps=[
            DiagnosticStep(
                step_number=1,
                title="Check Container Logs",
                description="Review the container logs for error messages",
                tool_name="list_log_entries",
                tool_params={
                    "filter": 'resource.type="k8s_container" AND resource.labels.pod_name="{pod_name}"',
                    "minutes_ago": 30,
                },
                expected_outcome="Logs reveal the cause of the crash",
            ),
            DiagnosticStep(
                step_number=2,
                title="Check Previous Container Logs",
                description="Get logs from the previous crashed container instance",
                command="kubectl logs {pod_name} --previous",
                expected_outcome="Previous container logs show crash reason",
            ),
            DiagnosticStep(
                step_number=3,
                title="Check Resource Limits",
                description="Verify memory and CPU limits are sufficient",
                tool_name="get_container_oom_events",
                tool_params={"namespace": "{namespace}", "minutes_ago": 60},
                expected_outcome="No OOM events indicate adequate resources",
            ),
        ],
        remediation_steps=[
            DiagnosticStep(
                step_number=1,
                title="Fix Application Error",
                description="Address the application error causing the crash",
                expected_outcome="Application starts without errors",
            ),
            DiagnosticStep(
                step_number=2,
                title="Increase Memory Limits",
                description="If OOMKilled, increase the container memory limits",
                expected_outcome="Container has sufficient memory to run",
            ),
            DiagnosticStep(
                step_number=3,
                title="Adjust Liveness Probe",
                description="Increase initialDelaySeconds or adjust failure threshold",
                expected_outcome="Probe allows application time to start",
            ),
        ],
        prevention_tips=[
            "Implement proper error handling and graceful shutdown",
            "Set appropriate resource requests and limits",
            "Use startup probes for slow-starting applications",
            "Test containers locally before deployment",
        ],
        related_metrics=[
            "kubernetes.io/container/restart_count",
            "kubernetes.io/container/memory/limit_utilization",
        ],
        related_logs=[
            'severity>=ERROR AND resource.type="k8s_container"',
            'textPayload:"OOMKilled"',
        ],
        error_codes=["CrashLoopBackOff", "Error", "OOMKilled"],
        documentation_urls=[
            "https://cloud.google.com/kubernetes-engine/docs/troubleshooting/deployed-workloads#crashloopbackoff"
        ],
    )


def _pod_unschedulable() -> TroubleshootingIssue:
    """Pod Unschedulable troubleshooting issue."""
    return TroubleshootingIssue(
        issue_id="gke-pod-unschedulable",
        title="Pod Unschedulable",
        description="Pod cannot be scheduled to any node",
        symptoms=[
            "Pod stuck in Pending state",
            "FailedScheduling event in pod events",
            "Insufficient CPU or memory warnings",
            "No nodes available to schedule pod",
        ],
        root_causes=[
            "Insufficient cluster resources (CPU, memory)",
            "Node selector not matching any nodes",
            "Pod tolerations not matching node taints",
            "PodDisruptionBudget blocking eviction",
            "ResourceQuota exceeded in namespace",
            "Node affinity rules too restrictive",
        ],
        severity=PlaybookSeverity.MEDIUM,
        diagnostic_steps=[
            DiagnosticStep(
                step_number=1,
                title="Check Pod Events",
                description="Review the scheduling events for the pod",
                command="kubectl describe pod {pod_name} -n {namespace}",
                expected_outcome="Events show the scheduling failure reason",
            ),
            DiagnosticStep(
                step_number=2,
                title="Check Node Resources",
                description="Verify nodes have available resources",
                tool_name="analyze_node_conditions",
                tool_params={
                    "cluster_name": "{cluster_name}",
                    "location": "{location}",
                },
                expected_outcome="Nodes have capacity for new pods",
            ),
            DiagnosticStep(
                step_number=3,
                title="Check Resource Quotas",
                description="Verify namespace quotas are not exceeded",
                command="kubectl describe resourcequota -n {namespace}",
                expected_outcome="Quotas have available headroom",
            ),
        ],
        remediation_steps=[
            DiagnosticStep(
                step_number=1,
                title="Scale Up Cluster",
                description="Add more nodes or enable cluster autoscaler",
                command="gcloud container clusters resize {cluster} --num-nodes={count}",
                expected_outcome="Additional capacity available for pods",
            ),
            DiagnosticStep(
                step_number=2,
                title="Reduce Pod Requirements",
                description="Lower resource requests if over-specified",
                expected_outcome="Pod requests fit on available nodes",
            ),
            DiagnosticStep(
                step_number=3,
                title="Fix Node Selector",
                description="Update node selector to match available nodes",
                expected_outcome="Pod can be scheduled on matching nodes",
            ),
        ],
        prevention_tips=[
            "Enable cluster autoscaler for dynamic capacity",
            "Set appropriate resource requests (not too high)",
            "Use node auto-provisioning for diverse workloads",
            "Monitor cluster capacity proactively",
        ],
        related_metrics=[
            "kubernetes.io/node/cpu/allocatable_utilization",
            "kubernetes.io/node/memory/allocatable_utilization",
        ],
        related_logs=['textPayload:"FailedScheduling"', 'textPayload:"Insufficient"'],
        error_codes=["FailedScheduling", "Unschedulable"],
        documentation_urls=[
            "https://cloud.google.com/kubernetes-engine/docs/troubleshooting/deployed-workloads#unschedulable"
        ],
    )


def _node_not_ready() -> TroubleshootingIssue:
    """Node NotReady troubleshooting issue."""
    return TroubleshootingIssue(
        issue_id="gke-node-not-ready",
        title="Node NotReady",
        description="Node fails to join the cluster or becomes unhealthy",
        symptoms=[
            "Node in NotReady state",
            "Pods being evicted from node",
            "Node registration timeout",
            "kubelet not responding",
        ],
        root_causes=[
            "Network connectivity to control plane",
            "Node disk pressure",
            "Node memory pressure",
            "kubelet service crashed",
            "Container runtime issues",
            "Service account permissions",
        ],
        severity=PlaybookSeverity.HIGH,
        diagnostic_steps=[
            DiagnosticStep(
                step_number=1,
                title="Check Node Conditions",
                description="Get detailed node conditions",
                tool_name="analyze_node_conditions",
                tool_params={
                    "cluster_name": "{cluster_name}",
                    "location": "{location}",
                },
                expected_outcome="Node conditions reveal the issue",
            ),
            DiagnosticStep(
                step_number=2,
                title="Check Node Logs",
                description="Review system logs on the node",
                tool_name="list_log_entries",
                tool_params={
                    "filter": 'resource.type="gce_instance" AND resource.labels.instance_id="{node_id}"',
                    "minutes_ago": 30,
                },
                expected_outcome="Logs show node health issues",
            ),
            DiagnosticStep(
                step_number=3,
                title="Check Serial Console",
                description="Check node serial port output for boot issues",
                command="gcloud compute instances get-serial-port-output {node_name}",
                expected_outcome="Serial output shows boot progress",
            ),
        ],
        remediation_steps=[
            DiagnosticStep(
                step_number=1,
                title="Cordon and Drain Node",
                description="Safely remove workloads from the unhealthy node",
                command="kubectl cordon {node_name} && kubectl drain {node_name} --ignore-daemonsets --delete-emptydir-data",
                expected_outcome="Workloads moved to healthy nodes",
            ),
            DiagnosticStep(
                step_number=2,
                title="Repair or Replace Node",
                description="Let GKE repair the node or delete for replacement",
                expected_outcome="New healthy node joins the cluster",
            ),
        ],
        prevention_tips=[
            "Enable node auto-repair for automatic recovery",
            "Set appropriate node pool size for fault tolerance",
            "Use regional clusters for higher availability",
            "Monitor node health metrics proactively",
        ],
        related_metrics=[
            "kubernetes.io/node/cpu/allocatable_utilization",
            "kubernetes.io/node/memory/allocatable_utilization",
            "kubernetes.io/node/ephemeral_storage/used_bytes",
        ],
        related_logs=[
            'resource.type="k8s_node"',
            'textPayload:"NodeNotReady"',
        ],
        error_codes=["NodeNotReady", "KubeletNotReady"],
        documentation_urls=[
            "https://cloud.google.com/kubernetes-engine/docs/troubleshooting/node-registration"
        ],
    )


def _oom_killed() -> TroubleshootingIssue:
    """OOMKilled troubleshooting issue."""
    return TroubleshootingIssue(
        issue_id="gke-oom-killed",
        title="OOMKilled",
        description="Container killed due to exceeding memory limits",
        symptoms=[
            "Container exit code 137",
            "OOMKilled reason in pod status",
            "Sudden container restarts",
            "Application performance degradation before crash",
        ],
        root_causes=[
            "Memory limit set too low",
            "Memory leak in application",
            "Large data processing in memory",
            "JVM heap misconfiguration",
            "Caching without eviction",
        ],
        severity=PlaybookSeverity.HIGH,
        diagnostic_steps=[
            DiagnosticStep(
                step_number=1,
                title="Check OOM Events",
                description="Find containers that were OOMKilled",
                tool_name="get_container_oom_events",
                tool_params={"namespace": "{namespace}", "minutes_ago": 120},
                expected_outcome="Identify affected containers",
            ),
            DiagnosticStep(
                step_number=2,
                title="Check Memory Usage Trend",
                description="Analyze memory utilization over time",
                tool_name="list_time_series",
                tool_params={
                    "metric_type": "kubernetes.io/container/memory/used_bytes",
                    "minutes_ago": 60,
                },
                expected_outcome="Memory usage pattern reveals leak or spike",
            ),
        ],
        remediation_steps=[
            DiagnosticStep(
                step_number=1,
                title="Increase Memory Limits",
                description="Increase the container memory limits",
                expected_outcome="Container has sufficient memory headroom",
            ),
            DiagnosticStep(
                step_number=2,
                title="Fix Memory Leak",
                description="Profile and fix the memory leak in application code",
                expected_outcome="Memory usage stabilizes over time",
            ),
            DiagnosticStep(
                step_number=3,
                title="Enable Vertical Pod Autoscaler",
                description="Use VPA to automatically adjust memory limits",
                expected_outcome="Memory limits auto-adjust based on usage",
            ),
        ],
        prevention_tips=[
            "Set memory limits with 20% headroom above typical usage",
            "Use memory profiling in development",
            "Implement proper garbage collection tuning",
            "Monitor memory utilization trends",
        ],
        related_metrics=[
            "kubernetes.io/container/memory/used_bytes",
            "kubernetes.io/container/memory/limit_utilization",
            "kubernetes.io/container/restart_count",
        ],
        related_logs=['textPayload:"OOMKilled"', 'textPayload:"killed"'],
        error_codes=["OOMKilled", "137"],
        documentation_urls=[
            "https://cloud.google.com/kubernetes-engine/docs/troubleshooting/deployed-workloads#oomkilled"
        ],
    )


def _hpa_not_scaling() -> TroubleshootingIssue:
    """HPA Not Scaling troubleshooting issue."""
    return TroubleshootingIssue(
        issue_id="gke-hpa-not-scaling",
        title="HPA Not Scaling",
        description="Horizontal Pod Autoscaler is not scaling workloads",
        symptoms=[
            "Pods not scaling despite high load",
            "HPA shows unknown metrics",
            "Desired replicas not changing",
            "Scale-up taking too long",
        ],
        root_causes=[
            "Metrics server not available",
            "Custom metrics not being collected",
            "Resource requests not set on containers",
            "HPA thresholds not triggering",
            "Max replicas already reached",
            "Stabilization window too long",
        ],
        severity=PlaybookSeverity.MEDIUM,
        diagnostic_steps=[
            DiagnosticStep(
                step_number=1,
                title="Check HPA Status",
                description="Get the current HPA status and metrics",
                command="kubectl describe hpa {hpa_name} -n {namespace}",
                expected_outcome="HPA shows current and target metrics",
            ),
            DiagnosticStep(
                step_number=2,
                title="Check Metrics Availability",
                description="Verify metrics are being collected",
                command="kubectl top pods -n {namespace}",
                expected_outcome="Metrics are available for pods",
            ),
            DiagnosticStep(
                step_number=3,
                title="Analyze HPA Events",
                description="Review HPA scaling decisions",
                tool_name="analyze_hpa_events",
                tool_params={
                    "namespace": "{namespace}",
                    "deployment_name": "{deployment}",
                    "minutes_ago": 60,
                },
                expected_outcome="Scaling events show decision pattern",
            ),
        ],
        remediation_steps=[
            DiagnosticStep(
                step_number=1,
                title="Set Resource Requests",
                description="Ensure containers have CPU/memory requests set",
                expected_outcome="HPA can calculate utilization percentages",
            ),
            DiagnosticStep(
                step_number=2,
                title="Adjust HPA Thresholds",
                description="Lower the target utilization to trigger scaling earlier",
                expected_outcome="HPA scales up at appropriate load levels",
            ),
            DiagnosticStep(
                step_number=3,
                title="Increase Max Replicas",
                description="Raise maxReplicas if capacity limit reached",
                expected_outcome="HPA can scale to handle peak load",
            ),
        ],
        prevention_tips=[
            "Always set resource requests for HPA to work",
            "Use custom metrics for application-specific scaling",
            "Set appropriate stabilization windows",
            "Monitor HPA behavior during load tests",
        ],
        related_metrics=[
            "kubernetes.io/deployment/replicas",
            "kubernetes.io/deployment/desired_replicas",
            "kubernetes.io/container/cpu/limit_utilization",
        ],
        related_logs=[
            'resource.type="k8s_cluster" AND textPayload:"autoscaler"',
        ],
        error_codes=["FailedGetScale", "FailedComputeMetricsReplicas"],
        documentation_urls=[
            "https://cloud.google.com/kubernetes-engine/docs/how-to/horizontal-pod-autoscaling"
        ],
    )
