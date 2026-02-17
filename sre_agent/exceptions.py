from fastapi import HTTPException


class SREAgentError(HTTPException):
    """Base exception for SRE Agent.

    This exception and its subclasses can be configured to expose their
    messages to the client safely.
    """

    def __init__(self, message: str, user_facing: bool = False, status_code: int = 500):
        """Initialize the SRE Agent error.

        Args:
            message: The error message.
            user_facing: Whether the message is safe to show to the user.
            status_code: The HTTP status code to return.
        """
        super().__init__(status_code=status_code, detail=message)
        self.user_facing = user_facing
        self.status_code = status_code


class UserFacingError(SREAgentError):
    """Exception that is safe to expose to the client."""

    def __init__(self, message: str):
        """Initialize a user-facing error."""
        super().__init__(message, user_facing=True)


class ToolExecutionError(UserFacingError):
    """Exception raised when a tool fails but the error is safe to show."""

    def __init__(self, message: str):
        """Initialize a tool execution error."""
        super().__init__(message)
        self.status_code = 502
