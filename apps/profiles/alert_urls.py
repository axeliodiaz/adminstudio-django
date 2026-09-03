from django.urls import path

from apps.profiles.views import AlertPreferenceView

urlpatterns = [
    path(
        "preferences/",
        AlertPreferenceView.as_view({"get": "get", "put": "update"}),
        name="alert-preferences",
    ),
]
