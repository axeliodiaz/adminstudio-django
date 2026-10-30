import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from model_bakery import baker

from apps.inventory.models import Supplier, SupplierProduct


@pytest.fixture
def admin(api_client):
    api_client.force_authenticate(baker.make(get_user_model(), is_staff=True, is_superuser=True))
    return api_client


@pytest.mark.django_db
@pytest.mark.parametrize("role", ["anonymous", "member", "coach", "staff"])
def test_supplier_access_is_admin_only(api_client, role):
    if role != "anonymous":
        user = baker.make(get_user_model(), is_staff=role == "staff", is_superuser=False)
        if role == "coach":
            baker.make("instructors.Instructor", user=user)
        api_client.force_authenticate(user)
    supplier = Supplier.objects.create(name="Synthetic supplier")
    url = reverse("inventory-suppliers")
    expected = 401 if role == "anonymous" else 403
    assert api_client.get(url).status_code == expected
    assert api_client.post(url, {"name": "Forbidden"}).status_code == expected
    assert (
        api_client.patch(
            reverse("inventory-supplier-detail", args=[supplier.id]), {"name": "Forbidden"}
        ).status_code
        == expected
    )
    supplier.refresh_from_db()
    assert supplier.name == "Synthetic supplier"


@pytest.mark.django_db
def test_create_edit_quotes_and_pagination(admin):
    url = reverse("inventory-suppliers")
    response = admin.post(
        url,
        {
            "name": "Fixture",
            "contact_name": "Test contact",
            "email": "fixture@example.invalid",
            "phone": "+5600000",
            "products": [
                {"name": "Towels", "price": "123.45", "currency": "CLP", "lead_time_days": 3},
                {"name": "Unknown quote"},
            ],
        },
        format="json",
    )
    assert response.status_code == 201
    assert response.data["products"][0]["price"] == "123.45"
    assert response.data["products"][1]["price"] is None
    pk = response.data["id"]
    detail = reverse("inventory-supplier-detail", args=[pk])
    assert admin.patch(detail, {"phone": "new"}, format="json").status_code == 200
    assert SupplierProduct.objects.count() == 2
    response = admin.patch(
        detail,
        {"products": [{"name": "Replacement", "price": "0.00", "lead_time_days": 0}]},
        format="json",
    )
    assert response.status_code == 200
    assert response.data["products"][0]["price"] == "0.00"
    assert SupplierProduct.objects.count() == 1
    listing = admin.get(url, {"search": "fixture", "page": 1, "page_size": 1})
    assert listing.data["count"] == 1
    assert listing.data["results"][0]["phone"] == "new"
    assert admin.get(url, {"search": "missing"}).data["count"] == 0
    Supplier.objects.get(pk=pk).delete()
    assert admin.get(url).data["count"] == 0
    assert admin.patch(detail, {"name": "No revival"}, format="json").status_code == 404


@pytest.mark.django_db
@pytest.mark.parametrize(
    "payload",
    [
        {"name": " "},
        {"name": "x", "email": "bad"},
        {"name": "x", "products": [{"name": "x", "price": "-1"}]},
        {"name": "x", "products": [{"name": "x", "currency": "INVALID"}]},
        {"name": "x", "products": [{"name": "x", "lead_time_days": -1}]},
        {"name": "x", "products": [{"price": "2"}]},
    ],
)
def test_invalid_payload_is_atomic(admin, payload):
    response = admin.post(reverse("inventory-suppliers"), payload, format="json")
    assert response.status_code == 400
    assert Supplier.objects.count() == SupplierProduct.objects.count() == 0


@pytest.mark.django_db
def test_invalid_partial_product_replacement_keeps_existing_rows(admin):
    supplier = Supplier.objects.create(name="Fixture")
    SupplierProduct.objects.create(supplier=supplier, name="Keep me")
    response = admin.patch(
        reverse("inventory-supplier-detail", args=[supplier.id]),
        {"name": "Changed", "products": [{"price": "2"}]},
        format="json",
    )
    assert response.status_code == 400
    supplier.refresh_from_db()
    assert supplier.name == "Fixture"
    assert supplier.products.get().name == "Keep me"
