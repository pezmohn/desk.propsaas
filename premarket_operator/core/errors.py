class PremarketOperatorError(Exception):
    """Base application error."""


class TenantScopeError(PremarketOperatorError):
    """Raised when a tenant-scoped operation is missing a user id."""
