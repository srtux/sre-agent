### Intelligent Remediation
Suggestions are ranked by Risk and Confidence.
- **Low Risk**: Restarting a pod, rolling back a small config change.
- **High Risk**: Resizing a DB cluster, changing IAM global permissions.

### Safe Execution:
Every "Write" action (Remediation) requires human approval via a confirmation button. The agent never makes destructive changes autonomously.
