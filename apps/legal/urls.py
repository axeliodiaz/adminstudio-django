from django.urls import path

from apps.legal.views import LegalDocumentViewSet

urlpatterns = [
    path("", LegalDocumentViewSet.as_view({"get": "list"}), name="legal-documents-list"),
    path(
        "terms-and-conditions/",
        LegalDocumentViewSet.as_view({"get": "terms_and_conditions"}),
        name="legal-terms-and-conditions",
    ),
    path(
        "privacy-policy/",
        LegalDocumentViewSet.as_view({"get": "privacy_policy"}),
        name="legal-privacy-policy",
    ),
    path(
        "waiver/",
        LegalDocumentViewSet.as_view({"get": "waiver"}),
        name="legal-waiver",
    ),
    path(
        "<str:slug>/",
        LegalDocumentViewSet.as_view({"get": "retrieve_by_slug"}),
        name="legal-document-detail",
    ),
]
