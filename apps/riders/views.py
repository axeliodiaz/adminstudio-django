from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.riders.serializers import RiderSerializer
from apps.riders.services import create_rider_user


class RiderRegistrationView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        rider_serializer = RiderSerializer(data=request.data)
        rider_serializer.is_valid(raise_exception=True)
        print(rider_serializer.validated_data)
        rider = create_rider_user(rider_serializer.validated_data)
        data = RiderSerializer(rider.user).data
        return Response(data, status=status.HTTP_201_CREATED)
