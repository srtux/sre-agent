# Security & Encryption

Auto SRE handles sensitive data, including temporary End-User Credentials (EUC). This document outlines how we secure this data and how to configure encryption for production.

## SRE_AGENT_ENCRYPTION_KEY

The `SRE_AGENT_ENCRYPTION_KEY` is a 32-byte (AES-256) Fernet key used to encrypt OAuth access tokens before they are stored in session state (Firestore). This ensures that even if someone gains access to your Firestore database, user tokens remain encrypted and unusable.

### Current Implementation

- **Encryption**: tokens are encrypted using the `cryptography.fernet` library.
- **Storage**: Encrypted tokens are stored in the session state under the key `_user_access_token`.
- **Decryption**: The Cloud Run proxy decrypts these tokens before calling GCP APIs on the user's behalf.

### Persistence

If `SRE_AGENT_ENCRYPTION_KEY` is not set, the agent generates a **transient key** at startup. This works for a single process, but:
1. Tokens will not be decryptable after a service restart.
2. In multi-instance deployments (Cloud Run), different instances will have different keys, causing random decryption failures.

**Recommendation**: Always set a static key for any environment where persistence or multi-instance scaling is required.

### Generating a Key

You can generate a valid key using Python:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### Production Configuration (GCP)

For production, we recommend using **GCP Secret Manager** instead of plain environment variables.

#### 1. Create the Secret

```bash
echo -n "your-generated-key" | gcloud secrets create sre-agent-encryption-key --data-file=-
```

#### 2. Update Deployment Configuration

The `deploy/deploy_web.py` script is pre-configured to pull this from Secret Manager. Ensure your Cloud Run service account has the `roles/secretmanager.secretAccessor` role (handled by `deploy/grant_permissions.py`).

Once the secret exists, the deployment script automatically includes it:

```bash
--set-secrets=SRE_AGENT_ENCRYPTION_KEY=sre-agent-encryption-key:latest
```

## End-User Credentials (EUC)

Auto SRE uses **End-User Credentials** flow. This means it never stores your password. It only uses short-lived OAuth access tokens granted during the Google Sign-In process on the frontend.

- **Strict EUC Enforcement**: When `STRICT_EUC_ENFORCEMENT=true`, the agent will explicitly fail if no user token is present, preventing any fallback to the Service Account's credentials. This is the recommended setting for production to ensure per-user data isolation.
