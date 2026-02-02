from django.contrib.auth import authenticate
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from apps.authentication.services import generate_access_token, rotate_refresh_token

class LoginView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")

        if not username or not password:
            return Response(
                {"detail": "Usuario y contraseña requeridos"},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = authenticate(username=username, password=password)

        if not user:
            return Response(
                {"detail": "Credenciales inválidas"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        access = generate_access_token(user)
        refresh = rotate_refresh_token(user)

        return Response({
            "access": access,
            "refresh": refresh.token,
            "user": {
                "id": user.id,
                "username": user.username,
                "is_superuser": user.is_superuser
            }
        })
