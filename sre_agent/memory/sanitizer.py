import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class MemorySanitizer:
    """Utility to sanitize data for global memory sharing.

    Ensures that sensitive identifiers like project IDs, emails, IP addresses,
    and cluster names are redacted before being stored in the global
    `system_shared_patterns` scope.
    """

    def __init__(self, user_id: str | None = None, project_id: str | None = None):
        """Initialize with current context to improve redaction accuracy.

        Args:
            user_id: The current user's email/ID.
            project_id: The current GCP project ID.
        """
        self.user_id = user_id
        self.project_id = project_id

        # General sensitive patterns
        self.generic_patterns = [
            # Email addresses
            (r"[a-zA-Z0-9_.+-]+ @ [a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", "<EMAIL>"),
            # IPv4 addresses
            (r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", "<IP_ADDRESS>"),
            # Bearer tokens / Auth headers
            (r"[Bb]earer\s+[a-zA-Z0-9._~+/-]+=*", "Bearer <REDACTED_TOKEN>"),
            # Potential Project IDs in text (only if they look like standard GCP IDs)
            # This is risky so we prioritize specific redaction of self.project_id
        ]
        # Clean up the email regex (removed spaces around @ for real usage)
        self.generic_patterns[0] = (
            r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
            "<EMAIL>",
        )

    def sanitize_text(self, text: str) -> str:
        """Redact sensitive information from a string.

        Args:
            text: The raw text to sanitize.

        Returns:
            Sanitized text with placeholders.
        """
        if not text:
            return text

        # 1. Redact specific known context (Highest priority)
        if self.user_id and len(self.user_id) > 3:
            text = text.replace(self.user_id, "<USER_IDENTITY>")

        if self.project_id and len(self.project_id) > 3:
            text = text.replace(self.project_id, "<PROJECT_ID>")

        # 2. Redact common patterns
        for pattern, replacement in self.generic_patterns:
            text = re.sub(pattern, replacement, text)

        # 3. Specific SRE patterns
        # Mask GKE cluster names if they look like "gke_<project>_<zone>_<name>"
        text = re.sub(
            r"gke_[a-z0-9-]+_[a-z0-9-]+_[a-z0-9-]+",
            "gke_<PROJECT>_<ZONE>_<CLUSTER>",
            text,
        )

        return text

    def sanitize_dict(self, data: dict[str, Any]) -> dict[str, Any]:
        """Recursively sanitize a dictionary."""
        return self._sanitize_recursive(data)  # type: ignore[no-any-return]

    def _sanitize_recursive(self, data: Any) -> Any:
        """Helper for recursive sanitization."""
        if isinstance(data, str):
            return self.sanitize_text(data)
        elif isinstance(data, list):
            return [self._sanitize_recursive(item) for item in data]
        elif isinstance(data, dict):
            return {k: self._sanitize_recursive(v) for k, v in data.items()}
        return data

    @classmethod
    def sanitize_global_record(
        cls, text: str, user_id: str | None, project_id: str | None
    ) -> str:
        """Convenience method for one-off sanitization."""
        sanitizer = cls(user_id=user_id, project_id=project_id)
        return sanitizer.sanitize_text(text)
