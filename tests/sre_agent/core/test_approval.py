"""Tests for the Human-in-the-Loop Approval System."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from sre_agent.core.approval import (
    ApprovalManager,
    ApprovalState,
    ApprovalStatus,
    HumanApprovalEvent,
    HumanApprovalRequest,
    get_approval_manager,
)


class TestHumanApprovalRequest:
    """Tests for HumanApprovalRequest model."""

    def test_create_approval_request(self) -> None:
        """Test creating an approval request."""
        now = datetime.now(timezone.utc)
        request = HumanApprovalRequest(
            request_id="test-123",
            tool_name="restart_pod",
            tool_args={"pod_name": "test-pod"},
            reason="Agent wants to restart the pod",
            risk_assessment="Medium risk",
            session_id="session-456",
            user_id="user-789",
            created_at=now.isoformat(),
        )

        assert request.request_id == "test-123"
        assert request.tool_name == "restart_pod"
        assert request.tool_args == {"pod_name": "test-pod"}
        assert request.session_id == "session-456"

    def test_approval_request_immutable(self) -> None:
        """Test that approval request is immutable."""
        now = datetime.now(timezone.utc)
        request = HumanApprovalRequest(
            request_id="test-123",
            tool_name="restart_pod",
            tool_args={},
            reason="Test",
            risk_assessment="Low",
            session_id="session-456",
            user_id="user-789",
            created_at=now.isoformat(),
        )

        with pytest.raises(ValidationError):
            request.tool_name = "other_tool"  # type: ignore[misc]


class TestHumanApprovalEvent:
    """Tests for HumanApprovalEvent model."""

    def test_create_approval_event(self) -> None:
        """Test creating an approval event."""
        now = datetime.now(timezone.utc)
        event = HumanApprovalEvent(
            request_id="test-123",
            status=ApprovalStatus.APPROVED,
            approver_id="admin-user",
            decided_at=now.isoformat(),
            comment="Looks good, proceeding.",
        )

        assert event.request_id == "test-123"
        assert event.status == ApprovalStatus.APPROVED
        assert event.approver_id == "admin-user"
        assert event.comment == "Looks good, proceeding."

    def test_rejection_event(self) -> None:
        """Test creating a rejection event."""
        now = datetime.now(timezone.utc)
        event = HumanApprovalEvent(
            request_id="test-123",
            status=ApprovalStatus.REJECTED,
            approver_id="admin-user",
            decided_at=now.isoformat(),
            comment="Not safe to proceed.",
        )

        assert event.status == ApprovalStatus.REJECTED


class TestApprovalState:
    """Tests for ApprovalState tracking."""

    def test_add_request(self) -> None:
        """Test adding a pending request."""
        state = ApprovalState()
        now = datetime.now(timezone.utc)

        request = HumanApprovalRequest(
            request_id="test-123",
            tool_name="restart_pod",
            tool_args={},
            reason="Test",
            risk_assessment="Low",
            session_id="session-456",
            user_id="user-789",
            created_at=now.isoformat(),
        )

        state.add_request(request)

        assert state.has_pending() is True
        assert state.get_pending("test-123") == request

    def test_complete_request(self) -> None:
        """Test completing a request."""
        state = ApprovalState()
        now = datetime.now(timezone.utc)

        request = HumanApprovalRequest(
            request_id="test-123",
            tool_name="restart_pod",
            tool_args={},
            reason="Test",
            risk_assessment="Low",
            session_id="session-456",
            user_id="user-789",
            created_at=now.isoformat(),
        )
        state.add_request(request)

        event = HumanApprovalEvent(
            request_id="test-123",
            status=ApprovalStatus.APPROVED,
            approver_id="admin",
            decided_at=now.isoformat(),
        )
        state.complete_request(event)

        assert state.has_pending() is False
        assert state.get_pending("test-123") is None
        assert state.is_approved("test-123") is True

    def test_is_approved_for_rejected(self) -> None:
        """Test is_approved returns False for rejected request."""
        state = ApprovalState()
        now = datetime.now(timezone.utc)

        request = HumanApprovalRequest(
            request_id="test-123",
            tool_name="restart_pod",
            tool_args={},
            reason="Test",
            risk_assessment="Low",
            session_id="session-456",
            user_id="user-789",
            created_at=now.isoformat(),
        )
        state.add_request(request)

        event = HumanApprovalEvent(
            request_id="test-123",
            status=ApprovalStatus.REJECTED,
            approver_id="admin",
            decided_at=now.isoformat(),
        )
        state.complete_request(event)

        assert state.is_approved("test-123") is False


class TestApprovalManager:
    """Tests for ApprovalManager."""

    @pytest.fixture
    def manager(self) -> ApprovalManager:
        """Create an approval manager for testing."""
        return ApprovalManager(expiration_seconds=60)

    def test_create_request(self, manager: ApprovalManager) -> None:
        """Test creating an approval request."""
        request = manager.create_request(
            session_id="session-123",
            user_id="user-456",
            tool_name="restart_pod",
            tool_args={"pod_name": "test-pod"},
            reason="Test restart",
            risk_assessment="Low risk",
        )

        assert request.tool_name == "restart_pod"
        assert request.session_id == "session-123"
        assert request.user_id == "user-456"
        assert request.expires_at is not None

    def test_get_pending_requests(self, manager: ApprovalManager) -> None:
        """Test getting pending requests."""
        manager.create_request(
            session_id="session-123",
            user_id="user-456",
            tool_name="restart_pod",
            tool_args={},
            reason="Test",
            risk_assessment="Low",
        )
        manager.create_request(
            session_id="session-123",
            user_id="user-456",
            tool_name="scale_deployment",
            tool_args={},
            reason="Test",
            risk_assessment="Low",
        )

        pending = manager.get_pending_requests("session-123")
        assert len(pending) == 2

    def test_process_approval(self, manager: ApprovalManager) -> None:
        """Test processing an approval."""
        request = manager.create_request(
            session_id="session-123",
            user_id="user-456",
            tool_name="restart_pod",
            tool_args={},
            reason="Test",
            risk_assessment="Low",
        )

        event = manager.process_decision(
            session_id="session-123",
            request_id=request.request_id,
            approved=True,
            approver_id="admin",
            comment="Approved",
        )

        assert event.status == ApprovalStatus.APPROVED
        assert len(manager.get_pending_requests("session-123")) == 0

    def test_process_rejection(self, manager: ApprovalManager) -> None:
        """Test processing a rejection."""
        request = manager.create_request(
            session_id="session-123",
            user_id="user-456",
            tool_name="restart_pod",
            tool_args={},
            reason="Test",
            risk_assessment="Low",
        )

        event = manager.process_decision(
            session_id="session-123",
            request_id=request.request_id,
            approved=False,
            approver_id="admin",
            comment="Not safe",
        )

        assert event.status == ApprovalStatus.REJECTED

    def test_process_already_processed_request(self, manager: ApprovalManager) -> None:
        """Test processing an already processed request."""
        request = manager.create_request(
            session_id="session-123",
            user_id="user-456",
            tool_name="restart_pod",
            tool_args={},
            reason="Test",
            risk_assessment="Low",
        )

        # Process once
        manager.process_decision(
            session_id="session-123",
            request_id=request.request_id,
            approved=True,
            approver_id="admin",
        )

        # Try to process again
        with pytest.raises(ValueError, match="already been processed"):
            manager.process_decision(
                session_id="session-123",
                request_id=request.request_id,
                approved=False,
                approver_id="other-admin",
            )

    def test_process_nonexistent_request(self, manager: ApprovalManager) -> None:
        """Test processing a non-existent request."""
        with pytest.raises(ValueError, match="not found"):
            manager.process_decision(
                session_id="session-123",
                request_id="nonexistent-id",
                approved=True,
                approver_id="admin",
            )

    def test_separate_sessions(self, manager: ApprovalManager) -> None:
        """Test that sessions are separate."""
        manager.create_request(
            session_id="session-1",
            user_id="user-456",
            tool_name="restart_pod",
            tool_args={},
            reason="Test",
            risk_assessment="Low",
        )
        manager.create_request(
            session_id="session-2",
            user_id="user-456",
            tool_name="scale_deployment",
            tool_args={},
            reason="Test",
            risk_assessment="Low",
        )

        assert len(manager.get_pending_requests("session-1")) == 1
        assert len(manager.get_pending_requests("session-2")) == 1


class TestApprovalManagerSingleton:
    """Tests for singleton access."""

    def test_get_approval_manager_singleton(self) -> None:
        """Test that get_approval_manager returns singleton."""
        manager1 = get_approval_manager()
        manager2 = get_approval_manager()

        assert manager1 is manager2
