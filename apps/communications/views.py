from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.communications.permissions import IsCommunicationsAdmin


class CommunicationsModuleView(APIView):
    """Module shell (CYC-391): confirms the Communications module exists.

    Feature flags advertise which sub-capabilities are already wired so the
    frontend can render only what exists while the stacked tickets land.
    """

    permission_classes = [IsAuthenticated, IsCommunicationsAdmin]

    def get(self, request, *args, **kwargs):
        return Response(
            {
                "module": "communications",
                "status": "active",
                "features": {
                    "audience_filter": False,
                    "composer": False,
                    "click_tracking": False,
                    "sending": False,
                },
            }
        )
