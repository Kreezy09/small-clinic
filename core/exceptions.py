"""Base class for domain errors reported to API clients."""


class DomainError(Exception):
    """A business rule violation whose message is safe to show to clients."""
