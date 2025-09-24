from django.urls import path

from apps.verifications.views import VerificationView

urlpatterns = [
    path("verify/<uuid:verification_uuid>/", VerificationView.as_view(), name="verification"),
]
