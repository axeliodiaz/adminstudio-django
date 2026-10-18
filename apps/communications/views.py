from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.communications import audience
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
                    "audience_filter": True,
                    "composer": False,
                    "click_tracking": False,
                    "sending": False,
                },
            }
        )


class AudienceConditionsView(APIView):
    """List the available audience condition types and their params (CYC-392)."""

    permission_classes = [IsAuthenticated, IsCommunicationsAdmin]

    def get(self, request, *args, **kwargs):
        conditions = [
            {
                "type": cond_type,
                "label": spec["label"],
                "description": spec["description"],
                "params": spec["params"],
            }
            for cond_type, spec in audience.CONDITIONS.items()
        ]
        return Response({"conditions": conditions, "operators": list(audience.OPERATORS)})


class AudiencePreviewView(APIView):
    """Filter action: audience count plus a sample list of people (CYC-392)."""

    permission_classes = [IsAuthenticated, IsCommunicationsAdmin]

    def post(self, request, *args, **kwargs):
        definition = request.data.get("filter")
        if definition is None:
            return Response(
                {"detail": "'filter' is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            queryset = audience.build_audience_queryset(definition)
        except audience.AudienceFilterError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        normalized = audience.validate_filter_definition(definition)
        return Response(
            {
                "count": queryset.count(),
                "sample": audience.sample_audience(queryset, request.data.get("sample_size")),
                "filter": normalized,
            }
        )
