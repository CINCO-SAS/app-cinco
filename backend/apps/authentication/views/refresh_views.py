# apps/authentication/views/refresh_views.py
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from apps.authentication.services import rotate_refresh_token

class RefreshTokenView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        refresh_token = request.data.get("refresh_token")

        if not refresh_token:
            return Response(
                {"detail": "refresh_token is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            tokens = rotate_refresh_token(refresh_token)
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_401_UNAUTHORIZED
            )

        return Response(tokens, status=status.HTTP_200_OK)
