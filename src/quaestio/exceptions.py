"""Domain exceptions for Limes Quaestio."""


class QuaestioError(Exception):
    """Base class for Limes Quaestio errors."""


class ResourceConflict(QuaestioError):
    """Raised when an active resource lease blocks a new lease."""


class ReviewParseError(QuaestioError):
    """Raised when reviewer output does not follow the review protocol."""


class StateMachineError(QuaestioError):
    """Raised when a state machine cannot dispatch an event."""


class TaskGraphError(QuaestioError):
    """Raised when a task graph is invalid or cannot advance."""


class ExecutionPlanError(QuaestioError):
    """Raised when an execution plan cannot be built safely."""


class ProvisioningError(QuaestioError):
    """Raised when environments cannot be provisioned for a plan."""


class PlanExecutionError(QuaestioError):
    """Raised when an execution plan cannot be executed safely."""


class BudgetExceeded(QuaestioError):
    """Raised when a workflow tries to spend beyond its configured budget."""


class BundleValidationError(QuaestioError):
    """Raised when a saved workflow bundle is missing required structure."""


class VerificationError(QuaestioError):
    """Raised when verification cannot be configured or executed."""
