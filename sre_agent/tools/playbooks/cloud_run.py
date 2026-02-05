"""Cloud Run Troubleshooting Playbook.

Based on official Google Cloud documentation for Cloud Run troubleshooting.
"""

from .schemas import (
    DiagnosticStep,
    Playbook,
    PlaybookCategory,
    PlaybookSeverity,
    TroubleshootingIssue,
)


def get_playbook() -> Playbook:
    """Get the Cloud Run troubleshooting playbook."""
    return Playbook(
        playbook_id="cloud-run-troubleshooting",
        service_name="Cloud Run",
        display_name="Cloud Run",
        category=PlaybookCategory.COMPUTE,
        description=(
            "Troubleshooting playbook for Cloud Run covering container startup, "
            "networking, memory issues, and cold starts."
        ),
        issues=[
            _container_failed_to_start(),
            _cold_start_latency(),
            _memory_limit_exceeded(),
            _connection_reset(),
            _permission_denied(),
        ],
        general_diagnostic_steps=[
            DiagnosticStep(
                step_number=1,
                title="Check Service Status",
                description="Verify the Cloud Run service is deployed and healthy",
                command="gcloud run services describe {service_name} --region={region}",
                expected_outcome="Service is active with healthy revisions",
            ),
            DiagnosticStep(
                step_number=2,
                title="Check Recent Logs",
                description="Review container logs for errors",
                tool_name="list_log_entries",
                tool_params={
                    "filter": 'resource.type="cloud_run_revision" AND resource.labels.service_name="{service_name}"',
                    "minutes_ago": 30,
                },
                expected_outcome="No error logs in recent entries",
            ),
            DiagnosticStep(
                step_number=3,
                title="Check Request Logs",
                description="Review request-level logs for errors",
                tool_name="list_log_entries",
                tool_params={
                    "filter": 'resource.type="cloud_run_revision" AND httpRequest.status>=400',
                    "minutes_ago": 30,
                },
                expected_outcome="No 4xx/5xx errors in request logs",
            ),
        ],
        best_practices=[
            "Configure appropriate memory and CPU limits",
            "Use minimum instances for latency-sensitive services",
            "Enable startup CPU boost for faster cold starts",
            "Implement health checks for reliability",
            "Use Cloud Run Jobs for background tasks",
            "Configure request timeout appropriately",
        ],
        key_metrics=[
            "run.googleapis.com/request_count",
            "run.googleapis.com/request_latencies",
            "run.googleapis.com/container/memory/utilizations",
            "run.googleapis.com/container/cpu/utilizations",
            "run.googleapis.com/container/startup_latencies",
        ],
        key_logs=[
            "resource.type=cloud_run_revision",
            "resource.type=cloud_run_job",
        ],
        related_services=["Cloud Build", "Artifact Registry", "Cloud Logging"],
        documentation_urls=[
            "https://cloud.google.com/run/docs/troubleshooting",
        ],
    )


def _container_failed_to_start() -> TroubleshootingIssue:
    """Container failed to start issue."""
    return TroubleshootingIssue(
        issue_id="cloudrun-container-failed-start",
        title="Container Failed to Start",
        description="Container exits immediately or fails to become ready within 4 minutes",
        symptoms=[
            "Deployment fails with 'Container failed to start'",
            "Service shows 0 healthy instances",
            "Revision stuck in deploying state",
            "Container exits with non-zero code",
        ],
        root_causes=[
            "Container not listening on correct PORT",
            "Container listening on localhost instead of 0.0.0.0",
            "Missing dependencies or configuration",
            "Application crash during startup",
            "Container not 64-bit Linux compatible",
            "Startup takes longer than 4 minutes",
        ],
        severity=PlaybookSeverity.HIGH,
        diagnostic_steps=[
            DiagnosticStep(
                step_number=1,
                title="Check Container Logs",
                description="Review logs from the failed container startup",
                tool_name="list_log_entries",
                tool_params={
                    "filter": 'resource.type="cloud_run_revision" AND severity>=ERROR',
                    "minutes_ago": 30,
                },
                expected_outcome="Logs reveal startup failure reason",
            ),
            DiagnosticStep(
                step_number=2,
                title="Verify Port Configuration",
                description="Check that container listens on $PORT environment variable",
                expected_outcome="Container binds to 0.0.0.0:$PORT",
            ),
            DiagnosticStep(
                step_number=3,
                title="Test Locally",
                description="Run container locally to reproduce the issue",
                command="docker run -p 8080:8080 -e PORT=8080 {image}",
                expected_outcome="Container starts and responds to requests",
            ),
        ],
        remediation_steps=[
            DiagnosticStep(
                step_number=1,
                title="Fix Port Binding",
                description="Ensure application listens on 0.0.0.0:$PORT",
                expected_outcome="Container accepts connections on the configured port",
            ),
            DiagnosticStep(
                step_number=2,
                title="Increase Startup Timeout",
                description="Configure longer startup probe timeout if needed",
                expected_outcome="Container has time to complete startup",
            ),
            DiagnosticStep(
                step_number=3,
                title="Enable Startup CPU Boost",
                description="Enable CPU boost to accelerate startup",
                command="gcloud run services update {service} --cpu-boost",
                expected_outcome="Faster startup with boosted CPU",
            ),
        ],
        prevention_tips=[
            "Test containers locally with the same PORT configuration",
            "Use startup probes to signal readiness",
            "Enable startup CPU boost for initialization-heavy apps",
            "Keep startup time under 4 minutes",
        ],
        related_metrics=[
            "run.googleapis.com/container/startup_latencies",
        ],
        related_logs=[
            'severity>=ERROR AND resource.type="cloud_run_revision"',
        ],
        error_codes=["CONTAINER_MISSING", "USER_CODE_FAILED"],
        documentation_urls=[
            "https://cloud.google.com/run/docs/troubleshooting#container-failed-to-start"
        ],
    )


def _cold_start_latency() -> TroubleshootingIssue:
    """Cold start latency issue."""
    return TroubleshootingIssue(
        issue_id="cloudrun-cold-start",
        title="Cold Start Latency",
        description="High latency on first requests due to container initialization",
        symptoms=[
            "First requests have much higher latency",
            "Intermittent latency spikes",
            "Latency increases after idle periods",
            "p99 latency much higher than p50",
        ],
        root_causes=[
            "No minimum instances configured",
            "Slow application initialization",
            "Large container image",
            "Heavy dependencies loaded at startup",
            "JIT compilation overhead (Java/Node)",
        ],
        severity=PlaybookSeverity.MEDIUM,
        diagnostic_steps=[
            DiagnosticStep(
                step_number=1,
                title="Check Startup Latencies",
                description="Review container startup time metrics",
                tool_name="list_time_series",
                tool_params={
                    "metric_type": "run.googleapis.com/container/startup_latencies",
                    "minutes_ago": 60,
                },
                expected_outcome="Identify typical startup duration",
            ),
            DiagnosticStep(
                step_number=2,
                title="Check Instance Count",
                description="Review minimum instance configuration",
                command="gcloud run services describe {service} --region={region} --format='value(spec.template.spec.containerConcurrency)'",
                expected_outcome="Minimum instances configured for traffic pattern",
            ),
        ],
        remediation_steps=[
            DiagnosticStep(
                step_number=1,
                title="Set Minimum Instances",
                description="Configure minimum instances to keep containers warm",
                command="gcloud run services update {service} --min-instances=1",
                expected_outcome="At least one instance always running",
            ),
            DiagnosticStep(
                step_number=2,
                title="Enable Startup CPU Boost",
                description="Enable CPU boost to accelerate cold starts",
                command="gcloud run services update {service} --cpu-boost",
                expected_outcome="Startup time reduced by up to 50%",
            ),
            DiagnosticStep(
                step_number=3,
                title="Optimize Initialization",
                description="Defer expensive initialization until after startup",
                expected_outcome="Faster time to first request",
            ),
        ],
        prevention_tips=[
            "Use minimum instances for latency-sensitive services",
            "Enable startup CPU boost",
            "Implement lazy initialization",
            "Optimize container image size and dependencies",
        ],
        related_metrics=[
            "run.googleapis.com/container/startup_latencies",
            "run.googleapis.com/request_latencies",
            "run.googleapis.com/container/instance_count",
        ],
        related_logs=[],
        error_codes=[],
        documentation_urls=[
            "https://cloud.google.com/run/docs/tips/general#optimizing_performance"
        ],
    )


def _memory_limit_exceeded() -> TroubleshootingIssue:
    """Memory limit exceeded issue."""
    return TroubleshootingIssue(
        issue_id="cloudrun-memory-exceeded",
        title="Memory Limit Exceeded",
        description="Container crashes due to exceeding configured memory limit",
        symptoms=[
            "Container restarts unexpectedly",
            "503 errors during high load",
            "Memory utilization at 100%",
            "OOM errors in logs",
        ],
        root_causes=[
            "Memory limit set too low",
            "Memory leak in application",
            "High concurrency with large request payloads",
            "Temporary files consuming memory (in-memory filesystem)",
            "Large in-memory caches",
        ],
        severity=PlaybookSeverity.HIGH,
        diagnostic_steps=[
            DiagnosticStep(
                step_number=1,
                title="Check Memory Utilization",
                description="Review memory usage metrics",
                tool_name="list_time_series",
                tool_params={
                    "metric_type": "run.googleapis.com/container/memory/utilizations",
                    "minutes_ago": 60,
                },
                expected_outcome="Memory utilization pattern visible",
            ),
            DiagnosticStep(
                step_number=2,
                title="Check Logs for OOM",
                description="Look for out-of-memory errors in logs",
                tool_name="list_log_entries",
                tool_params={
                    "filter": 'resource.type="cloud_run_revision" AND textPayload:"memory"',
                    "minutes_ago": 60,
                },
                expected_outcome="OOM errors visible if occurring",
            ),
        ],
        remediation_steps=[
            DiagnosticStep(
                step_number=1,
                title="Increase Memory Limit",
                description="Increase the container memory allocation",
                command="gcloud run services update {service} --memory=2Gi",
                expected_outcome="Container has sufficient memory",
            ),
            DiagnosticStep(
                step_number=2,
                title="Reduce Concurrency",
                description="Lower max concurrent requests per instance",
                command="gcloud run services update {service} --concurrency=50",
                expected_outcome="Lower per-request memory pressure",
            ),
            DiagnosticStep(
                step_number=3,
                title="Delete Temporary Files",
                description="Ensure temporary files are deleted promptly",
                expected_outcome="Filesystem memory freed after use",
            ),
        ],
        prevention_tips=[
            "Monitor memory utilization trends",
            "Delete temporary files immediately after use",
            "Set concurrency based on per-request memory needs",
            "Use Cloud Storage for large files instead of memory",
        ],
        related_metrics=[
            "run.googleapis.com/container/memory/utilizations",
        ],
        related_logs=[
            'textPayload:"memory" OR textPayload:"OOM"',
        ],
        error_codes=["MEMORY_LIMIT_EXCEEDED"],
        documentation_urls=[
            "https://cloud.google.com/run/docs/configuring/services/memory-limits"
        ],
    )


def _connection_reset() -> TroubleshootingIssue:
    """Connection reset issue."""
    return TroubleshootingIssue(
        issue_id="cloudrun-connection-reset",
        title="Connection Reset by Peer",
        description="Outbound connections are being reset unexpectedly",
        symptoms=[
            "ECONNRESET errors in logs",
            "Connection refused for external services",
            "Timeouts on outbound requests",
            "Intermittent failures to external APIs",
        ],
        root_causes=[
            "Long-lived connections closed after instance shutdown",
            "VPC connector misconfiguration",
            "Firewall rules blocking traffic",
            "HTTP proxy timeout exceeded",
        ],
        severity=PlaybookSeverity.MEDIUM,
        diagnostic_steps=[
            DiagnosticStep(
                step_number=1,
                title="Check Connection Errors",
                description="Look for connection reset errors in logs",
                tool_name="list_log_entries",
                tool_params={
                    "filter": 'resource.type="cloud_run_revision" AND textPayload:"ECONNRESET"',
                    "minutes_ago": 60,
                },
                expected_outcome="Connection error pattern visible",
            ),
            DiagnosticStep(
                step_number=2,
                title="Check VPC Configuration",
                description="Verify VPC connector is properly configured",
                command="gcloud run services describe {service} --format='value(spec.template.metadata.annotations)'",
                expected_outcome="VPC connector configured correctly",
            ),
        ],
        remediation_steps=[
            DiagnosticStep(
                step_number=1,
                title="Use Instance-Based Billing",
                description="Switch to instance-based billing for background work",
                expected_outcome="Connections maintained during instance lifecycle",
            ),
            DiagnosticStep(
                step_number=2,
                title="Implement Connection Pooling",
                description="Re-establish connections with retry logic",
                expected_outcome="Automatic reconnection on failures",
            ),
            DiagnosticStep(
                step_number=3,
                title="Configure Keepalive",
                description="Set socket keepalive options",
                expected_outcome="Connections stay alive during idle periods",
            ),
        ],
        prevention_tips=[
            "Don't hold connections open between requests",
            "Implement retry with exponential backoff",
            "Use connection pooling with proper lifecycle management",
            "Configure HTTP proxy exceptions for metadata server",
        ],
        related_metrics=[],
        related_logs=[
            'textPayload:"ECONNRESET"',
            'textPayload:"connection refused"',
        ],
        error_codes=["ECONNRESET", "ETIMEDOUT"],
        documentation_urls=[
            "https://cloud.google.com/run/docs/troubleshooting#connection-reset"
        ],
    )


def _permission_denied() -> TroubleshootingIssue:
    """Permission denied issue."""
    return TroubleshootingIssue(
        issue_id="cloudrun-permission-denied",
        title="Permission Denied (401/403)",
        description="Requests failing with authentication or authorization errors",
        symptoms=[
            "401 Unauthorized responses",
            "403 Forbidden responses",
            "Unable to invoke service",
            "IAM authentication failures",
        ],
        root_causes=[
            "Missing roles/run.invoker role",
            "Invalid or expired ID token",
            "Wrong audience in ID token",
            "Service not allowing unauthenticated access",
        ],
        severity=PlaybookSeverity.MEDIUM,
        diagnostic_steps=[
            DiagnosticStep(
                step_number=1,
                title="Check IAM Bindings",
                description="Verify invoker permissions on the service",
                command="gcloud run services get-iam-policy {service} --region={region}",
                expected_outcome="Required principals have invoker role",
            ),
            DiagnosticStep(
                step_number=2,
                title="Check Authentication Config",
                description="Verify service authentication requirements",
                command="gcloud run services describe {service} --format='value(spec.template.metadata.annotations[run.googleapis.com/ingress])'",
                expected_outcome="Authentication configured appropriately",
            ),
        ],
        remediation_steps=[
            DiagnosticStep(
                step_number=1,
                title="Grant Invoker Role",
                description="Add the Cloud Run Invoker role to the principal",
                command="gcloud run services add-iam-policy-binding {service} --member='user:{email}' --role='roles/run.invoker'",
                expected_outcome="Principal can invoke the service",
            ),
            DiagnosticStep(
                step_number=2,
                title="Allow Unauthenticated",
                description="Allow unauthenticated access if appropriate",
                command="gcloud run services add-iam-policy-binding {service} --member='allUsers' --role='roles/run.invoker'",
                expected_outcome="Service accessible without authentication",
            ),
        ],
        prevention_tips=[
            "Use IAP for browser-based access",
            "Use service accounts for service-to-service auth",
            "Verify audience claim in ID tokens",
            "Test authentication in staging before production",
        ],
        related_metrics=[
            "run.googleapis.com/request_count",
        ],
        related_logs=[
            "httpRequest.status=401 OR httpRequest.status=403",
        ],
        error_codes=["401", "403", "PERMISSION_DENIED"],
        documentation_urls=[
            "https://cloud.google.com/run/docs/authenticating/overview"
        ],
    )
