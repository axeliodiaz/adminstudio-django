from django.urls import path

from apps.profiles.views import ProfileView

urlpatterns = [
    path(
        "me/",
        ProfileView.as_view(
            {
                "get": "get",
                "put": "update",
                "patch": "update",
            }
        ),
        name="profile-me",
    ),
]
