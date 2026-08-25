class PurchaseAlreadyActivatedException(Exception):
    """Raised when attempting to activate a purchase that is already activated."""

    pass


class InsufficientCreditsException(Exception):
    """Raised when a member has no class credits left to book."""

    pass
