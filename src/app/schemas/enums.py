from enum import Enum


class Visibility(str, Enum):
    """Visibility levels for files and resources."""
    RESTRICTED = "restricted"
    PRIVATE = "private"
    PUBLIC = "public"


class Scope(str, Enum):
    """Scope levels for resources."""
    PRIVATE = "private"
    PUBLIC = "public"


class TriggerType(str, Enum):
    """Types of workflow run triggers."""
    MANUAL = "manual"
    PUBLIC_LINK = "public_link"
    INTEGRATION = "integration"


class RunStatus(str, Enum):
    """Status of workflow and step runs."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


class UpdatePolicy(str, Enum):
    """Policy for agent version updates."""
    LOCK_VERSION = "lock_version"
    USE_LATEST = "use_latest" 