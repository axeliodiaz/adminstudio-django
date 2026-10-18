from django.urls import path

from .views import (
    AudienceConditionsView,
    AudiencePreviewView,
    CommunicationChannelsView,
    CommunicationsModuleView,
    ComposerPreviewView,
    ComposerVariablesView,
)

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
    path(
        "channels/",
        CommunicationChannelsView.as_view(),
        name="communications-channels",
    ),
    path(
        "composer/variables/",
        ComposerVariablesView.as_view(),
        name="communications-composer-variables",
    ),
    path(
        "composer/preview/",
        ComposerPreviewView.as_view(),
        name="communications-composer-preview",
    ),
]
