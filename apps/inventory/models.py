"""Inventory module models (CYC-414).

Base records for the studio inventory: categories, locations (rooms or
storage) and items assigned to a location/spot (e.g. which bike is in
which spot). Stock levels, maintenance, suppliers and purchases arrive in
later tickets (CYC-415..418).
"""

from django.db import models
from model_utils.models import SoftDeletableModel, TimeStampedModel, UUIDModel


class Category(SoftDeletableModel, UUIDModel, TimeStampedModel):
    """Grouping for inventory items (e.g. Bikes, Towels, Cleaning)."""

    name = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True, default="")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class Location(SoftDeletableModel, UUIDModel, TimeStampedModel):
    """Where inventory lives: a studio room or a storage area."""

    ROOM = "room"
    STORAGE = "storage"
    KIND_CHOICES = ((ROOM, "Room"), (STORAGE, "Storage"))

    name = models.CharField(max_length=120, unique=True)
    kind = models.CharField(max_length=20, choices=KIND_CHOICES, default=STORAGE)
    description = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Item(SoftDeletableModel, UUIDModel, TimeStampedModel):
    """One tracked thing in the studio.

    ``location`` + ``spot`` are the assignment: which room/storage and
    which spot inside it the item occupies (e.g. bike 12 in spot 12).
    ``identifier`` holds a studio-side code such as a bike number.
    """

    name = models.CharField(max_length=160)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="items")
    location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        related_name="items",
        null=True,
        blank=True,
    )
    spot = models.CharField(max_length=80, blank=True, default="")
    identifier = models.CharField(max_length=80, blank=True, default="")
    notes = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["category", "location", "is_active"])]

    def __str__(self):
        return self.name


class Supplier(SoftDeletableModel, UUIDModel, TimeStampedModel):
    """Contact directory, without purchase orders or outbound communication."""

    name = models.CharField(max_length=160)
    contact_name = models.CharField(max_length=160, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    phone = models.CharField(max_length=80, blank=True, default="")
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["name", "id"]


class SupplierProduct(UUIDModel):
    """Reference quote: an unknown price or lead time is null, never zero."""

    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name="products")
    name = models.CharField(max_length=160)
    price = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default="CLP")
    lead_time_days = models.PositiveIntegerField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["name", "id"]


class InventoryAudit(UUIDModel):
    """Append-only application event for supported inventory API writes."""

    at = models.DateTimeField(auto_now_add=True)
    actor_id = models.CharField(max_length=80)
    actor_name = models.CharField(max_length=160)
    entity = models.CharField(max_length=40)
    entity_id = models.UUIDField()
    action = models.CharField(max_length=20)
    before = models.JSONField(null=True)
    after = models.JSONField()

    class Meta:
        ordering = ["-at", "-id"]


class StockBalance(UUIDModel):
    """Explicitly initialized integer counts; absent means unknown, not zero."""

    item = models.OneToOneField(Item, on_delete=models.PROTECT, related_name="stock")
    available = models.PositiveIntegerField(default=0)
    laundry = models.PositiveIntegerField(default=0)
    minimum = models.PositiveIntegerField(default=0)
    version = models.PositiveIntegerField(default=1)
