"""Domain exceptions for VO Agent."""


class VoError(Exception):
    """Base class for VO Agent errors."""


class ResourceConflict(VoError):
    """Raised when an active resource lease blocks a new lease."""


class ReviewParseError(VoError):
    """Raised when reviewer output does not follow the review protocol."""


class StateMachineError(VoError):
    """Raised when a state machine cannot dispatch an event."""


class TaskGraphError(VoError):
    """Raised when a task graph is invalid or cannot advance."""


class ExecutionPlanError(VoError):
    """Raised when an execution plan cannot be built safely."""


class ProvisioningError(VoError):
    """Raised when environments cannot be provisioned for a plan."""


class PlanExecutionError(VoError):
    """Raised when an execution plan cannot be executed safely."""


class BudgetExceeded(VoError):
    """Raised when a workflow tries to spend beyond its configured budget."""


class BundleValidationError(VoError):
    """Raised when a saved workflow bundle is missing required structure."""


class VerificationError(VoError):
    """Raised when verification cannot be configured or executed."""
