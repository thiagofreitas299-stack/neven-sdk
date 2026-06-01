"""NEVEN SDK — Custom Exceptions"""


class NevenError(Exception):
    """Base exception for all NEVEN SDK errors."""
    def __init__(self, message: str, code: str = "NEVEN_ERROR", details: dict = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(message)

    def __repr__(self):
        return f"{self.__class__.__name__}(code={self.code!r}, message={self.message!r})"


class NevenAuthError(NevenError):
    """Raised when authentication or authorization fails."""
    def __init__(self, message: str = "Invalid API key or agent signature", **kwargs):
        super().__init__(message, code="UNAUTHORIZED", **kwargs)


class NevenConnectionError(NevenError):
    """Raised when connection to NEVEN runtime or node fails."""
    def __init__(self, message: str = "Cannot connect to NEVEN runtime", **kwargs):
        super().__init__(message, code="CONNECTION_ERROR", **kwargs)


class NevenSafetyError(NevenError):
    """
    Raised when Deterministic Safety Engine (DSE) blocks an action.
    This is by design — the DSE protects the physical world from
    probabilistic AI hallucinations.
    """
    def __init__(self, message: str, rule_id: str = None, **kwargs):
        self.rule_id = rule_id
        super().__init__(message, code="SAFETY_RULE_VIOLATION", **kwargs)

    def __repr__(self):
        return f"NevenSafetyError(rule={self.rule_id!r}, message={self.message!r})"


class NevenNodeNotFoundError(NevenError):
    """Raised when a physical node ID is not found in the network."""
    def __init__(self, node_id: str, **kwargs):
        super().__init__(
            f"Node '{node_id}' not found or not accessible in current session",
            code="NODE_NOT_FOUND",
            **kwargs
        )


class NevenActuationError(NevenError):
    """Raised when a physical actuation command fails at hardware level."""
    def __init__(self, message: str, actuator_code: str = None, **kwargs):
        self.actuator_code = actuator_code
        super().__init__(message, code="ACTUATION_ERROR", **kwargs)


class NevenSessionError(NevenError):
    """Raised for session lifecycle errors (not connected, expired, etc.)."""
    def __init__(self, message: str = "No active session. Call connect() first.", **kwargs):
        super().__init__(message, code="SESSION_ERROR", **kwargs)
