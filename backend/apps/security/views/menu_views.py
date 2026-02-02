from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.security.services.menu_service import build_menu_for_user
from apps.security.permissions.has_menu_permission import HasMenuPermission


class MenuView(APIView):
    permission_classes = [
        IsAuthenticated,
        HasMenuPermission,
    ]

    def get(self, request):
        menu = build_menu_for_user(request.user)
        return Response(menu)
