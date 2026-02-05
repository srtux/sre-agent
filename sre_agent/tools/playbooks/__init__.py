"""GCP Troubleshooting Playbooks Module.

This module provides hierarchical troubleshooting playbooks for GCP services.
Each playbook contains structured diagnostic steps, common issues, and
remediation guidance based on official Google Cloud documentation.

Playbook Categories:
- Compute: GKE, Cloud Run, GCE, App Engine
- Data: BigQuery, Cloud SQL, Spanner, Dataflow, Dataproc
- Storage: GCS, Firestore
- Messaging: Pub/Sub, Cloud Tasks
- AI/ML: Vertex AI
- Observability: Cloud Logging, Cloud Monitoring, Cloud Trace
- Security: IAM, IAP
- Management: Cloud Asset Inventory, AppHub
"""

from .registry import PlaybookRegistry, get_playbook_registry
from .schemas import (
    DiagnosticStep,
    Playbook,
    PlaybookCategory,
    PlaybookSeverity,
    TroubleshootingIssue,
)

__all__ = [
    "DiagnosticStep",
    "Playbook",
    "PlaybookCategory",
    "PlaybookRegistry",
    "PlaybookSeverity",
    "TroubleshootingIssue",
    "get_playbook_registry",
]
