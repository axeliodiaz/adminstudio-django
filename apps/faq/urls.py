from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.faq.views import FAQViewSet

router = DefaultRouter()
router.register(r"faq", FAQViewSet, basename="faq")

urlpatterns = [
    path("", include(router.urls)),
]
