"""Custom exceptions for PromptView."""


class PromptViewError(Exception):
    """Base exception."""


class NotInitializedError(PromptViewError):
    """Raised when no .promptview/ directory exists."""


class PromptNotFoundError(PromptViewError):
    """Raised when a prompt cannot be found."""


class NothingToCommitError(PromptViewError):
    """Raised when the staging index is empty."""


class AlreadyInitializedError(PromptViewError):
    """Raised when .promptview/ already exists."""
