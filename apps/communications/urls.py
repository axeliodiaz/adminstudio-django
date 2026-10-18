from django.urls import path

from .views import AudienceConditionsView, AudiencePreviewView, CommunicationsModuleView

urlpatterns = [
    path("", CommunicationsModuleView.as_view(), name="communications-module"),
    path(
        "audience/conditions/",
        AudienceConditionsView.as_view(),
        name="communications-audience-conditions",
    ),
    path(
        "audience/preview/",
        AudiencePreviewView.as_view(),
        name="communications-audience-preview",
    ),
]
