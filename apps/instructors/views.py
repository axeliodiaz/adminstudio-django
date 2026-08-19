"""Instructor views using DRF ViewSet."""

from pydantic import ValidationError as PydanticValidationError
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.instructors.schemas import AdminInstructorCreateSchema, AdminInstructorUpdateSchema
from apps.instructors.serializers import InstructorCreateSerializer, InstructorUpdateSerializer
from apps.instructors.services import (
    create_admin_instructor,
    get_admin_instructor,
    get_instructor_by_id,
    get_instructors_list,
    get_or_create_instructor_user,
    list_admin_instructors,
    update_admin_instructor,
    update_instructor,
)


class InstructorViewSet(viewsets.ViewSet):
    """Instructor ViewSet supporting create, list, retrieve, update, and partial update."""

    permission_classes = [AllowAny]

    def create(self, request):
        serializer = InstructorCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data, created = get_or_create_instructor_user(serializer.validated_data)
        status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(data, status=status_code)

    def retrieve(self, request, pk=None):
        instructor = get_instructor_by_id(pk)
        return Response(instructor, status=status.HTTP_200_OK)

    def list(self, request):
        data = get_instructors_list()
        return Response(data, status=status.HTTP_200_OK)

    def update(self, request, pk=None):
        serializer = InstructorUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = update_instructor(pk, serializer.validated_data, partial=False)
        return Response(data, status=status.HTTP_200_OK)

    def partial_update(self, request, pk=None):
        serializer = InstructorUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = update_instructor(pk, serializer.validated_data, partial=True)
        return Response(data, status=status.HTTP_200_OK)


def _pydantic_error_response(exc: PydanticValidationError):
    first = exc.errors()[0] if exc.errors() else {}
    loc = ".".join(str(part) for part in first.get("loc", [])) or "payload"
    return Response(
        {"detail": f"{loc}: {first.get('msg', 'Datos inválidos.')}"},
        status=status.HTTP_400_BAD_REQUEST,
    )


class AdminInstructorListView(APIView):
    """List or create instructors for the PulseFit admin. Staff only."""

    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request, *args, **kwargs):
        instructors = list_admin_instructors(
            search=request.query_params.get("search"),
            status=request.query_params.get("status"),
        )
        return Response(instructors, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        try:
            payload = AdminInstructorCreateSchema.model_validate(request.data)
        except PydanticValidationError as exc:
            return _pydantic_error_response(exc)

        try:
            instructor, created = create_admin_instructor(
                data=payload.model_dump(exclude_unset=True),
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            instructor,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class AdminInstructorDetailView(APIView):
    """Retrieve or update an instructor for the PulseFit admin. Staff only."""

    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request, instructor_id, *args, **kwargs):
        instructor = get_admin_instructor(instructor_id=instructor_id)
        return Response(instructor, status=status.HTTP_200_OK)

    def patch(self, request, instructor_id, *args, **kwargs):
        try:
            payload = AdminInstructorUpdateSchema.model_validate(request.data)
        except PydanticValidationError as exc:
            return _pydantic_error_response(exc)

        try:
            instructor = update_admin_instructor(
                instructor_id=instructor_id,
                data=payload.model_dump(exclude_unset=True),
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(instructor, status=status.HTTP_200_OK)
