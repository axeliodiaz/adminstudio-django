"""FAQ views using DRF ViewSet."""

from pydantic import ValidationError as PydanticValidationError
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny, BasePermission, IsAdminUser, IsAuthenticated
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


class IsSuperUser(BasePermission):
    """Only Django superusers."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_superuser)


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
    """List or create FAQ sections. GET: staff. POST: superuser only (CYC-120)."""

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), IsSuperUser()]
        return [IsAuthenticated(), IsAdminUser()]

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
    """Retrieve or update an FAQ section. GET: staff. PATCH: superuser only (CYC-120)."""

    def get_permissions(self):
        if self.request.method == "PATCH":
            return [IsAuthenticated(), IsSuperUser()]
        return [IsAuthenticated(), IsAdminUser()]

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
    """List or create FAQ items.

    GET: staff; non-superusers only ever see published items (CYC-120).
    POST: superuser only.
    """

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), IsSuperUser()]
        return [IsAuthenticated(), IsAdminUser()]

    def get(self, request, *args, **kwargs):
        status_filter = request.query_params.get("status")
        if not request.user.is_superuser:
            status_filter = "published"
        items = list_admin_faq_items(
            search=request.query_params.get("search"),
            section_id=request.query_params.get("section_id"),
            status=status_filter,
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
    """Retrieve or update an FAQ item.

    GET: staff; drafts are 404 for non-superusers (CYC-120).
    PATCH: superuser only.
    """

    def get_permissions(self):
        if self.request.method == "PATCH":
            return [IsAuthenticated(), IsSuperUser()]
        return [IsAuthenticated(), IsAdminUser()]

    def get(self, request, item_id, *args, **kwargs):
        item = get_admin_faq_item(item_id=item_id)
        if not request.user.is_superuser and not item.get("is_published"):
            return Response(
                {"detail": "No encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(item, status=status.HTTP_200_OK)

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
