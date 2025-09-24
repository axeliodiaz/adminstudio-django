import pytest


@pytest.fixture
def validated_registration_data():
    return {
        "email": "john.doe@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "phone": "+123456789",
        "password": "should_be_ignored",
    }


@pytest.fixture
def serialized_user_payload():
    return {
        "first_name": "John",
        "last_name": "Doe",
        "email": "john.doe@example.com",
        "phone_number": "+123456789",
    }
