from django.urls import path

from .views import HealthcheckView, LivenessView

urlpatterns = [
    path("live/", LivenessView.as_view(), name="healthcheck-live"),
    path("", HealthcheckView.as_view(), name="healthcheck"),
]
