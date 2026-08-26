"""ViewSets for studios app (list and retrieve in same class)."""

from pydantic import ValidationError as PydanticValidationError
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny, BasePermission, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.studios.schemas import (
    AdminRoomWriteSchema,
    AdminStudioWriteSchema,
    StudioSettingsWriteSchema,
)
from apps.studios.serializers import AddressSerializer, RoomSerializer, StudioSerializer
from apps.studios.services import (
    create_admin_room,
    create_admin_studio,
    get_address,
    get_admin_room,
    get_admin_studio,
    get_list_addresses,
    get_list_rooms,
    get_list_studios,
    get_room,
    get_studio,
    get_studio_settings,
    list_admin_rooms,
    list_admin_studios,
    update_admin_room,
    update_admin_studio,
    update_studio_settings,
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


class StudioViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]

    def list(self, request):
        data = StudioSerializer(get_list_studios(), many=True).data
        return Response(data, status=status.HTTP_200_OK)

    def retrieve(self, request, pk=None):
        studio = get_studio(pk)
        data = StudioSerializer(studio).data
        return Response(data, status=status.HTTP_200_OK)


class RoomViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]

    def list(self, request):
        data = RoomSerializer(get_list_rooms(), many=True).data
        return Response(data, status=status.HTTP_200_OK)

    def retrieve(self, request, pk=None):
        room = get_room(pk)
        data = RoomSerializer(room).data
        return Response(data, status=status.HTTP_200_OK)


class AddressViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]

    def list(self, request):
        data = AddressSerializer(get_list_addresses(), many=True).data
        return Response(data, status=status.HTTP_200_OK)

    def retrieve(self, request, pk=None):
        address = get_address(pk)
        data = AddressSerializer(address).data
        return Response(data, status=status.HTTP_200_OK)


class AdminStudioListView(APIView):
    """List or create studios for the PulseFit admin. Staff only."""

    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request, *args, **kwargs):
        studios = list_admin_studios(
            search=request.query_params.get("search"),
            status=request.query_params.get("status"),
        )
        return Response(studios, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        try:
            payload = AdminStudioWriteSchema.model_validate(request.data)
        except PydanticValidationError as exc:
            return _pydantic_error_response(exc)

        try:
            studio = create_admin_studio(data=payload.model_dump(exclude_unset=True))
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(studio, status=status.HTTP_201_CREATED)


class AdminStudioDetailView(APIView):
    """Retrieve or update a studio for the PulseFit admin. Staff only."""

    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request, studio_id, *args, **kwargs):
        return Response(get_admin_studio(studio_id=studio_id), status=status.HTTP_200_OK)

    def patch(self, request, studio_id, *args, **kwargs):
        try:
            payload = AdminStudioWriteSchema.model_validate(request.data)
        except PydanticValidationError as exc:
            return _pydantic_error_response(exc)

        try:
            studio = update_admin_studio(
                studio_id=studio_id,
                data=payload.model_dump(exclude_unset=True),
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(studio, status=status.HTTP_200_OK)


class AdminRoomListView(APIView):
    """List or create rooms for the PulseFit admin. Staff only."""

    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request, *args, **kwargs):
        rooms = list_admin_rooms(
            studio_id=request.query_params.get("studio_id"),
            search=request.query_params.get("search"),
        )
        return Response(rooms, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        try:
            payload = AdminRoomWriteSchema.model_validate(request.data)
        except PydanticValidationError as exc:
            return _pydantic_error_response(exc)

        try:
            room = create_admin_room(data=payload.model_dump(exclude_unset=True))
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(room, status=status.HTTP_201_CREATED)


class AdminRoomDetailView(APIView):
    """Retrieve or update a room for the PulseFit admin. Staff only."""

    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request, room_id, *args, **kwargs):
        return Response(get_admin_room(room_id=room_id), status=status.HTTP_200_OK)

    def patch(self, request, room_id, *args, **kwargs):
        try:
            payload = AdminRoomWriteSchema.model_validate(request.data)
        except PydanticValidationError as exc:
            return _pydantic_error_response(exc)

        try:
            room = update_admin_room(
                room_id=room_id,
                data=payload.model_dump(exclude_unset=True),
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(room, status=status.HTTP_200_OK)


class AdminStudioSettingsView(APIView):
    """Read/update studio policy settings. GET: staff. PATCH: superuser only."""

    def get_permissions(self):
        if self.request.method == "PATCH":
            return [IsAuthenticated(), IsSuperUser()]
        return [IsAuthenticated(), IsAdminUser()]

    def get(self, request, *args, **kwargs):
        return Response(get_studio_settings(), status=status.HTTP_200_OK)

    def patch(self, request, *args, **kwargs):
        try:
            payload = StudioSettingsWriteSchema.model_validate(request.data)
        except PydanticValidationError as exc:
            return _pydantic_error_response(exc)

        try:
            settings_data = update_studio_settings(payload.model_dump())
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(settings_data, status=status.HTTP_200_OK)
