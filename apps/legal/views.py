"""Legal document views using DRF ViewSet."""

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.legal.models import LegalDocumentType
from apps.legal.services import (
    get_all_published_legal_documents,
    get_legal_document_by_slug,
    get_published_legal_document,
)


class LegalDocumentViewSet(viewsets.ViewSet):
    """Legal Document ViewSet for retrieving published legal documents."""

    permission_classes = [AllowAny]

    def list(self, request):
        """Get all published legal documents grouped by type."""
        language = request.query_params.get("language", "es")
        data = get_all_published_legal_documents(language=language)
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="terms-and-conditions")
    def terms_and_conditions(self, request):
        """Get the latest Terms and Conditions document."""
        language = request.query_params.get("language", "es")
        data = get_published_legal_document(
            document_type=LegalDocumentType.TERMS_AND_CONDITIONS, language=language
        )
        if data:
            return Response(data, status=status.HTTP_200_OK)
        return Response(
            {"detail": "Terms and Conditions not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    @action(detail=False, methods=["get"], url_path="privacy-policy")
    def privacy_policy(self, request):
        """Get the latest Privacy Policy document."""
        language = request.query_params.get("language", "es")
        data = get_published_legal_document(
            document_type=LegalDocumentType.PRIVACY_POLICY, language=language
        )
        if data:
            return Response(data, status=status.HTTP_200_OK)
        return Response(
            {"detail": "Privacy Policy not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    @action(detail=False, methods=["get"], url_path="waiver")
    def waiver(self, request):
        """Get the latest Waiver document."""
        language = request.query_params.get("language", "es")
        data = get_published_legal_document(
            document_type=LegalDocumentType.WAIVER, language=language
        )
        if data:
            return Response(data, status=status.HTTP_200_OK)
        return Response(
            {"detail": "Waiver not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    def retrieve_by_slug(self, request, slug):
        """Get a legal document by slug."""
        data = get_legal_document_by_slug(slug)
        if data:
            return Response(data, status=status.HTTP_200_OK)
        return Response(
            {"detail": "Legal document not found"},
            status=status.HTTP_404_NOT_FOUND,
        )
