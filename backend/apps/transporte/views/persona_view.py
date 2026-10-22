"""
PersonaViewSet — ficha de personas y móviles (B9).

Expone el único endpoint de la matriz §6 que faltaba: la **ficha del móvil**
(`GET /personas/{cedula}/ficha-movil/`), que el plan §5.1 define como
`SalidaService.buscar_movil(cedula)`.

Qué resuelve: dado una cédula, responde QUIÉN es (conductor externo,
personal de nómina o línea corporativa), qué VEHÍCULO tiene asignado y con
qué SALIDA salió hoy. En el legacy esto era la columna única `movil_sale`,
que guardaba valores de tres naturalezas distintas; aquí la cascada mapea
1:1 sobre los tres campos normalizados (`conductor`, `tecnico_asignado`,
`es_disponible`).

Contrato ADMCINCO (D-A3): la vista solo enruta; la regla vive en
`SalidaService.buscar_movil`.
"""
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.security.permissions.api_permissions import IsAuthenticatedOrAPIKey

from ..serializers import persona_serializer
from ..services import SalidaService


class PersonaViewSet(GenericViewSet):
    """Consultas de personas/móviles. Solo lectura."""

    permission_classes = [IsAuthenticatedOrAPIKey]

    # La "pk" de este recurso es la CÉDULA, no un id numérico: es lo que
    # usa el backoffice y lo que devuelve el QR/las planillas.
    lookup_field = "cedula"
    lookup_url_kwarg = "cedula"

    @extend_schema(
        responses={200: persona_serializer.FichaMovilSerializer},
        description=(
            "Ficha del móvil (B9): quién es, vehículo asignado y salida de "
            "hoy. Cascada: conductor externo → personal de nómina → línea "
            "corporativa Nokia (esa última no está disponible mientras no "
            "exista el alias `negra` en la base de datos; se informa con "
            "`nokia_disponible=false`)."
        ),
    )
    @action(detail=True, methods=["get"], url_path="ficha-movil")
    def ficha_movil(self, request, cedula=None):
        try:
            datos = SalidaService.buscar_movil(cedula)
        except ValueError as exc:
            return Response(
                {"ok": False, "error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {
                "ok": True,
                "data": persona_serializer.FichaMovilSerializer(datos).data,
            }
        )
