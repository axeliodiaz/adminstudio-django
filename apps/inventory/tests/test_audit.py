import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from model_bakery import baker

from apps.inventory.models import Category, InventoryAudit, Supplier


@pytest.fixture
def admin(api_client):
    user = baker.make(get_user_model(), username="audit-admin", is_staff=True, is_superuser=True)
    api_client.force_authenticate(user)
    return api_client, user


@pytest.mark.django_db
@pytest.mark.parametrize("role", ["anonymous", "member", "coach", "staff"])
def test_audit_is_admin_only(api_client, role):
    if role != "anonymous":
        user = baker.make(get_user_model(), is_staff=role == "staff", is_superuser=False)
        if role == "coach":
            baker.make("instructors.Instructor", user=user)
        api_client.force_authenticate(user)
    assert api_client.get(reverse("inventory-audit")).status_code == (
        401 if role == "anonymous" else 403
    )


@pytest.mark.django_db
def test_create_paths_capture_truthful_actor_and_before_after(admin):
    client, user = admin
    assert client.get(reverse("inventory-audit")).data["count"] == 0
    category = client.post(
        reverse("inventory-categories"), {"name": "Synthetic category"}, format="json"
    ).data
    location = client.post(
        reverse("inventory-locations"), {"name": "Synthetic storage"}, format="json"
    ).data
    item = client.post(
        reverse("inventory-items"),
        {"name": "Synthetic item", "category_id": category["id"], "location_id": location["id"]},
        format="json",
    ).data
    supplier = client.post(
        reverse("inventory-suppliers"),
        {"name": "Synthetic supplier", "actor_id": "spoofed"},
        format="json",
    ).data
    assert InventoryAudit.objects.count() == 4
    for row in InventoryAudit.objects.all():
        assert row.actor_id == str(user.pk)
        assert row.actor_name == "audit-admin"
        assert row.at is not None and row.before is None and row.action == "create"
    event = InventoryAudit.objects.get(entity="item")
    assert event.after == item
    detail = reverse("inventory-supplier-detail", args=[supplier["id"]])
    client.patch(detail, {"phone": "Synthetic phone"}, format="json")
    event = InventoryAudit.objects.first()
    assert event.action == "update"
    assert event.before["phone"] == "" and event.after["phone"] == "Synthetic phone"
    count = InventoryAudit.objects.count()
    client.patch(detail, {"phone": "Synthetic phone"}, format="json")
    assert InventoryAudit.objects.count() == count
    client.patch(detail, {"email": "invalid"}, format="json")
    assert InventoryAudit.objects.count() == count
    listing = client.get(reverse("inventory-audit"), {"page_size": 1})
    assert listing.data["count"] == count and len(listing.data["results"]) == 1
    assert client.post(reverse("inventory-audit"), {}, format="json").status_code == 405


@pytest.mark.django_db
def test_audit_failure_rolls_back_the_original_write(admin, mocker):
    client, _ = admin
    mocker.patch(
        "apps.inventory.audit.InventoryAudit.objects.create",
        side_effect=RuntimeError("synthetic audit failure"),
    )
    with pytest.raises(RuntimeError):
        client.post(reverse("inventory-categories"), {"name": "Must rollback"}, format="json")
    assert not Category.objects.exists()
    with pytest.raises(RuntimeError):
        client.post(reverse("inventory-suppliers"), {"name": "Must rollback"}, format="json")
    assert not Supplier.objects.exists()
