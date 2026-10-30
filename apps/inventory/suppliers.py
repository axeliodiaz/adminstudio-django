"""Admin-only supplier directory. Quotes are reference data, never purchases."""

from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.pagination import paginate
from apps.inventory.models import Supplier, SupplierProduct
from apps.inventory.audit import record_inventory_change
from apps.inventory.permissions import IsInventoryAdmin


class ProductInput(serializers.Serializer):
    name = serializers.CharField(max_length=160)
    price = serializers.DecimalField(
        max_digits=14, decimal_places=2, min_value=0, required=False, allow_null=True
    )
    currency = serializers.ChoiceField(choices=["CLP", "USD", "EUR"], default="CLP")
    lead_time_days = serializers.IntegerField(
        min_value=0, max_value=3650, required=False, allow_null=True
    )
    notes = serializers.CharField(max_length=2000, required=False, allow_blank=True, default="")


class SupplierInput(serializers.Serializer):
    name = serializers.CharField(max_length=160)
    contact_name = serializers.CharField(
        max_length=160, required=False, allow_blank=True, default=""
    )
    email = serializers.EmailField(required=False, allow_blank=True, default="")
    phone = serializers.CharField(max_length=80, required=False, allow_blank=True, default="")
    notes = serializers.CharField(max_length=4000, required=False, allow_blank=True, default="")
    products = ProductInput(many=True, required=False, max_length=100)

    def validate_products(self, value):
        # PATCH replaces the supplied reference list, so each row must be complete.
        rows = ProductInput(data=value, many=True)
        rows.is_valid(raise_exception=True)
        return rows.validated_data


def serialize_supplier(supplier):
    return {
        "id": str(supplier.id),
        "name": supplier.name,
        "contact_name": supplier.contact_name,
        "email": supplier.email,
        "phone": supplier.phone,
        "notes": supplier.notes,
        "products": [
            {
                "name": p.name,
                "price": str(p.price) if p.price is not None else None,
                "currency": p.currency,
                "lead_time_days": p.lead_time_days,
                "notes": p.notes,
            }
            for p in supplier.products.all()
        ],
    }


@transaction.atomic
def save_supplier(data, instance=None):
    products = data.pop("products", None)
    if instance is None:
        instance = Supplier.objects.create(**data)
    else:
        for field, value in data.items():
            setattr(instance, field, value)
        instance.save()
    if products is not None:
        instance.products.all().delete()
        SupplierProduct.objects.bulk_create(
            [SupplierProduct(supplier=instance, **p) for p in products]
        )
    return instance


class SupplierListCreateView(APIView):
    permission_classes = [IsAuthenticated, IsInventoryAdmin]

    def get(self, request):
        suppliers = Supplier.objects.prefetch_related("products")
        search = (request.query_params.get("search") or "").strip()
        if search:
            suppliers = suppliers.filter(
                Q(name__icontains=search) | Q(contact_name__icontains=search)
            )
        return Response(paginate(request.query_params, suppliers, serialize_supplier))

    @transaction.atomic
    def post(self, request):
        serializer = SupplierInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        supplier = save_supplier(serializer.validated_data)
        payload = serialize_supplier(supplier)
        record_inventory_change(request.user, "supplier", supplier.pk, payload)
        return Response(payload, status=status.HTTP_201_CREATED)


class SupplierDetailView(APIView):
    permission_classes = [IsAuthenticated, IsInventoryAdmin]

    @transaction.atomic
    def patch(self, request, pk):
        supplier = get_object_or_404(Supplier, pk=pk)
        before = serialize_supplier(supplier)
        serializer = SupplierInput(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        supplier = save_supplier(serializer.validated_data, supplier)
        payload = serialize_supplier(supplier)
        record_inventory_change(request.user, "supplier", supplier.pk, payload, before)
        return Response(payload)
