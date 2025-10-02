"""Instructor views using DRF ViewSet."""

from rest_framework import status, viewsets
from rest_framework.response import Response

from apps.instructors.serializers import InstructorSerializer
from apps.instructors.services import (
    get_instructor_by_id,
    get_instructors_list,
    get_or_create_instructor_user,
    update_instructor,
)


class InstructorViewSet(viewsets.ViewSet):
    """Instructor ViewSet supporting create, list, retrieve, update, and partial update."""

    def create(self, request):
        serializer = InstructorSerializer(data=request.data)
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
        serializer = InstructorSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = update_instructor(pk, serializer.validated_data, partial=False)
        return Response(data, status=status.HTTP_200_OK)

    def partial_update(self, request, pk=None):
        serializer = InstructorSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = update_instructor(pk, serializer.validated_data, partial=True)
        return Response(data, status=status.HTTP_200_OK)
