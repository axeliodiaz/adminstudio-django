from django.urls import path

from .suppliers import SupplierDetailView, SupplierListCreateView

from .views import (
    CategoryListCreateView,
    InventoryModuleView,
    ItemListCreateView,
    LocationListCreateView,
)

urlpatterns = [
    path("suppliers/", SupplierListCreateView.as_view(), name="inventory-suppliers"),
    path("suppliers/<uuid:pk>/", SupplierDetailView.as_view(), name="inventory-supplier-detail"),
    path("", InventoryModuleView.as_view(), name="inventory-module"),
    path("categories/", CategoryListCreateView.as_view(), name="inventory-categories"),
    path("locations/", LocationListCreateView.as_view(), name="inventory-locations"),
    path("items/", ItemListCreateView.as_view(), name="inventory-items"),
]
