#!/bin/bash
set -e

# Ensure we are in the script's directory
cd "$(dirname "$0")"

PROJECT_ID=${GOOGLE_CLOUD_PROJECT:-$(gcloud config get-value project)}
if [ -z "${PROJECT_ID}" ]; then
    echo "Error: PROJECT_ID is not set and could not be determined from gcloud config."
    exit 1
fi
echo "Using Project ID: ${PROJECT_ID}"
REGION=${GOOGLE_CLOUD_LOCATION:-us-central1}
SERVICE_NAME="toolbox-mcp"
SECRET_NAME="toolbox-mcp-config"
SERVICE_ACCOUNT="toolbox-sa@${PROJECT_ID}.iam.gserviceaccount.com"

# Create Service Account if it doesn't exist
if ! gcloud iam service-accounts describe ${SERVICE_ACCOUNT} >/dev/null 2>&1; then
    echo "Creating service account ${SERVICE_ACCOUNT}..."
    gcloud iam service-accounts create toolbox-sa \
        --display-name="Toolbox MCP Service Account"
fi

# Grant necessary permissions
# Secret Manager Access
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/secretmanager.secretAccessor" \
    --condition=None

# BigQuery Access (assuming it needs to run queries)
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/bigquery.jobUser" \
    --condition=None

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/bigquery.dataViewer" \
    --condition=None

# Build and push container

SERVICE_IMAGE="us-central1-docker.pkg.dev/database-toolbox/toolbox/toolbox:latest"

# Create secret for config.yaml if it doesn't exist
if ! gcloud secrets describe ${SECRET_NAME} >/dev/null 2>&1; then
    gcloud secrets create ${SECRET_NAME} --replication-policy="automatic"
fi

# Add a new version of the secret with the contents of config.yaml
gcloud secrets versions add ${SECRET_NAME} --data-file="config.yaml"

# Deploy to Cloud Run
gcloud run deploy ${SERVICE_NAME} \
    --image ${SERVICE_IMAGE} \
    --platform managed \
    --region ${REGION} \
    --allow-unauthenticated \
    --service-account ${SERVICE_ACCOUNT} \
    --set-secrets="/app/tools.yaml=${SECRET_NAME}:latest" \
    --args="--tools-file=/app/tools.yaml","--address=0.0.0.0","--port=8080"

# Explicitly allow unauthenticated access (in case --allow-unauthenticated failed)
gcloud run services add-iam-policy-binding ${SERVICE_NAME} \
    --region ${REGION} \
    --member="allUsers" \
    --role="roles/run.invoker"

# Get service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
    --region ${REGION} \
    --format 'value(status.url)')

echo "Toolbox MCP deployed at: ${SERVICE_URL}"
echo "Set TOOLBOX_MCP_URL=${SERVICE_URL} in .env"
