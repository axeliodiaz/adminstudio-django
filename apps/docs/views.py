"""Public documentation endpoints. Staff edits content in Django admin."""

from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.docs.models import DocAudience
from apps.docs.services import get_published_doc_page, get_published_docs_index


class DocsViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]

    def list(self, request):
        audience = request.query_params.get("audience")
        if audience and audience not in DocAudience.values:
            return Response(
                {"detail": "Audiencia inválida."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(get_published_docs_index(audience=audience), status=status.HTTP_200_OK)

    def retrieve(self, request, section_slug, page_slug):
        data = get_published_doc_page(section_slug=section_slug, page_slug=page_slug)
        return Response(data, status=status.HTTP_200_OK)
