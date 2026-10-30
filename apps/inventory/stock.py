"""Optimistic stock transactions and the existing append-only API audit ledger."""

from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.exceptions import APIException
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.pagination import paginate
from apps.inventory.audit import record_inventory_change
from apps.inventory.models import Item, StockBalance
from apps.inventory.permissions import IsInventoryAdmin


class Conflict(APIException):
    status_code = 409
    default_detail = "El stock cambió. Recarga antes de volver a guardar."


class StockInput(serializers.Serializer):
    action = serializers.ChoiceField(
        choices=[
            "opening",
            "restock",
            "consume",
            "laundry_send",
            "laundry_receive",
            "loss",
            "write_off",
            "minimum",
        ]
    )
    quantity = serializers.IntegerField(min_value=0, max_value=1000000, required=False)
    laundry = serializers.IntegerField(min_value=0, max_value=1000000, required=False)
    minimum = serializers.IntegerField(min_value=0, max_value=1000000, required=False)
    version = serializers.IntegerField(min_value=1, required=False)
    reason = serializers.CharField(max_length=1000, required=False, allow_blank=True, default="")
    bucket = serializers.ChoiceField(choices=["available", "laundry"], default="available")

    def validate(self, data):
        if data["action"] != "minimum" and "quantity" not in data:
            raise serializers.ValidationError("quantity: requerida.")
        if data["action"] not in {"opening", "minimum"} and data.get("quantity", 0) == 0:
            raise serializers.ValidationError("quantity: debe ser mayor que cero.")
        if data["action"] == "minimum" and "minimum" not in data:
            raise serializers.ValidationError("minimum: requerido.")
        if data["action"] in {"loss", "write_off"} and not data["reason"].strip():
            raise serializers.ValidationError("reason: requerida para pérdidas o bajas.")
        action = data["action"]
        if "laundry" in data and action != "opening":
            raise serializers.ValidationError("laundry: solo para conteo inicial.")
        if "minimum" in data and action not in {"opening", "minimum"}:
            raise serializers.ValidationError("minimum: usa cambiar mínimo.")
        if "quantity" in data and action == "minimum":
            raise serializers.ValidationError("quantity: no corresponde a cambiar mínimo.")
        if data["bucket"] == "laundry" and action not in {"loss", "write_off"}:
            raise serializers.ValidationError("bucket: solo para pérdidas o bajas.")
        return data


def serialize_stock(item):
    balance = getattr(item, "stock", None)
    return {
        "id": str(item.id),
        "name": item.name,
        "initialized": balance is not None,
        "available": balance.available if balance else None,
        "laundry": balance.laundry if balance else None,
        "minimum": balance.minimum if balance else None,
        "version": balance.version if balance else None,
        "restock_alert": balance.available < balance.minimum if balance else False,
    }


@transaction.atomic
def apply_stock(user, item, data):
    action = data["action"]
    before = serialize_stock(item)
    if action == "opening":
        if before["initialized"]:
            raise Conflict("El stock ya tiene conteo inicial.")
        try:
            with transaction.atomic():
                StockBalance.objects.create(
                    item=item,
                    available=data["quantity"],
                    laundry=data.get("laundry", 0),
                    minimum=data.get("minimum", 0),
                )
        except IntegrityError:
            raise Conflict("El stock ya tiene conteo inicial.")
    else:
        balance = getattr(item, "stock", None)
        if balance is None:
            raise serializers.ValidationError("Registra primero el conteo inicial.")
        if data.get("version") != balance.version:
            raise Conflict()
        available, laundry = balance.available, balance.laundry
        quantity = data.get("quantity", 0)
        if action == "restock":
            available += quantity
        elif action == "consume":
            available -= quantity
        elif action == "laundry_send":
            available -= quantity
            laundry += quantity
        elif action == "laundry_receive":
            laundry -= quantity
            available += quantity
        elif action in {"loss", "write_off"}:
            if data["bucket"] == "laundry":
                laundry -= quantity
            else:
                available -= quantity
        if available > 2147483647 or laundry > 2147483647:
            raise serializers.ValidationError("El saldo supera el límite permitido.")
        if available < 0 or laundry < 0:
            raise serializers.ValidationError(
                "La cantidad supera el stock disponible en ese estado."
            )
        minimum = data["minimum"] if action == "minimum" else balance.minimum
        if (available, laundry, minimum) == (balance.available, balance.laundry, balance.minimum):
            raise serializers.ValidationError("No hay cambios.")
        changed = StockBalance.objects.filter(pk=balance.pk, version=balance.version).update(
            available=available, laundry=laundry, minimum=minimum, version=balance.version + 1
        )
        if not changed:
            raise Conflict()
    after = serialize_stock(Item.objects.select_related("stock").get(pk=item.pk))
    record_inventory_change(
        user,
        "stock",
        item.pk,
        {
            **after,
            "movement": action,
            "quantity": data.get("quantity"),
            "bucket": data["bucket"],
            "reason": data["reason"],
        },
        before,
    )
    return after


class StockListView(APIView):
    permission_classes = [IsAuthenticated, IsInventoryAdmin]

    def get(self, request):
        items = Item.objects.filter(is_active=True).select_related("stock").order_by("name", "id")
        search = (request.query_params.get("search") or "").strip()
        if search:
            items = items.filter(name__icontains=search)
        return Response(paginate(request.query_params, items, serialize_stock))


class StockMovementView(APIView):
    permission_classes = [IsAuthenticated, IsInventoryAdmin]

    def post(self, request, pk):
        item = get_object_or_404(Item.objects.select_related("stock"), pk=pk, is_active=True)
        serializer = StockInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(apply_stock(request.user, item, serializer.validated_data))
