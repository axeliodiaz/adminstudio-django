from django.urls import path

from apps.docs.views import DocsViewSet

urlpatterns = [
    path("", DocsViewSet.as_view({"get": "list"}), name="docs-list"),
    path(
        "<slug:section_slug>/<slug:page_slug>/",
        DocsViewSet.as_view({"get": "retrieve"}),
        name="docs-detail",
    ),
]
