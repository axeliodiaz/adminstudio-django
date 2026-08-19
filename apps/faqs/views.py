"""FAQ views using DRF ViewSet."""

from pydantic import ValidationError as PydanticValidationError
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.faqs.schemas import AdminFAQItemWriteSchema, AdminSectionWriteSchema
from apps.faqs.services import (
    create_admin_faq_item,
    create_admin_section,
    get_admin_faq_item,
    get_admin_section,
    get_published_faq,
    list_admin_faq_items,
    list_admin_sections,
    update_admin_faq_item,
    update_admin_section,
)


def _pydantic_error_response(exc: PydanticValidationError) -> Response:
    first = exc.errors()[0] if exc.errors() else {}
    loc = ".".join(str(part) for part in first.get("loc", [])) or "payload"
    return Response(
        {"detail": f"{loc}: {first.get('msg', 'Datos inválidos.')}"},
        status=status.HTTP_400_BAD_REQUEST,
    )


class FAQViewSet(viewsets.ViewSet):
    """FAQ ViewSet for retrieving published FAQ items."""

    permission_classes = [AllowAny]

    def list(self, request):
        """Get all published FAQ items grouped by sections."""
        data = get_published_faq()
        return Response(data, status=status.HTTP_200_OK)


class AdminFAQSectionListView(APIView):
    """List or create FAQ sections for the PulseFit admin. Staff only."""

    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request, *args, **kwargs):
        sections = list_admin_sections(search=request.query_params.get("search"))
        return Response(sections, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        try:
            payload = AdminSectionWriteSchema.model_validate(request.data)
        except PydanticValidationError as exc:
            return _pydantic_error_response(exc)

        try:
            section = create_admin_section(data=payload.model_dump(exclude_unset=True))
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(section, status=status.HTTP_201_CREATED)


class AdminFAQSectionDetailView(APIView):
    """Retrieve or update an FAQ section for the PulseFit admin. Staff only."""

    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request, section_id, *args, **kwargs):
        return Response(get_admin_section(section_id=section_id), status=status.HTTP_200_OK)

    def patch(self, request, section_id, *args, **kwargs):
        try:
            payload = AdminSectionWriteSchema.model_validate(request.data)
        except PydanticValidationError as exc:
            return _pydantic_error_response(exc)

        try:
            section = update_admin_section(
                section_id=section_id,
                data=payload.model_dump(exclude_unset=True),
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(section, status=status.HTTP_200_OK)


class AdminFAQItemListView(APIView):
    """List or create FAQ items for the PulseFit admin. Staff only."""

    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request, *args, **kwargs):
        items = list_admin_faq_items(
            search=request.query_params.get("search"),
            section_id=request.query_params.get("section_id"),
            status=request.query_params.get("status"),
        )
        return Response(items, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        try:
            payload = AdminFAQItemWriteSchema.model_validate(request.data)
        except PydanticValidationError as exc:
            return _pydantic_error_response(exc)

        try:
            item = create_admin_faq_item(data=payload.model_dump(exclude_unset=True))
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(item, status=status.HTTP_201_CREATED)


class AdminFAQItemDetailView(APIView):
    """Retrieve or update an FAQ item for the PulseFit admin. Staff only."""

    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request, item_id, *args, **kwargs):
        return Response(get_admin_faq_item(item_id=item_id), status=status.HTTP_200_OK)

    def patch(self, request, item_id, *args, **kwargs):
        try:
            payload = AdminFAQItemWriteSchema.model_validate(request.data)
        except PydanticValidationError as exc:
            return _pydantic_error_response(exc)

        try:
            item = update_admin_faq_item(
                item_id=item_id,
                data=payload.model_dump(exclude_unset=True),
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(item, status=status.HTTP_200_OK)
