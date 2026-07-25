class OperationalError(Exception):
    """A user-correctable filesystem or validation failure."""


class ManualRecoveryError(OperationalError):
    """A preserved marker blocks automatic recovery and needs operator action."""


class ClaudeInterrupted(KeyboardInterrupt):
    """Carry an actionable Claude projection diagnostic while preserving exit 130."""

    def __init__(self, message):
        super().__init__()
        self.message = message
