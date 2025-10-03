from enum import member

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.members.serializers import MemberSerializer
from apps.members.services import get_or_create_member_user


class MemberRegistrationView(APIView):

    def post(self, request, *args, **kwargs):
        member_serializer = MemberSerializer(data=request.data)
        member_serializer.is_valid(raise_exception=True)
        member, created = get_or_create_member_user(member_serializer.validated_data)
        data = MemberSerializer(member.user).data
        if created:
            return Response(data, status=status.HTTP_201_CREATED)
        return Response(data, status=status.HTTP_200_OK)
