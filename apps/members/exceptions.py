class RoomFullException(Exception):
    pass


class ReservationInvalidStateException(Exception):
    """Raised when a reservation action is invalid for its current status."""

    pass


class InvalidSpotException(Exception):
    """Raised when the selected spot is invalid (out of range)."""

    pass
