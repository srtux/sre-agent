"""BigQuery Troubleshooting Playbook."""

from .schemas import (
    DiagnosticStep,
    Playbook,
    PlaybookCategory,
    PlaybookSeverity,
    TroubleshootingIssue,
)


def get_playbook() -> Playbook:
    """Get the BigQuery troubleshooting playbook."""
    return Playbook(
        playbook_id="bigquery-troubleshooting",
        service_name="BigQuery",
        display_name="BigQuery",
        category=PlaybookCategory.DATA,
        description="Troubleshooting playbook for BigQuery covering query failures, performance, and quota issues.",
        issues=[
            TroubleshootingIssue(
                issue_id="bigquery-query-failed",
                title="Query Failed",
                description="Query execution fails with an error",
                symptoms=[
                    "Query returns error",
                    "Query timeout",
                    "Resource exceeded error",
                    "Permission denied",
                ],
                root_causes=[
                    "Syntax error",
                    "Resource limits exceeded",
                    "Missing permissions",
                    "Table not found",
                    "Schema mismatch",
                ],
                severity=PlaybookSeverity.MEDIUM,
                diagnostic_steps=[
                    DiagnosticStep(
                        step_number=1,
                        title="Check Error Message",
                        description="Review the error message in job details",
                        command="bq show -j {job_id}",
                        expected_outcome="Error details visible",
                    ),
                    DiagnosticStep(
                        step_number=2,
                        title="Check Permissions",
                        description="Verify bigquery.jobs.create permission",
                        expected_outcome="User has required permissions",
                    ),
                ],
                remediation_steps=[
                    DiagnosticStep(
                        step_number=1,
                        title="Fix Query Syntax",
                        description="Correct any syntax errors in the query",
                    ),
                    DiagnosticStep(
                        step_number=2,
                        title="Optimize Query",
                        description="Reduce data scanned, use partitioning, avoid ORDER BY on large datasets",
                    ),
                ],
                prevention_tips=[
                    "Use dry runs to estimate costs",
                    "Set maximumBytesBilled to cap costs",
                    "Use partitioned tables",
                ],
                related_metrics=[],
                error_codes=[
                    "RESOURCE_EXCEEDED",
                    "QUOTA_EXCEEDED",
                    "PERMISSION_DENIED",
                ],
                documentation_urls=[
                    "https://cloud.google.com/bigquery/docs/troubleshoot-queries"
                ],
            ),
            TroubleshootingIssue(
                issue_id="bigquery-slow-query",
                title="Slow Query Performance",
                description="Query taking longer than expected to execute",
                symptoms=[
                    "Long query execution time",
                    "High slot usage",
                    "Query stuck in RUNNING state",
                ],
                root_causes=[
                    "Full table scan",
                    "Missing partitioning/clustering",
                    "Complex joins",
                    "Insufficient slots",
                    "Large shuffle",
                ],
                severity=PlaybookSeverity.MEDIUM,
                diagnostic_steps=[
                    DiagnosticStep(
                        step_number=1,
                        title="Check Execution Plan",
                        description="Review the query execution plan",
                        expected_outcome="Bottlenecks identified",
                    ),
                    DiagnosticStep(
                        step_number=2,
                        title="Check Slot Usage",
                        description="Review slot consumption in job details",
                        expected_outcome="Slot usage pattern visible",
                    ),
                ],
                remediation_steps=[
                    DiagnosticStep(
                        step_number=1,
                        title="Add Partitioning",
                        description="Partition table by date column",
                    ),
                    DiagnosticStep(
                        step_number=2,
                        title="Add Clustering",
                        description="Cluster table by frequently filtered columns",
                    ),
                    DiagnosticStep(
                        step_number=3,
                        title="Optimize Query",
                        description="Select only needed columns, filter early, optimize joins",
                    ),
                ],
                prevention_tips=[
                    "Use partitioned and clustered tables",
                    "Avoid SELECT *",
                    "Use Query Insights",
                    "Monitor slot usage",
                ],
                related_metrics=["bigquery.googleapis.com/query/execution_times"],
                error_codes=[],
                documentation_urls=[
                    "https://cloud.google.com/bigquery/docs/best-practices-performance-overview"
                ],
            ),
            TroubleshootingIssue(
                issue_id="bigquery-quota-exceeded",
                title="Quota Exceeded",
                description="Query or operation fails due to quota limits",
                symptoms=[
                    "quotaExceeded error",
                    "Query queued indefinitely",
                    "Concurrent query limit reached",
                ],
                root_causes=[
                    "Too many concurrent queries",
                    "Bytes scanned limit reached",
                    "Daily query limit exceeded",
                    "Insufficient slots",
                ],
                severity=PlaybookSeverity.MEDIUM,
                diagnostic_steps=[
                    DiagnosticStep(
                        step_number=1,
                        title="Check Quota Usage",
                        description="Review quota usage in console",
                        expected_outcome="Quota limits visible",
                    ),
                    DiagnosticStep(
                        step_number=2,
                        title="Check Job History",
                        description="Review concurrent job count",
                        expected_outcome="Job concurrency visible",
                    ),
                ],
                remediation_steps=[
                    DiagnosticStep(
                        step_number=1,
                        title="Request Quota Increase",
                        description="Request higher quota limits",
                    ),
                    DiagnosticStep(
                        step_number=2,
                        title="Purchase Slots",
                        description="Purchase reserved slots for guaranteed capacity",
                    ),
                    DiagnosticStep(
                        step_number=3,
                        title="Optimize Queries",
                        description="Reduce bytes scanned per query",
                    ),
                ],
                prevention_tips=[
                    "Monitor quota usage",
                    "Use reservations for critical workloads",
                    "Set custom quotas per project",
                ],
                related_metrics=[],
                error_codes=["quotaExceeded", "RESOURCE_EXHAUSTED"],
                documentation_urls=[
                    "https://cloud.google.com/bigquery/docs/troubleshoot-quotas"
                ],
            ),
        ],
        best_practices=[
            "Use partitioned and clustered tables",
            "Avoid SELECT * - select only needed columns",
            "Use maximumBytesBilled to cap costs",
            "Use dry runs to estimate query costs",
            "Enable Query Insights for monitoring",
            "Use reserved slots for predictable performance",
        ],
        key_metrics=[
            "bigquery.googleapis.com/query/count",
            "bigquery.googleapis.com/query/execution_times",
            "bigquery.googleapis.com/slots/total_available",
        ],
        key_logs=["resource.type=bigquery_resource"],
        related_services=["Cloud Logging", "Cloud Monitoring", "Cloud Storage"],
        documentation_urls=["https://cloud.google.com/bigquery/docs/troubleshooting"],
    )
