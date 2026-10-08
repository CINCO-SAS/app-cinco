from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from apps.authentication.services.authentication_service import AuthenticationService
from apps.authentication.serializers.password_serializer import ChangePasswordRequestSerializer
from apps.security.permissions.api_permissions import IsUserOnly
from apps.security.throttling.api_throttling import PasswordChangeRateThrottle


class ChangePasswordView(APIView):
    """
    Endpoint para cambiar la contraseña del usuario autenticado.
    """
    permission_classes = [IsUserOnly]
    throttle_classes = [PasswordChangeRateThrottle]

    @extend_schema(
        summary="Cambiar contraseña",
        description=(
            "Valida la contraseña actual, aplica la política de contraseñas "
            "(mínimo 8 caracteres, mayúscula, minúscula, número y carácter "
            "especial) y revoca las sesiones de los demás dispositivos."
        ),
        request=ChangePasswordRequestSerializer,
        responses={
            200: {"success": True, "message": "Contraseña actualizada exitosamente."},
            400: {"detail": "Error de validación o contraseña incorrecta."},
            401: {"detail": "No autenticado."},
            429: {"detail": "Demasiados intentos. Intenta más tarde."},
        },
    )
    def post(self, request):
        serializer = ChangePasswordRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        current_password = serializer.validated_data["current_password"]
        new_password = serializer.validated_data["new_password"]

        try:
            result = AuthenticationService.change_password(
                user=request.user,
                current_password=current_password,
                new_password=new_password,
                # Cookie httpOnly que identifica la sesión de este dispositivo:
                # la única que se conserva activa tras el cambio.
                current_refresh_token=request.COOKIES.get("refresh_token"),
            )
            return Response(result, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
