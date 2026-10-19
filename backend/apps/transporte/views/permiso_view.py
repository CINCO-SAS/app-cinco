"""
PermisoViewSet — estado de permisos del usuario (E3 / CR-8).

Reemplaza las constantes JS que el PHP quemaba por cédula
(``permi_especial``/``permi_editar_fecha``/``isPerfilTransporte``/
``isProgram``). El frontend consulta ``GET /permisos/estado/`` y decide
la UI con los flags reales de PermisoService. Solo LEE.
"""
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.security.permissions.api_permissions import IsAuthenticatedOrAPIKey

from ..services import PermisoService


class PermisoViewSet(GenericViewSet):
    """Sin CRUD: única acción ``GET /permisos/estado/``."""

    permission_classes = [IsAuthenticatedOrAPIKey]

    @extend_schema(auth=[{"sessionAuth": [], "apiKeyAuth": []}], responses=dict)
    @action(detail=False, methods=["get"], url_path="estado")
    def estado(self, request):
        return Response(
            {"ok": True, "data": PermisoService.estado(request.user)}
        )
