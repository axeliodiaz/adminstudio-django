from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.communications import audience, composer
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
                    "composer": True,
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


CHANNELS = [
    {"id": "email", "label": "Email", "enabled": True},
    {
        "id": "sms",
        "label": "SMS",
        "enabled": False,
        "reason": "SMS sending is not supported yet.",
    },
    {
        "id": "whatsapp",
        "label": "WhatsApp",
        "enabled": False,
        "reason": "WhatsApp sending is not supported yet.",
    },
]


class CommunicationChannelsView(APIView):
    """Channel selector metadata: email enabled, SMS/WhatsApp disabled (CYC-394)."""

    permission_classes = [IsAuthenticated, IsCommunicationsAdmin]

    def get(self, request, *args, **kwargs):
        return Response({"channels": CHANNELS})


class ComposerVariablesView(APIView):
    """Variables available to the message composer (CYC-394)."""

    permission_classes = [IsAuthenticated, IsCommunicationsAdmin]

    def get(self, request, *args, **kwargs):
        variables = [
            {
                "key": key,
                "label": spec["label"],
                "description": spec["description"],
                "sample": spec["sample"],
            }
            for key, spec in composer.VARIABLES.items()
        ]
        return Response({"variables": variables})


class ComposerPreviewView(APIView):
    """Render subject/message with variables resolved for a sample user."""

    permission_classes = [IsAuthenticated, IsCommunicationsAdmin]

    def post(self, request, *args, **kwargs):
        subject = request.data.get("subject") or ""
        message = request.data.get("message") or ""
        if not message.strip():
            return Response(
                {"detail": "'message' is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        unknown = composer.find_unknown_variables(subject, message)
        if unknown:
            return Response(
                {
                    "detail": f"Unknown variables: {', '.join(unknown)}.",
                    "unknown_variables": unknown,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        sample_user = None
        sample_user_id = request.data.get("sample_user_id")
        if sample_user_id:
            sample_user = composer.get_sample_user(sample_user_id)
            if sample_user is None:
                return Response(
                    {"detail": "Sample user not found."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        payload = {
            "subject": composer.render_template(subject, sample_user),
            "message": composer.render_template(message, sample_user),
            "sample_user": None,
        }
        if sample_user is not None:
            payload["sample_user"] = {
                "id": str(sample_user.id),
                "name": composer._display_name(sample_user),
                "email": sample_user.email,
            }
        return Response(payload)
