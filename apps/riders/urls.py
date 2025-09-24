from django.urls import path

from apps.riders.views import RiderRegistrationView

urlpatterns = [
    path("register/", RiderRegistrationView.as_view(), name="rider-register"),
]
