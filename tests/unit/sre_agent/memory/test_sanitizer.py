from sre_agent.memory.sanitizer import MemorySanitizer


def test_sanitize_context_identifiers():
    sanitizer = MemorySanitizer(
        user_id="user@example.com", project_id="my-secret-project"
    )

    # Test project ID redaction
    text = "Error in project my-secret-project"
    assert sanitizer.sanitize_text(text) == "Error in project <PROJECT_ID>"

    # Test user ID redaction
    text = "Action performed by user@example.com"
    assert sanitizer.sanitize_text(text) == "Action performed by <USER_IDENTITY>"


def test_sanitize_generic_patterns():
    sanitizer = MemorySanitizer()

    # Test IP address
    text = "Connection failed to 192.168.1.100"
    assert sanitizer.sanitize_text(text) == "Connection failed to <IP_ADDRESS>"

    # Test email
    text = "Contact support@google.com"
    assert sanitizer.sanitize_text(text) == "Contact <EMAIL>"

    # Test Bearer token
    text = "Authorization: Bearer abc123xyz.789"
    assert sanitizer.sanitize_text(text) == "Authorization: Bearer <REDACTED_TOKEN>"


def test_sanitize_gke_clusters():
    sanitizer = MemorySanitizer()
    text = "Node pool in gke_my-project_us-central1-a_my-cluster is full"
    assert (
        sanitizer.sanitize_text(text)
        == "Node pool in gke_<PROJECT>_<ZONE>_<CLUSTER> is full"
    )


def test_sanitize_recursive_dict():
    sanitizer = MemorySanitizer(project_id="secret-p")
    data = {
        "msg": "Log from secret-p",
        "nested": {"ip": "10.0.0.1", "list": ["secret-p", "1.1.1.1"]},
    }
    sanitized = sanitizer.sanitize_dict(data)
    assert sanitized["msg"] == "Log from <PROJECT_ID>"
    assert sanitized["nested"]["ip"] == "<IP_ADDRESS>"
    assert sanitized["nested"]["list"] == ["<PROJECT_ID>", "<IP_ADDRESS>"]
