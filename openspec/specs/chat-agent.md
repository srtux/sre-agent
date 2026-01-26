# Chat Agent API Spec

## Overview
The Chat Agent API is the primary entry point for users to interact with the SRE Agent. It supports streaming responses and operates in two modes: Local (for development) and Remote (for production).

## Endpoints

### POST `/api/genui/chat` (also `/agent`)
Starts or continues a chat session with the AI agent.

#### Request Schema
```yaml
messages: list[AgentMessage]  # History of messages
session_id: str | None        # Optional session identifier
project_id: str | None        # Target GCP project ID
user_id: str                  # Default "default"
```

#### Behavior (Local Mode)
1. Initializes a `Session` (via `SessionService`).
2. Creates an `InvocationContext`.
3. Loads/Creates `InvestigationState` from the session.
4. Initializes a `Runner` with the `root_agent`.
5. Streams `NDJSON` events back to the client:
    - `session` event with the `session_id`.
    - `text` events for streaming responses.
    - `a2ui` events for GenUI widgets (tool calls, results).

#### Behavior (Remote Mode)
1. Forwards the request to the **Vertex AI Agent Engine**.
2. Propagates End-User Credentials (EUC) via encrypted session state.
3. Streams the Agent Engine responses back to the client.

## Acceptance Criteria
- [ ] Must return `200 OK` with `application/x-ndjson` content type.
- [ ] Must yield a `session` event as the first event in the stream.
- [ ] Must support seamless switching between Local and Remote modes based on environment.
- [ ] Must auto-generate a session title for new sessions.

## Test Scenarios

### Scenario: Local Streaming Chat
- **Given** the agent is in local mode
- **When** I send a message "Hi"
- **Then** I should receive a `session` event
- **And** I should receive a text response containing the agent's reply

### Scenario: Remote Streaming Chat
- **Given** the agent is in remote mode
- **And** a managed Agent Engine client is available
- **When** I send a message
- **Then** the response should contain the results from the Agent Engine
