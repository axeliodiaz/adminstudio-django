from django.urls import path

from .views import PeopleMemberListView, PeopleModuleView

urlpatterns = [
    path("", PeopleModuleView.as_view(), name="people-module"),
    path("members/", PeopleMemberListView.as_view(), name="people-member-list"),
]
