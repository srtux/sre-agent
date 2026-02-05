#!/bin/bash

# Setup script for granting IAM permissions to Vertex AI Agent Identity

# Exit on error
set -e

PROJECT_ID=""
ORG_ID=""
LOCATION="us-central1"
AGENT_ENGINE_ID=""
PROJECT_NUMBER=""

# Parse arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --project-id) PROJECT_ID="$2"; shift ;;
        --org-id) ORG_ID="$2"; shift ;;
        --location) LOCATION="$2"; shift ;;
        --agent-id) AGENT_ENGINE_ID="$2"; shift ;;
        *) echo "Unknown parameter passed: $1"; exit 1 ;;
    esac
    shift
done

# Validate required arguments
if [ -z "$PROJECT_ID" ] || [ -z "$ORG_ID" ] || [ -z "$AGENT_ENGINE_ID" ]; then
    echo "Usage: $0 --project-id <PROJECT_ID> --org-id <ORG_ID> --agent-id <AGENT_ENGINE_ID> [--location <LOCATION>]"
    echo "Missing required arguments."
    exit 1
fi

# Get project number
if [ -z "$PROJECT_NUMBER" ]; then
    echo "🔍 Retrieving project number for $PROJECT_ID..."
    PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')
    echo "✅ Project Number: $PROJECT_NUMBER"
fi

# Construct Principal URI
# principal://agents.global.org-ORGANIZATION_ID.system.id.goog/resources/aiplatform/projects/PROJECT_NUMBER/locations/LOCATION/reasoningEngines/AGENT_ENGINE_ID
PRINCIPAL="principal://agents.global.org-${ORG_ID}.system.id.goog/resources/aiplatform/projects/${PROJECT_NUMBER}/locations/${LOCATION}/reasoningEngines/${AGENT_ENGINE_ID}"

echo "🔐 Principal: $PRINCIPAL"

# List of roles to grant
ROLES=(
    "roles/aiplatform.expressUser"
    "roles/serviceusage.serviceUsageConsumer"
    "roles/cloudtrace.agent"
    "roles/cloudtrace.user"
    "roles/logging.viewer"
    "roles/logging.logWriter"
    "roles/monitoring.viewer"
    "roles/monitoring.metricWriter"
    "roles/bigquery.dataViewer"
    "roles/bigquery.jobUser"
    "roles/secretmanager.secretAccessor"
    "roles/datastore.user"
    "roles/container.viewer"
    "roles/container.clusterViewer"
    "roles/cloudapiregistry.viewer"
    "roles/mcp.toolUser"
)

echo "🔐 Granting IAM Roles to Agent Identity..."

for ROLE in "${ROLES[@]}"; do
    echo "   Granting $ROLE..."
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
        --member="$PRINCIPAL" \
        --role="$ROLE" \
        --condition=None \
        --quiet
done

echo "✅ Successfully established Agent Identity permissions."
echo "🚀 The agent can now access GCP resources using its own identity."
