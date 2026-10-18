from django.urls import path

from .views import (
    AudienceConditionsView,
    AudiencePreviewView,
    CommunicationChannelsView,
    CommunicationsModuleView,
    ComposerPreviewView,
    ComposerVariablesView,
    TrackedLinkDetailView,
    TrackedLinkListCreateView,
    TrackedLinkRedirectView,
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
    path(
        "links/",
        TrackedLinkListCreateView.as_view(),
        name="communications-links",
    ),
    path(
        "links/<uuid:link_id>/",
        TrackedLinkDetailView.as_view(),
        name="communications-link-detail",
    ),
    path(
        "r/<str:token>/",
        TrackedLinkRedirectView.as_view(),
        name="communications-link-redirect",
    ),
]
