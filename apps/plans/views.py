"""Views for plans app using services layer and Pydantic schemas."""

from typing import Any

from django.http import Http404
from rest_framework import status, viewsets
from rest_framework.response import Response

from apps.plans import services
from apps.plans.models import Plan


class PlanViewSet(viewsets.ViewSet):
    """List and retrieve plans leveraging the services module."""

    def list(self, request, *args: Any, **kwargs: Any) -> Response:
        schemas = services.get_plans()
        data = [s.model_dump(by_alias=True) for s in schemas]
        return Response(data, status=status.HTTP_200_OK)

    def retrieve(self, request, pk: str | None = None, *args: Any, **kwargs: Any) -> Response:
        try:
            schema = services.get_plan_by_id(pk)
        except Plan.DoesNotExist as exc:
            raise Http404 from exc
        data = schema.model_dump(by_alias=True)
        return Response(data, status=status.HTTP_200_OK)
