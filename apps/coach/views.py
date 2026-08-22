from django.http import HttpResponse
from pydantic import TypeAdapter, ValidationError as PydanticValidationError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.coach.exceptions import CoachClassNotFound, CoachReservationNotFound
from apps.coach.permissions import IsCoach
from apps.coach.schemas import (
    CheckInSchema,
    ClassNotesSchema,
    ClassPlaylistOutSchema,
    CoachClassSchema,
    CoachProfileSchema,
    CoachProfileUpdateSchema,
    CoachStatsSchema,
    PlaylistTemplateSchema,
    PlaylistUpdateSchema,
    ReservationNotesUpdateSchema,
    RiderNotesSchema,
    RiderSchema,
    RiderSetupUpdateSchema,
    RosterSchema,
    TodaySchema,
)
from apps.coach.services import (
    build_ics,
    check_in_reservation,
    get_class,
    get_class_notes,
    get_coach_profile,
    get_instructor_for_user,
    get_playlist,
    get_roster,
    get_stats,
    get_today,
    list_playlist_templates,
    list_schedules,
    start_class,
    update_coach_profile,
    update_reservation_notes,
    update_rider_setup,
    upsert_playlist,
)


def _pydantic_error_response(exc: PydanticValidationError):
    first = exc.errors()[0] if exc.errors() else {}
    loc = ".".join(str(part) for part in first.get("loc", [])) or "payload"
    return Response(
        {"detail": f"{loc}: {first.get('msg', 'Datos inválidos.')}"},
        status=status.HTTP_400_BAD_REQUEST,
    )


def _not_found(exc: Exception):
    return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)


def _dump(schema, data, **kwargs):
    return schema.model_validate(data).model_dump(mode="json", **kwargs)


class CoachMeView(APIView):
    permission_classes = [IsAuthenticated, IsCoach]

    def get(self, request, *args, **kwargs):
        instructor = get_instructor_for_user(request.user)
        return Response(_dump(CoachProfileSchema, get_coach_profile(instructor)))

    def patch(self, request, *args, **kwargs):
        try:
            payload = CoachProfileUpdateSchema.model_validate(request.data)
        except PydanticValidationError as exc:
            return _pydantic_error_response(exc)
        instructor = get_instructor_for_user(request.user)
        return Response(
            _dump(
                CoachProfileSchema,
                update_coach_profile(instructor, payload.model_dump(exclude_unset=True)),
            )
        )


class CoachTodayView(APIView):
    permission_classes = [IsAuthenticated, IsCoach]

    def get(self, request, *args, **kwargs):
        instructor = get_instructor_for_user(request.user)
        return Response(_dump(TodaySchema, get_today(instructor, request.query_params.get("date"))))


class CoachScheduleListView(APIView):
    permission_classes = [IsAuthenticated, IsCoach]

    def get(self, request, *args, **kwargs):
        instructor = get_instructor_for_user(request.user)
        return Response(
            [
                CoachClassSchema.model_validate(item).model_dump(mode="json", exclude_none=True)
                for item in list_schedules(
                    instructor,
                    request.query_params.get("from"),
                    request.query_params.get("to"),
                )
            ]
        )


class CoachScheduleIcsView(APIView):
    permission_classes = [IsAuthenticated, IsCoach]

    def get(self, request, *args, **kwargs):
        instructor = get_instructor_for_user(request.user)
        body = build_ics(
            instructor,
            request.query_params.get("from"),
            request.query_params.get("to"),
        )
        response = HttpResponse(body, content_type="text/calendar; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="pulsefit-coach.ics"'
        return response


class CoachClassDetailView(APIView):
    permission_classes = [IsAuthenticated, IsCoach]

    def get(self, request, class_id, *args, **kwargs):
        instructor = get_instructor_for_user(request.user)
        try:
            return Response(_dump(CoachClassSchema, get_class(instructor, class_id)))
        except CoachClassNotFound as exc:
            return _not_found(exc)


class CoachClassRosterView(APIView):
    permission_classes = [IsAuthenticated, IsCoach]

    def get(self, request, class_id, *args, **kwargs):
        instructor = get_instructor_for_user(request.user)
        try:
            return Response(_dump(RosterSchema, get_roster(instructor, class_id), by_alias=True))
        except CoachClassNotFound as exc:
            return _not_found(exc)


class CoachClassStartView(APIView):
    permission_classes = [IsAuthenticated, IsCoach]

    def post(self, request, class_id, *args, **kwargs):
        instructor = get_instructor_for_user(request.user)
        try:
            return Response(start_class(instructor, class_id))
        except CoachClassNotFound as exc:
            return _not_found(exc)


class CoachClassNotesView(APIView):
    permission_classes = [IsAuthenticated, IsCoach]

    def get(self, request, class_id, *args, **kwargs):
        instructor = get_instructor_for_user(request.user)
        try:
            return Response(
                _dump(ClassNotesSchema, get_class_notes(instructor, class_id), by_alias=True)
            )
        except CoachClassNotFound as exc:
            return _not_found(exc)


class CoachClassPlaylistView(APIView):
    permission_classes = [IsAuthenticated, IsCoach]

    def get(self, request, class_id, *args, **kwargs):
        instructor = get_instructor_for_user(request.user)
        try:
            return Response(_dump(ClassPlaylistOutSchema, get_playlist(instructor, class_id)))
        except CoachClassNotFound as exc:
            return _not_found(exc)

    def patch(self, request, class_id, *args, **kwargs):
        try:
            payload = PlaylistUpdateSchema.model_validate(request.data)
        except PydanticValidationError as exc:
            return _pydantic_error_response(exc)
        instructor = get_instructor_for_user(request.user)
        try:
            return Response(
                _dump(
                    ClassPlaylistOutSchema,
                    upsert_playlist(instructor, class_id, payload.model_dump()),
                ),
            )
        except CoachClassNotFound as exc:
            return _not_found(exc)


class CoachReservationCheckInView(APIView):
    permission_classes = [IsAuthenticated, IsCoach]

    def patch(self, request, reservation_id, *args, **kwargs):
        try:
            payload = CheckInSchema.model_validate(request.data)
        except PydanticValidationError as exc:
            return _pydantic_error_response(exc)
        instructor = get_instructor_for_user(request.user)
        try:
            return Response(
                _dump(
                    RiderSchema,
                    check_in_reservation(instructor, reservation_id, payload.checked_in),
                ),
            )
        except CoachReservationNotFound as exc:
            return _not_found(exc)


class CoachReservationNotesView(APIView):
    permission_classes = [IsAuthenticated, IsCoach]

    def patch(self, request, reservation_id, *args, **kwargs):
        try:
            payload = ReservationNotesUpdateSchema.model_validate(request.data)
        except PydanticValidationError as exc:
            return _pydantic_error_response(exc)
        instructor = get_instructor_for_user(request.user)
        try:
            return Response(
                _dump(
                    RiderNotesSchema,
                    update_reservation_notes(instructor, reservation_id, payload.notes),
                )
            )
        except CoachReservationNotFound as exc:
            return _not_found(exc)


class CoachReservationSetupView(APIView):
    permission_classes = [IsAuthenticated, IsCoach]

    def patch(self, request, reservation_id, *args, **kwargs):
        try:
            payload = RiderSetupUpdateSchema.model_validate(request.data)
        except PydanticValidationError as exc:
            return _pydantic_error_response(exc)
        instructor = get_instructor_for_user(request.user)
        try:
            return Response(
                _dump(
                    RiderNotesSchema,
                    update_rider_setup(
                        instructor,
                        reservation_id,
                        payload.model_dump(exclude_unset=True),
                    ),
                )
            )
        except CoachReservationNotFound as exc:
            return _not_found(exc)


class CoachPlaylistTemplateListView(APIView):
    permission_classes = [IsAuthenticated, IsCoach]

    def get(self, request, *args, **kwargs):
        instructor = get_instructor_for_user(request.user)
        return Response(
            TypeAdapter(list[PlaylistTemplateSchema]).dump_python(
                list_playlist_templates(instructor), mode="json"
            )
        )


class CoachStatsView(APIView):
    permission_classes = [IsAuthenticated, IsCoach]

    def get(self, request, *args, **kwargs):
        instructor = get_instructor_for_user(request.user)
        try:
            months = int(request.query_params.get("months") or 6)
        except (TypeError, ValueError):
            months = 6
        return Response(_dump(CoachStatsSchema, get_stats(instructor, months=months)))
