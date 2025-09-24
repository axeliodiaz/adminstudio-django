import uuid

import pytest
from model_bakery import baker


@pytest.fixture
@pytest.mark.django_db
def notification():
    notification = baker.make(
        "notifications.Notification",
        subject="Test Subject",
        message="Test Message",
        user=baker.make("users.User"),
    )
    return notification


@pytest.fixture
def mocked_pending():
    return [
        {
            "id": uuid.uuid4(),
            "subject": "Hello",
            "message": "World",
            "user_id": uuid.uuid4(),
        },
        {
            "id": uuid.uuid4(),
            "subject": "Foo",
            "message": "Bar",
            "user_id": uuid.uuid4(),
        },
    ]


@pytest.fixture
@pytest.mark.django_db
def recipients():
    return baker.make("users.User", _quantity=3)


@pytest.fixture
@pytest.mark.django_db
def enqueued_notifications():
    return baker.make(
        "notifications.Notification",
        _quantity=2,
        status="enqueued",
    )


@pytest.fixture
@pytest.mark.django_db
def sent_notifications():
    return baker.make(
        "notifications.Notification",
        _quantity=2,
        status="sent",
    )
