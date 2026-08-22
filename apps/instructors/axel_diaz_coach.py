"""Promote the real Axel Diaz account to coach without creating a duplicate user."""

from django.db.models import Q

AXEL_DIAZ_USERNAME = "axelio"
AXEL_DIAZ_EMAIL = "diaz.axelio@gmail.com"


def axel_diaz_user_q():
    return (
        Q(username__iexact=AXEL_DIAZ_USERNAME)
        | Q(email__iexact=AXEL_DIAZ_EMAIL)
        | (Q(first_name__iexact="Axel") & Q(last_name__iexact="Diaz"))
        | (Q(first_name__iexact="Axel") & Q(last_name__iexact="Díaz"))
    )


def find_axel_diaz_user(user_model):
    return user_model.objects.filter(axel_diaz_user_q()).order_by("date_joined").first()


def ensure_axel_diaz_is_coach(user_model, instructor_model):
    """Attach a live Instructor to Axel Diaz if that user already exists.

    Does not create a user and does not change passwords.
    Returns the instructor, or None if no matching user was found.
    """
    user = find_axel_diaz_user(user_model)
    if user is None:
        return None

    instructor = instructor_model.objects.filter(user_id=user.pk).first()
    created = instructor is None
    if created:
        instructor = instructor_model(user=user)

    if getattr(instructor, "is_removed", False):
        instructor.is_removed = False

    if not getattr(instructor, "tagline", ""):
        instructor.tagline = "Indoor cycling · PulseFit"
    if not getattr(instructor, "specialties", None):
        instructor.specialties = ["Power Ride", "HIIT"]
    if not getattr(instructor, "languages", None):
        instructor.languages = ["Español", "English"]

    instructor.save()
    return instructor
