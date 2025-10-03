from rest_framework import status
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from apps.members.serializers import MemberSerializer
from apps.members.services import get_or_create_member_user


class MemberView(ViewSet):
    def create(self, request, *args, **kwargs):
        member_serializer = MemberSerializer(data=request.data)
        member_serializer.is_valid(raise_exception=True)
        member_schema, created = get_or_create_member_user(member_serializer.validated_data)
        data = member_schema.user.model_dump()
        if created:
            return Response(data, status=status.HTTP_201_CREATED)
        return Response(data, status=status.HTTP_200_OK)
