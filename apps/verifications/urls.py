from django.urls import path

from apps.verifications.views import VerificationView

urlpatterns = [
    path("verify/", VerificationView.as_view(), name="verification"),
]
