from django.urls import path

from apps.profiles.views import FavoritesView, ProfileView

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
    path(
        "favorites/",
        FavoritesView.as_view({"get": "get", "put": "update"}),
        name="profile-favorites",
    ),
]
