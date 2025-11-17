from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.wallets.views import WalletViewSet

router = DefaultRouter()
router.register(r"", WalletViewSet, basename="wallet")

urlpatterns = [
    path(
        "activate-purchase/",
        WalletViewSet.as_view({"post": "activate_purchase"}),
        name="wallet-activate-purchase",
    ),
    path("", include(router.urls)),
]
