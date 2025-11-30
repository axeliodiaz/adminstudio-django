"""FAQ views using DRF ViewSet."""

from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.faq.services import get_published_faq


class FAQViewSet(viewsets.ViewSet):
    """FAQ ViewSet for retrieving published FAQ items."""

    permission_classes = [AllowAny]

    def list(self, request):
        """Get all published FAQ items grouped by sections."""
        data = get_published_faq()
        return Response(data, status=status.HTTP_200_OK)
