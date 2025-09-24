"""Instructor views."""

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.instructors.serializers import InstructorSerializer
from apps.instructors.services import get_or_create_instructor_user


class InstructorRegistrationView(APIView):
    """Instructor registration view."""

    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        """Handle POST request."""
        serializer = InstructorSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instructor, created = get_or_create_instructor_user(serializer.validated_data)
        data = InstructorSerializer(instructor.user).data
        if created:
            return Response(data, status=status.HTTP_201_CREATED)
        return Response(data, status=status.HTTP_200_OK)
