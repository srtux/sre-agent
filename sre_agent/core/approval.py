"""Human-in-the-Loop Approval Workflow.

Implements the approval mechanism for write operations that require
human confirmation before execution.
"""

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ApprovalStatus(str, Enum):
    """Status of an approval request."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class HumanApprovalRequest(BaseModel):
    """Request for human approval of a write operation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    request_id: str = Field(description="Unique identifier for this request")
    tool_name: str = Field(description="Name of the tool requiring approval")
    tool_args: dict[str, Any] = Field(description="Arguments for the tool call")
    reason: str = Field(description="Why the agent wants to perform this action")
    risk_assessment: str = Field(description="Assessment of potential risks")
    session_id: str = Field(description="Session this request belongs to")
    user_id: str = Field(description="User who needs to approve")
    created_at: str = Field(description="ISO 8601 timestamp of request creation")
    expires_at: str | None = Field(
        default=None, description="ISO 8601 timestamp when request expires"
    )


class HumanApprovalEvent(BaseModel):
    """Event representing a human's decision on an approval request."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    request_id: str = Field(description="ID of the approval request")
    status: ApprovalStatus = Field(description="The approval decision")
    approver_id: str = Field(description="ID of the person who made the decision")
    decided_at: str = Field(description="ISO 8601 timestamp of decision")
    comment: str | None = Field(
        default=None, description="Optional comment from approver"
    )


@dataclass
class ApprovalState:
    """Tracks pending approval requests for a session."""

    pending_requests: dict[str, HumanApprovalRequest] = field(default_factory=dict)
    completed_requests: dict[str, HumanApprovalEvent] = field(default_factory=dict)

    def add_request(self, request: HumanApprovalRequest) -> None:
        """Add a pending approval request."""
        self.pending_requests[request.request_id] = request

    def complete_request(self, event: HumanApprovalEvent) -> None:
        """Mark a request as completed with the given decision."""
        if event.request_id in self.pending_requests:
            del self.pending_requests[event.request_id]
        self.completed_requests[event.request_id] = event

    def get_pending(self, request_id: str) -> HumanApprovalRequest | None:
        """Get a pending request by ID."""
        return self.pending_requests.get(request_id)

    def is_approved(self, request_id: str) -> bool:
        """Check if a request was approved."""
        event = self.completed_requests.get(request_id)
        return event is not None and event.status == ApprovalStatus.APPROVED

    def has_pending(self) -> bool:
        """Check if there are any pending requests."""
        return len(self.pending_requests) > 0


class ApprovalManager:
    """Manages approval requests and their lifecycle."""

    def __init__(self, expiration_seconds: int = 300) -> None:
        """Initialize the approval manager.

        Args:
            expiration_seconds: Time before requests expire (default 5 minutes)
        """
        self.expiration_seconds = expiration_seconds
        self._states: dict[str, ApprovalState] = {}
        self._lock = threading.Lock()

    def get_state(self, session_id: str) -> ApprovalState:
        """Get or create approval state for a session (thread-safe)."""
        with self._lock:
            if session_id not in self._states:
                self._states[session_id] = ApprovalState()
            return self._states[session_id]

    def create_request(
        self,
        session_id: str,
        user_id: str,
        tool_name: str,
        tool_args: dict[str, Any],
        reason: str,
        risk_assessment: str,
    ) -> HumanApprovalRequest:
        """Create a new approval request.

        Args:
            session_id: Session the request belongs to
            user_id: User who needs to approve
            tool_name: Name of the tool requiring approval
            tool_args: Arguments for the tool call
            reason: Why the agent wants to perform this action
            risk_assessment: Assessment of potential risks

        Returns:
            The created approval request
        """
        import uuid

        now = datetime.now(timezone.utc)
        expires_at = datetime.fromtimestamp(
            now.timestamp() + self.expiration_seconds, tz=timezone.utc
        )

        request = HumanApprovalRequest(
            request_id=str(uuid.uuid4()),
            tool_name=tool_name,
            tool_args=tool_args,
            reason=reason,
            risk_assessment=risk_assessment,
            session_id=session_id,
            user_id=user_id,
            created_at=now.isoformat(),
            expires_at=expires_at.isoformat(),
        )

        state = self.get_state(session_id)
        state.add_request(request)
        return request

    def process_decision(
        self,
        session_id: str,
        request_id: str,
        approved: bool,
        approver_id: str,
        comment: str | None = None,
    ) -> HumanApprovalEvent:
        """Process a human's decision on an approval request.

        Args:
            session_id: Session the request belongs to
            request_id: ID of the approval request
            approved: Whether the request was approved
            approver_id: ID of the person who made the decision
            comment: Optional comment from approver

        Returns:
            The approval event

        Raises:
            ValueError: If the request is not found or already processed
        """
        state = self.get_state(session_id)
        request = state.get_pending(request_id)

        if request is None:
            if request_id in state.completed_requests:
                raise ValueError(f"Request {request_id} has already been processed")
            raise ValueError(f"Request {request_id} not found")

        # Check expiration
        now = datetime.now(timezone.utc)
        if request.expires_at:
            expires = datetime.fromisoformat(request.expires_at)
            if now > expires:
                event = HumanApprovalEvent(
                    request_id=request_id,
                    status=ApprovalStatus.EXPIRED,
                    approver_id="system",
                    decided_at=now.isoformat(),
                    comment="Request expired before decision",
                )
                state.complete_request(event)
                raise ValueError(f"Request {request_id} has expired")

        status = ApprovalStatus.APPROVED if approved else ApprovalStatus.REJECTED
        event = HumanApprovalEvent(
            request_id=request_id,
            status=status,
            approver_id=approver_id,
            decided_at=now.isoformat(),
            comment=comment,
        )

        state.complete_request(event)
        return event

    def get_pending_requests(self, session_id: str) -> list[HumanApprovalRequest]:
        """Get all pending requests for a session."""
        state = self.get_state(session_id)
        return list(state.pending_requests.values())

    def cleanup_expired(self, session_id: str) -> int:
        """Clean up expired requests for a session.

        Returns:
            Number of requests expired
        """
        state = self.get_state(session_id)
        now = datetime.now(timezone.utc)
        expired_count = 0

        for request_id, request in list(state.pending_requests.items()):
            if request.expires_at:
                expires = datetime.fromisoformat(request.expires_at)
                if now > expires:
                    event = HumanApprovalEvent(
                        request_id=request_id,
                        status=ApprovalStatus.EXPIRED,
                        approver_id="system",
                        decided_at=now.isoformat(),
                        comment="Request expired",
                    )
                    state.complete_request(event)
                    expired_count += 1

        return expired_count


# Singleton instance
_approval_manager: ApprovalManager | None = None
_approval_manager_lock = threading.Lock()


def get_approval_manager() -> ApprovalManager:
    """Get the singleton approval manager instance (thread-safe)."""
    global _approval_manager
    if _approval_manager is None:
        with _approval_manager_lock:
            if _approval_manager is None:
                _approval_manager = ApprovalManager()
    return _approval_manager
