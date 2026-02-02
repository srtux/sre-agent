### Incident Correlation
The agent scans for events that happened just before an incident.
- **Data**: GCP Audit Logs, Deployment History, Feature Flag toggles.
- **Logic**: It looks for "IAM changed", "K8s updated", or "Config changed" within a 15m window of an alert.

### Example Workflow:
1. Alert: "High Error Rate in Checkout."
2. Agent find a `RoleBinding` removal 2 minutes before the incident.
3. It suggests rollback of the IAM policy.
