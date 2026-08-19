from django.urls import path

from apps.faqs.views import (
    AdminFAQItemDetailView,
    AdminFAQItemListView,
    AdminFAQSectionDetailView,
    AdminFAQSectionListView,
    FAQViewSet,
)

urlpatterns = [
    path("admin/sections/", AdminFAQSectionListView.as_view(), name="admin-faq-section-list"),
    path(
        "admin/sections/<uuid:section_id>/",
        AdminFAQSectionDetailView.as_view(),
        name="admin-faq-section-detail",
    ),
    path("admin/items/", AdminFAQItemListView.as_view(), name="admin-faq-item-list"),
    path(
        "admin/items/<uuid:item_id>/",
        AdminFAQItemDetailView.as_view(),
        name="admin-faq-item-detail",
    ),
    path("", FAQViewSet.as_view({"get": "list"}), name="faqs-list"),
]
