"""Cloud SQL Troubleshooting Playbook."""

from .schemas import (
    DiagnosticStep,
    Playbook,
    PlaybookCategory,
    PlaybookSeverity,
    TroubleshootingIssue,
)


def get_playbook() -> Playbook:
    """Get the Cloud SQL troubleshooting playbook."""
    return Playbook(
        playbook_id="cloud-sql-troubleshooting",
        service_name="Cloud SQL",
        display_name="Cloud SQL",
        category=PlaybookCategory.DATA,
        description="Troubleshooting playbook for Cloud SQL covering connectivity, performance, and replication issues.",
        issues=[
            TroubleshootingIssue(
                issue_id="cloudsql-connection-failed",
                title="Connection Failed",
                description="Cannot connect to Cloud SQL instance",
                symptoms=[
                    "Connection timeout errors",
                    "Connection refused errors",
                    "SSL handshake failures",
                    "IP not authorized errors",
                ],
                root_causes=[
                    "IP address not in authorized networks",
                    "Private IP not configured correctly",
                    "SSL certificates expired or misconfigured",
                    "Instance is stopped or in maintenance",
                    "Firewall rules blocking connection",
                ],
                severity=PlaybookSeverity.HIGH,
                diagnostic_steps=[
                    DiagnosticStep(
                        step_number=1,
                        title="Check Instance Status",
                        description="Verify the Cloud SQL instance is running",
                        command="gcloud sql instances describe {instance}",
                        expected_outcome="Instance state is RUNNABLE",
                    ),
                    DiagnosticStep(
                        step_number=2,
                        title="Check Authorized Networks",
                        description="Verify client IP is in authorized networks",
                        command="gcloud sql instances describe {instance} --format='value(settings.ipConfiguration.authorizedNetworks)'",
                        expected_outcome="Client IP is authorized",
                    ),
                ],
                remediation_steps=[
                    DiagnosticStep(
                        step_number=1,
                        title="Add Authorized Network",
                        description="Add client IP to authorized networks",
                        command="gcloud sql instances patch {instance} --authorized-networks={ip}/32",
                        expected_outcome="Client can connect",
                    ),
                ],
                prevention_tips=[
                    "Use Cloud SQL Auth Proxy for secure connections",
                    "Use private IP for VPC-based access",
                ],
                related_metrics=[
                    "cloudsql.googleapis.com/database/network/connections"
                ],
                error_codes=["NETWORK_ERROR", "SSL_ERROR"],
                documentation_urls=[
                    "https://cloud.google.com/sql/docs/mysql/debugging-connectivity"
                ],
            ),
            TroubleshootingIssue(
                issue_id="cloudsql-high-latency",
                title="High Query Latency",
                description="Queries taking longer than expected",
                symptoms=[
                    "Slow query responses",
                    "Application timeouts",
                    "High CPU utilization",
                    "High memory utilization",
                ],
                root_causes=[
                    "Missing or suboptimal indexes",
                    "Table lock contention",
                    "Insufficient instance resources",
                    "Large result sets",
                    "Network latency",
                ],
                severity=PlaybookSeverity.MEDIUM,
                diagnostic_steps=[
                    DiagnosticStep(
                        step_number=1,
                        title="Enable Query Insights",
                        description="Use Query Insights to identify slow queries",
                        expected_outcome="Slow queries identified",
                    ),
                    DiagnosticStep(
                        step_number=2,
                        title="Check Instance Metrics",
                        description="Review CPU and memory utilization",
                        tool_name="list_time_series",
                        tool_params={
                            "metric_type": "cloudsql.googleapis.com/database/cpu/utilization"
                        },
                        expected_outcome="Resource bottleneck identified",
                    ),
                ],
                remediation_steps=[
                    DiagnosticStep(
                        step_number=1,
                        title="Add Missing Indexes",
                        description="Create indexes for slow queries",
                        expected_outcome="Query performance improved",
                    ),
                    DiagnosticStep(
                        step_number=2,
                        title="Scale Instance",
                        description="Upgrade to larger instance type",
                        command="gcloud sql instances patch {instance} --tier=db-custom-4-16384",
                        expected_outcome="More resources available",
                    ),
                ],
                prevention_tips=[
                    "Enable slow query logging",
                    "Use Query Insights for monitoring",
                    "Size instances appropriately",
                ],
                related_metrics=[
                    "cloudsql.googleapis.com/database/cpu/utilization",
                    "cloudsql.googleapis.com/database/memory/utilization",
                ],
                error_codes=[],
                documentation_urls=[
                    "https://cloud.google.com/sql/docs/mysql/using-query-insights"
                ],
            ),
            TroubleshootingIssue(
                issue_id="cloudsql-replication-lag",
                title="Replication Lag",
                description="Read replica is lagging behind primary",
                symptoms=[
                    "Stale data on read replica",
                    "Increasing lag metrics",
                    "Inconsistent read results",
                ],
                root_causes=[
                    "Primary sending changes faster than replica can apply",
                    "Long-running transactions on replica",
                    "Network connectivity issues",
                    "Replica undersized for workload",
                ],
                severity=PlaybookSeverity.MEDIUM,
                diagnostic_steps=[
                    DiagnosticStep(
                        step_number=1,
                        title="Check Replication Lag",
                        description="Monitor replication lag metric",
                        tool_name="list_time_series",
                        tool_params={
                            "metric_type": "cloudsql.googleapis.com/database/replication/replica_lag"
                        },
                        expected_outcome="Lag value and trend visible",
                    ),
                ],
                remediation_steps=[
                    DiagnosticStep(
                        step_number=1,
                        title="Scale Replica",
                        description="Increase replica instance size",
                        expected_outcome="Replica can keep up with changes",
                    ),
                    DiagnosticStep(
                        step_number=2,
                        title="Kill Long Queries",
                        description="Terminate blocking queries on replica",
                        expected_outcome="Replication can proceed",
                    ),
                ],
                prevention_tips=[
                    "Size replicas appropriately",
                    "Monitor replication lag",
                    "Avoid long-running queries on replicas",
                ],
                related_metrics=[
                    "cloudsql.googleapis.com/database/replication/replica_lag"
                ],
                error_codes=[],
                documentation_urls=[
                    "https://cloud.google.com/sql/docs/mysql/replication/replication-lag"
                ],
            ),
        ],
        best_practices=[
            "Use Cloud SQL Auth Proxy for secure connections",
            "Enable automated backups",
            "Configure maintenance windows appropriately",
            "Use connection pooling",
            "Enable Query Insights for performance monitoring",
        ],
        key_metrics=[
            "cloudsql.googleapis.com/database/cpu/utilization",
            "cloudsql.googleapis.com/database/memory/utilization",
            "cloudsql.googleapis.com/database/disk/utilization",
            "cloudsql.googleapis.com/database/network/connections",
        ],
        key_logs=["resource.type=cloudsql_database"],
        related_services=["Cloud Logging", "Cloud Monitoring", "VPC"],
        documentation_urls=["https://cloud.google.com/sql/docs/troubleshooting"],
    )
