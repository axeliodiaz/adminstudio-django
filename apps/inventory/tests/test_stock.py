import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from model_bakery import baker

from apps.inventory.models import InventoryAudit, Item, StockBalance


@pytest.fixture
def setup(api_client):
    user = baker.make(get_user_model(), is_staff=True, is_superuser=True)
    api_client.force_authenticate(user)
    item = baker.make(Item, is_active=True)
    return api_client, item


def move(client, item, action, **data):
    return client.post(
        reverse("inventory-stock-movement", args=[item.pk]),
        {"action": action, **data},
        format="json",
    )


@pytest.mark.django_db
@pytest.mark.parametrize("role", ["anonymous", "member", "coach", "staff"])
def test_stock_admin_only(api_client, role):
    if role != "anonymous":
        user = baker.make(get_user_model(), is_staff=role == "staff", is_superuser=False)
        if role == "coach":
            baker.make("instructors.Instructor", user=user)
        api_client.force_authenticate(user)
    item = baker.make(Item)
    expected = 401 if role == "anonymous" else 403
    assert api_client.get(reverse("inventory-stock")).status_code == expected
    assert move(api_client, item, "opening", quantity=10).status_code == expected
    assert not StockBalance.objects.exists()


@pytest.mark.django_db
def test_opening_zero_is_explicit_not_inferred(setup):
    client, item = setup
    row = client.get(reverse("inventory-stock")).data["results"][0]
    assert row["initialized"] is False and row["available"] is None
    assert move(client, item, "consume", quantity=1, version=1).status_code == 400
    row = move(client, item, "opening", quantity=0, minimum=2, laundry=5).data
    assert row["available"] == 0 and row["laundry"] == 5 and row["restock_alert"] is True
    assert move(client, item, "opening", quantity=100).status_code == 409
    assert StockBalance.objects.get().available == 0
    assert InventoryAudit.objects.count() == 1


@pytest.mark.django_db
def test_full_stock_and_laundry_cycle_has_truthful_audit(setup):
    client, item = setup
    row = move(client, item, "opening", quantity=10, minimum=3).data
    for action, data, expected in [
        ("consume", {"quantity": 2}, (8, 0)),
        ("laundry_send", {"quantity": 5}, (3, 5)),
        ("laundry_receive", {"quantity": 2}, (5, 3)),
        ("loss", {"quantity": 1, "bucket": "laundry", "reason": "Missing towel"}, (5, 2)),
        ("write_off", {"quantity": 4, "reason": "Damaged"}, (1, 2)),
        ("restock", {"quantity": 5}, (6, 2)),
        ("minimum", {"minimum": 7}, (6, 2)),
    ]:
        response = move(client, item, action, version=row["version"], **data)
        assert response.status_code == 200, response.data
        row = response.data
        assert (row["available"], row["laundry"]) == expected
    assert row["restock_alert"] is True
    events = InventoryAudit.objects.filter(entity="stock")
    assert events.count() == 8
    assert events.first().after["movement"] == "minimum"
    assert events.first().before["minimum"] == 3
    assert events.first().after["minimum"] == 7


@pytest.mark.django_db
@pytest.mark.parametrize(
    "data",
    [
        {"action": "consume", "quantity": 11, "version": 1},
        {"action": "laundry_receive", "quantity": 1, "version": 1},
        {"action": "restock", "quantity": 1, "version": 999},
        {"action": "loss", "quantity": 1, "version": 1},
        {"action": "restock", "quantity": 0, "version": 1},
        {"action": "restock", "quantity": -1, "version": 1},
        {"action": "restock", "quantity": 1.5, "version": 1},
        {"action": "minimum", "minimum": 0, "version": 1},
        {"action": "consume", "quantity": 1, "minimum": 2, "version": 1},
        {"action": "restock", "quantity": 1, "laundry": 3, "version": 1},
        {"action": "minimum", "quantity": 5, "minimum": 2, "version": 1},
        {"action": "consume", "quantity": 1, "bucket": "laundry", "version": 1},
    ],
)
def test_invalid_or_stale_movements_leave_state_unchanged(setup, data):
    client, item = setup
    move(client, item, "opening", quantity=10)
    response = move(client, item, **data)
    assert response.status_code in {400, 409}
    balance = StockBalance.objects.get()
    assert (balance.available, balance.laundry, balance.version) == (10, 0, 1)
    assert InventoryAudit.objects.count() == 1


@pytest.mark.django_db
def test_audit_failure_rolls_back_stock(setup, mocker):
    client, item = setup
    move(client, item, "opening", quantity=10)
    mocker.patch(
        "apps.inventory.audit.InventoryAudit.objects.create", side_effect=RuntimeError("synthetic")
    )
    with pytest.raises(RuntimeError):
        move(client, item, "consume", quantity=1, version=1)
    assert StockBalance.objects.get().available == 10


@pytest.mark.django_db
def test_version_replay_does_not_duplicate_and_inactive_items_cannot_move(setup):
    client, item = setup
    move(client, item, "opening", quantity=10)
    assert move(client, item, "consume", quantity=1, version=1).status_code == 200
    assert move(client, item, "consume", quantity=1, version=1).status_code == 409
    item.is_active = False
    item.save()
    assert move(client, item, "restock", quantity=1, version=2).status_code == 404
    assert client.get(reverse("inventory-stock")).data["count"] == 0
