class CoachException(Exception):
    """Base exception for the coach app."""


class CoachClassNotFound(CoachException):
    pass


class CoachReservationNotFound(CoachException):
    pass
