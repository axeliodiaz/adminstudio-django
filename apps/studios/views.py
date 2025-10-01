"""ViewSets for studios app (list and retrieve in same class)."""

from rest_framework import status, viewsets
from rest_framework.response import Response

from apps.studios.serializers import RoomSerializer, StudioSerializer
from apps.studios.services import get_list_rooms, get_list_studios, get_room, get_studio


class StudioViewSet(viewsets.ViewSet):
    def list(self, request):
        data = StudioSerializer(get_list_studios(), many=True).data
        return Response(data, status=status.HTTP_200_OK)

    def retrieve(self, request, pk=None):
        studio = get_studio(pk)
        data = StudioSerializer(studio).data
        return Response(data, status=status.HTTP_200_OK)


class RoomViewSet(viewsets.ViewSet):
    def list(self, request):
        data = RoomSerializer(get_list_rooms(), many=True).data
        return Response(data, status=status.HTTP_200_OK)

    def retrieve(self, request, pk=None):
        room = get_room(pk)
        data = RoomSerializer(room).data
        return Response(data, status=status.HTTP_200_OK)
