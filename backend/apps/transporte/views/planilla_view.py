"""
PlanillaViewSet — Planilla Oficial de Salida (§5.6 / S5).

Contrato ADMCINCO (D-A3) consolidado:
Endpoint único RPC-style para generar y consultar la planilla de despacho con QR y consecutivos.

Ruta registrada en urls.py:
  POST /planillas/generar/   → genera la planilla para el alcance y fecha dados.

Respuesta estandarizada:
  Éxito: { "ok": true, "data": PlanillaPayload }
  Fallo: { "ok": false, "error": "mensaje descriptivo" }
"""
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.security.permissions.api_permissions import IsAuthenticatedOrAPIKey

from ..serializers import planilla_serializer
from ..services import PlanillaService


class PlanillaViewSet(GenericViewSet):
    """Genera la Planilla Oficial de Salida para uno o varios vehículos."""

    permission_classes = [IsAuthenticatedOrAPIKey]

    @extend_schema(
        request=planilla_serializer.PlanillaInputSerializer,
        responses={200: planilla_serializer.PlanillaSerializer},
        description=(
            "Genera la Planilla Oficial de Salida consolidada (§5.6 / CR-11). "
            "Alcances: PLACA (una placa), PROPIO/EXTERNO/RENTING (por contrato), "
            "TODAS (toda la flota activa). "
            "Exclusión dura de motocicletas. "
            "El consecutivo mensual y el archivo QR se resuelven automáticamente."
        ),
    )
    @action(detail=False, methods=["post"], url_path="generar")
    def generar(self, request):
        serializer = planilla_serializer.PlanillaInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        datos = serializer.validated_data

        actor = getattr(request.user, "empleado", None)

        try:
            planilla = PlanillaService.generar_planilla(
                fecha=datos["fecha"],
                alcance=datos["alcance"],
                placa=datos.get("placa"),
                actor=actor,
            )
            return Response(
                {
                    "ok": True,
                    "data": planilla_serializer.PlanillaSerializer(planilla).data,
                },
                status=status.HTTP_200_OK,
            )
        except ValueError as exc:
            return Response(
                {"ok": False, "error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
