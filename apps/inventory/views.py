"""Inventory module views (CYC-414).

Admin-only module shell plus base CRUD (list/create) for categories,
locations and items. Later tickets add stock levels, maintenance records,
suppliers and purchases (CYC-415..418).
"""

from django.db import transaction
from rest_framework import status

from apps.inventory.audit import record_inventory_change
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.pagination import paginate
from apps.inventory.models import Category, Item, Location
from apps.inventory.permissions import IsInventoryAdmin


def _serialize_category(category: Category) -> dict:
    return {
        "id": str(category.id),
        "name": category.name,
        "description": category.description,
        "order": category.order,
        "item_count": category.items.filter(is_removed=False).count(),
    }


def _serialize_location(location: Location) -> dict:
    return {
        "id": str(location.id),
        "name": location.name,
        "kind": location.kind,
        "kind_label": location.get_kind_display(),
        "description": location.description,
        "item_count": location.items.filter(is_removed=False).count(),
    }


def _serialize_item(item: Item) -> dict:
    return {
        "id": str(item.id),
        "name": item.name,
        "category_id": str(item.category_id),
        "category_name": item.category.name,
        "location_id": str(item.location_id) if item.location_id else None,
        "location_name": item.location.name if item.location_id else None,
        "spot": item.spot,
        "identifier": item.identifier,
        "notes": item.notes,
        "is_active": item.is_active,
    }


def _invalid(detail: str) -> Response:
    return Response({"detail": detail}, status=status.HTTP_400_BAD_REQUEST)


class InventoryModuleView(APIView):
    """Module shell (CYC-414): confirms the Inventory module exists."""

    permission_classes = [IsAuthenticated, IsInventoryAdmin]

    def get(self, request, *args, **kwargs):
        return Response(
            {
                "module": "inventory",
                "status": "active",
                "features": {
                    "categories": True,
                    "locations": True,
                    "items": True,
                    "stock_levels": False,
                    "maintenance": False,
                    "suppliers": True,
                    "purchases": False,
                    "audit_log": True,
                },
            }
        )


class CategoryListCreateView(APIView):
    """List or create inventory categories (CYC-414)."""

    permission_classes = [IsAuthenticated, IsInventoryAdmin]

    def get(self, request, *args, **kwargs):
        categories = Category.objects.filter(is_removed=False)
        return Response(paginate(request.query_params, categories, _serialize_category))

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        name = (request.data.get("name") or "").strip()
        if not name:
            return _invalid("name: este campo es requerido.")
        if Category.objects.filter(name__iexact=name, is_removed=False).exists():
            return _invalid("name: ya existe una categoría con este nombre.")
        category = Category.objects.create(
            name=name,
            description=(request.data.get("description") or "").strip(),
            order=request.data.get("order") or 0,
        )
        payload = _serialize_category(category)
        record_inventory_change(request.user, "category", category.pk, payload)
        return Response(payload, status=status.HTTP_201_CREATED)


class LocationListCreateView(APIView):
    """List or create inventory locations (CYC-414)."""

    permission_classes = [IsAuthenticated, IsInventoryAdmin]

    def get(self, request, *args, **kwargs):
        locations = Location.objects.filter(is_removed=False)
        kind = (request.query_params.get("kind") or "").strip().lower()
        if kind in {Location.ROOM, Location.STORAGE}:
            locations = locations.filter(kind=kind)
        return Response(paginate(request.query_params, locations, _serialize_location))

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        name = (request.data.get("name") or "").strip()
        if not name:
            return _invalid("name: este campo es requerido.")
        kind = (request.data.get("kind") or Location.STORAGE).strip().lower()
        if kind not in {Location.ROOM, Location.STORAGE}:
            return _invalid("kind: debe ser 'room' o 'storage'.")
        if Location.objects.filter(name__iexact=name, is_removed=False).exists():
            return _invalid("name: ya existe una ubicación con este nombre.")
        location = Location.objects.create(
            name=name,
            kind=kind,
            description=(request.data.get("description") or "").strip(),
        )
        payload = _serialize_location(location)
        record_inventory_change(request.user, "location", location.pk, payload)
        return Response(payload, status=status.HTTP_201_CREATED)


class ItemListCreateView(APIView):
    """List or create inventory items with their assignment (CYC-414).

    Filters: ``category`` and ``location`` (UUID), ``search`` (name,
    identifier or spot).
    """

    permission_classes = [IsAuthenticated, IsInventoryAdmin]

    def get(self, request, *args, **kwargs):
        items = Item.objects.filter(is_removed=False).select_related("category", "location")
        category = request.query_params.get("category")
        if category:
            items = items.filter(category_id=category)
        location = request.query_params.get("location")
        if location:
            items = items.filter(location_id=location)
        search = (request.query_params.get("search") or "").strip()
        if search:
            items = (
                items.filter(name__icontains=search)
                | items.filter(identifier__icontains=search)
                | items.filter(spot__icontains=search)
            )
        return Response(paginate(request.query_params, items, _serialize_item))

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        name = (request.data.get("name") or "").strip()
        if not name:
            return _invalid("name: este campo es requerido.")
        category_id = request.data.get("category_id")
        category = Category.objects.filter(id=category_id, is_removed=False).first()
        if category is None:
            return _invalid("category_id: categoría inválida.")
        location = None
        location_id = request.data.get("location_id")
        if location_id:
            location = Location.objects.filter(id=location_id, is_removed=False).first()
            if location is None:
                return _invalid("location_id: ubicación inválida.")
        item = Item.objects.create(
            name=name,
            category=category,
            location=location,
            spot=(request.data.get("spot") or "").strip(),
            identifier=(request.data.get("identifier") or "").strip(),
            notes=(request.data.get("notes") or "").strip(),
        )
        payload = _serialize_item(item)
        record_inventory_change(request.user, "item", item.pk, payload)
        return Response(payload, status=status.HTTP_201_CREATED)
