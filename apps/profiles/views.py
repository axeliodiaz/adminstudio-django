from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from apps.profiles.serializers import ProfileSerializer
from apps.users.services import get_user_profile, update_user_profile


class ProfileView(ViewSet):
    """
    Endpoints para obtener y actualizar el perfil del usuario autenticado.

    La lógica de negocio y persistencia vive en apps.users.services.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        """
        GET: devuelve el perfil del usuario autenticado.
        """
        user = request.user
        profile_schema = get_user_profile(user)
        return Response(profile_schema.model_dump(), status=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        """
        PUT/PATCH: actualiza los datos de perfil del usuario autenticado.
        """
        user = request.user
        serializer = ProfileSerializer(data=request.data, partial=request.method == "PATCH")
        serializer.is_valid(raise_exception=True)
        profile_schema = update_user_profile(user, serializer.validated_data)
        return Response(profile_schema.model_dump(), status=status.HTTP_200_OK)
