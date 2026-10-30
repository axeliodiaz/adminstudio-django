from django.urls import path
from .stock import StockListView, StockMovementView
from .audit import InventoryAuditListView

from .suppliers import SupplierDetailView, SupplierListCreateView

from .views import (
    CategoryListCreateView,
    InventoryModuleView,
    ItemListCreateView,
    LocationListCreateView,
)

urlpatterns = [
    path("stock/", StockListView.as_view(), name="inventory-stock"),
    path(
        "stock/<uuid:pk>/movements/", StockMovementView.as_view(), name="inventory-stock-movement"
    ),
    path("audit/", InventoryAuditListView.as_view(), name="inventory-audit"),
    path("suppliers/", SupplierListCreateView.as_view(), name="inventory-suppliers"),
    path("suppliers/<uuid:pk>/", SupplierDetailView.as_view(), name="inventory-supplier-detail"),
    path("", InventoryModuleView.as_view(), name="inventory-module"),
    path("categories/", CategoryListCreateView.as_view(), name="inventory-categories"),
    path("locations/", LocationListCreateView.as_view(), name="inventory-locations"),
    path("items/", ItemListCreateView.as_view(), name="inventory-items"),
]
