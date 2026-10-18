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
                    "click_tracking": True,
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


class TrackedLinkListCreateView(APIView):
    """Admin: create tracked links and list them with click stats (CYC-396)."""

    permission_classes = [IsAuthenticated, IsCommunicationsAdmin]

    def get(self, request, *args, **kwargs):
        links = TrackedLink.objects.select_related("user")
        return Response(
            paginate(
                request.query_params,
                links,
                lambda link: tracking.serialize_link(link, request),
            )
        )

    def post(self, request, *args, **kwargs):
        try:
            target_url = tracking.validate_target_url(request.data.get("target_url"))
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        user = None
        user_id = request.data.get("user_id")
        if user_id:
            user = composer.get_sample_user(user_id)
            if user is None:
                return Response(
                    {"detail": "Recipient user not found."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        recipient_email = (request.data.get("recipient_email") or "").strip()
        if user is not None and not recipient_email:
            recipient_email = user.email

        link = TrackedLink.objects.create(
            target_url=target_url,
            label=(request.data.get("label") or "").strip()[:255],
            user=user,
            recipient_email=recipient_email,
            created_by=request.user,
        )
        return Response(
            tracking.serialize_link(link, request), status=status.HTTP_201_CREATED
        )


class TrackedLinkDetailView(APIView):
    """Admin: tracked link stats plus the most recent clicks (CYC-396)."""

    permission_classes = [IsAuthenticated, IsCommunicationsAdmin]

    def get(self, request, link_id, *args, **kwargs):
        link = get_object_or_404(TrackedLink, pk=link_id)
        payload = tracking.serialize_link(link, request)
        payload["recent_clicks"] = [
            {"created": click.created, "user_agent": click.user_agent}
            for click in link.clicks.all()[:10]
        ]
        return Response(payload)


class TrackedLinkRedirectView(APIView):
    """Public redirect endpoint: records the click, then redirects (CYC-396)."""

    authentication_classes = []
    permission_classes = []

    def get(self, request, token, *args, **kwargs):
        link = TrackedLink.objects.filter(token=token, is_active=True).first()
        if link is None:
            return Response(
                {"detail": "Link not found."}, status=status.HTTP_404_NOT_FOUND
            )
        tracking.record_click(link, request)
        return HttpResponseRedirect(link.target_url)
