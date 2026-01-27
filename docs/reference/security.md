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

The `deploy/deploy_web.py` script (Cloud Run) pulls this key from Secret Manager at **runtime**.

However, the `deploy/deploy.py` script (Agent Engine) pulls the key from your **local environment** at **deployment time**.

> [!CAUTION]
> **Key Synchronization Hazard**: You must ensure the key in your local `.env` file matches the key in Secret Manager *before* running any deployment scripts. If you update the secret, you must also update your `.env` and redeploy the backend.

```bash
# 1. Update Secret Manager (if changing key)
echo -n "new-key" | gcloud secrets versions add sre-agent-encryption-key --data-file=-

# 2. Update local .env
# SRE_AGENT_ENCRYPTION_KEY=new-key

# 3. Redeploy Backend (Agent Engine)
uv run python deploy/deploy.py --create
```

## End-User Credentials (EUC)

Auto SRE uses **End-User Credentials** flow. This means it never stores your password. It only uses short-lived OAuth access tokens granted during the Google Sign-In process on the frontend.

- **Strict EUC Enforcement**: When `STRICT_EUC_ENFORCEMENT=true`, the agent will explicitly fail if no user token is present, preventing any fallback to the Service Account's credentials. This is the recommended setting for production to ensure per-user data isolation.

## Privacy & Data Sovereignty

### 1. PII Masking
The agent includes specialized middleware that automatically redacts PII (Emails, Credit Cards, IP addresses) from tool outputs before they are processed by the LLM. This ensures that sensitive user data never leaves your environment or is stored in the LLM's history.

### 2. Regionalized Processing
Auto SRE can be configured to run in specific GCP regions. All data processing (parsing, analysis, and session storage) stays within the configured region boundary to satisfy strict data residency requirements.

## Protected Access

By default, Cloud Run is deployed in **Authenticated Mode** (`--no-allow-unauthenticated`). This means only authorized users (with `roles/run.invoker`) can access the URL.

If your organization allows public access and you wish to enable it, you must explicitly use the `--allow-unauthenticated` flag:

```bash
uv run python deploy/deploy_web.py --allow-unauthenticated
```

When deployed in the default (Authenticated) mode:
1.  The service is created with `--no-allow-unauthenticated`.
2.  You will need to grant users the `roles/run.invoker` role to access the URL.
3.  Direct browser access may require an IAP (Identity-Aware Proxy) or Load Balancer if not accessed via a Google-authenticated tunnel.
