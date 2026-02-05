"""Compute Engine (GCE) Troubleshooting Playbook."""

from .schemas import (
    DiagnosticStep,
    Playbook,
    PlaybookCategory,
    PlaybookSeverity,
    TroubleshootingIssue,
)


def get_playbook() -> Playbook:
    """Get the Compute Engine troubleshooting playbook."""
    return Playbook(
        playbook_id="gce-troubleshooting",
        service_name="Compute Engine",
        display_name="Compute Engine",
        category=PlaybookCategory.COMPUTE,
        description="Troubleshooting playbook for GCE covering VM startup, networking, SSH, and performance issues.",
        issues=[
            TroubleshootingIssue(
                issue_id="gce-vm-not-starting",
                title="VM Not Starting",
                description="Virtual machine fails to start or boot",
                symptoms=[
                    "VM stuck in STAGING state",
                    "Boot timeout errors",
                    "Serial console shows errors",
                    "Instance fails to reach RUNNING state",
                ],
                root_causes=[
                    "Quota exceeded",
                    "Boot disk full or corrupted",
                    "MBR corruption",
                    "Disk cloning in progress",
                    "Service account issues",
                ],
                severity=PlaybookSeverity.HIGH,
                diagnostic_steps=[
                    DiagnosticStep(
                        step_number=1,
                        title="Check Serial Console",
                        description="Review boot messages",
                        command="gcloud compute instances get-serial-port-output {instance}",
                        expected_outcome="Boot errors visible",
                    ),
                    DiagnosticStep(
                        step_number=2,
                        title="Check Quota",
                        description="Verify CPU quota",
                        command="gcloud compute project-info describe",
                        expected_outcome="Sufficient quota available",
                    ),
                ],
                remediation_steps=[
                    DiagnosticStep(
                        step_number=1,
                        title="Request Quota Increase",
                        description="Request additional quota if needed",
                    ),
                    DiagnosticStep(
                        step_number=2,
                        title="Attach Disk to Debug VM",
                        description="Mount disk on temporary VM to repair",
                    ),
                ],
                prevention_tips=[
                    "Monitor quota usage",
                    "Test images before production use",
                ],
                related_metrics=["compute.googleapis.com/instance/uptime"],
                error_codes=["QUOTA_EXCEEDED", "RESOURCE_NOT_FOUND"],
                documentation_urls=[
                    "https://cloud.google.com/compute/docs/troubleshooting/vm-startup"
                ],
            ),
            TroubleshootingIssue(
                issue_id="gce-ssh-failure",
                title="SSH Connection Failure",
                description="Cannot connect to VM via SSH",
                symptoms=[
                    "SSH timeout",
                    "Permission denied",
                    "Connection refused",
                    "Host key verification failed",
                ],
                root_causes=[
                    "Firewall rules blocking port 22",
                    "SSH daemon not running",
                    "SSH keys misconfigured",
                    "VM not fully booted",
                    "Disk full",
                ],
                severity=PlaybookSeverity.MEDIUM,
                diagnostic_steps=[
                    DiagnosticStep(
                        step_number=1,
                        title="Run SSH Troubleshooter",
                        description="Use built-in troubleshooter",
                        command="gcloud compute ssh {instance} --troubleshoot",
                        expected_outcome="Issue identified",
                    ),
                    DiagnosticStep(
                        step_number=2,
                        title="Check Firewall Rules",
                        description="Verify SSH firewall rule exists",
                        command="gcloud compute firewall-rules list --filter='name~allow-ssh'",
                        expected_outcome="SSH rule exists",
                    ),
                ],
                remediation_steps=[
                    DiagnosticStep(
                        step_number=1,
                        title="Create SSH Firewall Rule",
                        description="Allow SSH traffic",
                        command="gcloud compute firewall-rules create allow-ssh --allow tcp:22",
                    ),
                    DiagnosticStep(
                        step_number=2,
                        title="Reset SSH Keys",
                        description="Remove and re-add SSH keys via metadata",
                    ),
                ],
                prevention_tips=[
                    "Use IAP for SSH",
                    "Configure OS Login",
                    "Monitor firewall rule changes",
                ],
                related_metrics=[],
                error_codes=["SSH_TIMEOUT", "PERMISSION_DENIED"],
                documentation_urls=[
                    "https://cloud.google.com/compute/docs/troubleshooting/troubleshooting-ssh"
                ],
            ),
            TroubleshootingIssue(
                issue_id="gce-high-cpu",
                title="High CPU Utilization",
                description="VM experiencing sustained high CPU usage",
                symptoms=[
                    "Slow application response",
                    "CPU utilization above 90%",
                    "Unresponsive VM",
                    "Timeout errors",
                ],
                root_causes=[
                    "Insufficient CPU for workload",
                    "Runaway process",
                    "DDoS attack",
                    "Cryptomining malware",
                ],
                severity=PlaybookSeverity.MEDIUM,
                diagnostic_steps=[
                    DiagnosticStep(
                        step_number=1,
                        title="Check CPU Metrics",
                        description="Review CPU utilization",
                        tool_name="list_time_series",
                        tool_params={
                            "metric_type": "compute.googleapis.com/instance/cpu/utilization"
                        },
                        expected_outcome="CPU usage pattern visible",
                    ),
                    DiagnosticStep(
                        step_number=2,
                        title="Check Process List",
                        description="SSH and run top/htop to identify consumers",
                        expected_outcome="High CPU process identified",
                    ),
                ],
                remediation_steps=[
                    DiagnosticStep(
                        step_number=1,
                        title="Stop Runaway Process",
                        description="Kill the high-CPU process",
                    ),
                    DiagnosticStep(
                        step_number=2,
                        title="Resize VM",
                        description="Upgrade to larger machine type",
                        command="gcloud compute instances set-machine-type {instance} --machine-type={type}",
                    ),
                ],
                prevention_tips=[
                    "Set up CPU utilization alerts",
                    "Use managed instance groups with autoscaling",
                ],
                related_metrics=["compute.googleapis.com/instance/cpu/utilization"],
                error_codes=[],
                documentation_urls=[
                    "https://cloud.google.com/compute/docs/troubleshooting/troubleshooting-performance"
                ],
            ),
        ],
        best_practices=[
            "Use managed instance groups for high availability",
            "Enable live migration for maintenance events",
            "Use preemptible VMs for batch workloads",
            "Configure startup and shutdown scripts",
            "Use IAP for secure SSH access",
        ],
        key_metrics=[
            "compute.googleapis.com/instance/cpu/utilization",
            "compute.googleapis.com/instance/disk/read_bytes_count",
            "compute.googleapis.com/instance/disk/write_bytes_count",
            "compute.googleapis.com/instance/network/received_bytes_count",
        ],
        key_logs=["resource.type=gce_instance"],
        related_services=["Cloud Logging", "Cloud Monitoring", "VPC"],
        documentation_urls=["https://cloud.google.com/compute/docs/troubleshooting"],
    )
