from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from apps.members.models import (
    AlertPreference,
    FavoriteInstructor,
    FavoriteSpot,
    FavoriteTimeSlot,
    Member,
)
from apps.profiles.serializers import (
    AlertPreferenceSerializer,
    FavoritesSerializer,
    ProfileSerializer,
)
from apps.instructors.models import Instructor
from apps.studios.models import Room
from apps.users.services import get_user_profile, update_user_profile


class ProfileView(ViewSet):
    """
    Endpoints para obtener y actualizar el perfil del usuario autenticado.

    La lógica de negocio y persistencia vive en apps.users.services.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        """
        GET: devuelve el perfil del usuario autenticado.
        """
        user = request.user
        profile_schema = get_user_profile(user)
        return Response(profile_schema.model_dump(), status=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        """PUT/PATCH: actualiza los datos de perfil del usuario autenticado."""
        serializer = ProfileSerializer(data=request.data, partial=request.method == "PATCH")
        serializer.is_valid(raise_exception=True)
        profile_schema = update_user_profile(request.user, serializer.validated_data)
        return Response(profile_schema.model_dump(), status=status.HTTP_200_OK)


class FavoritesView(ViewSet):
    """Full-replacement favorites document for the authenticated member."""

    permission_classes = [IsAuthenticated]

    def _member(self, user):
        member, _ = Member.objects.get_or_create(user=user)
        return member

    def get(self, request, *args, **kwargs):
        member = self._member(request.user)
        return Response(
            {
                "instructor_ids": list(
                    member.favorite_instructors.values_list("instructor_id", flat=True)
                ),
                "time_slots": list(
                    member.favorite_time_slots.values("weekday", "start_hour", "end_hour")
                ),
                "spots": list(member.favorite_spots.values("room_id", "spot")),
            }
        )

    def update(self, request, *args, **kwargs):
        serializer = FavoritesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        member = self._member(request.user)
        data = serializer.validated_data
        instructor_ids = data["instructor_ids"]
        room_ids = [item["room_id"] for item in data["spots"]]
        if Instructor.objects.filter(id__in=instructor_ids).count() != len(set(instructor_ids)):
            return Response(
                {"detail": "Instructor no encontrado."}, status=status.HTTP_400_BAD_REQUEST
            )
        if Room.objects.filter(id__in=room_ids).count() != len(set(room_ids)):
            return Response({"detail": "Sala no encontrada."}, status=status.HTTP_400_BAD_REQUEST)
        FavoriteInstructor.objects.filter(member=member).delete()
        FavoriteTimeSlot.objects.filter(member=member).delete()
        FavoriteSpot.objects.filter(member=member).delete()
        FavoriteInstructor.objects.bulk_create(
            [
                FavoriteInstructor(member=member, instructor_id=value)
                for value in set(instructor_ids)
            ]
        )
        time_slots = {
            (value["weekday"], value["start_hour"], value["end_hour"]): value
            for value in data["time_slots"]
        }
        spots = {(value["room_id"], value["spot"]): value for value in data["spots"]}
        FavoriteTimeSlot.objects.bulk_create(
            [FavoriteTimeSlot(member=member, **value) for value in time_slots.values()]
        )
        FavoriteSpot.objects.bulk_create(
            [FavoriteSpot(member=member, **value) for value in spots.values()]
        )
        return self.get(request)


class AlertPreferenceView(ViewSet):
    permission_classes = [IsAuthenticated]

    def _preference(self, user):
        member, _ = Member.objects.get_or_create(user=user)
        return AlertPreference.objects.get_or_create(member=member)

    def get(self, request, *args, **kwargs):
        preference, _ = self._preference(request.user)
        return Response(
            {
                "email_enabled": preference.email_enabled,
                "quiet_hours_start": preference.quiet_hours_start,
                "quiet_hours_end": preference.quiet_hours_end,
                "timezone": "Django default timezone",
                "daily_limit": 5,
            }
        )

    def update(self, request, *args, **kwargs):
        serializer = AlertPreferenceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        preference, _ = self._preference(request.user)
        for field, value in serializer.validated_data.items():
            setattr(preference, field, value)
        preference.save()
        return self.get(request)
