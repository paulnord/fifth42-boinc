"""Separate invalid client output from unavailable server validation machinery."""


class ScientificValidationError(ValueError):
    """The uploaded result fails the trusted scientific acceptance rules."""


class ValidationInfrastructureError(RuntimeError):
    """A server dependency failed; defer validation without blaming the client."""
