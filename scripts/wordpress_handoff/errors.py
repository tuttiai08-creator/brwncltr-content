"""Handoff failures. Messages must never include credentials."""


class HandoffError(Exception):
    """Fail-closed error. Safe to print."""

    def __init__(self, message: str, *, exit_code: int = 1) -> None:
        super().__init__(message)
        self.exit_code = exit_code
