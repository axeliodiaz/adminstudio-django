from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.wallets.admin_views import AdminPurchaseListView, AdminWalletListView
from apps.wallets.views import WalletViewSet

router = DefaultRouter()
router.register(r"", WalletViewSet, basename="wallet")

urlpatterns = [
    path("admin/wallets/", AdminWalletListView.as_view(), name="admin-wallet-list"),
    path("admin/purchases/", AdminPurchaseListView.as_view(), name="admin-purchase-list"),
    path(
        "activate-purchase/",
        WalletViewSet.as_view({"post": "activate_purchase"}),
        name="wallet-activate-purchase",
    ),
    path("", include(router.urls)),
]
