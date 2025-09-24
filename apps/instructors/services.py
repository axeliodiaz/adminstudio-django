from django.contrib.auth import get_user_model

from apps.instructors.models import Instructor
from apps.users.services import create_user
from apps.verifications.services import create_verification_code

User = get_user_model()


def get_or_create_user(data: dict) -> User:
    """
    Retrieves an existing user by email or creates a new user using the provided data.

    The function first attempts to retrieve a user matching the specified email address.
    If no such user exists, it creates a new user based on the provided data dictionary.

    Parameters:
        data (dict): A dictionary containing user-related information. The dictionary
            must include at least an 'email' key to perform the lookup.

    Returns:
        User: The existing or newly created User instance.
    """
    try:
        user = User.objects.get(email=data["email"])
    except User.DoesNotExist:
        user = create_user(data)
    return user


def get_or_create_instructor_user(validated_data: dict) -> tuple[Instructor, bool]:
    """
    Gets an existing instructor or creates one based on provided validated data.

    This function retrieves an existing instructor or creates a new one by utilizing the
    `validated_data`. It first ensures the associated user exists and then either retrieves
    or creates the instructor. If a new instructor is created, a verification code is
    generated for the associated user.

    Args:
        validated_data (dict): The validated data required to create or fetch the user
        and instructor.

    Returns:
        tuple[Instructor, bool]: A tuple containing the retrieved or newly created
        Instructor object and a boolean indicating whether it was created.
    """
    user = get_or_create_user(validated_data)
    instructor, created = Instructor.objects.get_or_create(user=user)
    return instructor, created
