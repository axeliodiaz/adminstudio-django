from django.urls import path

from apps.instructors.views import InstructorRegistrationView

urlpatterns = [
    path("register/", InstructorRegistrationView.as_view(), name="instructor-register"),
]
