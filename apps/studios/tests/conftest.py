import pytest
from model_bakery import baker


@pytest.fixture
def address():
    """Create an Address instance for testing."""
    return baker.make(
        "studios.Address",
        address="123 Test St",
        latitude=None,
        longitude=None,
    )


@pytest.fixture
def studio(address):
    return baker.make(
        "studios.Studio",
        name="Test Studio",
        address=address,
        is_active=True,
    )


@pytest.fixture
def room(studio):
    return baker.make(
        "studios.Room",
        studio=studio,
        name="Room A",
        capacity=10,
        is_active=True,
    )


@pytest.fixture
def extra_room(studio):
    """An additional room in the same studio, created with model_bakery."""
    return baker.make(
        "studios.Room",
        studio=studio,
        name="Room B",
        capacity=20,
        is_active=False,
    )


@pytest.fixture
def empty_address():
    """Create an Address instance for empty studio."""
    return baker.make(
        "studios.Address",
        address="Nowhere",
        latitude=None,
        longitude=None,
    )


@pytest.fixture
def empty_studio(empty_address):
    """A studio without any rooms."""
    return baker.make(
        "studios.Studio",
        name="Empty Studio",
        address=empty_address,
        is_active=False,
    )
