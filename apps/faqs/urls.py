from django.urls import path

from apps.faqs.views import FAQViewSet

urlpatterns = [
    path("", FAQViewSet.as_view({"get": "list"}), name="faqs-list"),
]
