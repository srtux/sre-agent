"""Pub/Sub Troubleshooting Playbook."""

from .schemas import (
    DiagnosticStep,
    Playbook,
    PlaybookCategory,
    PlaybookSeverity,
    TroubleshootingIssue,
)


def get_playbook() -> Playbook:
    """Get the Pub/Sub troubleshooting playbook."""
    return Playbook(
        playbook_id="pubsub-troubleshooting",
        service_name="Pub/Sub",
        display_name="Cloud Pub/Sub",
        category=PlaybookCategory.MESSAGING,
        description="Troubleshooting playbook for Pub/Sub covering message delivery, acknowledgment, and performance issues.",
        issues=[
            TroubleshootingIssue(
                issue_id="pubsub-message-not-delivered",
                title="Messages Not Being Delivered",
                description="Messages are not reaching subscribers",
                symptoms=[
                    "Messages accumulating in subscription",
                    "Subscribers not receiving messages",
                    "High unacked message count",
                ],
                root_causes=[
                    "Subscriber not pulling",
                    "Push endpoint failing",
                    "Filter excluding messages",
                    "Subscription expired",
                    "Permission issues",
                ],
                severity=PlaybookSeverity.HIGH,
                diagnostic_steps=[
                    DiagnosticStep(
                        step_number=1,
                        title="Check Subscription Status",
                        description="Verify subscription exists and is active",
                        command="gcloud pubsub subscriptions describe {subscription}",
                        expected_outcome="Subscription is active",
                    ),
                    DiagnosticStep(
                        step_number=2,
                        title="Check Backlog",
                        description="Check unacked message count",
                        tool_name="list_time_series",
                        tool_params={
                            "metric_type": "pubsub.googleapis.com/subscription/num_undelivered_messages"
                        },
                        expected_outcome="Message backlog visible",
                    ),
                ],
                remediation_steps=[
                    DiagnosticStep(
                        step_number=1,
                        title="Start Subscriber",
                        description="Ensure subscriber is running and pulling messages",
                    ),
                    DiagnosticStep(
                        step_number=2,
                        title="Fix Push Endpoint",
                        description="Verify push endpoint URL and authentication",
                    ),
                    DiagnosticStep(
                        step_number=3,
                        title="Check Filter",
                        description="Review subscription filter to ensure messages match",
                    ),
                ],
                prevention_tips=[
                    "Monitor subscription backlog",
                    "Set up dead letter topics",
                    "Configure retry policies",
                ],
                related_metrics=[
                    "pubsub.googleapis.com/subscription/num_undelivered_messages",
                    "pubsub.googleapis.com/subscription/oldest_unacked_message_age",
                ],
                error_codes=["PERMISSION_DENIED", "NOT_FOUND"],
                documentation_urls=[
                    "https://cloud.google.com/pubsub/docs/troubleshooting"
                ],
            ),
            TroubleshootingIssue(
                issue_id="pubsub-high-latency",
                title="High Message Latency",
                description="Messages taking too long to be delivered",
                symptoms=[
                    "High oldest unacked message age",
                    "Increasing delivery latency",
                    "Subscriber can't keep up",
                ],
                root_causes=[
                    "Insufficient subscribers",
                    "Slow message processing",
                    "Network latency",
                    "High message volume",
                    "Flow control throttling",
                ],
                severity=PlaybookSeverity.MEDIUM,
                diagnostic_steps=[
                    DiagnosticStep(
                        step_number=1,
                        title="Check Oldest Unacked Message",
                        description="Monitor oldest unacked message age",
                        tool_name="list_time_series",
                        tool_params={
                            "metric_type": "pubsub.googleapis.com/subscription/oldest_unacked_message_age"
                        },
                        expected_outcome="Latency trend visible",
                    ),
                    DiagnosticStep(
                        step_number=2,
                        title="Check Subscriber Count",
                        description="Verify sufficient StreamingPull connections",
                        tool_name="list_time_series",
                        tool_params={
                            "metric_type": "pubsub.googleapis.com/subscription/streaming_pull_response_count"
                        },
                        expected_outcome="Subscriber count visible",
                    ),
                ],
                remediation_steps=[
                    DiagnosticStep(
                        step_number=1,
                        title="Add Subscribers",
                        description="Increase number of subscriber instances",
                    ),
                    DiagnosticStep(
                        step_number=2,
                        title="Optimize Processing",
                        description="Reduce per-message processing time",
                    ),
                    DiagnosticStep(
                        step_number=3,
                        title="Tune Flow Control",
                        description="Adjust flow control settings for throughput",
                    ),
                ],
                prevention_tips=[
                    "Monitor delivery latency",
                    "Scale subscribers with demand",
                    "Use efficient batch processing",
                ],
                related_metrics=[
                    "pubsub.googleapis.com/subscription/oldest_unacked_message_age",
                    "pubsub.googleapis.com/subscription/delivery_latency_health_score",
                ],
                error_codes=[],
                documentation_urls=[
                    "https://cloud.google.com/pubsub/docs/subscribe-best-practices"
                ],
            ),
            TroubleshootingIssue(
                issue_id="pubsub-push-failures",
                title="Push Subscription Failures",
                description="Push endpoint failing to receive messages",
                symptoms=[
                    "4xx/5xx errors from push endpoint",
                    "Messages redelivering repeatedly",
                    "Push request timeouts",
                ],
                root_causes=[
                    "Endpoint returning errors",
                    "Authentication failures",
                    "Network connectivity issues",
                    "Slow endpoint response",
                    "Endpoint not reachable",
                ],
                severity=PlaybookSeverity.MEDIUM,
                diagnostic_steps=[
                    DiagnosticStep(
                        step_number=1,
                        title="Check Push Metrics",
                        description="Review push request success/failure rates",
                        tool_name="list_time_series",
                        tool_params={
                            "metric_type": "pubsub.googleapis.com/subscription/push_request_count"
                        },
                        expected_outcome="Error rate visible",
                    ),
                    DiagnosticStep(
                        step_number=2,
                        title="Check Push Latency",
                        description="Review push endpoint response times",
                        tool_name="list_time_series",
                        tool_params={
                            "metric_type": "pubsub.googleapis.com/subscription/push_request_latencies"
                        },
                        expected_outcome="Latency pattern visible",
                    ),
                ],
                remediation_steps=[
                    DiagnosticStep(
                        step_number=1,
                        title="Fix Endpoint Errors",
                        description="Resolve 4xx/5xx errors in push endpoint",
                    ),
                    DiagnosticStep(
                        step_number=2,
                        title="Configure Authentication",
                        description="Ensure service account has proper roles",
                    ),
                    DiagnosticStep(
                        step_number=3,
                        title="Improve Endpoint Performance",
                        description="Optimize endpoint to respond within ack deadline",
                    ),
                ],
                prevention_tips=[
                    "Monitor push success rate",
                    "Use dead letter topics for failed messages",
                    "Configure appropriate retry policy",
                ],
                related_metrics=[
                    "pubsub.googleapis.com/subscription/push_request_count",
                    "pubsub.googleapis.com/subscription/push_request_latencies",
                ],
                error_codes=["4xx", "5xx", "deadline_exceeded"],
                documentation_urls=[
                    "https://cloud.google.com/pubsub/docs/push-troubleshooting"
                ],
            ),
        ],
        best_practices=[
            "Use dead letter topics for undeliverable messages",
            "Configure appropriate ack deadlines",
            "Implement exponential backoff retry policies",
            "Monitor subscription backlog metrics",
            "Use message ordering only when necessary",
            "Scale subscribers based on backlog",
        ],
        key_metrics=[
            "pubsub.googleapis.com/subscription/num_undelivered_messages",
            "pubsub.googleapis.com/subscription/oldest_unacked_message_age",
            "pubsub.googleapis.com/subscription/delivery_latency_health_score",
            "pubsub.googleapis.com/topic/message_sizes",
        ],
        key_logs=["resource.type=pubsub_subscription", "resource.type=pubsub_topic"],
        related_services=["Cloud Logging", "Cloud Monitoring", "Cloud Functions"],
        documentation_urls=["https://cloud.google.com/pubsub/docs/troubleshooting"],
    )
