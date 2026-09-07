from django.urls import path

from apps.referrals.views import MyReferralView, ReferralAdminDashboardView, ReferralClickView

urlpatterns = [
    path("click/", ReferralClickView.as_view(), name="referral-click"),
    path("me/", MyReferralView.as_view(), name="referral-me"),
    path("admin/", ReferralAdminDashboardView.as_view(), name="referral-admin-dashboard"),
]
