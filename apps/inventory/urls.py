from django.urls import path

from .views import (
    CategoryListCreateView,
    InventoryModuleView,
    ItemListCreateView,
    LocationListCreateView,
)

urlpatterns = [
    path("", InventoryModuleView.as_view(), name="inventory-module"),
    path("categories/", CategoryListCreateView.as_view(), name="inventory-categories"),
    path("locations/", LocationListCreateView.as_view(), name="inventory-locations"),
    path("items/", ItemListCreateView.as_view(), name="inventory-items"),
]
