from django.urls import path

from .views import CommunicationsModuleView

urlpatterns = [
    path("", CommunicationsModuleView.as_view(), name="communications-module"),
]
