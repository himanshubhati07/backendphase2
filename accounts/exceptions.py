"""Domain exceptions for account operations."""


class AccountDomainError(Exception):
    """Base exception for an account domain operation."""


class EmailAlreadyRegisteredError(AccountDomainError):
    """Raised when registration attempts to reuse an email address."""


class InvalidCredentialsError(AccountDomainError):
    """Raised when credentials cannot authenticate an active account."""
