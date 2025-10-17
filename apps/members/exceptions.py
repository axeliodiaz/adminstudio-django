class RoomFullException(Exception):
    pass


class ReservationInvalidStateException(Exception):
    """Raised when a reservation action is invalid for its current status."""

    pass
