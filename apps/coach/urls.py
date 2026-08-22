from django.urls import path

from apps.coach.views import (
    CoachClassDetailView,
    CoachClassNotesView,
    CoachClassPlaylistView,
    CoachClassRosterView,
    CoachClassStartView,
    CoachMeView,
    CoachPlaylistTemplateListView,
    CoachReservationCheckInView,
    CoachReservationNotesView,
    CoachReservationSetupView,
    CoachScheduleIcsView,
    CoachScheduleListView,
    CoachStatsView,
    CoachTodayView,
)

app_name = "coach"

urlpatterns = [
    path("me/", CoachMeView.as_view(), name="me"),
    path("today/", CoachTodayView.as_view(), name="today"),
    path("schedules/", CoachScheduleListView.as_view(), name="schedules"),
    path("schedules.ics", CoachScheduleIcsView.as_view(), name="schedules-ics"),
    path("classes/<uuid:class_id>/", CoachClassDetailView.as_view(), name="class-detail"),
    path("classes/<uuid:class_id>/roster/", CoachClassRosterView.as_view(), name="class-roster"),
    path("classes/<uuid:class_id>/start/", CoachClassStartView.as_view(), name="class-start"),
    path("classes/<uuid:class_id>/notes/", CoachClassNotesView.as_view(), name="class-notes"),
    path(
        "classes/<uuid:class_id>/playlist/",
        CoachClassPlaylistView.as_view(),
        name="class-playlist",
    ),
    path(
        "reservations/<uuid:reservation_id>/check-in/",
        CoachReservationCheckInView.as_view(),
        name="reservation-check-in",
    ),
    path(
        "reservations/<uuid:reservation_id>/notes/",
        CoachReservationNotesView.as_view(),
        name="reservation-notes",
    ),
    path(
        "reservations/<uuid:reservation_id>/setup/",
        CoachReservationSetupView.as_view(),
        name="reservation-setup",
    ),
    path("playlist-templates/", CoachPlaylistTemplateListView.as_view(), name="playlist-templates"),
    path("stats/", CoachStatsView.as_view(), name="stats"),
]
