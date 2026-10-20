"""Shared truthful error envelopes for CLI and host adapters."""

from .jsonio import ContractError


class ExecutionInterrupted(ContractError):
    def __init__(self, message, attempt_id, execution_performed):
        super().__init__(message)
        self.attempt_id = attempt_id
        self.execution_performed = execution_performed
        self.recovery_required = True


def result(error, action):
    code = "EXECUTION_INTERRUPTED" if isinstance(error, ExecutionInterrupted) else "EXECUTION_UNAVAILABLE" if action in ("run", "resume", "approve") else "INVALID_REQUEST"
    value = {"error": code, "message": str(error), "execution_performed": getattr(error, "execution_performed", False)}
    if isinstance(error, ExecutionInterrupted):
        value.update(attempt_id=error.attempt_id, recovery_required=True)
    return value
